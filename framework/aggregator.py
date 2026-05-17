"""framework.aggregator — Agregación de hits en SSC/SMC totales + alerta.

Clustering temporal por (category, best_geo) con ventana deslizante de N horas
(fix punto F): hits del mismo evento físico no se duplican aunque crucen
medianoche UTC.
"""

import logging

from framework.scoring import AssetConfig

log = logging.getLogger("framework.aggregator")


# ---------------------------------------------------------------------------
# Por-categoría
# ---------------------------------------------------------------------------

def calc_ssc(score_bruto: float, category: str, cfg: AssetConfig) -> float:
    """Aplica el multiplicador SSC del asset a un score bruto."""
    w = cfg.ssc_category_weights.get(category, 0.4)
    return round(score_bruto * w, 3)


def calc_smc(score_bruto: float, category: str, cfg: AssetConfig) -> float:
    """Aplica el override SMC del asset a un score bruto (1.0 si no override)."""
    override = cfg.smc_category_overrides.get(category, 1.0)
    return round(score_bruto * override, 3)


# ---------------------------------------------------------------------------
# Agregación principal
# ---------------------------------------------------------------------------

def aggregate_scores(hits: list, cfg: AssetConfig, time_window_hours: int = 24) -> tuple:
    """
    Agrega scores de hits individuales en (total_SSC, total_SMC).

    Fórmula: primary + 0.5 * Σ(secondary) tras clustering por evento
    (`scoring_rules.md` §7).

    Fix punto F: clustering por ventana deslizante (no por bucket UTC). Hits
    del mismo (category, best_geo) cuyo pub_date dista < `time_window_hours`
    del último hit del cluster en curso se agrupan juntos. Hits fuera de la
    ventana abren un cluster nuevo.

    Multi-source confirmation: si un cluster tiene ≥3 fuentes con
    `source_credibility >= 0.80`, se aplica un bonus ×1.30.
    """
    if not hits:
        return 0.0, 0.0

    # Paso 1: agrupar por (category, best_geo) sin tener en cuenta el tiempo
    by_key: dict = {}
    for hit in hits:
        key_base = (hit["category"], hit["best_geo"] or "NONE")
        by_key.setdefault(key_base, []).append(hit)

    # Paso 2: dentro de cada grupo, clustering por ventana deslizante
    event_clusters: list = []
    window_seconds = time_window_hours * 3600
    for group_hits in by_key.values():
        group_hits.sort(key=lambda h: h["pub_date"])
        current = [group_hits[0]]
        for hit in group_hits[1:]:
            delta = (hit["pub_date"] - current[-1]["pub_date"]).total_seconds()
            if delta < window_seconds:
                current.append(hit)
            else:
                event_clusters.append(current)
                current = [hit]
        event_clusters.append(current)

    ssc_scores: list = []
    smc_scores: list = []

    for event_hits in event_clusters:
        # Mejor score del cluster
        best = max(event_hits, key=lambda h: abs(h["score_bruto"]))
        cat = best["category"]
        sb = best["score_bruto"]

        # Bonus multi-fuente
        unique_sources = set(h["source_name"] for h in event_hits)
        high_cred_sources = sum(
            1 for s in unique_sources
            if cfg.source_credibility.get(s, 0) >= 0.80
        )
        if high_cred_sources >= 3:
            sb = sb * 1.30

        ssc_scores.append(calc_ssc(sb, cat, cfg))
        smc_scores.append(calc_smc(sb, cat, cfg))

    # Ordenar por valor absoluto descendente
    ssc_scores.sort(key=abs, reverse=True)
    smc_scores.sort(key=abs, reverse=True)

    def _aggregate(scores: list) -> float:
        if not scores:
            return 0.0
        total = scores[0]
        for s in scores[1:]:
            total += s * 0.5   # preservar signo (DEM-SUBSTITUTE negativos)
        return total

    return round(_aggregate(ssc_scores), 2), round(_aggregate(smc_scores), 2)


# ---------------------------------------------------------------------------
# Niveles (semáforo)
# ---------------------------------------------------------------------------

def _level_from_table(score: float, levels: list) -> tuple:
    """
    levels = [(umbral_max_excluyente, "NOMBRE", "color"), …]

    Devuelve la primera entrada cuyo umbral_max > score. La última debe ser
    sentinela (float('inf'), "ROJO", "rojo") o similar.
    """
    for threshold, name, color in levels:
        if score < threshold:
            return name, color
    # fallback: última entrada (no debería llegarse si la tabla cierra con inf)
    _, name, color = levels[-1]
    return name, color


def level_ssc(score: float, cfg: AssetConfig) -> tuple:
    return _level_from_table(score, cfg.ssc_levels)


def level_smc(score: float, cfg: AssetConfig) -> tuple:
    return _level_from_table(score, cfg.smc_levels)


# ---------------------------------------------------------------------------
# Disparador de alerta
# ---------------------------------------------------------------------------

def should_alert(ssc: float, smc: float, cfg: AssetConfig) -> bool:
    """
    Condición de alerta (`scoring_rules.md` §4.3):
        ssc >= ssc_min  OR  smc >= smc_min  OR  (ssc >= combined_ssc AND smc >= combined_smc)
    """
    th = cfg.alert_thresholds
    if ssc >= th["ssc_min"]:
        return True
    if smc >= th["smc_min"]:
        return True
    if ssc >= th["combined_ssc"] and smc >= th["combined_smc"]:
        return True
    return False
