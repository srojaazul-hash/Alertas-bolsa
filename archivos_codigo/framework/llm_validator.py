"""framework.llm_validator — Capa Gemini (validador YES/NO + multiplicador).

Dos paths complementarios (`scoring_rules.md` §8):

  Path A — score_bruto >= cfg.gemini_score_threshold
      Gemini valida YES/NO. NO descarta TODOS los hits del artículo. YES los
      conserva tal cual.

  Path B — count_context_hits >= cfg.gemini_context_min
      Gemini devuelve un multiplicador {0.0, 0.5, 1.0, 1.5} que se aplica al
      score_bruto de cada hit.

Si ambas condiciones se cumplen, Path A tiene prioridad.

Fail-safe:
  - Sin GEMINI_API_KEY o sin google-genai instalado → bypass total.
  - Cualquier excepción de la API → comportamiento conservador (mantener hits).
"""

import logging
from typing import Optional

try:
    from google import genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

from framework.scoring import AssetConfig, normalize

log = logging.getLogger("framework.llm_validator")

# Modelo por defecto: free tier (Google AI Studio).
# Cambiar a un modelo pagado requiere autorización explícita del usuario (CLAUDE.md).
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------

def make_gemini_client(api_key: str):
    """Devuelve un cliente Gemini, o None si no está disponible."""
    if not _GENAI_AVAILABLE or not api_key:
        return None
    return genai.Client(api_key=api_key)


def is_available() -> bool:
    return _GENAI_AVAILABLE


# ---------------------------------------------------------------------------
# Heurísticas previas a la llamada
# ---------------------------------------------------------------------------

def count_context_hits(article: dict, context_trigger_terms: list) -> int:
    """Cuenta cuántos context_trigger_terms aparecen en el artículo."""
    text_norm = normalize(article.get("title", "") + " " + article.get("body", ""))
    return sum(1 for t in context_trigger_terms if normalize(t) in text_norm)


# ---------------------------------------------------------------------------
# Path A — YES/NO
# ---------------------------------------------------------------------------

def gemini_validate(article: dict, client, prompt_template: str, model: str = DEFAULT_GEMINI_MODEL) -> bool:
    """
    Path A. `prompt_template` debe contener placeholders {title} y {body}.

    Fail-safe: si hay error, devuelve True (no descarta hits).
    """
    if client is None:
        return True
    prompt = prompt_template.format(
        title=article.get("title", ""),
        body=article.get("body", "")[:1500],
    )
    try:
        answer = client.models.generate_content(model=model, contents=prompt).text.strip().upper()
        log.info("Gemini Path A [%s]: %s", article.get("title", "?")[:55], answer)
        return answer.startswith("YES")
    except Exception as exc:
        log.warning("Gemini Path A error: %s — conservando hits", exc)
        return True


# ---------------------------------------------------------------------------
# Path B — multiplicador 0.0/0.5/1.0/1.5
# ---------------------------------------------------------------------------

def gemini_multiplier(article: dict, client, prompt_template: str, model: str = DEFAULT_GEMINI_MODEL) -> float:
    """
    Path B. `prompt_template` debe contener placeholders {title} y {body} y pedir
    una de {0.0, 0.5, 1.0, 1.5}.

    Fail-safe: si hay error, devuelve 1.0 (multiplicador neutro).
    """
    if client is None:
        return 1.0
    prompt = prompt_template.format(
        title=article.get("title", ""),
        body=article.get("body", "")[:1500],
    )
    try:
        val = float(client.models.generate_content(model=model, contents=prompt).text.strip())
        val = max(0.0, min(1.5, val))
        log.info("Gemini Path B [%s]: x%.1f", article.get("title", "?")[:55], val)
        return val
    except Exception as exc:
        log.warning("Gemini Path B error: %s — multiplicador 1.0", exc)
        return 1.0


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def analyze_with_gemini(article: dict, hits: list, cfg: AssetConfig, client) -> list:
    """
    Dispatcher principal. Devuelve la lista de hits (vacía, modificada o intacta).

    Si client es None (Gemini deshabilitado) o no hay hits, bypass total.
    Path A tiene prioridad sobre Path B si ambos aplican.
    """
    if not hits or client is None:
        return hits

    max_score = max(abs(h["score_bruto"]) for h in hits)

    # Path A
    if max_score >= cfg.gemini_score_threshold:
        if not gemini_validate(article, client, cfg.gemini_validate_prompt):
            log.info("Gemini descartó (Path A): %s", article.get("title", "?")[:60])
            return []
        return hits

    # Path B
    if count_context_hits(article, cfg.context_trigger_terms) >= cfg.gemini_context_min:
        mult = gemini_multiplier(article, client, cfg.gemini_multiplier_prompt)
        if mult == 0.0:
            log.info("Gemini descartó (Path B x0.0): %s", article.get("title", "?")[:60])
            return []
        for h in hits:
            h["score_bruto"] = round(h["score_bruto"] * mult, 3)
            h["gemini_mult"] = mult
        return hits

    return hits
