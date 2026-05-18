"""framework.scoring — Núcleo de scoring genérico.

Toda función que dependía de variables globales de cobalto ahora recibe un
`AssetConfig` con los datos del asset concreto. Las funciones de texto puro
(normalize, tokenize, simple_similarity) no necesitan config.

Fix history preservado (ver `scoring_rules.md` para spec):
  - Punto A: todas las ocurrencias de un keyword se evalúan, no solo la primera.
  - Punto B: el filtro de falsos positivos se aplica por ocurrencia, no global.
  - Punto C: segundo umbral 1.0 post-multiplicadores limpia residuo.
  - Punto D: negación de peso negativo invierte signo semántico.
"""

import logging
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger("framework.scoring")


# ---------------------------------------------------------------------------
# AssetConfig — todo lo que el framework necesita saber sobre el asset
# ---------------------------------------------------------------------------

@dataclass
class AssetConfig:
    """Configuración completa de un asset (cobalt, copper, …).

    Cada asset bajo `assets/<name>/dictionary.py` instancia este dataclass
    con sus keywords, geo, umbrales y prompts. Los módulos del framework
    reciben esta instancia como parámetro y nunca leen estado global.
    """

    # Identidad
    asset_name: str                  # "cobalt", "copper", …
    asset_display: str               # "COBALTO", "COBRE", … (para emails)

    # Dictionary — texto y categorías
    anchor_terms: list               # términos ancla (filtran requires_context)
    geographic_terms: dict           # {GEO_CODE: [términos, …]}
    geo_weights: dict                # {GEO_CODE: float}
    keywords: list                   # [(term, category, weight, requires_context, window, geo_boost), …]
    category_multipliers: dict       # {category: float} — multiplicador score
    ssc_category_weights: dict       # {category: float} — peso en SSC
    smc_category_overrides: dict     # {category: float} — override en SMC
    all_negation_terms: set          # set normalizado de términos de negación
    coup_context_terms: list         # términos que validan "coup" como real
    false_positive_filters: dict     # {category: [patrones FP, …]}
    source_credibility: dict         # {source_name: 0.0–1.0}

    # Fuentes
    rss_sources: list                # lista de dicts {name, url, lang, …}
    scraping_sources: list           # lista de dicts (portales sin RSS)

    # Niveles (semáforo) — listas ordenadas: [(umbral_max, nombre, color), …]
    # El primer tuple con `score < umbral_max` gana. Último entry es el "infinito".
    ssc_levels: list                 # ej. [(16,"VERDE","verde"), (31,"AMARILLO","amarillo"), …]
    smc_levels: list

    # Trigger de alerta
    alert_thresholds: dict           # {"ssc_min": 31, "smc_min": 41, "combined_ssc": 20, "combined_smc": 30}

    # Filtros geográficos genéricos (sin GEO específico pero con menciones vagas)
    generic_geo_terms: list          # ej. ["africa", "emerging markets", "developing countries"]
    generic_only_penalty: float = 0.40   # multiplicador cuando solo hay geo genérico

    # Umbrales internos del scoring
    raw_min_threshold: float = 3.0        # corte tras score_bruto antes de modifs
    final_min_threshold: float = 1.0      # corte residual post-modifs (fix punto C)
    negation_attenuation: float = 0.15    # factor aplicado a hits negados

    # Gemini
    gemini_score_threshold: float = 8.0   # Path A: max score que activa YES/NO
    gemini_context_min: int = 3            # Path B: mínimo context terms para multiplicador
    context_trigger_terms: list = field(default_factory=list)
    gemini_validate_prompt: str = ""       # template; se formatea con title/body
    gemini_multiplier_prompt: str = ""     # template; idem

    # Categorías que no decaen por edad (REG, sanciones — la tensión persiste)
    no_decay_categories: set = field(default_factory=set)

    # NewsAPI.org queries (opcional). Si presente y NEWSAPI_KEY está configurado
    # en el entorno, `fetch_news_api()` se invoca con estas queries en cada run.
    # Cada query gasta 1 request del cuota del free tier (100 req/día). 3 queries
    # × 3 runs/día = 9 req/día, muy dentro del límite.
    news_api_queries: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Utilidades de texto (sin estado, sin config)
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


def tokenize(text: str) -> list:
    """Normalize y split en palabras (para búsquedas por ventana)."""
    return normalize(text).split()


# ---------------------------------------------------------------------------
# Checks dependientes de config
# ---------------------------------------------------------------------------

def has_anchor(text_norm: str, anchor_terms: list) -> bool:
    """True si algún término ancla aparece en el texto normalizado."""
    for anchor in anchor_terms:
        if normalize(anchor) in text_norm:
            return True
    return False


def has_coup_context(words: list, kw_pos: int, coup_context_terms: list, window: int = 40) -> bool:
    """True si al menos un término geo/político aparece en ±window de la ocurrencia."""
    start = max(0, kw_pos - window)
    end = min(len(words), kw_pos + window + 1)
    window_slice = set(words[start:end])
    return any(t in window_slice for t in coup_context_terms)


def has_negation_near(words: list, kw_pos: int, all_negation_terms: set, window: int = 5) -> bool:
    """Detecta negación en ±window palabras de la posición del keyword."""
    start = max(0, kw_pos - window)
    end = min(len(words), kw_pos + window + 1)
    context = words[start:end]
    for neg in all_negation_terms:
        if normalize(neg) in context:
            return True
    return False


def occurrence_is_false_positive(
    text_norm: str, pos: int, term_norm: str, category: str, false_positive_filters: dict
) -> bool:
    """
    True si la ocurrencia de term_norm en `pos` forma parte de un patrón FP conocido
    (ej: 'coup' dentro de 'coup de grace').

    Fix punto B: antes era global al artículo; ahora se evalúa por ocurrencia,
    de modo que un FP en el párrafo 10 no anula menciones reales en el párrafo 1.
    """
    patterns = false_positive_filters.get(category, [])
    for pat in patterns:
        pat_norm = normalize(pat)
        idx_in_pat = pat_norm.find(term_norm)
        if idx_in_pat == -1:
            continue
        pat_start = pos - idx_in_pat
        if pat_start < 0:
            continue
        if text_norm[pat_start:pat_start + len(pat_norm)] == pat_norm:
            return True
    return False


def detect_geo(text_norm: str, geographic_terms: dict) -> list:
    """Devuelve lista de GEO codes detectados en el texto normalizado."""
    found: list = []
    for geo_code, terms in geographic_terms.items():
        for t in terms:
            if normalize(t) in text_norm:
                if geo_code not in found:
                    found.append(geo_code)
                break
    return found


def age_factor(pub_date: datetime, category: str, no_decay_categories: set) -> float:
    """
    Factor de decaimiento por edad.

    REG y GEO-SANCTION (en `no_decay_categories`) no decaen: la tensión
    regulatoria persiste hasta una resolución explícita.
    """
    now = datetime.now(timezone.utc)
    age_hours = (now - pub_date).total_seconds() / 3600.0
    age_days = age_hours / 24.0

    if category in no_decay_categories:
        return 1.0
    if age_days > 7:
        return 0.10
    if age_hours > 72:
        if category.startswith("LOG") or category.startswith("LAB"):
            return 0.30
        return 0.60
    return 1.0


# ---------------------------------------------------------------------------
# score_article — corazón del scoring por artículo
# ---------------------------------------------------------------------------

def score_article(article: dict, cfg: AssetConfig) -> list:
    """
    Puntúa un artículo contra todos los keywords del asset.

    Returns: lista de hits — {keyword, category, score_bruto, geo_codes, …}

    La fórmula y los fixes A/B/C/D están documentados en `scoring_rules.md`.
    """
    full_text = (article.get("title", "") + " " + article.get("body", ""))
    text_norm = normalize(full_text)
    words = text_norm.split()
    geos = detect_geo(text_norm, cfg.geographic_terms)
    has_specific_geo = len(geos) > 0

    # Geo genérico (Africa, emerging markets…) sin GEO específico
    generic_only = (
        not has_specific_geo and
        any(normalize(g) in text_norm for g in cfg.generic_geo_terms)
    )

    hits: list = []
    for (term, category, weight, requires_context, context_window, geo_boost) in cfg.keywords:
        term_norm = normalize(term)

        # Fix punto A: recolectar TODAS las ocurrencias válidas (no solo la primera).
        # Una primera mención negada no debe bloquear menciones positivas posteriores.
        # Fix punto B: el filtro FP se evalúa por ocurrencia, no global.
        valid_occurrences = []
        search_start = 0
        while True:
            pos = text_norm.find(term_norm, search_start)
            if pos == -1:
                break
            word_pos = len(text_norm[:pos].split())

            if requires_context:
                window_start = max(0, word_pos - context_window)
                window_end = min(len(words), word_pos + context_window)
                window_text = " ".join(words[window_start:window_end])
                if not has_anchor(window_text, cfg.anchor_terms):
                    search_start = pos + len(term_norm)
                    continue
            if term_norm == "coup" and not has_coup_context(words, word_pos, cfg.coup_context_terms, window=40):
                search_start = pos + len(term_norm)
                continue
            if occurrence_is_false_positive(text_norm, pos, term_norm, category, cfg.false_positive_filters):
                search_start = pos + len(term_norm)
                continue

            negated = has_negation_near(words, word_pos, cfg.all_negation_terms, window=5)
            valid_occurrences.append({"word_pos": word_pos, "negated": negated})
            search_start = pos + len(term_norm)

        if not valid_occurrences:
            continue

        # Mejor ocurrencia: cualquier no-negada gana sobre negadas.
        non_negated = [o for o in valid_occurrences if not o["negated"]]
        best = non_negated[0] if non_negated else valid_occurrences[0]
        word_pos = best["word_pos"]
        negated = best["negated"]

        # Mejor geo weight (detectado + boost específico del keyword)
        best_geo_weight = 1.0
        best_geo_code: Optional[str] = None
        for geo in geos:
            gw = cfg.geo_weights.get(geo, 1.0)
            if gw > best_geo_weight:
                best_geo_weight = gw
                best_geo_code = geo
        for gb in geo_boost:
            if gb in geos:
                gw = cfg.geo_weights.get(gb, 1.0)
                if gw > best_geo_weight:
                    best_geo_weight = gw
                    best_geo_code = gb

        cat_mult = abs(cfg.category_multipliers.get(category, 1.0))
        cred = cfg.source_credibility.get(article["source_name"], 0.70)
        age_f = age_factor(article["pub_date"], category, cfg.no_decay_categories)

        # Umbral mínimo se evalúa sobre el bruto SIN penalización (scoring_rules.md §6.6 y §7)
        score_bruto = abs(weight) * best_geo_weight * cat_mult * cred

        if score_bruto < cfg.raw_min_threshold:
            continue

        # Negación: una sola aplicación, post-umbral.
        if negated:
            score_bruto *= cfg.negation_attenuation

        score_bruto *= age_f

        # Generic geo penalty
        if not has_specific_geo:
            if generic_only:
                score_bruto *= cfg.generic_only_penalty
            else:
                continue  # sin contexto geográfico, descartar

        # Fix punto C: segundo umbral post-multiplicadores limpia residuo.
        # Sin esto, un hit negado + age decay + geo genérico podía quedar en
        # 0.07 y contaminar el agregado.
        if score_bruto < cfg.final_min_threshold:
            continue

        # Signo:
        #   - Pesos positivos (disrupciones): siempre +1. Negación atenúa magnitud
        #     (×0.15) pero mantiene el signo — "huelga cancelada" sigue siendo
        #     señal débil de disrupción, no señal contraria.
        #   - Pesos negativos (DEM-SUBSTITUTE, RES-RESOLVE): -1 por defecto.
        #     Si están negados, fix punto D invierte el signo: "LFP no reemplaza
        #     cobalto" pasa a ser señal positiva para la demanda.
        if weight < 0:
            sign = +1 if negated else -1
        else:
            sign = 1

        hits.append({
            "keyword": term,
            "category": category,
            "score_bruto": round(score_bruto * sign, 3),
            "geo_codes": geos,
            "best_geo": best_geo_code,
            "pub_date": article["pub_date"],
            "source_name": article["source_name"],
            "url": article.get("url", ""),
            "title": article.get("title", ""),
            "negated": negated,
        })

    return hits
