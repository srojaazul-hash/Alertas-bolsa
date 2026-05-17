"""framework.state — Gestión de estado persistente, .env y deduplicación.

Funciones puramente genéricas: no dependen de ningún asset concreto.
El path al `state.json` se pasa por argumento (cada asset usa el suyo).
"""

import json
import logging
import unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path

log = logging.getLogger("framework.state")


# ---------------------------------------------------------------------------
# .env loader
# ---------------------------------------------------------------------------

def load_env(path: Path) -> dict:
    """Lee pares KEY=VALUE de un archivo .env; ignora comentarios y líneas vacías."""
    env: dict = {}
    if not path.exists():
        log.warning(".env no encontrado en %s — email/APIs desactivados", path)
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


# ---------------------------------------------------------------------------
# state.json load / save
# ---------------------------------------------------------------------------

def _default_state() -> dict:
    return {
        "last_run": None,
        "processed_urls": [],
        "active_events": [],
        "source_health": {},
        "score_history": [],
        "run_count_today": 0,
        "last_run_date": None,
    }


def load_state(state_file: Path) -> dict:
    if state_file.exists():
        try:
            with open(state_file, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception as exc:
            log.warning("No se pudo leer %s: %s — iniciando estado limpio", state_file, exc)
    return _default_state()


def save_state(state: dict, state_file: Path) -> None:
    try:
        with open(state_file, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("No se pudo guardar %s: %s", state_file, exc)


# ---------------------------------------------------------------------------
# URLs procesadas (anti-duplicado entre runs)
# ---------------------------------------------------------------------------

def purge_old_urls(state: dict, hours: int = 72) -> None:
    """Elimina URLs procesadas con más de `hours` horas de antigüedad."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    kept = [
        entry for entry in state.get("processed_urls", [])
        if datetime.fromisoformat(entry["ts"]) > cutoff
    ]
    state["processed_urls"] = kept


def mark_url_processed(state: dict, url: str) -> None:
    state.setdefault("processed_urls", []).append(
        {"url": url, "ts": datetime.now(timezone.utc).isoformat()}
    )


def is_url_processed(state: dict, url: str) -> bool:
    return any(e["url"] == url for e in state.get("processed_urls", []))


# ---------------------------------------------------------------------------
# Source health
# ---------------------------------------------------------------------------

# Tiempo en horas tras el cual una fuente DEGRADED se reintenta una vez.
# Si el reintento falla, el cooldown vuelve a empezar. Si tiene éxito, recupera.
DEGRADED_RETRY_HOURS = 24


def update_source_health(state: dict, source_name: str, success: bool) -> None:
    health = state.setdefault("source_health", {})
    entry = health.setdefault(source_name, {"consecutive_failures": 0, "status": "OK"})
    now_iso = datetime.now(timezone.utc).isoformat()
    # last_attempt se actualiza en cada intento (éxito o fallo) para que el
    # cooldown del reintento cuente desde la última prueba real.
    entry["last_attempt"] = now_iso
    if success:
        entry["consecutive_failures"] = 0
        entry["status"] = "OK"
        entry["last_success"] = now_iso
    else:
        entry["consecutive_failures"] = entry.get("consecutive_failures", 0) + 1
        if entry["consecutive_failures"] >= 3:
            entry["status"] = "DEGRADED"
            log.warning(
                "Fuente DEGRADED: %s (%d fallos consecutivos)",
                source_name, entry["consecutive_failures"],
            )


def is_source_degraded(
    state: dict, source_name: str, retry_after_hours: int = DEGRADED_RETRY_HOURS
) -> bool:
    """
    True si la fuente está DEGRADED y aún en cooldown (saltarla en este run).

    Fix histórico (2026-05-17): antes una fuente DEGRADED se saltaba
    indefinidamente sin posibilidad de recuperación. El único camino al
    `status = "OK"` era a través de `update_source_health(success=True)`,
    que solo se llama dentro de `fetch_rss`. Pero `fetch_rss` salta la
    fuente si está DEGRADED → bloqueo permanente. Una fuente que fallara
    3 veces (caída temporal, mantenimiento, blip de red) quedaba muerta
    para siempre hasta intervención manual.

    Ahora, tras `retry_after_hours` desde el último intento, se permite
    UN reintento. Si vuelve a fallar, otras N horas. Si vuelve OK, la
    fuente se recupera automáticamente.
    """
    entry = state.get("source_health", {}).get(source_name, {})
    if entry.get("status") != "DEGRADED":
        return False
    # Fall back a last_success por compatibilidad con states.json antiguos
    # que no tenían last_attempt (anterior al fix).
    last = entry.get("last_attempt") or entry.get("last_success")
    if not last:
        return False  # sin marca temporal: permitir reintento conservadoramente
    try:
        since = datetime.now(timezone.utc) - datetime.fromisoformat(last)
        if since > timedelta(hours=retry_after_hours):
            return False  # cooldown expirado
    except Exception:
        return False  # parsing del timestamp falla: no bloquear
    return True


# ---------------------------------------------------------------------------
# Deduplicación intra-run
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Local copy of normalize() para no crear dependencia circular con scoring."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _simple_similarity(s1: str, s2: str) -> float:
    w1 = set(s1.lower().split())
    w2 = set(s2.lower().split())
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / max(len(w1), len(w2))


def is_duplicate_article(article: dict, seen_articles: list, state: dict) -> bool:
    """True si el artículo es duplicado (URL ya vista o título muy similar en el mismo dominio)."""
    url = article.get("url", "")
    if url and is_url_processed(state, url):
        return True
    title = article.get("title", "")
    domain = url.split("/")[2] if url.startswith("http") else article.get("source_name", "")
    for seen in seen_articles:
        seen_url = seen.get("url", "")
        seen_domain = (
            seen_url.split("/")[2] if seen_url.startswith("http")
            else seen.get("source_name", "")
        )
        if seen_domain == domain and _simple_similarity(title, seen.get("title", "")) > 0.85:
            return True
    return False


# ---------------------------------------------------------------------------
# Run-number counter (1/2/3 del día)
# ---------------------------------------------------------------------------

def compute_run_number(state: dict) -> int:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("last_run_date") != today:
        state["run_count_today"] = 0
        state["last_run_date"] = today
    state["run_count_today"] = state.get("run_count_today", 0) + 1
    return state["run_count_today"]
