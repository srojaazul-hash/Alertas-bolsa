"""tests.synthetic_articles — Suite sintética de regresión.

Cada artículo y caso de cluster es un test de regresión permanente. Cubren:

  Artículo 1   Path A YES esperado (disrupción real DRC, score >> 8.0)
  Artículo 2   Path A NO esperado (falso positivo: chocolatería)
  Artículo 3   Path B x1.5 esperado (cadena de suministro China)
  Artículo 4   Path B x0.0 esperado (semiconductores, no cobalto)
  Artículo 5   Sin Gemini esperado (score 3.0–8.0, < 3 context terms)
  Artículo 6   Fix A — múltiples ocurrencias (primera negada, posteriores reales)
  Artículo 7   Fix B — FP localizado ("coup de grace" + military takeover real)
  Artículo 8   Fix C — filtro residual post-multiplicadores (descarta hit 0.07)
  Artículo 9   Fix D — negación invierte signo en DEM-SUBSTITUTE

  Cluster F1   Fix F — mismo evento cruzando medianoche UTC se mantiene unido
  Cluster F2   Fix F — eventos distintos (30h apart) siguen separados
  Cluster F3   Fix F — 3 fuentes high-cred cruzando medianoche → bonus ×1.30
  Cluster F4   Fix F — distinto geo siempre = clusters distintos

`run_gemini_test(cfg, client)` ejecuta toda la suite. Si `client` es None,
Path A/B real se omite (modo COBALT_TEST_NO_GEMINI). Diseñado para no consumir
cuota durante iteración.
"""

import logging
import os
from datetime import datetime, timezone, timedelta

from framework.aggregator import aggregate_scores
from framework.llm_validator import analyze_with_gemini, count_context_hits, is_available
from framework.scoring import AssetConfig, score_article

log = logging.getLogger("tests.synthetic_articles")


# ---------------------------------------------------------------------------
# Artículos sintéticos (textos cobalto-específicos por necesidad de los fixes)
# ---------------------------------------------------------------------------

def build_test_articles() -> list:
    """Construye los 9 artículos sintéticos con `pub_date` en runtime."""
    now = datetime.now(timezone.utc)
    return [
        # --- Artículo 1: Path A YES esperado ---
        {
            "title": "Armed conflict near Kolwezi halts cobalt mining operations in DRC",
            "body": (
                "An armed conflict erupted overnight in the Lualaba province near Kolwezi, "
                "forcing major cobalt mining sites in the DRC Copperbelt to suspend operations. "
                "Militia attack reports from Katanga indicate that several mine sites in "
                "Lubumbashi and Fungurume were targeted. Cobalt production at Tenke Fungurume "
                "is on hold and cobalt supply is severely affected. Industry analysts warn that "
                "the cobalt market will tighten in coming weeks as security forces struggle to "
                "restore order. The rebel attack on a mine in Lualaba is the worst incident in "
                "months and threatens battery-grade cobalt feedstock destined for refineries. "
                "Workers on strike were not involved; this is purely a security incident mine event."
            ),
            "url": "https://test.local/article-1-drc-conflict",
            "pub_date": now,
            "source_name": "northern_miner",
            "lang": "en",
        },
        # --- Artículo 2: Path A NO esperado (falso positivo) ---
        {
            "title": "Workers on strike at Cobalt Chocolatiers factory in Lubumbashi",
            "body": (
                "Employees at the Cobalt Chocolatiers confectionery plant in Lubumbashi launched "
                "a mining strike — pun intended by union leaders — to demand better working "
                "conditions in the chocolate factory. The artisanal sweets producer, whose brand "
                "trades on the 'cobalt' name purely for marketing reasons, has nothing to do with "
                "actual cobalt mining. The workers on strike will return after wage negotiations. "
                "Cobalt Chocolatiers operations are suspended only on the production line for "
                "pralines. The dispute does not affect any mine or cobalt feedstock supply. "
                "Local press in Katanga emphasised the symbolic naming and the fact that no "
                "cobalt market disruption is expected."
            ),
            "url": "https://test.local/article-2-chocolate-strike",
            "pub_date": now,
            "source_name": "allafrica",
            "lang": "en",
        },
        # --- Artículo 3: Path B x1.5 esperado ---
        {
            "title": "China cobalt refining capacity faces feedstock tightness, analysts warn",
            "body": (
                "Chinese cobalt refiners including Huayou Cobalt and Jiangxi Cobalt are seeing "
                "tighter feedstock availability, according to a new supply chain analysis. The "
                "report highlights how China's processing capacity dominates the global battery "
                "metals landscape, with critical mineral flows still routed through Zhejiang and "
                "Guangdong refineries. Downstream processing of cathode material relies on stable "
                "concentrate shipments, and any slowdown in raw material supply would reverberate "
                "through the EV supply chain. Industry observers note that cobalt shortage signals "
                "are visible across precursor producers, and that strategic reserve discussions "
                "in Beijing point to growing concern about hydrometallurgy bottlenecks. Offtake "
                "agreements with African suppliers remain the dominant route for upstream feedstock."
            ),
            "url": "https://test.local/article-3-china-feedstock",
            "pub_date": now,
            "source_name": "mining_technology",  # ex-mining_com_cobalt (eliminada en audit 2026-05-17)
            "lang": "en",
        },
        # --- Artículo 4: Path B x0.0 esperado (semiconductores) ---
        {
            "title": "Semiconductor supply chain stress mirrors past cobalt shortage episodes",
            "body": (
                "Analysts at a Sulawesi-based research firm note that the current semiconductor "
                "supply chain crunch in Indonesia resembles, in structure only, the cobalt shortage "
                "of 2022. Their report focuses entirely on chip fabrication, wafer feedstock, and "
                "the downstream processing of silicon. Critical mineral discussions in the paper "
                "refer to gallium and germanium, not battery metals. Mention of a refinery here "
                "refers to a silicon refinery, not a cobalt or nickel facility. The cathode material "
                "comparison is purely rhetorical; the authors stress that no cobalt feedstock or "
                "concentrate shipment issue is at play. Investors should not confuse this with raw "
                "material supply tightness in actual cobalt markets. The Indonesian government's "
                "strategic reserve plans target chips, not minerals."
            ),
            "url": "https://test.local/article-4-semiconductors",
            "pub_date": now,
            "source_name": "mongabay",
            "lang": "en",
        },
        # --- Artículo 5: Sin Gemini esperado ---
        {
            "title": "Indonesian nickel-cobalt output rises modestly at Morowali",
            "body": (
                "Indonesia's HPAL operations at Morowali reported a modest uptick in production "
                "this quarter. The Sulawesi facility, part of IMIP, continues steady output of "
                "intermediate products. Local officials in Halmahera confirmed no disruptions at "
                "Weda Bay. A cobalt supply deficit headline cited by one trader earlier this month "
                "appears to have been overstated. Markets reacted with little volatility and "
                "industry watchers see this as routine reporting rather than a flag. No strike, "
                "no closure, no regulatory action has been announced at the site."
            ),
            "url": "https://test.local/article-5-routine-indonesia",
            "pub_date": now,
            "source_name": "antara_business",
            "lang": "en",
        },
        # --- Artículo 6: Fix A — múltiples ocurrencias ---
        # Primera mención de "mining strike" negada por "cancelled". Las
        # posteriores son activas y reales. Pre-fix: score atenuado ×0.15.
        # Post-fix: la mejor ocurrencia no-negada gana → score completo.
        {
            "title": "Mining strike resumes at Tenke Fungurume after July truce",
            "body": (
                "The mining strike at Tenke Fungurume that was cancelled in July "
                "has resumed. A new mining strike began this morning in the "
                "Lualaba province. Workers at Mutanda have joined a new mining strike "
                "to demand wage revisions tied to the cobalt price spike. Cobalt "
                "production in the DRC Copperbelt is severely affected and union "
                "leaders confirm the mining strike will continue indefinitely until "
                "operators return to the negotiation table. Industry sources in "
                "Kolwezi describe the situation as the worst labor disruption in "
                "the cobalt sector this year."
            ),
            "url": "https://test.local/article-6-negation-recovery",
            "pub_date": now,
            "source_name": "northern_miner",
            "lang": "en",
        },
        # --- Artículo 7: Fix B — falsos positivos localizados ---
        # 'coup de grace' (FP figurativo) Y 'military takeover' (real) en el
        # mismo texto. Pre-fix: el FP anulaba toda la categoría GEO-COUP del
        # artículo. Post-fix: solo la ocurrencia dentro del patrón FP se descarta.
        {
            "title": "DRC president orders military takeover of artisanal cobalt sector",
            "body": (
                "The coup de grace for the informal mining sector came when president "
                "Tshisekedi ordered a sweeping military takeover of irregular sites "
                "in Lualaba province. The armed conflict that has plagued cobalt "
                "mining in the DRC Copperbelt entered a new phase as government forces "
                "moved into Kolwezi and Likasi. A mine attack near Tenke Fungurume was "
                "repelled this week according to security incident mine reports. "
                "Industry analysts in Lubumbashi describe the situation as the worst "
                "security disruption in the cobalt sector in five years, with "
                "production at multiple sites suspended on security grounds."
            ),
            "url": "https://test.local/article-7-fp-localization",
            "pub_date": now,
            "source_name": "northern_miner",
            "lang": "en",
        },
        # --- Artículo 8: Fix C — filtro residual post-multiplicadores ---
        # "vessel shortage" (LOG-VESSEL, peso 3.0) en northern_miner (cred 0.85):
        #   sin geo específico (×1.0) × LOG-VESSEL (×1.3) × 0.85 = 3.315 → pasa 3.0
        #   negado (cancelled) ×0.15 = 0.497
        #   pub_date hace 4 días, LOG-* > 72h ×0.30 = 0.149
        #   solo geo genérico "africa" ×0.40 = 0.060
        # Pre-fix C: hit emitido con score 0.06 (ruido en aggregate_scores).
        # Post-fix C: hit descartado por el segundo umbral (< 1.0).
        {
            "title": "Vessel shortage concerns cancelled by African shipping authorities",
            "body": (
                "Industry sources have cancelled the vessel shortage warnings "
                "issued last week regarding cobalt market exports. Africa-wide "
                "carriers confirm operations across the continent will resume "
                "as normal in the coming days, with no further vessel shortage "
                "expected at this stage."
            ),
            "url": "https://test.local/article-8-residue-filter",
            "pub_date": now - timedelta(days=4),
            "source_name": "northern_miner",
            "lang": "en",
        },
        # --- Artículo 9: Fix D — negación invierte signo en DEM-SUBSTITUTE ---
        # "lfp battery" (DEM-SUBSTITUTE, peso -3.0) negado por "not". Mención
        # de DRC para que el score supere el umbral 1.0 post-fix C:
        #   3.0 × 1.80 (GEO-01) × 1.5 (DEM-SUBSTITUTE) × 1.00 = 8.10
        #   negado ×0.15 = 1.215 → pasa el umbral 1.0
        # Pre-fix D: sign = -1 → -1.215 (señal NEGATIVA incorrecta: "LFP no
        #   reemplaza cobalto" interpretado como bajada de demanda).
        # Post-fix D: sign = +1 (weight<0 AND negated) → +1.215 (señal POSITIVA
        #   correcta para la demanda de cobalto).
        # NB: este test está calibrado al filo del umbral 1.0. Necesita una
        # fuente con credibilidad=1.00 para que el cálculo de arriba se
        # mantenga (con cred=0.85 el hit cae bajo el umbral y desaparece).
        # Se usa `gdacs` (cred 1.00) por estabilidad — el source_name es
        # incidental al test, lo que importa es la rama del scoring.
        {
            "title": "LFP batteries have not replaced cobalt in EV markets, DRC analysts confirm",
            "body": (
                "Despite years of speculation, lfp battery technology has not "
                "displaced cobalt-based chemistries in premium EV segments. "
                "Industry observers in the DRC Copperbelt confirm that lfp "
                "battery adoption has not eliminated cobalt requirements. "
                "Analysts in Kolwezi say lfp battery shift forecasts have not "
                "materialized at the scale predicted by 2023 reports."
            ),
            "url": "https://test.local/article-9-dem-negation-inversion",
            "pub_date": now,
            "source_name": "gdacs",
            "lang": "en",
        },
        # --- Artículo 10: Cobertura keyword militar deployment ---
        # Gap encontrado en audit forense de NewsAPI (2026-05-17). Un artículo real
        # de The Conversation Africa decía: "DRC is sending in the military to guard
        # mines and critical minerals. Will it be enough?". El sistema tenía anchor
        # ("critical mineral") + geo (GEO-01) OK pero NINGÚN keyword del dictionary
        # cubría despliegue militar preventivo (sólo ataques activos / coup).
        # Tras añadir keywords "military deployment", "military to guard mines",
        # "militarization of mines", "soldiers deployed" (en EN/FR/ES/PT), este
        # tipo de señal puntua correctamente. Este test bloquea regresión: si los
        # keywords se eliminan accidentalmente, hits caería a 0.
        # Esperado: hits>=3, max_score>=10, path=A (max_score>=8 trigger Gemini Path A)
        {
            "title": "DRC sends in the military to guard cobalt mines after rebel threats in Kolwezi",
            "body": (
                "Kinshasa announced today that military deployment to the Kolwezi region "
                "would begin immediately. The military to guard mines initiative aims to "
                "protect strategic cobalt assets in the DRC Copperbelt. Soldiers deployed "
                "to key production sites in Lualaba province will safeguard critical "
                "minerals output amid escalating instability. Industry analysts in "
                "Lubumbashi confirm the militarization of mines is unprecedented and "
                "signals heightened supply chain risk for cobalt-dependent markets."
            ),
            "url": "https://test.local/article-10-military-deployment",
            "pub_date": now,
            "source_name": "northern_miner",
            "lang": "en",
        },
    ]


# ---------------------------------------------------------------------------
# Aggregate clustering tests (fix F)
# ---------------------------------------------------------------------------

def _run_aggregate_clustering_tests(cfg: AssetConfig) -> None:
    """Tests sintéticos del clustering temporal en aggregate_scores (fix F)."""
    log.info("--- Tests F: clustering temporal en aggregate_scores ---")

    def _mk_hit(score: float, pub_date: datetime, source: str = "northern_miner") -> dict:
        """Hit sintético — todos GEO-01/LAB-STRIKE-ACT."""
        return {
            "keyword": "mining strike",
            "category": "LAB-STRIKE-ACT",
            "score_bruto": score,
            "geo_codes": ["GEO-01"],
            "best_geo": "GEO-01",
            "pub_date": pub_date,
            "source_name": source,
            "url": "test://aggregate",
            "title": "synthetic",
            "negated": False,
        }

    midnight = datetime(2026, 5, 15, 0, 0, tzinfo=timezone.utc)

    # Caso 1: mismo evento cruzando medianoche UTC (30 min)
    # Pre-fix F: 2 buckets distintos → ssc = 18 + 18*0.5 = 27.0
    # Post-fix F: 1 cluster → ssc = 18.0
    ssc, smc = aggregate_scores([
        _mk_hit(18.0, midnight - timedelta(minutes=20)),
        _mk_hit(18.0, midnight + timedelta(minutes=10)),
    ], cfg)
    log.info("F Caso 1 (mismo evento cruzando medianoche, 30min): SSC=%.2f SMC=%.2f"
             "  [esperado post-fix: SSC=18.00 — pre-fix habria sido 27.00]", ssc, smc)

    # Caso 2: 2 hits realmente distintos (30h apart) → sin cambio
    # Ambos pre y post-fix: 2 clusters → ssc = 18 + 18*0.5 = 27.0
    ssc, smc = aggregate_scores([
        _mk_hit(18.0, midnight),
        _mk_hit(18.0, midnight + timedelta(hours=30)),
    ], cfg)
    log.info("F Caso 2 (eventos distintos, 30h apart): SSC=%.2f SMC=%.2f"
             "  [esperado pre y post: SSC=27.00 — sin cambio]", ssc, smc)

    # Caso 3: 3 fuentes high-cred cruzando medianoche → bonus ×1.30
    # Pre-fix F: 2 buckets, ninguno con 3 fuentes → 27.0
    # Post-fix F: 1 cluster con 3 fuentes ≥0.80 → bonus → 18 * 1.30 = 23.40
    ssc, smc = aggregate_scores([
        _mk_hit(18.0, midnight - timedelta(minutes=30), source="northern_miner"),  # 0.85
        _mk_hit(18.0, midnight + timedelta(minutes=30), source="allafrica"),       # 0.85
        _mk_hit(18.0, midnight + timedelta(hours=2),    source="bbc_africa"),      # 0.90
    ], cfg)
    log.info("F Caso 3 (3 fuentes cruzando medianoche, bonus): SSC=%.2f SMC=%.2f"
             "  [esperado post-fix: SSC=23.40 — pre-fix habria sido 27.00 sin bonus]", ssc, smc)

    # Caso 4: hits mismo tiempo pero distinto geo → siempre 2 clusters
    h_drc = _mk_hit(18.0, midnight); h_drc["best_geo"] = "GEO-01"
    h_zam = _mk_hit(18.0, midnight); h_zam["best_geo"] = "GEO-02"
    ssc, smc = aggregate_scores([h_drc, h_zam], cfg)
    log.info("F Caso 4 (mismo tiempo, distinto geo): SSC=%.2f SMC=%.2f"
             "  [esperado: SSC=27.00 — sin cambio, geos distintos = clusters distintos]", ssc, smc)

    log.info("--- FIN tests F ---")


# ---------------------------------------------------------------------------
# Tests del fix DEGRADED-cooldown (source_health)
# ---------------------------------------------------------------------------

def _run_source_health_tests() -> None:
    """
    Tests del fix DEGRADED-cooldown (2026-05-17).

    Antes del fix: una fuente con 3 fallos consecutivos quedaba marcada como
    DEGRADED para siempre. `fetch_rss` la saltaba en cada run, y el único
    camino a `OK` era `update_source_health(success=True)` que se llamaba
    dentro de `fetch_rss` → bloqueo permanente.

    Después del fix: tras 24h del último intento, `is_source_degraded`
    devuelve False una vez, dando oportunidad a un reintento. Si falla,
    el cooldown vuelve a contar. Si tiene éxito, la fuente recupera OK.
    """
    from framework.state import is_source_degraded, update_source_health

    log.info("--- Tests SH: DEGRADED debe poder reintentarse tras cooldown ---")

    # Caso 1: tres fallos consecutivos marcan DEGRADED, sigue bloqueada
    state: dict = {"source_health": {}}
    for _ in range(3):
        update_source_health(state, "test_src", success=False)
    blocked = is_source_degraded(state, "test_src")
    log.info("SH Caso 1 (DEGRADED recién marcado): is_degraded=%s  [esperado: True]", blocked)
    assert blocked is True, "Caso 1 falló — DEGRADED reciente debería bloquear"

    # Caso 2: backdate last_attempt >24h → cooldown expirado, permite reintento
    state["source_health"]["test_src"]["last_attempt"] = (
        datetime.now(timezone.utc) - timedelta(hours=25)
    ).isoformat()
    blocked = is_source_degraded(state, "test_src")
    log.info("SH Caso 2 (DEGRADED >24h, cooldown expirado): is_degraded=%s  [esperado: False]", blocked)
    assert blocked is False, "Caso 2 falló — DEGRADED >24h debería permitir reintento"

    # Caso 3: tras reintento fallido, el cooldown se reinicia
    update_source_health(state, "test_src", success=False)
    blocked = is_source_degraded(state, "test_src")
    log.info("SH Caso 3 (reintento falla, cooldown reseteado): is_degraded=%s  [esperado: True]", blocked)
    assert blocked is True, "Caso 3 falló — tras fallo, cooldown debería reiniciarse"

    # Caso 4: tras reintento exitoso, la fuente vuelve a OK
    state["source_health"]["test_src"]["last_attempt"] = (
        datetime.now(timezone.utc) - timedelta(hours=25)
    ).isoformat()
    update_source_health(state, "test_src", success=True)
    blocked = is_source_degraded(state, "test_src")
    status = state["source_health"]["test_src"]["status"]
    log.info("SH Caso 4 (reintento OK, recuperación): is_degraded=%s status=%s  [esperado: False/OK]", blocked, status)
    assert blocked is False, "Caso 4 falló — tras éxito debería desbloquear"
    assert status == "OK", "Caso 4 falló — status debería volver a OK"

    log.info("--- FIN tests SH ---")


# ---------------------------------------------------------------------------
# Tests del fetcher de NewsAPI (NA — NewsAPI)
# ---------------------------------------------------------------------------

def _run_newsapi_tests() -> None:
    """
    Tests del fetcher de NewsAPI (2026-05-17).

    No prueba la API en sí (requiere key + red). Prueba:
      1. _normalize_source_name maneja los casos comunes y edge cases
      2. fetch_news_api es fail-safe cuando falta api_key o queries
    """
    from framework.sources import _normalize_source_name, fetch_news_api

    log.info("--- Tests NA: NewsAPI source normalization y fail-safe ---")

    # Caso 1: nombres normales de medios
    cases = [
        ("Reuters",                    "reuters"),
        ("BBC News",                   "bbc_news"),
        ("South China Morning Post",   "south_china_morning_post"),
        ("Mining.com",                 "mining_com"),
        ("The Wall Street Journal",    "the_wall_street_journal"),
        ("",                           "newsapi_unknown"),
        (None,                         "newsapi_unknown"),
        ("  Bloomberg  ",              "bloomberg"),
        ("CNBC TV-18",                 "cnbc_tv_18"),
    ]
    for raw, expected in cases:
        got = _normalize_source_name(raw)
        assert got == expected, f"NA normalize falla: input='{raw}' got='{got}' expected='{expected}'"
        log.info("NA normalize ok: '%s' -> '%s'", raw, got)

    # Caso 2: fail-safe sin api_key
    state: dict = {"source_health": {}}
    result = fetch_news_api(state, None, "", ["foo"])  # session=None irrelevante si bails out
    assert result == [], "NA fail-safe falló: sin api_key debería devolver []"
    log.info("NA fail-safe ok: sin api_key devuelve []")

    # Caso 3: fail-safe sin queries
    result = fetch_news_api(state, None, "fake_key", [])
    assert result == [], "NA fail-safe falló: sin queries debería devolver []"
    log.info("NA fail-safe ok: sin queries devuelve []")

    # Caso 4: el flag full_text debe ser opcional (default False)
    # y respetable cuando se pasa explícitamente. Sin api_key sigue siendo
    # fail-safe — no debe intentar fetch_url si no llega a iterar artículos.
    result = fetch_news_api(state, None, "", ["foo"], full_text=True)
    assert result == [], "NA full_text falló: sin api_key debe bail antes de cualquier fetch"
    log.info("NA full_text ok: flag respetado, sin api_key sigue siendo fail-safe")

    # Caso 5: el field news_api_full_text existe en AssetConfig con default False.
    # Esto bloquea regresiones futuras que rompan la API del dataclass.
    from framework.scoring import AssetConfig
    import dataclasses
    fields_by_name = {f.name: f for f in dataclasses.fields(AssetConfig)}
    assert "news_api_full_text" in fields_by_name, "AssetConfig debe tener news_api_full_text"
    assert fields_by_name["news_api_full_text"].default is False, (
        "AssetConfig.news_api_full_text debe ser False por defecto "
        "(opt-in para evitar cambios de comportamiento accidentales en otros assets)"
    )
    log.info("NA AssetConfig.news_api_full_text presente y default=False ✓")

    log.info("--- FIN tests NA ---")


# ---------------------------------------------------------------------------
# Tests del fetcher de GNews.io (GN)
# ---------------------------------------------------------------------------

def _run_gnews_tests() -> None:
    """
    Tests del fetcher de GNews (2026-05-17).

    Análogos a los tests de NewsAPI. No prueba la API en sí (requiere key + red).
    Prueba:
      1. fetch_gnews fail-safe sin api_key / sin queries
      2. fetch_gnews respeta el flag full_text incluso cuando bails out
      3. AssetConfig tiene gnews_queries (default []) y gnews_full_text (default False)

    El helper `_normalize_source_name` ya está cubierto por los tests NA
    porque GNews lo reutiliza con la misma normalización.
    """
    from framework.scoring import AssetConfig
    from framework.sources import fetch_gnews
    import dataclasses

    log.info("--- Tests GN: GNews.io fail-safe y AssetConfig fields ---")

    # Caso 1: fail-safe sin api_key
    state: dict = {"source_health": {}}
    result = fetch_gnews(state, None, "", ["foo"])
    assert result == [], "GN fail-safe falló: sin api_key debería devolver []"
    log.info("GN fail-safe ok: sin api_key devuelve []")

    # Caso 2: fail-safe sin queries
    result = fetch_gnews(state, None, "fake_key", [])
    assert result == [], "GN fail-safe falló: sin queries debería devolver []"
    log.info("GN fail-safe ok: sin queries devuelve []")

    # Caso 3: el flag full_text es respetado y no rompe el fail-safe
    result = fetch_gnews(state, None, "", ["foo"], full_text=True)
    assert result == [], "GN full_text falló: sin api_key debe bail antes de cualquier fetch"
    log.info("GN full_text ok: flag respetado, sin api_key sigue siendo fail-safe")

    # Caso 4: AssetConfig tiene gnews_queries con default []
    fields_by_name = {f.name: f for f in dataclasses.fields(AssetConfig)}
    assert "gnews_queries" in fields_by_name, "AssetConfig debe tener gnews_queries"
    # default_factory=list, así que verificamos la default_factory
    default_factory = fields_by_name["gnews_queries"].default_factory
    assert default_factory is not dataclasses.MISSING and default_factory() == [], (
        "AssetConfig.gnews_queries debe tener default_factory=list (lista vacia)"
    )
    log.info("GN AssetConfig.gnews_queries presente con default_factory=list ✓")

    # Caso 5: AssetConfig tiene gnews_full_text con default False
    assert "gnews_full_text" in fields_by_name, "AssetConfig debe tener gnews_full_text"
    assert fields_by_name["gnews_full_text"].default is False, (
        "AssetConfig.gnews_full_text debe ser False por defecto (opt-in)"
    )
    log.info("GN AssetConfig.gnews_full_text presente y default=False ✓")

    log.info("--- FIN tests GN ---")


# ---------------------------------------------------------------------------
# Tests de URL normalization (UN)
# ---------------------------------------------------------------------------

def _run_url_normalization_tests() -> None:
    """
    Tests de _normalize_url y backwards-compat de is_url_processed (2026-05-17).

    Fix histórico: el dedup cross-run usaba URL exact match. El mismo artículo
    podía llegar desde dos APIs distintas con URLs ligeramente distintas
    (?utm_source=, prefijo www., trailing slash) y ser tratado como artículos
    independientes. En aggregate_scores se contaba dos veces (best + 0.5*sec),
    inflando el cluster hasta 50%.

    Tras este fix, todas las variaciones triviales colapsan al mismo URL
    canónico antes de cualquier comparación.
    """
    from framework.state import _normalize_url, mark_url_processed, is_url_processed

    log.info("--- Tests UN: URL normalization para dedup estable cross-run ---")

    # Caso 1: URL vacía e URLs no-HTTP se mantienen sin cambios
    assert _normalize_url("") == ""
    assert _normalize_url("acled://data_id_123") == "acled://data_id_123"
    assert _normalize_url("test://aggregate") == "test://aggregate"
    log.info("UN Caso 1 (empty + non-HTTP intactos): ✓")

    # Caso 2: strip de query string
    assert _normalize_url("https://reuters.com/article?utm_source=newsapi") == "https://reuters.com/article"
    assert _normalize_url("https://reuters.com/article?a=1&b=2") == "https://reuters.com/article"
    log.info("UN Caso 2 (query string strip): ✓")

    # Caso 3: strip de fragment
    assert _normalize_url("https://reuters.com/article#section-1") == "https://reuters.com/article"
    log.info("UN Caso 3 (fragment strip): ✓")

    # Caso 4: strip de trailing slash
    assert _normalize_url("https://reuters.com/article/") == "https://reuters.com/article"
    assert _normalize_url("https://reuters.com/") == "https://reuters.com"
    log.info("UN Caso 4 (trailing slash strip): ✓")

    # Caso 5: strip de prefijo www.
    assert _normalize_url("https://www.reuters.com/article") == "https://reuters.com/article"
    log.info("UN Caso 5 (www. prefix strip): ✓")

    # Caso 6: scheme y host lowercase, path case-sensitive preservado
    assert _normalize_url("HTTPS://Reuters.COM/Article/X") == "https://reuters.com/Article/X"
    log.info("UN Caso 6 (scheme+host lower, path preservado): ✓")

    # Caso 7: combinación de todas las normalizaciones
    raw = "HTTPS://Www.Reuters.com/Article/X/?utm_source=foo&ref=feed#section"
    expected = "https://reuters.com/Article/X"
    got = _normalize_url(raw)
    assert got == expected, f"UN Caso 7 falló: esperado={expected!r} got={got!r}"
    log.info("UN Caso 7 (combinación completa): ✓")

    # Caso 8: mismo artículo con variaciones URL → dedup match cross-API
    # Escenario: GNews día 1 trae artículo con URL "limpia"; NewsAPI día 2
    # lo trae con UTM tracking y prefijo www.
    state: dict = {"source_health": {}, "processed_urls": []}
    mark_url_processed(state, "https://reuters.com/cobalt-drc-strike")
    assert is_url_processed(state, "https://www.reuters.com/cobalt-drc-strike/"), (
        "UN Caso 8 falló: variación www+slash no detectada"
    )
    assert is_url_processed(state, "https://reuters.com/cobalt-drc-strike?utm_source=newsapi"), (
        "UN Caso 8 falló: variación utm_source no detectada"
    )
    assert is_url_processed(state, "https://reuters.com/cobalt-drc-strike#breaking"), (
        "UN Caso 8 falló: variación fragment no detectada"
    )
    log.info("UN Caso 8 (dedup cross-variation API): ✓")

    # Caso 9: backwards-compat con state.json viejo (URLs sin normalizar)
    # Las entradas históricas en producción están guardadas con su URL original.
    # is_url_processed debe normalizar ambos lados para que matcheen.
    state2: dict = {
        "source_health": {},
        "processed_urls": [
            # Entry "vieja" como podría existir en state.json pre-fix
            {"url": "https://www.example.com/old-article?ref=feed",
             "ts": "2026-05-15T00:00:00+00:00"},
        ],
    }
    assert is_url_processed(state2, "https://example.com/old-article"), (
        "UN Caso 9 falló: backwards-compat con state.json viejo no funciona"
    )
    log.info("UN Caso 9 (backwards-compat state.json viejo): ✓")

    log.info("--- FIN tests UN ---")


# ---------------------------------------------------------------------------
# Suite completa
# ---------------------------------------------------------------------------

def run_gemini_test(cfg: AssetConfig, gemini_client=None) -> None:
    """
    Modo test: ejecuta los artículos sintéticos a través de score_article y
    (opcionalmente) Gemini, más los tests directos de aggregate_scores.

    Si `gemini_client` es None, se omite la llamada real a Gemini (útil para
    iterar sin consumir cuota free tier — equivalente a COBALT_TEST_NO_GEMINI=1).
    """
    skip_gemini = gemini_client is None
    log.info("=== MODO TEST ACTIVADO === (skip_gemini=%s)", skip_gemini)
    log.info("google-genai disponible: %s | client: %s", is_available(), gemini_client is not None)

    # --- 1. Tests por artículo (cubren fixes A, B, C, D) ---
    test_articles = build_test_articles()
    for art in test_articles:
        hits = score_article(art, cfg)
        max_s = max((abs(h["score_bruto"]) for h in hits), default=0.0)
        signed_sum = sum(h["score_bruto"] for h in hits)
        ctx = count_context_hits(art, cfg.context_trigger_terms)
        if max_s >= cfg.gemini_score_threshold:
            path = "A"
        elif ctx >= cfg.gemini_context_min:
            path = "B"
        else:
            path = "NONE"
        log.info(
            "TEST [%s] pre-Gemini : hits=%d, max_score=%.2f, signed_sum=%+.2f, ctx_terms=%d, path=%s",
            art["title"][:50], len(hits), max_s, signed_sum, ctx, path,
        )

        if skip_gemini:
            hits_after = hits  # bypass
        else:
            hits_after = analyze_with_gemini(art, hits, cfg, gemini_client)
        max_after = max((abs(h["score_bruto"]) for h in hits_after), default=0.0)
        signed_after = sum(h["score_bruto"] for h in hits_after)
        log.info(
            "TEST [%s] post-Gemini: hits=%d, max_score=%.2f, signed_sum=%+.2f",
            art["title"][:50], len(hits_after), max_after, signed_after,
        )

    # --- 2. Tests directos de aggregate_scores (cubren fix F) ---
    _run_aggregate_clustering_tests(cfg)

    # --- 3. Tests del fix DEGRADED-cooldown en source_health ---
    _run_source_health_tests()

    # --- 4. Tests del fetcher de NewsAPI ---
    _run_newsapi_tests()

    # --- 5. Tests del fetcher de GNews.io ---
    _run_gnews_tests()

    # --- 6. Tests de URL normalization ---
    _run_url_normalization_tests()

    log.info("=== FIN TEST ===")


def is_test_mode_active() -> bool:
    """True si la env var COBALT_TEST_MODE=1 está presente."""
    return os.environ.get("COBALT_TEST_MODE") == "1"


def is_no_gemini_active() -> bool:
    """True si la env var COBALT_TEST_NO_GEMINI=1 está presente (omite cuota)."""
    return os.environ.get("COBALT_TEST_NO_GEMINI") == "1"
