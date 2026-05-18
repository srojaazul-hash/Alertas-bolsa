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

def _normalize_url(url: str) -> str:
    """
    Normaliza una URL para dedup estable cross-run.

    Aplica:
      - Strip de query string (?utm_source=..., ?ref=feed, etc.)
      - Strip de fragment (#section)
      - Strip de trailing slash
      - Lowercase del scheme y host
      - Strip de prefijo "www."

    Mantiene tal cual:
      - URLs no-HTTP (e.g., "acled://12345", "test://aggregate")
      - Cadenas vacías
      - Case del path (las rutas URL son case-sensitive por estándar)

    Justificación (audit 2026-05-17): el mismo artículo puede llegar al sistema
    desde diferentes APIs con URLs ligeramente distintas — `?utm_source=`,
    prefijo `www.`, trailing slash inconsistente, etc. Sin normalización,
    `is_url_processed` no detecta el duplicado, el artículo se scorea dos
    veces, y aggregate_scores infla el cluster hasta 50% (best + 0.5*secondary).
    """
    if not url:
        return url
    # Solo normalizamos esquemas HTTP/HTTPS. URLs internas como "acled://..."
    # se mantienen exactas para no romper su dedup.
    url_lower_check = url.lower()
    if not (url_lower_check.startswith("http://") or url_lower_check.startswith("https://")):
        return url

    # Strip query y fragment (orden no importa, cualquiera puede aparecer primero)
    url = url.split("?", 1)[0].split("#", 1)[0]
    # Strip trailing slash (rstrip elimina todos los slashes finales)
    url = url.rstrip("/")

    # Parse scheme://host/path
    try:
        scheme, rest = url.split("://", 1)
        scheme = scheme.lower()
        if "/" in rest:
            host, path = rest.split("/", 1)
            path = "/" + path
        else:
            host = rest
            path = ""
        host = host.lower()
        # Strip prefijo www.
        if host.startswith("www."):
            host = host[4:]
        return f"{scheme}://{host}{path}"
    except (ValueError, IndexError):
        # Fallback defensivo: si el parse falla, devolver la URL truncada
        # (sin query/fragment/trailing slash) sin perder el dedup parcial.
        return url


def purge_old_urls(state: dict, hours: int = 72) -> None:
    """Elimina URLs procesadas con más de `hours` horas de antigüedad."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    kept = [
        entry for entry in state.get("processed_urls", [])
        if datetime.fromisoformat(entry["ts"]) > cutoff
    ]
    state["processed_urls"] = kept


def mark_url_processed(state: dict, url: str) -> None:
    """Marca URL como procesada usando la versión normalizada para dedup estable."""
    state.setdefault("processed_urls", []).append(
        {"url": _normalize_url(url), "ts": datetime.now(timezone.utc).isoformat()}
    )


def is_url_processed(state: dict, url: str) -> bool:
    """
    Comprueba si una URL ya fue procesada en runs previos.

    Backwards-compat: las URLs guardadas en `state.json` previo a este fix
    se almacenaron sin normalizar. No las reescribimos (perdería timestamps
    útiles). En su lugar, normalizamos ambos lados en cada comparación.
    Coste: O(N) normalizaciones por llamada — para N~300 URLs, despreciable.
    """
    norm_target = _normalize_url(url)
    for entry in state.get("processed_urls", []):
        if _normalize_url(entry.get("url", "")) == norm_target:
            return True
    return False


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
