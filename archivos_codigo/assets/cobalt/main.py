#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""assets.cobalt.main — Orquestador del sistema de alerta de cobalto.

Punto de entrada del cron. Importa SOLO del framework y del dictionary; toda
la lógica genérica vive bajo `framework/`.

Ejecutar: python3 -m assets.cobalt.main
Cron:     0 0,8,16 * * * /usr/bin/python3 -m assets.cobalt.main

Modos test (no envían email, no llaman fuentes reales):
    COBALT_TEST_MODE=1                   activa la suite sintética
    COBALT_TEST_MODE=1 COBALT_TEST_NO_GEMINI=1   también omite cuota Gemini
"""

import logging
import os
import smtplib
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from assets.cobalt.dictionary import COBALT_CONFIG
from framework.aggregator import aggregate_scores, level_smc, level_ssc, should_alert
from framework.llm_validator import analyze_with_gemini, make_gemini_client
from framework.scoring import score_article
from framework.sources import (
    fetch_acled,
    fetch_gnews,
    fetch_news_api,
    fetch_rss,
    fetch_scraping,
    make_session,
)
from framework.state import (
    compute_run_number,
    is_duplicate_article,
    load_env,
    load_state,
    mark_url_processed,
    purge_old_urls,
    save_state,
)
from tests.synthetic_articles import (
    is_no_gemini_active,
    is_test_mode_active,
    run_gemini_test,
)

# ---------------------------------------------------------------------------
# 0. PATHS Y CONFIGURACIÓN
# ---------------------------------------------------------------------------

# BASE_DIR se autodetecta:
#   1) Si hay un .env junto al propio script → usa ese directorio (dev local en Windows).
#   2) Si no, usa ~/cobalt-alert/ (producción en la VM GCP).
_SCRIPT_DIR = Path(__file__).resolve().parent
_HOME_DIR = Path.home() / "cobalt-alert"
BASE_DIR = _SCRIPT_DIR if (_SCRIPT_DIR / ".env").exists() else _HOME_DIR

ENV_FILE = BASE_DIR / ".env"
STATE_FILE = BASE_DIR / "state.json"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "scorer.log"

BASE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. LOGGING — raíz (todos los módulos del framework loguean a este logger)
# ---------------------------------------------------------------------------

# En modo test (COBALT_TEST_MODE=1) NO escribimos al log file de producción —
# solo consola. Tests sintéticos no deben contaminar el histórico del cron real.
_IN_TEST_MODE = os.environ.get("COBALT_TEST_MODE") == "1"

root_log = logging.getLogger()
root_log.setLevel(logging.INFO)

if not root_log.handlers:
    _console_handler = logging.StreamHandler()
    _console_handler.setFormatter(logging.Formatter("%(levelname)-8s %(name)s %(message)s"))
    root_log.addHandler(_console_handler)

    if not _IN_TEST_MODE:
        # Solo en modo producción: añadir el log a archivo rotativo.
        # `TimedRotatingFileHandler` abre el fichero al instanciarlo, así que
        # también es importante NO instanciarlo en modo test para no tocar
        # `scorer.log` ni siquiera para escribir una cabecera.
        _file_handler = TimedRotatingFileHandler(
            LOG_FILE, when="midnight", interval=1, backupCount=7, encoding="utf-8"
        )
        _file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-8s %(name)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%SZ",
            )
        )
        root_log.addHandler(_file_handler)

log = logging.getLogger("cobalt_scorer")

# ---------------------------------------------------------------------------
# 2. CARGA DE CREDENCIALES (.env)
# ---------------------------------------------------------------------------

ENV = load_env(ENV_FILE)

SMTP_HOST = ENV.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(ENV.get("SMTP_PORT", "587"))
SMTP_USER = ENV.get("SMTP_USER", "")
SMTP_PASS = ENV.get("SMTP_PASS", "")
ALERT_TO = ENV.get("ALERT_TO", SMTP_USER)
ACLED_KEY = ENV.get("ACLED_KEY", "")
ACLED_EMAIL = ENV.get("ACLED_EMAIL", "")
BOT_EMAIL = ENV.get("BOT_EMAIL", SMTP_USER)
GEMINI_API_KEY = ENV.get("GEMINI_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
NEWSAPI_KEY = ENV.get("NEWSAPI_KEY", "") or os.environ.get("NEWSAPI_KEY", "")
GNEWS_KEY = ENV.get("GNEWS_KEY", "") or os.environ.get("GNEWS_KEY", "")

# ---------------------------------------------------------------------------
# 3. EMAIL — datos cobalto-específicos para la composición HTML
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
    "300750.SZ": ("CATL", "Shenzhen",
                  False, "Mayor fabricante baterias; margen comprimido con cobalto caro"),
}

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


def select_assets(hits: list, ssc: float, smc: float) -> list:
    """Devuelve lista de (ticker, name, direction, horizon, reason) para emails."""
    cats = set(h["category"] for h in hits)
    geos = set(g for h in hits for g in h.get("geo_codes", []))
    selected: dict = {}

    def add(ticker: str, direction: str, horizon: str) -> None:
        if ticker in ASSET_TABLE and ticker not in selected:
            name, exchange, pos, reason = ASSET_TABLE[ticker]
            selected[ticker] = (ticker, name, direction, horizon, reason)

    # LOG events en puertos clave
    if any(c.startswith("LOG") for c in cats):
        if geos & {"GEO-08", "GEO-03A", "GEO-03B", "GEO-04"}:
            for t in ["LIT", "REMX", "UMI.BR"]:
                add(t, "LARGO", "1-3 semanas")

    # Conflicto o coup en DRC
    if cats & {"GEO-CONFLICT", "GEO-COUP"}:
        if "GEO-01" in geos:
            for t in ["GLEN.L", "LIT", "COPX", "REMX"]:
                add(t, "LARGO", "1-3 semanas")

    # Export ban — max alert
    if "REG-EXPORT-BAN" in cats:
        for t in ["LIT", "REMX", "GLEN.L", "UMI.BR", "BATT"]:
            add(t, "LARGO", "inmediato — 1-2 semanas")

    # Cualquier disrupción de suministro — LIT como señal general
    if ssc >= 20 or smc >= 30:
        add("LIT", "LARGO", "1-3 semanas")
        add("UMI.BR", "LARGO", "2-4 semanas")

    # SMC alto: activos negativos
    if smc > 50:
        add("DRIV", "CORTO", "3-6 semanas")
        add("IDRV", "CORTO", "3-6 semanas")
        add("300750.SZ", "CORTO", "2-4 semanas")

    return list(selected.values())


def build_event_cards(hits: list) -> str:
    """Build HTML event cards from top 5 unique events by absolute score."""
    seen_keys: set = set()
    top_hits: list = []
    for h in sorted(hits, key=lambda x: abs(x["score_bruto"]), reverse=True):
        key = f"{h['category']}__{h['best_geo']}"
        if key not in seen_keys:
            seen_keys.add(key)
            top_hits.append(h)
        if len(top_hits) >= 5:
            break

    cards = ""
    now = datetime.now(timezone.utc)
    for h in top_hits:
        diff = now - h["pub_date"]
        if diff.total_seconds() < 3600:
            age_str = f"hace {int(diff.total_seconds() / 60)} minutos"
        elif diff.total_seconds() < 86400:
            age_str = f"hace {int(diff.total_seconds() / 3600)} horas"
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
    level_ssc_name, color_ssc = level_ssc(ssc, COBALT_CONFIG)
    level_smc_name, color_smc = level_smc(smc, COBALT_CONFIG)

    overall_levels = [level_ssc_name, level_smc_name]
    level_order = ["VERDE", "AMARILLO", "NARANJA", "ROJO"]
    nivel_alerta = max(overall_levels, key=lambda x: level_order.index(x))
    color_nivel = nivel_alerta.lower()

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    subject = f"[COBALT-ALERT] {nivel_alerta} | SSC:{ssc:.1f} SMC:{smc:.1f} | {now_str} UTC"

    # Categoría dominante
    cat_counts: dict = {}
    for h in hits:
        cat_counts[h["category"]] = cat_counts.get(h["category"], 0) + abs(h["score_bruto"])
    dominant_cat = max(cat_counts, key=cat_counts.get) if cat_counts else "DEFAULT"

    # Resumen ejecutivo
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
  <h2 style="margin:0">Alerta de Riesgo de Suministro — {COBALT_CONFIG.asset_display}</h2>
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
  Mineral: {COBALT_CONFIG.asset_display} | scoring_rules.md v1.0 + keyword_dictionary.md v1.0<br>
  Frecuencia: 3x/dia (00:00, 08:00, 16:00 UTC) | GCP e2-micro
</div>

</body>
</html>"""

    return subject, html


def send_email(subject: str, html_body: str) -> None:
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
# 4. MAIN LOOP
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== CobaltScorer iniciando ===")
    state = load_state(STATE_FILE)

    # Modo test: corre la suite sintética y termina sin tocar red ni email
    if is_test_mode_active():
        gemini_client = None if is_no_gemini_active() else make_gemini_client(GEMINI_API_KEY)
        run_gemini_test(COBALT_CONFIG, gemini_client)
        return

    purge_old_urls(state, hours=72)
    run_number = compute_run_number(state)
    log.info("Ejecucion %d del dia %s", run_number, state["last_run_date"])

    session = make_session(BOT_EMAIL)
    gemini_client = make_gemini_client(GEMINI_API_KEY)

    all_articles: list = []
    seen_this_run: list = []

    # --- RSS sources ---
    for source in COBALT_CONFIG.rss_sources:
        time.sleep(0.5)  # politeness
        articles = fetch_rss(source, state, session)
        for art in articles:
            if not is_duplicate_article(art, seen_this_run, state):
                seen_this_run.append(art)
                all_articles.append(art)
            time.sleep(source.get("rate_limit", 30) / 60.0 * 0.1)

    # --- Scraping sources ---
    for source in COBALT_CONFIG.scraping_sources:
        time.sleep(1)
        articles = fetch_scraping(source, state, session)
        for art in articles:
            if not is_duplicate_article(art, seen_this_run, state):
                seen_this_run.append(art)
                all_articles.append(art)

    # --- ACLED ---
    acled_articles = fetch_acled(state, session, ACLED_KEY, ACLED_EMAIL)
    for art in acled_articles:
        if not is_duplicate_article(art, seen_this_run, state):
            seen_this_run.append(art)
            all_articles.append(art)

    # --- NewsAPI.org (queries cobalto-específicas, 24h delay free tier) ---
    # 9 req/día con 3 queries × 3 runs/día. Free tier permite 100/día.
    # full_text=True descarga la página completa para superar el truncado de
    # ~200ch del free tier (audit forense 2026-05-17).
    newsapi_articles = fetch_news_api(
        state, session, NEWSAPI_KEY, COBALT_CONFIG.news_api_queries,
        full_text=COBALT_CONFIG.news_api_full_text,
    )
    for art in newsapi_articles:
        if not is_duplicate_article(art, seen_this_run, state):
            seen_this_run.append(art)
            all_articles.append(art)

    # --- GNews.io (queries cobalto-específicas, real-time) ---
    # Complementario a NewsAPI: API separada (100 req/día propios), sin delay.
    # Mismas queries por simplicidad; los duplicados con NewsAPI los filtra
    # is_duplicate_article (URL match). Total combinado: 200 req/día efectivos.
    gnews_articles = fetch_gnews(
        state, session, GNEWS_KEY, COBALT_CONFIG.gnews_queries,
        full_text=COBALT_CONFIG.gnews_full_text,
    )
    for art in gnews_articles:
        if not is_duplicate_article(art, seen_this_run, state):
            seen_this_run.append(art)
            all_articles.append(art)

    log.info("Total articulos unicos recopilados: %d", len(all_articles))

    # --- Score each article ---
    all_hits: list = []
    for art in all_articles:
        hits = score_article(art, COBALT_CONFIG)
        hits = analyze_with_gemini(art, hits, COBALT_CONFIG, gemini_client)
        all_hits.extend(hits)
        if hits:
            # INFO log por artículo con hits — observabilidad esencial para
            # diagnóstico continuo. Muestra qué keywords disparan, en qué
            # categoría, con qué score signed. Sin esto los runs son cajas
            # negras: SSC=X sin saber qué keywords están contribuyendo.
            # Top 5 hits por |score| para evitar líneas eternas en feeds
            # ruidosos.
            hits_summary = ", ".join(
                f"{h['keyword']}({h['category']},{h['score_bruto']:+.1f})"
                for h in sorted(hits, key=lambda x: abs(x["score_bruto"]), reverse=True)[:5]
            )
            geos_set = sorted({h["best_geo"] for h in hits if h["best_geo"]})
            log.info(
                "HIT [%s] source=%s geo=%s n=%d | %s",
                art.get("title", "?")[:70],
                art.get("source_name", "?"),
                ",".join(geos_set) or "-",
                len(hits),
                hits_summary,
            )

    log.info("Total hits de scoring: %d", len(all_hits))

    # --- Compute totals ---
    ssc, smc = aggregate_scores(all_hits, COBALT_CONFIG)
    level_ssc_name, _ = level_ssc(ssc, COBALT_CONFIG)
    level_smc_name, _ = level_smc(smc, COBALT_CONFIG)
    log.info("SSC=%.2f (%s) | SMC=%.2f (%s)", ssc, level_ssc_name, smc, level_smc_name)

    # --- Update state ---
    for art in all_articles:
        if art.get("url"):
            mark_url_processed(state, art["url"])

    state["last_run"] = datetime.now(timezone.utc).isoformat()
    state.setdefault("score_history", []).append({
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
        "ssc": ssc, "smc": smc,
        "nivel_ssc": level_ssc_name, "nivel_smc": level_smc_name,
        "num_hits": len(all_hits),
    })
    state["score_history"] = state["score_history"][-90:]

    save_state(state, STATE_FILE)

    # --- Send alert if threshold exceeded ---
    if should_alert(ssc, smc, COBALT_CONFIG):
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
