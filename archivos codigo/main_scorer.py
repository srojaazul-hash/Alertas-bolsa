#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main_scorer.py — Sistema de Alerta Temprana de Riesgo de Suministro: Cobalto
Version: 1.0 | Referencia: scoring_rules.md v1.0, keyword_dictionary.md v1.0,
                            asset_map.md v1.0, data_sources.md v1.0

Ejecutar: python3 main_scorer.py
Cron:     0 0,8,16 * * * /usr/bin/python3 /home/usuario/cobalt-alert/main_scorer.py
"""

import os
import re
import json
import time
import logging
import hashlib
import smtplib
import unicodedata
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

try:
    from google import genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

# ---------------------------------------------------------------------------
# 0. PATHS Y CONFIGURACION
# ---------------------------------------------------------------------------

BASE_DIR = Path.home() / "cobalt-alert"
ENV_FILE = BASE_DIR / ".env"
STATE_FILE = BASE_DIR / "state.json"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "scorer.log"

BASE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. LOGGING
# ---------------------------------------------------------------------------

log = logging.getLogger("cobalt_scorer")
log.setLevel(logging.INFO)

_file_handler = TimedRotatingFileHandler(
    LOG_FILE, when="midnight", interval=1, backupCount=7, encoding="utf-8"
)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%dT%H:%M:%SZ")
)
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(logging.Formatter("%(levelname)-8s %(message)s"))
log.addHandler(_file_handler)
log.addHandler(_console_handler)

# ---------------------------------------------------------------------------
# 2. CARGA DE CREDENCIALES DESDE .env
# ---------------------------------------------------------------------------

def load_env(path: Path) -> dict:
    """Lee pares KEY=VALUE de un archivo .env; ignora comentarios y líneas vacías."""
    env = {}
    if not path.exists():
        log.warning(".env no encontrado en %s — email desactivado", path)
        return env
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env

ENV = load_env(ENV_FILE)

SMTP_HOST = ENV.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(ENV.get("SMTP_PORT", "587"))
SMTP_USER = ENV.get("SMTP_USER", "")
SMTP_PASS = ENV.get("SMTP_PASS", "")
ALERT_TO   = ENV.get("ALERT_TO", SMTP_USER)
ACLED_KEY  = ENV.get("ACLED_KEY", "")
ACLED_EMAIL = ENV.get("ACLED_EMAIL", "")
BOT_EMAIL  = ENV.get("BOT_EMAIL", SMTP_USER)   # para User-Agent
GEMINI_API_KEY = ENV.get("GEMINI_API_KEY", "")

REQUEST_HEADERS = {
    "User-Agent": f"CobaltSupplyMonitor/1.0 (research bot; contact: {BOT_EMAIL})",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8,pt;q=0.7,es;q=0.6",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "close",
}

# ---------------------------------------------------------------------------
# 3. ESTADO PERSISTENTE
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception as exc:
            log.warning("No se pudo leer state.json: %s — iniciando estado limpio", exc)
    return {
        "last_run": None,
        "processed_urls": [],
        "active_events": [],
        "source_health": {},
        "score_history": [],
        "run_count_today": 0,
        "last_run_date": None,
    }

def save_state(state: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("No se pudo guardar state.json: %s", exc)

def purge_old_urls(state: dict, hours: int = 72):
    """Elimina URLs procesadas con más de `hours` horas de antigüedad."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    kept = [
        entry for entry in state.get("processed_urls", [])
        if datetime.fromisoformat(entry["ts"]) > cutoff
    ]
    state["processed_urls"] = kept

def mark_url_processed(state: dict, url: str):
    state.setdefault("processed_urls", []).append(
        {"url": url, "ts": datetime.now(timezone.utc).isoformat()}
    )

def is_url_processed(state: dict, url: str) -> bool:
    return any(e["url"] == url for e in state.get("processed_urls", []))

def update_source_health(state: dict, source_name: str, success: bool):
    health = state.setdefault("source_health", {})
    entry = health.setdefault(source_name, {"consecutive_failures": 0, "status": "OK"})
    if success:
        entry["consecutive_failures"] = 0
        entry["status"] = "OK"
        entry["last_success"] = datetime.now(timezone.utc).isoformat()
    else:
        entry["consecutive_failures"] = entry.get("consecutive_failures", 0) + 1
        if entry["consecutive_failures"] >= 3:
            entry["status"] = "DEGRADED"
            log.warning("Fuente DEGRADED: %s (%d fallos consecutivos)", source_name, entry["consecutive_failures"])

def is_source_degraded(state: dict, source_name: str) -> bool:
    return state.get("source_health", {}).get(source_name, {}).get("status") == "DEGRADED"

# ---------------------------------------------------------------------------
# 4. UTILIDADES DE TEXTO
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Convierte a lowercase y elimina diacríticos para comparación."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))

def simple_similarity(s1: str, s2: str) -> float:
    """Palabras en común / palabras totales (sin librerías pesadas)."""
    w1 = set(s1.lower().split())
    w2 = set(s2.lower().split())
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / max(len(w1), len(w2))

# ---------------------------------------------------------------------------
# 5. DICCIONARIO: ANCLAS, GEOGRAFÍAS Y KEYWORDS
# ---------------------------------------------------------------------------

ANCHOR_TERMS = [
    "cobalt", "cobalt ore", "cobalt hydroxide", "cobalt sulfate",
    "cobalt carbonate", "cobalt metal", "cobalt refining",
    "battery-grade cobalt", "cobalt supply", "cobalt market",
    "cobalt mining", "cobalt production", "cobalt export",
    "cobalt price", "cobalt demand", "critical mineral",
    "critical metals", "battery metals", "ev battery supply",
    # FR
    "minerai de cobalt", "hydroxyde de cobalt", "sulfate de cobalt",
    "raffinage du cobalt", "cobalt brut", "production de cobalt",
    "exportation de cobalt", "minerais critiques", "metaux de batterie",
    # PT
    "cobalto", "minerio de cobalto", "hidroxido de cobalto",
    "sulfato de cobalto", "refinacao de cobalto",
    "producao de cobalto", "exportacao de cobalto",
    "minerais criticos", "metais para baterias",
    # ES
    "mineral de cobalto", "hidroxido de cobalto",
    "sulfato de cobalto", "refinacion de cobalto",
    "produccion de cobalto", "exportacion de cobalto",
    "minerales criticos", "metales para baterias",
]

# Mapa geo_code -> lista de términos normalizados
GEOGRAPHIC_TERMS = {
    "GEO-01": [
        "democratic republic of congo", "drc", "congo kinshasa",
        "katanga", "lualaba", "haut-katanga", "kolwezi", "likasi",
        "lubumbashi", "fungurume", "tenke fungurume", "mutanda",
        "boss mining", "kamoto", "kamoa-kakula",
        # CMOC operations in DRC (Tenke Fungurume + Kisanfu)
        "cmoc", "kisanfu", "kfm mine",
        # Este de DRC — zonas de conflicto M23 / ADF (relevantes para GEO-CONFLICT)
        "north kivu", "south kivu", "nord-kivu", "sud-kivu",
        "goma", "bukavu", "ituri", "beni", "butembo",
        "copperbelt", "copper belt", "central african copperbelt",
        "republique democratique du congo", "rdc",
        "ceinture cuivriere", "province du lualaba",
        "republica democratica do congo",
        "republica democratica del congo", "cinturon cuprifero",
    ],
    "GEO-02": [
        "zambia", "zambian copperbelt", "ndola", "kitwe",
        "chingola", "mufulira", "chambishi", "nchanga",
        "konkola", "lumwana", "first quantum zambia",
        "mopani copper mines", "vedanta zambia",
        "zambie", "copperbelt zambiano",
    ],
    "GEO-03A": [
        # Corredor Este africano — Tanzania + Kenya (TAZARA, Central Corridor, Northern Corridor)
        "tanzania", "dar es salaam", "tpa", "tanzania ports authority",
        "central corridor", "tazara", "tazara railway",
        "northern corridor", "mombasa", "kenya",
        "east african corridor", "corredor central",
        "africa oriental",
    ],
    "GEO-03B": [
        # Corredor Sureste africano — Mozambique (Beira + Nacala corridors)
        "mozambique", "beira", "beira corridor", "nacala",
        "nacala corridor", "cfm", "porto de beira", "porto de nacala",
        "corridor de beira", "corredor de beira",
        "corredor de nacala",
    ],
    "GEO-04": [
        "south africa", "durban", "port of durban",
        "transnet", "transnet freight rail",
        "zimbabwe", "beitbridge",
        "southern african corridor", "southern corridor",
        "botswana", "maputo corridor", "maputo port",
        "richards bay",
        "afrique du sud", "corridor sud",
        "africa do sul", "porto de durban", "corredor sul",
        "sudafrica", "zimbabue", "corredor de maputo",
    ],
    "GEO-05": [
        "australia", "western australia", "murrin murrin",
        "nickel west", "cobalt blue holdings",
        "australian cobalt", "queensland cobalt",
        "australie", "australia occidental",
    ],
    "GEO-06": [
        "philippines", "palawan", "rio tuba", "coral bay",
        "taganito", "philippine nickel", "philippine cobalt",
        "mindanao mining", "filipinas",
    ],
    "GEO-07": [
        # Solo términos de localización/entidad (los eventos los detectan los KEYWORDS)
        "china cobalt refining", "chinese cobalt",
        "zhejiang cobalt", "guangdong cobalt", "huayou cobalt",
        "gem co", "ganzhou cobalt", "jiangxi cobalt",
        "chinese battery supply chain", "china battery metals",
        "chine cobalt", "raffinage chinois",
        "china cobalto", "refinacion china",
    ],
    "GEO-08": [
        "port of durban", "durban port", "durban harbour",
        "dar es salaam port", "tpa port", "port of dar es salaam",
        "beira port", "porto de beira", "port of beira",
        "nacala port", "port of nacala",
        "mombasa port", "port of mombasa",
        "lobito corridor", "lobito port", "angola port",
        "benguela railway", "lobito atlantic terminal",
        "port de durban", "port de dar es salaam",
        "port de beira", "puerto de durban",
        "puerto de dar es salaam", "puerto de beira",
        "corredor de lobito",
    ],
    "GEO-10": [
        # Indonesia — productor en alza de cobalto vía níquel laterítico (Sulawesi)
        "indonesia", "sulawesi", "morowali", "imip",
        "indonesia morowali industrial park", "weda bay",
        "iwip", "halmahera",
        "vale indonesia", "ptvi", "huayou indonesia",
        "tsingshan", "harita nickel", "indonesian nickel cobalt",
        "high pressure acid leach", "hpal",
        "indonesien", "indonesie",
    ],
    "GEO-11": [
        # Refino europeo — alternativa estructural a China (afecta más a SMC)
        "umicore", "umicore belgium", "kokkola refinery",
        "nornickel finland", "harjavalta", "terrafame",
        "glencore nikkelverk", "kristiansand refinery",
        "european cobalt refining", "european battery alliance",
        "belgium cobalt", "finland cobalt", "norway cobalt",
        "raffinage europeen", "raffinerie europe",
        "refinacion europea",
    ],
}

GEO_WEIGHTS = {
    "GEO-01": 1.80, "GEO-02": 1.20,
    "GEO-03A": 1.40, "GEO-03B": 1.40,
    "GEO-04": 1.30, "GEO-05": 0.90, "GEO-06": 0.80,
    "GEO-07": 1.60, "GEO-08": 1.50,
    "GEO-10": 1.10, "GEO-11": 0.80,
}

CATEGORY_MULTIPLIERS = {
    # LOG
    "LOG-PORT": 2.0, "LOG-RAIL": 1.8, "LOG-ROAD": 1.5,
    "LOG-CUSTOMS": 1.7, "LOG-FLOOD": 1.6, "LOG-VESSEL": 1.3,
    # GEO
    "GEO-CONFLICT": 2.2, "GEO-COUP": 2.0, "GEO-SANCTION": 1.9,
    "GEO-PROTEST": 1.4, "GEO-ELECTION": 0.8, "GEO-DIPLO": 1.2,
    # LAB
    "LAB-STRIKE-ACT": 2.1, "LAB-STRIKE-THR": 1.5,
    "LAB-STRIKE-NEG": 0.9, "LAB-ACCIDENT": 1.8, "LAB-PROTEST": 1.1,
    # REG
    "REG-EXPORT-BAN": 2.3, "REG-TAX": 1.6, "REG-LICENSE": 1.9,
    "REG-ENV": 1.7, "REG-NATIONAL": 1.8, "REG-TARIFF": 1.4,
    # DEM
    "DEM-SURGE": 1.5, "DEM-DROP": -1.3,
    "DEM-STOCK": 1.2, "DEM-SUBSTITUTE": -1.5,
    # FMA
    "FMA-FLOOD": 1.7, "FMA-DROUGHT": 1.4,
    "FMA-SEISMIC": 1.3, "FMA-DISEASE": 1.5,
    # RES
    "RES-RESOLVE": 1.5,
}

# SSC category weights (multiplicador sobre score bruto para horizonte corto)
SSC_CATEGORY_WEIGHTS = {
    "LOG-PORT": 1.0, "LOG-RAIL": 1.0, "LOG-ROAD": 1.0,
    "LOG-CUSTOMS": 1.0, "LOG-FLOOD": 1.0, "LOG-VESSEL": 1.0,
    "LAB-STRIKE-ACT": 1.0, "LAB-ACCIDENT": 1.0,
    "GEO-CONFLICT": 1.0, "GEO-COUP": 1.0,
    "REG-EXPORT-BAN": 1.0, "REG-LICENSE": 1.0,
    "FMA-FLOOD": 1.0, "FMA-DROUGHT": 1.0,
    "FMA-SEISMIC": 1.0, "FMA-DISEASE": 1.0,
    "LAB-STRIKE-THR": 0.6,
    "GEO-PROTEST": 0.4, "GEO-ELECTION": 0.4,
    # Not included in SSC: DEM-SUBSTITUTE -> 0
    "DEM-SUBSTITUTE": 0.0,
    # RES-RESOLVE: resolutions reduce score inmediato
    "RES-RESOLVE": 1.0,
    # Others default to 0.4 (reduced weight)
}

# SMC category multipliers (override sobre el valor base)
SMC_CATEGORY_OVERRIDES = {
    "GEO-ELECTION": 1.2,  # More weight in macro
    "REG-EXPORT-BAN": 1.2, "REG-TAX": 1.2,
    "REG-LICENSE": 1.2, "REG-ENV": 1.2,
    "REG-NATIONAL": 1.2, "REG-TARIFF": 1.2,
    # DEM-SUBSTITUTE puntua en SMC con signo negativo
    "DEM-SUBSTITUTE": 1.0,
    # RES-RESOLVE: menor impacto en macro (la tension estructural persiste)
    "RES-RESOLVE": 0.5,
}

NEGATION_TERMS = {
    "en": ["no", "not", "never", "ended", "resolved", "cancelled", "avoided",
           "prevented", "denied", "resumed", "lifted", "withdrawn", "rejected"],
    "fr": ["non", "pas", "jamais", "termine", "resolu", "annule", "evite",
           "empeche", "nie", "repris", "leve", "retire"],
    "pt": ["nao", "nunca", "terminado", "resolvido", "cancelado", "evitado",
           "impedido", "negado", "retomado", "levantado", "retirado"],
    "es": ["no", "nunca", "terminado", "resuelto", "cancelado", "evitado",
           "impedido", "negado", "reanudado", "levantado", "retirado"],
}
ALL_NEGATION_TERMS = set()
for terms in NEGATION_TERMS.values():
    ALL_NEGATION_TERMS.update(terms)

# Términos geo/políticos que deben aparecer cerca de "coup" para que puntúe.
# Sin al menos uno de ellos en ventana ±40 palabras, score = 0.
COUP_CONTEXT_TERMS = [
    "drc", "congo", "zambia", "africa", "katanga", "lualaba",
    "government", "military", "president", "junta",
]

FALSE_POSITIVE_FILTERS = {
    "LAB-STRIKE-ACT": ["bowling strike", "lightning strike", "airstrike",
                        "air strike", "hunger strike"],
    "GEO-COUP": ["coup de grace", "coup de theatre", "hat trick",
                  "coup de main"],
    "FMA-FLOOD": ["market flooding", "flooding the market",
                   "flood of orders", "flood of investment"],
    "GEO-SANCTION": ["academic sanction", "sports sanction",
                      "sanctioned move"],
    "LAB-ACCIDENT": ["market collapse", "price collapse",
                      "currency collapse", "economic collapse"],
}

# Gemini analysis thresholds
GEMINI_SCORE_THRESHOLD = 8.0   # Path A: max score_bruto que activa validación YES/NO
GEMINI_CONTEXT_MIN     = 3     # Path B: mínimo de context keywords para activar multiplicador

# Términos de contexto débiles: individualmente no puntúan,
# pero ≥ GEMINI_CONTEXT_MIN juntos en un artículo indican relevancia potencial
CONTEXT_TRIGGER_TERMS = [
    "supply chain", "critical mineral", "battery supply", "processing capacity",
    "export control", "refinery", "smelter", "feedstock", "offtake agreement",
    "artisanal mining", "upstream", "downstream processing", "mineral processing",
    "strategic reserve", "battery metals", "ev supply", "cathode material",
    "precursor", "hydrometallurgy", "concentrate shipment", "raw material supply",
    "chaîne d'approvisionnement", "minerai critique", "traitement mineral",
    "cadena de suministro", "mineral critico", "procesamiento mineral",
]

# ---------------------------------------------------------------------------
# 6. KEYWORD ENTRIES
# ---------------------------------------------------------------------------
# Cada entrada: (term, category, weight, requires_context, context_window, geo_boost)

KEYWORDS = [
    # --- LOG-PORT ---
    ("port closure",              "LOG-PORT", 4.5, False, 50,  ["GEO-08","GEO-03A","GEO-03B","GEO-04"]),
    ("port congestion",           "LOG-PORT", 3.5, False, 50,  ["GEO-08"]),
    ("port strike",               "LOG-PORT", 4.2, False, 50,  ["GEO-08"]),
    ("dock workers strike",       "LOG-PORT", 4.2, False, 50,  ["GEO-08"]),
    ("stevedores strike",         "LOG-PORT", 4.0, False, 50,  ["GEO-08"]),
    ("port backlog",              "LOG-PORT", 3.2, True,  80,  ["GEO-08"]),
    ("vessel queuing",            "LOG-PORT", 3.0, True,  80,  ["GEO-08"]),
    ("port shutdown",             "LOG-PORT", 4.5, False, 50,  ["GEO-08"]),
    ("terminal closure",          "LOG-PORT", 4.0, False, 50,  ["GEO-08"]),
    ("fermeture du port",         "LOG-PORT", 4.5, False, 50,  ["GEO-08"]),
    ("greve portuaire",           "LOG-PORT", 4.2, False, 50,  ["GEO-08"]),
    ("congestion portuaire",      "LOG-PORT", 3.5, False, 50,  ["GEO-08"]),
    ("bloqueio portuario",        "LOG-PORT", 4.2, False, 50,  ["GEO-08"]),
    ("encerramento do porto",     "LOG-PORT", 4.5, False, 50,  ["GEO-08"]),
    ("greve portuaria",           "LOG-PORT", 4.2, False, 50,  ["GEO-08"]),
    ("cierre portuario",          "LOG-PORT", 4.5, False, 50,  ["GEO-08"]),
    ("huelga portuaria",          "LOG-PORT", 4.2, False, 50,  ["GEO-08"]),
    ("congestion portuaria",      "LOG-PORT", 3.5, False, 50,  ["GEO-08"]),

    # --- LOG-RAIL ---
    ("railway disruption",        "LOG-RAIL", 3.8, False, 50,  ["GEO-03A","GEO-03B","GEO-04","GEO-08"]),
    ("rail shutdown",             "LOG-RAIL", 4.0, False, 50,  ["GEO-03A","GEO-03B","GEO-04"]),
    ("freight rail suspension",   "LOG-RAIL", 3.8, False, 50,  ["GEO-04"]),
    ("rail sabotage",             "LOG-RAIL", 4.5, False, 50,  ["GEO-04"]),
    ("cable theft railway",       "LOG-RAIL", 3.5, False, 50,  ["GEO-04"]),
    ("derailment",                "LOG-RAIL", 3.2, True,  80,  ["GEO-03A","GEO-03B","GEO-04"]),
    ("perturbation ferroviaire",  "LOG-RAIL", 3.8, False, 50,  ["GEO-03A","GEO-03B","GEO-04"]),
    ("interruption du chemin de fer","LOG-RAIL",4.0, False, 50, ["GEO-03A","GEO-03B","GEO-04"]),
    ("sabotagem ferroviaria",     "LOG-RAIL", 4.5, False, 50,  ["GEO-04"]),
    ("interrupcao ferroviaria",   "LOG-RAIL", 3.8, False, 50,  ["GEO-03A","GEO-03B","GEO-04"]),
    ("interrupcion ferroviaria",  "LOG-RAIL", 3.8, False, 50,  ["GEO-03A","GEO-03B","GEO-04"]),
    ("sabotaje ferroviario",      "LOG-RAIL", 4.5, False, 50,  ["GEO-04"]),

    # --- LOG-ROAD ---
    ("road blockade",             "LOG-ROAD", 3.2, True,  60,  ["GEO-01","GEO-02","GEO-03A","GEO-03B"]),
    ("border crossing closed",    "LOG-ROAD", 3.5, False, 50,  ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("border blockage",           "LOG-ROAD", 3.5, False, 50,  ["GEO-01","GEO-02"]),
    ("kasumbalesa",               "LOG-ROAD", 4.0, False, 100, ["GEO-01","GEO-02"]),
    ("beitbridge closure",        "LOG-ROAD", 3.8, False, 80,  ["GEO-04"]),
    ("truckers strike",           "LOG-ROAD", 3.0, True,  60,  ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("blocage routier",           "LOG-ROAD", 3.2, True,  60,  ["GEO-01","GEO-02"]),
    ("frontiere fermee",          "LOG-ROAD", 3.5, False, 50,  ["GEO-01","GEO-02"]),
    ("bloqueio rodoviario",       "LOG-ROAD", 3.2, True,  60,  ["GEO-03B","GEO-04"]),
    ("fronteira fechada",         "LOG-ROAD", 3.5, False, 50,  ["GEO-03B","GEO-04"]),
    ("bloqueo de carretera",      "LOG-ROAD", 3.2, True,  60,  ["GEO-01","GEO-02"]),
    ("frontera cerrada",          "LOG-ROAD", 3.5, False, 50,  ["GEO-01","GEO-02"]),

    # --- LOG-CUSTOMS ---
    ("customs delay",             "LOG-CUSTOMS", 3.0, True,  60, ["GEO-01","GEO-02","GEO-08"]),
    ("export permit suspended",   "LOG-CUSTOMS", 4.0, True,  80, ["GEO-01","GEO-02","GEO-07"]),
    ("export documentation",      "LOG-CUSTOMS", 2.5, True,  60, ["GEO-01"]),
    ("mineral export freeze",     "LOG-CUSTOMS", 4.2, False, 50, ["GEO-01","GEO-02","GEO-07"]),
    ("retard douanier",           "LOG-CUSTOMS", 3.0, True,  60, ["GEO-01"]),
    ("suspension permis exportation","LOG-CUSTOMS",4.0,True, 80, ["GEO-01","GEO-02"]),
    ("atraso alfandegario",       "LOG-CUSTOMS", 3.0, True,  60, ["GEO-03B","GEO-04"]),
    ("retraso aduanero",          "LOG-CUSTOMS", 3.0, True,  60, ["GEO-01","GEO-02"]),
    ("permiso de exportacion suspendido","LOG-CUSTOMS",4.0,True,80,["GEO-01"]),

    # --- LOG-VESSEL ---
    ("shipping delay",            "LOG-VESSEL", 2.8, True,  80, ["GEO-08"]),
    ("freight rates surge",       "LOG-VESSEL", 2.5, True,  80, []),
    ("vessel shortage",           "LOG-VESSEL", 3.0, True,  80, []),
    ("bulk carrier shortage",     "LOG-VESSEL", 3.2, True,  80, []),

    # --- GEO-CONFLICT ---
    ("armed conflict",            "GEO-CONFLICT", 4.5, False, 50, ["GEO-01","GEO-02"]),
    ("militia attack",            "GEO-CONFLICT", 4.8, False, 50, ["GEO-01"]),
    ("rebel attack",              "GEO-CONFLICT", 4.5, False, 50, ["GEO-01","GEO-03A","GEO-03B"]),
    ("m23",                       "GEO-CONFLICT", 4.0, True,  50, ["GEO-01"]),
    ("mai-mai",                   "GEO-CONFLICT", 3.8, False, 80, ["GEO-01"]),
    ("mine attack",               "GEO-CONFLICT", 5.0, False, 80, ["GEO-01","GEO-02"]),
    ("security incident mine",    "GEO-CONFLICT", 4.0, True,  60, ["GEO-01","GEO-02"]),
    ("operations suspended security","GEO-CONFLICT",4.5,True, 60, ["GEO-01","GEO-02"]),
    ("conflit arme",              "GEO-CONFLICT", 4.5, False, 50, ["GEO-01"]),
    ("attaque de milice",         "GEO-CONFLICT", 4.8, False, 50, ["GEO-01"]),
    ("attaque rebelle",           "GEO-CONFLICT", 4.5, False, 50, ["GEO-01"]),
    ("conflicto armado",          "GEO-CONFLICT", 4.5, False, 50, ["GEO-01"]),
    ("ataque a mina",             "GEO-CONFLICT", 5.0, False, 80, ["GEO-01","GEO-02"]),
    ("conflito armado",           "GEO-CONFLICT", 4.5, False, 50, ["GEO-01"]),
    ("ataque de milicia",         "GEO-CONFLICT", 4.8, False, 50, ["GEO-01"]),

    # --- GEO-COUP ---
    ("coup",                      "GEO-COUP", 4.5, True,  40, ["GEO-01","GEO-02"]),
    ("military takeover",         "GEO-COUP", 5.0, False, 50, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("government overthrown",     "GEO-COUP", 5.0, False, 50, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("state of emergency",        "GEO-COUP", 4.0, True,  80, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("coup d'etat",               "GEO-COUP", 5.0, False, 50, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("prise de pouvoir militaire","GEO-COUP", 5.0, False, 50, ["GEO-01"]),
    ("etat d'urgence",            "GEO-COUP", 4.0, True,  80, ["GEO-01"]),
    ("golpe de estado",           "GEO-COUP", 5.0, False, 50, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("golpe militar",             "GEO-COUP", 5.0, False, 50, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("estado de emergencia",      "GEO-COUP", 4.0, True,  80, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),

    # --- GEO-SANCTION ---
    ("sanctions",                 "GEO-SANCTION", 3.8, True,  80, ["GEO-01","GEO-02","GEO-07"]),
    ("trade embargo",             "GEO-SANCTION", 4.5, False, 50, ["GEO-01","GEO-07"]),
    ("asset freeze",              "GEO-SANCTION", 4.0, True,  60, ["GEO-01","GEO-07"]),
    ("ofac sanctions",            "GEO-SANCTION", 4.2, True,  80, ["GEO-01","GEO-07"]),
    ("sanctions commerciales",    "GEO-SANCTION", 3.8, True,  80, ["GEO-01"]),
    ("embargo comercial",         "GEO-SANCTION", 4.5, False, 50, ["GEO-01","GEO-07"]),
    ("sancoes comerciais",        "GEO-SANCTION", 3.8, True,  80, ["GEO-01","GEO-07"]),

    # --- GEO-PROTEST ---
    ("protests",                  "GEO-PROTEST", 2.2, True,  60, ["GEO-01","GEO-02","GEO-08"]),
    ("civil unrest",              "GEO-PROTEST", 2.8, True,  60, ["GEO-01","GEO-02"]),
    ("demonstrations",            "GEO-PROTEST", 2.0, True,  60, ["GEO-01","GEO-02"]),
    ("manifestations",            "GEO-PROTEST", 2.0, True,  60, ["GEO-01"]),
    ("troubles civils",           "GEO-PROTEST", 2.8, True,  60, ["GEO-01"]),
    ("protestos",                 "GEO-PROTEST", 2.2, True,  60, ["GEO-03B","GEO-04"]),
    ("protestas",                 "GEO-PROTEST", 2.2, True,  60, ["GEO-01","GEO-02"]),

    # --- LAB-STRIKE-ACT ---
    ("strike",                    "LAB-STRIKE-ACT", 4.0, True,  60, ["GEO-01","GEO-02","GEO-08"]),
    ("workers on strike",         "LAB-STRIKE-ACT", 4.5, False, 60, ["GEO-01","GEO-02","GEO-08"]),
    ("mining strike",             "LAB-STRIKE-ACT", 4.8, False, 50, ["GEO-01","GEO-02"]),
    ("walkout",                   "LAB-STRIKE-ACT", 4.2, True,  60, ["GEO-01","GEO-02","GEO-08"]),
    ("work stoppage",             "LAB-STRIKE-ACT", 4.2, True,  60, ["GEO-01","GEO-02","GEO-08"]),
    ("production halted",         "LAB-STRIKE-ACT", 4.5, True,  60, ["GEO-01","GEO-02"]),
    ("operations suspended",      "LAB-STRIKE-ACT", 4.3, True,  60, ["GEO-01","GEO-02"]),
    ("greve",                     "LAB-STRIKE-ACT", 4.0, True,  60, ["GEO-01","GEO-08"]),
    ("greve miniere",             "LAB-STRIKE-ACT", 4.8, False, 50, ["GEO-01"]),
    ("arret de travail",          "LAB-STRIKE-ACT", 4.2, True,  60, ["GEO-01","GEO-08"]),
    ("production suspendue",      "LAB-STRIKE-ACT", 4.5, True,  60, ["GEO-01"]),
    ("greve mineira",             "LAB-STRIKE-ACT", 4.8, False, 50, ["GEO-02"]),
    ("paralisacao",               "LAB-STRIKE-ACT", 4.2, True,  60, ["GEO-03B","GEO-04"]),
    ("huelga",                    "LAB-STRIKE-ACT", 4.0, True,  60, ["GEO-01","GEO-02","GEO-08"]),
    ("huelga minera",             "LAB-STRIKE-ACT", 4.8, False, 50, ["GEO-01","GEO-02"]),
    ("paro laboral",              "LAB-STRIKE-ACT", 4.2, True,  60, ["GEO-01","GEO-02"]),

    # --- LAB-STRIKE-THR ---
    ("strike threat",             "LAB-STRIKE-THR", 3.0, True, 60, ["GEO-01","GEO-02","GEO-08"]),
    ("strike notice",             "LAB-STRIKE-THR", 3.5, True, 60, ["GEO-01","GEO-02","GEO-08"]),
    ("workers threaten",          "LAB-STRIKE-THR", 2.8, True, 60, ["GEO-01","GEO-02"]),
    ("menace de greve",           "LAB-STRIKE-THR", 3.0, True, 60, ["GEO-01","GEO-08"]),
    ("preavis de greve",          "LAB-STRIKE-THR", 3.5, True, 60, ["GEO-01"]),
    ("ameaca de greve",           "LAB-STRIKE-THR", 3.0, True, 60, ["GEO-03B","GEO-04"]),
    ("amenaza de huelga",         "LAB-STRIKE-THR", 3.0, True, 60, ["GEO-01","GEO-02"]),

    # --- Kiswahili (DRC Oriental, Tanzania) ---
    ("mgomo",                    "LAB-STRIKE-ACT", 3.5, True,  60, ["GEO-01","GEO-02","GEO-03A"]),
    ("mgomo wa wachimbaji",      "LAB-STRIKE-ACT", 4.5, False, 50, ["GEO-01","GEO-02"]),
    ("mgodi kufungwa",           "LAB-STRIKE-ACT", 4.0, False, 60, ["GEO-01","GEO-02"]),
    ("bandari kufungwa",         "LOG-PORT",        4.0, False, 50, ["GEO-03A","GEO-08"]),

    # --- LAB-ACCIDENT ---
    ("mine collapse",             "LAB-ACCIDENT", 5.0, False, 50, ["GEO-01","GEO-02"]),
    ("artisanal mine collapse",   "LAB-ACCIDENT", 4.0, False, 50, ["GEO-01"]),
    ("flooding mine",             "LAB-ACCIDENT", 4.5, False, 50, ["GEO-01","GEO-02"]),
    ("mine explosion",            "LAB-ACCIDENT", 4.8, False, 50, ["GEO-01","GEO-02"]),
    ("mining accident",           "LAB-ACCIDENT", 3.8, True,  60, ["GEO-01","GEO-02"]),
    ("effondrement de mine",      "LAB-ACCIDENT", 5.0, False, 50, ["GEO-01"]),
    ("inondation de mine",        "LAB-ACCIDENT", 4.5, False, 50, ["GEO-01"]),
    ("acidente de mineracao",     "LAB-ACCIDENT", 3.8, True,  60, ["GEO-02","GEO-03B"]),
    ("colapso de mina",           "LAB-ACCIDENT", 5.0, False, 50, ["GEO-01","GEO-02"]),
    ("accidente minero",          "LAB-ACCIDENT", 3.8, True,  60, ["GEO-01","GEO-02"]),

    # --- LAB-ASM: Minería Artesanal / Small-Scale Mining ---
    ("creuseurs",                     "LAB-ACCIDENT", 3.0, True,  80, ["GEO-01"]),
    ("mineurs artisanaux",            "LAB-ACCIDENT", 2.8, True,  80, ["GEO-01"]),
    ("informal cobalt mining",        "LAB-ACCIDENT", 2.8, True,  80, ["GEO-01"]),
    ("artisanal mining ban",          "REG-LICENSE",  4.0, False, 60, ["GEO-01"]),
    ("asm suspension",                "REG-LICENSE",  3.8, False, 60, ["GEO-01"]),
    ("suspension exploitation artisanale", "REG-LICENSE", 4.0, False, 60, ["GEO-01"]),
    ("interdiction exploitation artisanale","REG-LICENSE",4.2, False, 60, ["GEO-01"]),
    ("mineria artesanal prohibida",   "REG-LICENSE",  4.0, False, 60, ["GEO-01"]),

    # --- REG-EXPORT-BAN ---
    ("export ban",                "REG-EXPORT-BAN", 5.0, True,  80, ["GEO-01","GEO-02","GEO-07"]),
    ("export restriction",        "REG-EXPORT-BAN", 4.5, True,  80, ["GEO-01","GEO-02","GEO-07"]),
    ("export quota",              "REG-EXPORT-BAN", 4.0, True,  80, ["GEO-01","GEO-07"]),
    ("raw mineral export ban",    "REG-EXPORT-BAN", 5.0, False, 80, ["GEO-01","GEO-02"]),
    ("interdiction d'exportation","REG-EXPORT-BAN", 5.0, True,  80, ["GEO-01"]),
    ("restriction a l'exportation","REG-EXPORT-BAN",4.5, True,  80, ["GEO-01"]),
    ("proibicao de exportacao",   "REG-EXPORT-BAN", 5.0, True,  80, ["GEO-02","GEO-03B"]),
    ("prohibicion de exportacion","REG-EXPORT-BAN", 5.0, True,  80, ["GEO-01","GEO-02"]),
    ("veda exportacion mineral",  "REG-EXPORT-BAN", 5.0, False, 80, ["GEO-01"]),

    # --- REG-TAX ---
    ("windfall tax",              "REG-TAX", 3.5, True,  80, ["GEO-01","GEO-02"]),
    ("mining royalty increase",   "REG-TAX", 3.8, False, 60, ["GEO-01","GEO-02"]),
    ("super profits tax",         "REG-TAX", 3.5, True,  80, ["GEO-01","GEO-02"]),
    ("taxe sur les super-profits","REG-TAX", 3.8, False, 80, ["GEO-01"]),
    ("redevance miniere",         "REG-TAX", 3.8, True,  80, ["GEO-01"]),
    ("royalty minerario",         "REG-TAX", 3.8, True,  80, ["GEO-02"]),
    ("impuesto minero",           "REG-TAX", 3.5, True,  80, ["GEO-01","GEO-02"]),

    # --- REG-LICENSE ---
    ("mining license suspended",  "REG-LICENSE", 4.5, False, 60, ["GEO-01","GEO-02"]),
    ("license revoked",           "REG-LICENSE", 4.5, True,  60, ["GEO-01","GEO-02"]),
    ("permit cancelled",          "REG-LICENSE", 4.0, True,  60, ["GEO-01","GEO-02"]),
    ("licence miniere suspendue", "REG-LICENSE", 4.5, False, 60, ["GEO-01"]),
    ("licenca mineira suspensa",  "REG-LICENSE", 4.5, False, 60, ["GEO-02"]),
    ("licencia minera suspendida","REG-LICENSE", 4.5, False, 60, ["GEO-01","GEO-02"]),

    # --- REG-NATIONAL ---
    ("nationalization",           "REG-NATIONAL", 4.8, True, 80, ["GEO-01","GEO-02"]),
    ("nationalisation",           "REG-NATIONAL", 4.8, True, 80, ["GEO-01"]),
    ("nacionalizacao",            "REG-NATIONAL", 4.8, True, 80, ["GEO-02"]),
    ("nacionalizacion",           "REG-NATIONAL", 4.8, True, 80, ["GEO-01","GEO-02"]),

    # --- FMA-FLOOD ---
    ("flooding",                  "FMA-FLOOD", 3.5, True,  60, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("flash flood",               "FMA-FLOOD", 4.0, False, 50, ["GEO-01","GEO-02","GEO-03A","GEO-03B"]),
    ("road washed out",           "FMA-FLOOD", 4.2, False, 50, ["GEO-01","GEO-02","GEO-03A","GEO-03B"]),
    ("cyclone",                   "FMA-FLOOD", 4.5, False, 50, ["GEO-03A","GEO-03B","GEO-04"]),
    ("inundacao",                 "FMA-FLOOD", 3.5, True,  60, ["GEO-03B","GEO-04"]),
    ("ciclone",                   "FMA-FLOOD", 4.5, False, 50, ["GEO-03B"]),
    ("inundacion",                "FMA-FLOOD", 3.5, True,  60, ["GEO-01","GEO-02","GEO-03A","GEO-03B"]),

    # --- FMA-DROUGHT ---
    ("power outage",              "FMA-DROUGHT", 3.8, True,  60, ["GEO-01"]),
    ("load shedding",             "FMA-DROUGHT", 3.5, True,  60, ["GEO-01","GEO-04"]),
    ("hydroelectric shortage",    "FMA-DROUGHT", 4.0, True,  80, ["GEO-01"]),
    ("inga dam",                  "FMA-DROUGHT", 4.5, False, 100,["GEO-01"]),
    ("delestage",                 "FMA-DROUGHT", 3.5, True,  60, ["GEO-01"]),
    ("coupure d'electricite",     "FMA-DROUGHT", 3.8, True,  60, ["GEO-01"]),
    ("corte electrico",           "FMA-DROUGHT", 3.8, True,  60, ["GEO-01"]),

    # --- DEM-SUBSTITUTE ---
    ("cobalt-free battery",       "DEM-SUBSTITUTE", -2.5, False, 80, []),
    ("lfp battery",               "DEM-SUBSTITUTE", -3.0, False, 80, []),
    ("lithium iron phosphate",    "DEM-SUBSTITUTE", -1.5, False, 80, []),
    ("lmfp battery",              "DEM-SUBSTITUTE", -2.0, False, 80, []),
    ("batterie lfp",              "DEM-SUBSTITUTE", -2.0, False, 80, []),
    ("bateria lfp",               "DEM-SUBSTITUTE", -2.0, False, 80, []),
    ("sodium-ion battery",        "DEM-SUBSTITUTE", -2.5, False, 80, []),
    ("sodium ion battery",        "DEM-SUBSTITUTE", -2.5, False, 80, []),
    ("solid state battery",       "DEM-SUBSTITUTE", -1.5, False, 80, []),
    ("batterie sans cobalt",      "DEM-SUBSTITUTE", -2.5, False, 80, []),
    ("bateria sin cobalto",       "DEM-SUBSTITUTE", -2.5, False, 80, []),
    ("bateria sem cobalto",       "DEM-SUBSTITUTE", -2.5, False, 80, []),

    # --- DEM-SURGE ---
    ("gigafactory",               "DEM-SURGE", 2.5, True,  80, []),
    ("battery supply contract",   "DEM-SURGE", 3.0, True,  80, []),
    ("strategic reserve cobalt",  "DEM-SURGE", 3.5, False, 80, []),
    ("cobalt stockpile",          "DEM-SURGE", 3.2, False, 60, []),
    # Señales de mercado (tensión en oferta — confirman disrupciones físicas)
    ("cobalt supply deficit",     "DEM-SURGE", 2.5, False, 80, []),
    ("cobalt shortage",           "DEM-SURGE", 2.8, False, 60, []),
    ("cobalt inventory low",      "DEM-SURGE", 2.5, False, 80, []),
    ("cobalt price spike",        "DEM-SURGE", 2.0, False, 80, []),
    ("lme cobalt inventory",      "DEM-SURGE", 2.2, False, 80, []),
    ("penurie de cobalt",         "DEM-SURGE", 2.8, False, 60, []),
    ("deficit de cobalto",        "DEM-SURGE", 2.5, False, 80, []),
    ("escassez de cobalto",       "DEM-SURGE", 2.8, False, 60, []),

    # --- RES-RESOLVE: Resolución de eventos activos (peso negativo — reduce score) ---
    ("strike ended",              "RES-RESOLVE", -3.0, True,  80, []),
    ("strike called off",         "RES-RESOLVE", -3.0, True,  80, []),
    ("workers return to work",    "RES-RESOLVE", -3.0, True,  80, []),
    ("agreement reached",         "RES-RESOLVE", -2.5, True,  80, []),
    ("operations resumed",        "RES-RESOLVE", -3.0, True,  80, []),
    ("port reopened",             "RES-RESOLVE", -3.5, False, 60, ["GEO-08","GEO-03A","GEO-03B","GEO-04"]),
    ("mine reopened",             "RES-RESOLVE", -3.0, False, 60, ["GEO-01","GEO-02"]),
    ("border reopened",           "RES-RESOLVE", -3.0, False, 60, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("greve terminee",            "RES-RESOLVE", -3.0, True,  80, []),
    ("reprise des operations",    "RES-RESOLVE", -3.0, True,  80, []),
    ("accord conclu",             "RES-RESOLVE", -2.5, True,  80, []),
    ("huelga terminada",          "RES-RESOLVE", -3.0, True,  80, []),
    ("operaciones reanudadas",    "RES-RESOLVE", -3.0, True,  80, []),
    ("acuerdo alcanzado",         "RES-RESOLVE", -2.5, True,  80, []),
    ("greve encerrada",           "RES-RESOLVE", -3.0, True,  80, []),
    ("operacoes retomadas",       "RES-RESOLVE", -3.0, True,  80, []),
]

# Credibility modifiers by source name key
SOURCE_CREDIBILITY = {
    "reuters_africa":     1.00,
    "reuters_commodities":1.00,
    "reuters_china":      1.00,
    "mining_com_cobalt":  1.00,
    "mining_com_general": 1.00,
    "ap_news":            1.00,
    "allafrica":          0.85,
    "bbc_africa":         0.90,
    "miningmx":           0.90,
    "rfi_afrique":        0.80,
    "club_mozambique":    0.80,
    "lusaka_times":       0.75,
    "transnet_durban":    1.00,
    "tpa_tanzania":       1.00,
    "cfm_mozambique":     1.00,
    "reliefweb_drc":      0.90,
    "gdacs":              1.00,
    "acled":              1.00,
    "kitco":              0.85,
    # GEO-10 (Indonesia / Sulawesi) — añadido v1.1
    "antara_business":    0.85,
    "antara_press":       0.85,
    "mining_technology":  0.90,
    "mongabay":           0.80,
    # GEO-11 (Refino europeo) — añadido v1.1
    "yle_news_en":        0.90,
    "energy_storage_news":0.85,
    # Google News (agregador)
    "gnews_cobalt_en":    0.50,
    "gnews_cobalt_fr":    0.50,
    "gnews_drc":          0.50,
    "gnews_durban":       0.50,
    "gnews_indonesia_nickel": 0.50,
    "gnews_europe_refining":  0.50,
}

# ---------------------------------------------------------------------------
# 7. FUENTES RSS
# ---------------------------------------------------------------------------

RSS_SOURCES = [
    # --- Tier 1 ---
    {"name": "reuters_africa",
     "url":  "https://www.northernminer.com/feed/",
     "lang": "en", "full_text": True, "rate_limit": 30, "timeout": 10},
    {"name": "reuters_commodities",
     "url":  "https://www.africanews.com/feed/",
     "lang": "en", "full_text": True, "rate_limit": 30, "timeout": 10},
    {"name": "reuters_china",
     "url":  "https://www.rfi.fr/en/rss",
     "lang": "en", "full_text": True, "rate_limit": 30, "timeout": 10},
    # --- Mining specialized ---
    {"name": "mining_com_cobalt",
     "url":  "https://www.mining.com/web/tag/cobalt/feed/",
     "lang": "en", "full_text": False, "rate_limit": 60, "timeout": 15},
    {"name": "kitco",
     "url":  "https://im-mining.com/feed/",
     "lang": "en", "full_text": False, "rate_limit": 45, "timeout": 10},
    # --- African regional ---
    {"name": "allafrica",
     "url":  "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf",
     "lang": "en", "full_text": True, "rate_limit": 45, "timeout": 15},
    {"name": "bbc_africa",
     "url":  "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
     "lang": "en", "full_text": False, "rate_limit": 60, "timeout": 15},
    {"name": "miningmx",
     "url":  "https://www.miningmx.com/feed/",
     "lang": "en", "full_text": False, "rate_limit": 60, "timeout": 15},
    {"name": "rfi_afrique",
     "url":  "https://www.rfi.fr/fr/afrique/rss",
     "lang": "fr", "full_text": True, "rate_limit": 45, "timeout": 15},
    {"name": "club_mozambique",
     "url":  "https://clubofmozambique.com/feed/",
     "lang": "en", "full_text": False, "rate_limit": 90, "timeout": 15},
    {"name": "lusaka_times",
     "url":  "https://www.lusakatimes.com/feed/",
     "lang": "en", "full_text": False, "rate_limit": 90, "timeout": 15},
    # --- GEO-10: Indonesia / Sulawesi (HPAL, MHP, ESDM, IMIP, IWIP) ---
    # Fase 2 — peso geográfico 1.10, fuentes robustas, ejecutar siempre
    {"name": "antara_business",
     "url":  "https://en.antaranews.com/rss/business-investment.xml",
     "lang": "en", "full_text": True, "rate_limit": 60, "timeout": 15},
    {"name": "antara_press",
     "url":  "https://en.antaranews.com/rss/press-release.xml",
     "lang": "en", "full_text": False, "rate_limit": 90, "timeout": 15},
    {"name": "mining_technology",
     "url":  "https://www.mining-technology.com/feed/",
     "lang": "en", "full_text": False, "rate_limit": 60, "timeout": 15},
    {"name": "mongabay",
     "url":  "https://news.mongabay.com/feed/",
     "lang": "en", "full_text": False, "rate_limit": 90, "timeout": 15},
    # --- Relief/Conflict ---
    {"name": "reliefweb_drc",
     "url":  "https://reliefweb.int/updates/rss.xml?country=cod",
     "lang": "en", "full_text": False, "rate_limit": 120, "timeout": 15},
    {"name": "gdacs",
     "url":  "https://www.gdacs.org/xml/rss.xml",
     "lang": "en", "full_text": False, "rate_limit": 120, "timeout": 10},
    # --- GEO-11: Refino europeo (Umicore, Kokkola, Harjavalta, Terrafame, Nikkelverk) ---
    # Fase 4 — peso geográfico 0.80, fuentes complementarias (afectan a SMC)
    {"name": "yle_news_en",
     "url":  "https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_NEWS",
     "lang": "en", "full_text": False, "rate_limit": 90, "timeout": 15},
    {"name": "energy_storage_news",
     "url":  "https://www.energy-storage.news/feed/",
     "lang": "en", "full_text": False, "rate_limit": 90, "timeout": 15},
    # --- Google News ---
    {"name": "gnews_cobalt_en",
     "url":  "https://news.google.com/rss/search?q=cobalt+supply+disruption&hl=en-US&gl=US&ceid=US:en",
     "lang": "en", "full_text": False, "rate_limit": 300, "timeout": 10},
    {"name": "gnews_cobalt_fr",
     "url":  "https://news.google.com/rss/search?q=cobalt+greve+mine+RDC&hl=fr-FR&gl=FR&ceid=FR:fr",
     "lang": "fr", "full_text": False, "rate_limit": 300, "timeout": 10},
    {"name": "gnews_drc",
     "url":  "https://news.google.com/rss/search?q=DRC+cobalt+mine&hl=en-US&gl=US&ceid=US:en",
     "lang": "en", "full_text": False, "rate_limit": 300, "timeout": 10},
    {"name": "gnews_durban",
     "url":  "https://news.google.com/rss/search?q=Durban+port+strike+disruption&hl=en-US&gl=US&ceid=US:en",
     "lang": "en", "full_text": False, "rate_limit": 300, "timeout": 10},
    # GEO-10: búsqueda específica para disrupciones en Indonesia (HPAL, Morowali, Sulawesi)
    {"name": "gnews_indonesia_nickel",
     "url":  "https://news.google.com/rss/search?q=Indonesia+nickel+cobalt+HPAL+disruption&hl=en-US&gl=US&ceid=US:en",
     "lang": "en", "full_text": False, "rate_limit": 300, "timeout": 10},
    # GEO-11: búsqueda específica para refinadores europeos
    {"name": "gnews_europe_refining",
     "url":  "https://news.google.com/rss/search?q=Umicore+OR+Glencore+Nikkelverk+OR+Terrafame+cobalt&hl=en-US&gl=US&ceid=US:en",
     "lang": "en", "full_text": False, "rate_limit": 300, "timeout": 10},
]

SCRAPING_SOURCES = [
    {"name": "transnet_durban",
     "url":  "https://www.transnet.net/BusinessWithTransnet/TPT/Pages/PortofDurban.aspx",
     "lang": "en", "timeout": 20, "rate_limit": 300},
    {"name": "tpa_tanzania",
     "url":  "https://www.tanzaniaports.go.tz/index.php/news",
     "lang": "en", "timeout": 20, "rate_limit": 300},
    {"name": "cfm_mozambique",
     "url":  "https://www.cfmnet.co.mz/noticias",
     "lang": "pt", "timeout": 20, "rate_limit": 300},
]

# ---------------------------------------------------------------------------
# 8. FETCHING
# ---------------------------------------------------------------------------

SESSION = requests.Session()
SESSION.headers.update(REQUEST_HEADERS)

def fetch_url(url: str, timeout: int = 15) -> Optional[str]:
    try:
        resp = SESSION.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        log.debug("fetch_url error %s: %s", url, exc)
        return None

def fetch_rss(source: dict, state: dict) -> list:
    """
    Fetches and parses an RSS feed. Returns list of article dicts.
    Each article: {url, title, summary, pub_date, source_name}
    """
    name = source["name"]
    if is_source_degraded(state, name):
        log.debug("Saltando fuente DEGRADED: %s", name)
        return []

    try:
        feed = feedparser.parse(
            source["url"],
            request_headers=REQUEST_HEADERS,
            agent=REQUEST_HEADERS["User-Agent"],
        )
        if feed.bozo and not feed.entries:
            raise ValueError(f"bozo feed, sin entradas: {feed.bozo_exception}")

        articles = []
        for entry in feed.entries:
            url = getattr(entry, "link", "") or ""
            title = getattr(entry, "title", "") or ""
            summary = getattr(entry, "summary", "") or ""

            # Parse pub date
            pub_date = None
            for date_attr in ("published_parsed", "updated_parsed", "created_parsed"):
                tp = getattr(entry, date_attr, None)
                if tp:
                    pub_date = datetime(*tp[:6], tzinfo=timezone.utc)
                    break
            if pub_date is None:
                pub_date = datetime.now(timezone.utc)

            # Optionally fetch full text (only if not already processed)
            body = summary
            if source.get("full_text") and url and not is_url_processed(state, url):
                time.sleep(1)
                full = fetch_url(url, timeout=source.get("timeout", 15))
                if full:
                    soup = BeautifulSoup(full, "lxml")
                    for tag in soup(["script", "style", "nav", "footer", "header"]):
                        tag.decompose()
                    body = soup.get_text(separator=" ", strip=True)[:8000]

            # Filtro de edad: descartar articulos con mas de 48h
            age_hours_dl = (datetime.now(timezone.utc) - pub_date).total_seconds() / 3600
            if age_hours_dl > 48:
                continue
            articles.append({
                "url": url,
                "title": title,
                "body": body,
                "pub_date": pub_date,
                "source_name": name,
            })

        update_source_health(state, name, True)
        log.info("RSS OK: %s — %d entradas", name, len(articles))
        return articles

    except Exception as exc:
        log.warning("RSS FAIL: %s — %s", name, exc)
        update_source_health(state, name, False)
        return []

def fetch_scraping(source: dict, state: dict) -> list:
    """Scraping simple de portales portuarios: extrae texto visible como un artículo."""
    name = source["name"]
    if is_source_degraded(state, name):
        return []
    try:
        html = fetch_url(source["url"], timeout=source.get("timeout", 20))
        if not html:
            raise ValueError("respuesta vacía")
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)[:6000]
        update_source_health(state, name, True)
        log.info("Scraping OK: %s", name)
        return [{
            "url": source["url"],
            "title": f"[{name}] portal scan",
            "body": text,
            "pub_date": datetime.now(timezone.utc),
            "source_name": name,
        }]
    except Exception as exc:
        log.warning("Scraping FAIL: %s — %s", name, exc)
        update_source_health(state, name, False)
        return []

def fetch_acled(state: dict) -> list:
    """Fetches ACLED conflict data for DRC and neighboring countries."""
    if not ACLED_KEY or not ACLED_EMAIL:
        log.debug("ACLED: sin credenciales configuradas, saltando")
        return []
    if is_source_degraded(state, "acled"):
        return []
    try:
        params = {
            "key": ACLED_KEY,
            "email": ACLED_EMAIL,
            "region": "1",
            "event_type": "Battles|Explosions/Remote violence|Violence against civilians",
            "country": "Democratic Republic of Congo|Zambia|Tanzania|Mozambique|South Africa",
            "limit": "50",
            "fields": "event_date|event_type|actor1|location|latitude|longitude|notes|source",
        }
        resp = SESSION.get(
            "https://api.acleddata.com/acled/read",
            params=params, timeout=20
        )
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for row in data.get("data", []):
            notes = row.get("notes", "") or ""
            location = row.get("location", "") or ""
            event_type = row.get("event_type", "") or ""
            actor = row.get("actor1", "") or ""
            event_date_str = row.get("event_date", "")
            try:
                pub_date = dateutil_parser.parse(event_date_str).replace(tzinfo=timezone.utc)
            except Exception:
                pub_date = datetime.now(timezone.utc)
            body = f"{event_type} {actor} {location} {notes}"
            url = f"acled://{row.get('data_id','unknown')}"
            articles.append({
                "url": url,
                "title": f"[ACLED] {event_type} — {location}",
                "body": body,
                "pub_date": pub_date,
                "source_name": "acled",
            })
        update_source_health(state, "acled", True)
        log.info("ACLED OK — %d eventos", len(articles))
        return articles
    except Exception as exc:
        log.warning("ACLED FAIL: %s", exc)
        update_source_health(state, "acled", False)
        return []

# ---------------------------------------------------------------------------
# 9. DEDUPLICACION
# ---------------------------------------------------------------------------

def is_duplicate_article(article: dict, seen_articles: list, state: dict) -> bool:
    """Returns True if article is a duplicate (URL already seen or similar title)."""
    url = article.get("url", "")
    if url and is_url_processed(state, url):
        return True
    title = article.get("title", "")
    domain = url.split("/")[2] if url.startswith("http") else article.get("source_name","")
    for seen in seen_articles:
        seen_domain = seen["url"].split("/")[2] if seen["url"].startswith("http") else seen.get("source_name","")
        if seen_domain == domain and simple_similarity(title, seen["title"]) > 0.85:
            return True
    return False

# ---------------------------------------------------------------------------
# 10. SCORING CORE
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list:
    """Normalize and split text into words for window searches."""
    return normalize(text).split()

def has_anchor(text_norm: str, window_words: list = None) -> bool:
    """Check if any anchor term is present in the normalized text."""
    for anchor in ANCHOR_TERMS:
        if normalize(anchor) in text_norm:
            return True
    return False

def has_coup_context(words: list, kw_pos: int, window: int = 40) -> bool:
    """Returns True if at least one geo/political term from COUP_CONTEXT_TERMS
    appears within ±window words of the 'coup' occurrence."""
    start = max(0, kw_pos - window)
    end = min(len(words), kw_pos + window + 1)
    window_slice = set(words[start:end])
    return any(t in window_slice for t in COUP_CONTEXT_TERMS)

def has_negation_near(words: list, kw_pos: int, window: int = 5) -> bool:
    """Check for negation within ±window words of keyword position."""
    start = max(0, kw_pos - window)
    end = min(len(words), kw_pos + window + 1)
    context = words[start:end]
    for neg in ALL_NEGATION_TERMS:
        neg_norm = normalize(neg)
        if neg_norm in context:
            return True
    return False

def check_false_positive(text_norm: str, category: str) -> bool:
    """Returns True if a known false-positive pattern is present."""
    patterns = FALSE_POSITIVE_FILTERS.get(category, [])
    for pat in patterns:
        if normalize(pat) in text_norm:
            return True
    return False

def detect_geo(text_norm: str) -> list:
    """Returns list of GEO codes detected in normalized text."""
    found = []
    for geo_code, terms in GEOGRAPHIC_TERMS.items():
        for t in terms:
            if normalize(t) in text_norm:
                if geo_code not in found:
                    found.append(geo_code)
                break
    return found

def age_factor(pub_date: datetime, category: str) -> float:
    """Returns decay factor based on article age."""
    now = datetime.now(timezone.utc)
    age_hours = (now - pub_date).total_seconds() / 3600.0
    age_days = age_hours / 24.0
    # REG y GEO-SANCTION no decaen
    no_decay_cats = {"REG-EXPORT-BAN","REG-TAX","REG-LICENSE","REG-ENV",
                     "REG-NATIONAL","REG-TARIFF","GEO-SANCTION"}
    if category in no_decay_cats:
        return 1.0
    if age_days > 7:
        return 0.10
    if age_hours > 72:
        if category.startswith("LOG") or category.startswith("LAB"):
            return 0.30
        return 0.60
    return 1.0

def score_article(article: dict) -> list:
    """
    Scores a single article against all keywords.
    Returns list of hit dicts: {keyword, category, score_bruto, geo_codes, pub_date, ...}
    """
    full_text = (article.get("title","") + " " + article.get("body",""))
    text_norm = normalize(full_text)
    words = text_norm.split()
    has_anc = has_anchor(text_norm)
    geos = detect_geo(text_norm)
    has_specific_geo = len(geos) > 0

    # Check for generic-only geo mentions
    generic_geo_terms = ["africa", "emerging markets", "developing countries"]
    generic_only = (
        not has_specific_geo and
        any(normalize(g) in text_norm for g in generic_geo_terms)
    )

    hits = []
    for (term, category, weight, requires_context, context_window, geo_boost) in KEYWORDS:
        term_norm = normalize(term)
        pos = text_norm.find(term_norm)
        if pos == -1:
            continue

        # requires_context: need anchor within context_window words
        if requires_context:
            # Count word position
            words_before = len(text_norm[:pos].split())
            window_start = max(0, words_before - context_window)
            window_end = min(len(words), words_before + context_window)
            window_text = " ".join(words[window_start:window_end])
            if not has_anchor(window_text):
                continue

        # False positive filter
        if check_false_positive(text_norm, category):
            continue

        # "coup" solo puntúa si hay contexto geo/político en ventana ±40 palabras
        word_pos = len(text_norm[:pos].split())
        if term_norm == "coup" and not has_coup_context(words, word_pos, window=40):
            continue

        # Negation check
        negated = has_negation_near(words, word_pos, window=5)
        if negated:
            weight = weight * 0.15

        # Determine best geo weight
        best_geo_weight = 1.0
        best_geo_code = None
        for geo in geos:
            gw = GEO_WEIGHTS.get(geo, 1.0)
            if gw > best_geo_weight:
                best_geo_weight = gw
                best_geo_code = geo
        # Also check geo_boost list
        for gb in geo_boost:
            if gb in geos:
                gw = GEO_WEIGHTS.get(gb, 1.0)
                if gw > best_geo_weight:
                    best_geo_weight = gw
                    best_geo_code = gb

        cat_mult = abs(CATEGORY_MULTIPLIERS.get(category, 1.0))
        cred = SOURCE_CREDIBILITY.get(article["source_name"], 0.70)
        age_f = age_factor(article["pub_date"], category)

        score_bruto = abs(weight) * best_geo_weight * cat_mult * cred

        if score_bruto < 3.0:
            continue

        # Negation applied
        if negated:
            score_bruto *= 0.15

        # Age factor
        score_bruto *= age_f

        # Generic geo penalty
        if not has_specific_geo:
            if generic_only:
                score_bruto *= 0.40
            else:
                continue  # no geo context at all

        # DEM-SUBSTITUTE: negative sign
        sign = -1 if weight < 0 else 1

        hits.append({
            "keyword": term,
            "category": category,
            "score_bruto": round(score_bruto * sign, 3),
            "geo_codes": geos,
            "best_geo": best_geo_code,
            "pub_date": article["pub_date"],
            "source_name": article["source_name"],
            "url": article.get("url",""),
            "title": article.get("title",""),
            "negated": negated,
        })

    return hits

def calc_ssc(score_bruto: float, category: str) -> float:
    """Apply SSC weight multiplier."""
    w = SSC_CATEGORY_WEIGHTS.get(category, 0.4)
    return round(score_bruto * w, 3)

def calc_smc(score_bruto: float, category: str) -> float:
    """Apply SMC category override if applicable."""
    override = SMC_CATEGORY_OVERRIDES.get(category, 1.0)
    return round(score_bruto * override, 3)

def aggregate_scores(hits: list) -> tuple:
    """
    Aggregates hit scores into total SSC and SMC using the
    primary + 0.5*secondary formula from scoring_rules.md s7.
    Multi-source confirmation bonus applied per event cluster.
    """
    if not hits:
        return 0.0, 0.0

    # Group hits into "events": same category + same geo + within 48h window
    # Use a hash key: category + best_geo + date bucket
    event_map = {}
    for hit in hits:
        bucket_date = hit["pub_date"].strftime("%Y-%m-%d")
        key = f"{hit['category']}__{hit['best_geo'] or 'NONE'}__{bucket_date}"
        if key not in event_map:
            event_map[key] = []
        event_map[key].append(hit)

    ssc_scores = []
    smc_scores = []

    for key, event_hits in event_map.items():
        # Best score for this event cluster
        best = max(event_hits, key=lambda h: abs(h["score_bruto"]))
        cat = best["category"]
        sb = best["score_bruto"]

        # Multi-source confirmation
        unique_sources = set(h["source_name"] for h in event_hits)
        high_cred_sources = sum(
            1 for s in unique_sources
            if SOURCE_CREDIBILITY.get(s, 0) >= 0.80
        )
        if high_cred_sources >= 3:
            sb = sb * 1.30

        ssc = calc_ssc(sb, cat)
        smc = calc_smc(sb, cat)
        ssc_scores.append(ssc)
        smc_scores.append(smc)

    # Sort descending by absolute value
    ssc_scores.sort(key=abs, reverse=True)
    smc_scores.sort(key=abs, reverse=True)

    def aggregate(scores):
        if not scores:
            return 0.0
        total = scores[0]
        for s in scores[1:]:
            # preserve sign for DEM-SUBSTITUTE negatives
            total += s * 0.5
        return total

    total_ssc = round(aggregate(ssc_scores), 2)
    total_smc = round(aggregate(smc_scores), 2)
    return total_ssc, total_smc

def level_ssc(score: float) -> tuple:
    """Returns (level_name, color) for SSC score."""
    if score < 16:
        return "VERDE", "verde"
    if score < 31:
        return "AMARILLO", "amarillo"
    if score < 51:
        return "NARANJA", "naranja"
    return "ROJO", "rojo"

def level_smc(score: float) -> tuple:
    if score < 21:
        return "VERDE", "verde"
    if score < 41:
        return "AMARILLO", "amarillo"
    if score < 66:
        return "NARANJA", "naranja"
    return "ROJO", "rojo"

def should_alert(ssc: float, smc: float) -> bool:
    """Trigger condition from scoring_rules.md s4.3"""
    return (ssc >= 31) or (smc >= 41) or (ssc >= 20 and smc >= 30)

# ---------------------------------------------------------------------------
# 10b. GEMINI ANALYSIS
# ---------------------------------------------------------------------------
# Path A (score >= GEMINI_SCORE_THRESHOLD): Gemini valida YES/NO.
#   YES → el artículo conserva su score tal cual.
#   NO  → todos sus hits se descartan.
# Path B (context keywords >= GEMINI_CONTEXT_MIN): Gemini devuelve un
#   multiplicador 0.0–1.5 que se aplica al score_bruto de cada hit.
# Si ambas condiciones se cumplen, Path A tiene prioridad.
# Si GEMINI_API_KEY está vacío o el paquete no está instalado, se omite
# sin afectar el flujo (fail-safe).
# ---------------------------------------------------------------------------

def _gemini_model():
    """Devuelve un modelo Gemini configurado, o None si no está disponible."""
    if not _GENAI_AVAILABLE or not GEMINI_API_KEY:
        return None
    return genai.Client(api_key=GEMINI_API_KEY)

def count_context_hits(article: dict) -> int:
    """Cuenta cuántos CONTEXT_TRIGGER_TERMS aparecen en el artículo."""
    text_norm = normalize(article.get("title", "") + " " + article.get("body", ""))
    return sum(1 for t in CONTEXT_TRIGGER_TERMS if normalize(t) in text_norm)

def gemini_validate(article: dict) -> bool:
    """Path A — pregunta YES/NO a Gemini. Fail-safe: True si hay error."""
    model = _gemini_model()
    if model is None:
        return True
    prompt = (
        "You are an analyst monitoring cobalt supply chain disruptions.\n"
        f"Title: {article.get('title', '')}\n"
        f"Text: {article.get('body', '')[:1500]}\n\n"
        "Does this article describe a real, current disruption or significant risk "
        "to cobalt supply chains (mining, transport, export, conflict, labor, regulation)?\n"
        "Answer only: YES or NO"
    )
    try:
        answer = model.models.generate_content(model="gemini-2.0-flash", contents=prompt).text.strip().upper()
        log.info("Gemini Path A [%s]: %s", article.get("title", "?")[:55], answer)
        return answer.startswith("YES")
    except Exception as exc:
        log.warning("Gemini Path A error: %s — conservando hits", exc)
        return True

def gemini_multiplier(article: dict) -> float:
    """Path B — devuelve multiplicador 0.0/0.5/1.0/1.5. Fail-safe: 1.0 si error."""
    model = _gemini_model()
    if model is None:
        return 1.0
    prompt = (
        "You are an analyst monitoring cobalt supply chain disruptions.\n"
        f"Title: {article.get('title', '')}\n"
        f"Text: {article.get('body', '')[:1500]}\n\n"
        "Rate the relevance of this article to cobalt supply chain disruption risk:\n"
        "0.0 = not relevant\n"
        "0.5 = marginally relevant\n"
        "1.0 = clearly relevant\n"
        "1.5 = highly relevant and urgent\n"
        "Answer only with one of these numbers: 0.0, 0.5, 1.0, or 1.5"
    )
    try:
        val = float(model.models.generate_content(model="gemini-2.0-flash", contents=prompt).text.strip())
        val = max(0.0, min(1.5, val))
        log.info("Gemini Path B [%s]: x%.1f", article.get("title", "?")[:55], val)
        return val
    except Exception as exc:
        log.warning("Gemini Path B error: %s — multiplicador 1.0", exc)
        return 1.0

def analyze_with_gemini(article: dict, hits: list) -> list:
    """
    Dispatcher principal. Devuelve la lista de hits (posiblemente vacía o modificada).
    Path A tiene prioridad si ambas condiciones se cumplen.
    """
    if not hits or not GEMINI_API_KEY or not _GENAI_AVAILABLE:
        return hits

    max_score = max(abs(h["score_bruto"]) for h in hits)

    if max_score >= GEMINI_SCORE_THRESHOLD:
        if not gemini_validate(article):
            log.info("Gemini descartó (Path A): %s", article.get("title", "?")[:60])
            return []
        return hits

    if count_context_hits(article) >= GEMINI_CONTEXT_MIN:
        mult = gemini_multiplier(article)
        if mult == 0.0:
            log.info("Gemini descartó (Path B x0.0): %s", article.get("title", "?")[:60])
            return []
        for h in hits:
            h["score_bruto"] = round(h["score_bruto"] * mult, 3)
            h["gemini_mult"] = mult
        return hits

    return hits

# ---------------------------------------------------------------------------
# 11. ASSET SELECTION
# ---------------------------------------------------------------------------

ASSET_TABLE = {
    # ticker: (name, exchange, direction_positive, reason)
    "LIT":      ("Global X Lithium & Battery Tech ETF", "NYSE",
                 True, "Tension en cadena de baterias eleva sector metales criticos"),
    "REMX":     ("VanEck Rare Earth/Strategic Metals ETF", "NYSE",
                 True, "Exposicion a metales criticos incluyendo cobalto"),
    "BATT":     ("Amplify Lithium & Battery Technology ETF", "NYSE",
                 True, "Exposicion indirecta a cadena de baterias"),
    "COPX":     ("Global X Copper Miners ETF", "NYSE",
                 True, "Copperbelt: DRC produce cobre y cobalto juntos"),
    "GLEN.L":   ("Glencore", "LSE",
                 True, "Mayor productor mundial; se beneficia si evento no afecta sus activos"),
    "UMI.BR":   ("Umicore", "Euronext Bruselas",
                 True, "Mayor reciclador cobalto Europa; escasez primaria sube valor reciclado"),
    "DRIV":     ("Global X Autonomous & EV ETF", "NYSE",
                 False, "Coste baterias sube; margen fabricantes VE comprimido"),
    "IDRV":     ("iShares Self-Driving EV and Tech ETF", "NYSE",
                 False, "Impacto negativo en disrupciones severas"),
    "300750.SZ":("CATL", "Shenzhen",
                 False, "Mayor fabricante baterias; margen comprimido con cobalto caro"),
}

def select_assets(hits: list, ssc: float, smc: float) -> list:
    """Returns list of (ticker, direction, horizon, reason) tuples."""
    cats = set(h["category"] for h in hits)
    geos = set(g for h in hits for g in h.get("geo_codes", []))
    selected = {}

    def add(ticker, direction, horizon):
        if ticker in ASSET_TABLE and ticker not in selected:
            name, exchange, pos, reason = ASSET_TABLE[ticker]
            selected[ticker] = (ticker, name, direction, horizon, reason)

    # LOG events at key ports
    if any(c.startswith("LOG") for c in cats):
        if geos & {"GEO-08","GEO-03A","GEO-03B","GEO-04"}:
            for t in ["LIT","REMX","UMI.BR"]:
                add(t, "LARGO", "1-3 semanas")

    # Conflict or coup in DRC
    if cats & {"GEO-CONFLICT","GEO-COUP"}:
        if "GEO-01" in geos:
            for t in ["GLEN.L","LIT","COPX","REMX"]:
                add(t, "LARGO", "1-3 semanas")

    # Export ban — max alert
    if "REG-EXPORT-BAN" in cats:
        for t in ["LIT","REMX","GLEN.L","UMI.BR","BATT"]:
            add(t, "LARGO", "inmediato — 1-2 semanas")

    # Any supply disruption — LIT as general signal
    if ssc >= 20 or smc >= 30:
        add("LIT", "LARGO", "1-3 semanas")
        add("UMI.BR", "LARGO", "2-4 semanas")

    # High SMC: add negative-direction assets
    if smc > 50:
        add("DRIV", "CORTO", "3-6 semanas")
        add("IDRV", "CORTO", "3-6 semanas")
        add("300750.SZ", "CORTO", "2-4 semanas")

    return list(selected.values())

# ---------------------------------------------------------------------------
# 12. EMAIL HTML
# ---------------------------------------------------------------------------

SOURCE_LINKS = {
    "LOG-PORT": [
        ("Puerto de Durban — Transnet", "https://www.transnet.net/BusinessWithTransnet/TPT/Pages/PortofDurban.aspx"),
        ("Tanzania Ports Authority", "https://www.tanzaniaports.go.tz"),
        ("CFM Mozambique", "https://www.cfmnet.co.mz"),
        ("Fastmarkets — Cobalt price", "https://www.fastmarkets.com/commodities/battery-raw-materials/cobalt"),
        ("Reuters Africa", "https://www.reuters.com/world/africa/"),
    ],
    "GEO-CONFLICT": [
        ("ACLED — Armed Conflict Data", "https://acleddata.com/dashboard/"),
        ("OCHA DRC", "https://www.unocha.org/democratic-republic-congo"),
        ("AllAfrica — DRC", "https://allafrica.com/congo/"),
        ("Reuters Africa", "https://www.reuters.com/world/africa/"),
        ("Mining.com — DRC", "https://www.mining.com/tag/democratic-republic-of-congo/"),
    ],
    "LAB-STRIKE-ACT": [
        ("Mining Weekly — Labour", "https://www.miningweekly.com/tag/labour"),
        ("AllAfrica", "https://allafrica.com/"),
        ("Reuters Commodities", "https://www.reuters.com/business/commodities/"),
        ("Fastmarkets — Cobalt", "https://www.fastmarkets.com/commodities/battery-raw-materials/cobalt"),
    ],
    "REG-EXPORT-BAN": [
        ("Journal Officiel RDC", "https://www.leganet.cd"),
        ("S&P Global Commodity Insights", "https://www.spglobal.com/commodityinsights/en/market-insights/topics/cobalt"),
        ("Benchmark Mineral Intelligence", "https://benchmarkminerals.com/cobalt/"),
        ("Mining.com — Cobalt", "https://www.mining.com/tag/cobalt/"),
        ("Reuters Commodities", "https://www.reuters.com/business/commodities/"),
    ],
    "FMA-FLOOD": [
        ("ReliefWeb — DRC", "https://reliefweb.int/country/cod"),
        ("OCHA DRC", "https://www.unocha.org/democratic-republic-congo"),
        ("GDACS — Global Disaster Alert", "https://www.gdacs.org"),
        ("INGC Mozambique", "https://www.ingc.gov.mz"),
    ],
    "GEO-COUP": [
        ("Reuters Africa", "https://www.reuters.com/world/africa/"),
        ("BBC Africa", "https://www.bbc.com/news/world/africa"),
        ("ACLED", "https://acleddata.com/dashboard/"),
        ("AllAfrica", "https://allafrica.com/"),
    ],
    "DEFAULT": [
        ("Mining.com — Cobalt", "https://www.mining.com/tag/cobalt/"),
        ("Reuters Commodities", "https://www.reuters.com/business/commodities/"),
        ("S&P Global Commodity Insights", "https://www.spglobal.com/commodityinsights/en/market-insights/topics/cobalt"),
        ("AllAfrica", "https://allafrica.com/"),
    ],
}

COLOR_MAP = {
    "verde": "#27ae60", "amarillo": "#f39c12",
    "naranja": "#e67e22", "rojo": "#c0392b",
}

def build_event_cards(hits: list) -> str:
    """Build HTML event cards from top hits (max 5 unique events)."""
    # Deduplicate by event key and take top 5 by absolute score
    seen_keys = set()
    top_hits = []
    for h in sorted(hits, key=lambda x: abs(x["score_bruto"]), reverse=True):
        key = f"{h['category']}__{h['best_geo']}"
        if key not in seen_keys:
            seen_keys.add(key)
            top_hits.append(h)
        if len(top_hits) >= 5:
            break

    cards = ""
    for h in top_hits:
        age_str = ""
        now = datetime.now(timezone.utc)
        diff = now - h["pub_date"]
        if diff.total_seconds() < 3600:
            age_str = f"hace {int(diff.total_seconds()/60)} minutos"
        elif diff.total_seconds() < 86400:
            age_str = f"hace {int(diff.total_seconds()/3600)} horas"
        else:
            age_str = f"hace {diff.days} dias"

        geos_str = ", ".join(h["geo_codes"]) if h["geo_codes"] else "N/A"
        score_str = f"+{abs(h['score_bruto']):.1f}" if h["score_bruto"] >= 0 else f"{h['score_bruto']:.1f}"
        neg_warning = " <em>(negacion detectada — verificar)</em>" if h.get("negated") else ""

        cards += f"""
        <div class="event-card">
          <strong>[{h['category']}] {h['title'][:120]}</strong>
          <p style="margin:4px 0; font-size:14px">
            <strong>Fuente:</strong> {h['source_name']} &nbsp;|&nbsp;
            <strong>Publicado:</strong> {age_str}{neg_warning}<br>
            <strong>Region afectada:</strong> {geos_str}<br>
            <strong>Keyword:</strong> <code>{h['keyword']}</code> &nbsp;|&nbsp;
            <strong>Contribucion:</strong> {score_str} pts brutos
          </p>
          {"<a class='source-link' href='" + h['url'] + "'>Leer fuente</a>" if h['url'].startswith('http') else ""}
        </div>
        """
    return cards

def build_asset_rows(assets: list) -> str:
    rows = ""
    for ticker, name, direction, horizon, reason in assets:
        arrow = "up" if direction == "LARGO" else "down"
        symbol = "&#8593; LARGO" if direction == "LARGO" else "&#8595; CORTO"
        rows += f"""
        <tr>
          <td><strong>{ticker}</strong></td>
          <td>{name}</td>
          <td class="{arrow}">{symbol}</td>
          <td>{horizon}</td>
          <td>{reason}</td>
        </tr>
        """
    return rows

def build_source_links(dominant_category: str) -> str:
    links = SOURCE_LINKS.get(dominant_category, SOURCE_LINKS["DEFAULT"])
    items = ""
    for label, url in links:
        items += f'<li><a class="source-link" href="{url}">{label}</a></li>\n'
    return items

def build_email(ssc: float, smc: float, hits: list, run_number: int) -> tuple:
    """Returns (subject, html_body)."""
    level_ssc_name, color_ssc = level_ssc(ssc)
    level_smc_name, color_smc = level_smc(smc)

    # Overall level is the worst of the two
    overall_levels = [level_ssc_name, level_smc_name]
    level_order = ["VERDE", "AMARILLO", "NARANJA", "ROJO"]
    nivel_alerta = max(overall_levels, key=lambda x: level_order.index(x))
    color_nivel = nivel_alerta.lower()

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    subject = f"[COBALT-ALERT] {nivel_alerta} | SSC:{ssc:.1f} SMC:{smc:.1f} | {now_str} UTC"

    # Dominant category
    cat_counts = {}
    for h in hits:
        cat_counts[h["category"]] = cat_counts.get(h["category"], 0) + abs(h["score_bruto"])
    dominant_cat = max(cat_counts, key=cat_counts.get) if cat_counts else "DEFAULT"

    # Executive summary
    top_hit = max(hits, key=lambda h: abs(h["score_bruto"])) if hits else None
    if top_hit:
        geo_str = ", ".join(top_hit["geo_codes"]) if top_hit["geo_codes"] else "zona no especificada"
        age_diff = datetime.now(timezone.utc) - top_hit["pub_date"]
        age_h = max(0, int(age_diff.total_seconds() / 3600))
        unique_sources = len(set(h["source_name"] for h in hits))
        resumen = (
            f"Se han detectado {len(hits)} senales de disrupcion en la cadena de suministro de cobalto. "
            f"El evento de mayor score es [{top_hit['category']}] detectado en {geo_str}, "
            f"reportado por {top_hit['source_name']} hace {age_h} horas. "
            f"Numero de fuentes independientes con senales: {unique_sources}."
        )
        argumento_urgencia = (
            f"Categoria [{dominant_cat}] con {unique_sources} fuentes detectadas. "
            f"El retardo historico entre este tipo de evento y su reflejo en precios de ETFs es tipicamente 5-14 dias habiles. "
            f"La ventana de entrada optima es 48-72h desde el primer evento detectado."
        )
        argumento_cautela = (
            f"El score SSC de {ssc:.1f} corresponde a nivel {level_ssc_name}. "
            f"Verificar siempre con fuentes primarias antes de ejecutar cualquier posicion. "
            f"Este sistema heuristico puede generar falsos positivos — revision humana obligatoria."
        )
    else:
        resumen = "Actividad moderada detectada. Revisar eventos individuales."
        argumento_urgencia = "Nivel de alerta alcanzado por combinacion de scores SSC/SMC."
        argumento_cautela = "Verificar con fuentes primarias antes de actuar."

    event_cards = build_event_cards(hits)
    assets = select_assets(hits, ssc, smc)
    asset_rows = build_asset_rows(assets)
    source_links_html = build_source_links(dominant_cat)

    color_ssc_hex = COLOR_MAP[color_ssc]
    color_smc_hex = COLOR_MAP[color_smc]
    color_header_hex = COLOR_MAP[color_nivel]

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; color: #1a1a1a; }}
    .header {{ background: {color_header_hex}; color: white; padding: 16px; border-radius: 6px; }}
    .score-box {{ display: inline-block; background: #f4f4f4; border: 1px solid #ddd;
                  padding: 8px 16px; border-radius: 4px; margin: 4px; font-size: 14px;
                  vertical-align: top; }}
    .event-card {{ border-left: 4px solid {color_header_hex}; padding: 12px; margin: 12px 0;
                   background: #fafafa; border-radius: 0 4px 4px 0; }}
    .asset-table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
    .asset-table th {{ background: #2c3e50; color: white; padding: 8px; text-align: left; font-size: 13px; }}
    .asset-table td {{ padding: 8px; border-bottom: 1px solid #eee; font-size: 13px; }}
    .up   {{ color: #27ae60; font-weight: bold; }}
    .down {{ color: #c0392b; font-weight: bold; }}
    .source-link {{ color: #2980b9; text-decoration: none; font-size: 13px; }}
    .disclaimer {{ font-size: 11px; color: #888; margin-top: 20px;
                   border-top: 1px solid #eee; padding-top: 10px; }}
    .section-title {{ font-size: 13px; text-transform: uppercase; color: #888;
                      letter-spacing: 1px; margin: 16px 0 8px 0; }}
    code {{ background: #f0f0f0; padding: 1px 4px; border-radius: 3px; font-size: 12px; }}
  </style>
</head>
<body>

<div class="header">
  <h2 style="margin:0">Alerta de Riesgo de Suministro — COBALTO</h2>
  <p style="margin:4px 0 0 0; font-size:14px">{now_str} UTC | Ejecucion {run_number}/3 del dia</p>
</div>

<div style="margin: 16px 0;">
  <div class="score-box">
    <strong>SWING CORTO (1-2 sem)</strong><br>
    <span style="font-size:24px; font-weight:bold">{ssc:.1f}</span>/50
    <br><span style="color:{color_ssc_hex}; font-weight:bold">{level_ssc_name}</span>
  </div>
  <div class="score-box">
    <strong>SWING MACRO (1-3 meses)</strong><br>
    <span style="font-size:24px; font-weight:bold">{smc:.1f}</span>/65
    <br><span style="color:{color_smc_hex}; font-weight:bold">{level_smc_name}</span>
  </div>
</div>

<p class="section-title">Que esta pasando</p>
<p style="font-size:15px; line-height:1.6">{resumen}</p>

<p class="section-title">Eventos Detectados ({len(hits)} senales totales)</p>
{event_cards}

<p class="section-title">Activos a Vigilar</p>
{"<p style='font-size:13px;color:#888'>Sin activos relevantes para el nivel de alerta actual.</p>" if not assets else ""}
{"<table class='asset-table'><tr><th>Ticker</th><th>Nombre</th><th>Direccion</th><th>Horizonte</th><th>Razon</th></tr>" + asset_rows + "</table>" if assets else ""}

<p class="section-title">Fuentes para Due Diligence</p>
<ul style="font-size:14px; line-height:2">
{source_links_html}
</ul>

<p class="section-title">Contexto para la Decision</p>
<div style="background:#eaf4fb; padding:12px; border-radius:4px; font-size:14px; line-height:1.6">
  <strong>Por que actuar ahora:</strong><br>
  {argumento_urgencia}
  <br><br>
  <strong>Por que ser cauteloso:</strong><br>
  {argumento_cautela}
</div>

<div class="disclaimer">
  Sistema automatico de alerta — no constituye asesoramiento financiero ni recomendacion de inversion.<br>
  Mineral: Cobalto | scoring_rules.md v1.0 + keyword_dictionary.md v1.0<br>
  Frecuencia: 3x/dia (00:00, 08:00, 16:00 UTC) | GCP e2-micro
</div>

</body>
</html>"""

    return subject, html

def send_email(subject: str, html_body: str):
    if not SMTP_USER or not SMTP_PASS:
        log.warning("Email no configurado (SMTP_USER/SMTP_PASS vacios) — volcando a log")
        log.info("EMAIL SUBJECT: %s", subject)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = ALERT_TO
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [ALERT_TO], msg.as_string())
        log.info("Email enviado a %s — %s", ALERT_TO, subject)
    except Exception as exc:
        log.error("Error enviando email: %s", exc)

# ---------------------------------------------------------------------------
# 13. MAIN LOOP
# ---------------------------------------------------------------------------

def compute_run_number(state: dict) -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("last_run_date") != today:
        state["run_count_today"] = 0
        state["last_run_date"] = today
    state["run_count_today"] = state.get("run_count_today", 0) + 1
    return state["run_count_today"]

def main():
    log.info("=== CobaltScorer iniciando ===")
    state = load_state()
    purge_old_urls(state, hours=72)
    run_number = compute_run_number(state)
    log.info("Ejecucion %d del dia %s", run_number, state["last_run_date"])

    all_articles = []
    seen_this_run = []

    # --- RSS sources ---
    for source in RSS_SOURCES:
        time.sleep(0.5)  # politeness
        articles = fetch_rss(source, state)
        for art in articles:
            if not is_duplicate_article(art, seen_this_run, state):
                seen_this_run.append(art)
                all_articles.append(art)
            time.sleep(source.get("rate_limit", 30) / 60.0 * 0.1)  # mini-delay

    # --- Scraping sources ---
    for source in SCRAPING_SOURCES:
        time.sleep(1)
        articles = fetch_scraping(source, state)
        for art in articles:
            if not is_duplicate_article(art, seen_this_run, state):
                seen_this_run.append(art)
                all_articles.append(art)

    # --- ACLED ---
    acled_articles = fetch_acled(state)
    for art in acled_articles:
        if not is_duplicate_article(art, seen_this_run, state):
            seen_this_run.append(art)
            all_articles.append(art)

    log.info("Total articulos unicos recopilados: %d", len(all_articles))

    # --- Score each article ---
    all_hits = []
    for art in all_articles:
        hits = score_article(art)
        hits = analyze_with_gemini(art, hits)
        all_hits.extend(hits)
        if hits:
            log.debug("%s -> %d hits (max bruto: %.2f)",
                      art.get("title","?")[:60],
                      len(hits),
                      max(abs(h["score_bruto"]) for h in hits))

    log.info("Total hits de scoring: %d", len(all_hits))

    # --- Compute totals ---
    ssc, smc = aggregate_scores(all_hits)
    level_ssc_name, _ = level_ssc(ssc)
    level_smc_name, _ = level_smc(smc)
    log.info("SSC=%.2f (%s) | SMC=%.2f (%s)", ssc, level_ssc_name, smc, level_smc_name)

    # --- Update state ---
    for art in all_articles:
        if art.get("url"):
            mark_url_processed(state, art["url"])

    state["last_run"] = datetime.now(timezone.utc).isoformat()
    history_entry = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
        "ssc": ssc, "smc": smc,
        "nivel_ssc": level_ssc_name, "nivel_smc": level_smc_name,
        "num_hits": len(all_hits),
    }
    state.setdefault("score_history", []).append(history_entry)
    # Keep only last 90 entries
    state["score_history"] = state["score_history"][-90:]

    save_state(state)

    # --- Send alert if threshold exceeded ---
    if should_alert(ssc, smc):
        log.info("UMBRAL SUPERADO — generando y enviando email de alerta")
        subject, html_body = build_email(ssc, smc, all_hits, run_number)
        send_email(subject, html_body)
    else:
        log.info("Sin alerta — scores bajo umbral (SSC<31, SMC<41, combinacion no cumplida)")

    log.info("=== CobaltScorer finalizado ===")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# INSTRUCCIONES DE DESPLIEGUE Y CRON
# ---------------------------------------------------------------------------
#
# 1. ESTRUCTURA DE DIRECTORIOS
# ============================
# Crear los directorios necesarios en GCP e2-micro:
#
#   mkdir -p ~/cobalt-alert/logs
#   chmod 700 ~/cobalt-alert
#
# 2. ARCHIVO .env
# ===============
# Crear ~/cobalt-alert/.env con el siguiente contenido:
#
#   SMTP_HOST=smtp.gmail.com
#   SMTP_PORT=587
#   SMTP_USER=tu_cuenta@gmail.com
#   SMTP_PASS=tu_app_password_de_gmail
#   ALERT_TO=tu_destino@gmail.com
#   ACLED_KEY=tu_clave_acled               # Registrarse gratis en developer.acleddata.com
#   ACLED_EMAIL=tu_email@gmail.com
#   BOT_EMAIL=tu_email@gmail.com
#
#   NOTA Gmail: usar "Contrasenas de aplicacion" (App Passwords), no la contrasena
#   normal de la cuenta. Activar en: myaccount.google.com/apppasswords
#
#   chmod 600 ~/cobalt-alert/.env
#
# 3. INSTALACION DE DEPENDENCIAS
# ================================
#   pip3 install --user feedparser requests beautifulsoup4 lxml python-dateutil
#
#   Verificar instalacion:
#   python3 -c "import feedparser, requests, bs4, lxml, dateutil; print('OK')"
#
# 4. UBICACION DEL SCRIPT
# ========================
#   cp main_scorer.py ~/cobalt-alert/main_scorer.py
#   chmod 755 ~/cobalt-alert/main_scorer.py
#
# 5. PRUEBA MANUAL
# =================
#   cd ~/cobalt-alert
#   python3 main_scorer.py
#
#   Verificar que:
#   - Se crea ~/cobalt-alert/state.json
#   - Se crea ~/cobalt-alert/logs/scorer.log con entradas
#   - No hay errores de importacion
#
# 6. CONFIGURACION DEL CRON JOB
# ================================
#   Editar crontab:
#   crontab -e
#
#   Anadir las siguientes 3 lineas (ejecuta a las 00:00, 08:00 y 16:00 UTC):
#
#   0  0 * * * /usr/bin/python3 /home/TU_USUARIO/cobalt-alert/main_scorer.py >> /home/TU_USUARIO/cobalt-alert/logs/cron.log 2>&1
#   0  8 * * * /usr/bin/python3 /home/TU_USUARIO/cobalt-alert/main_scorer.py >> /home/TU_USUARIO/cobalt-alert/logs/cron.log 2>&1
#   0 16 * * * /usr/bin/python3 /home/TU_USUARIO/cobalt-alert/main_scorer.py >> /home/TU_USUARIO/cobalt-alert/logs/cron.log 2>&1
#
#   NOTA: Reemplazar TU_USUARIO con el usuario real de la VM (ej: 'ubuntu', 'usuario').
#   Verificar la ruta de python3: which python3
#
#   Verificar que el cron esta activo:
#   crontab -l
#
# 7. VERIFICACION DE ZONA HORARIA DE LA VM
# ==========================================
#   Las horas del cron son UTC. Para confirmar que la VM usa UTC:
#   timedatectl | grep "Time zone"
#
#   Si la VM esta en UTC, las ejecuciones corresponden a:
#   - 00:00 UTC = 02:00 Madrid (hora de verano CEST)
#   - 08:00 UTC = 10:00 Madrid
#   - 16:00 UTC = 18:00 Madrid
#
# 8. ROTACION DE LOGS
# ====================
#   El script usa TimedRotatingFileHandler con backupCount=7 (7 dias).
#   Los logs en logs/cron.log NO rotan automaticamente. Para evitar crecimiento:
#
#   Anadir a crontab (limpieza semanal del log de cron):
#   0 3 * * 0 truncate -s 0 /home/TU_USUARIO/cobalt-alert/logs/cron.log
#
# 9. MONITOREO DE SALUD
# ======================
#   Ver estado de fuentes:
#   python3 -c "import json; s=json.load(open('/home/TU_USUARIO/cobalt-alert/state.json')); [print(k,v['status'],v.get('consecutive_failures',0)) for k,v in s.get('source_health',{}).items()]"
#
#   Ver ultimos scores:
#   python3 -c "import json; s=json.load(open('/home/TU_USUARIO/cobalt-alert/state.json')); [print(h['date'],h['ssc'],h['nivel_ssc'],h['smc'],h['nivel_smc']) for h in s.get('score_history',[])[-10:]]"
#
#   Ver cola de logs en tiempo real durante prueba:
#   tail -f ~/cobalt-alert/logs/scorer.log
