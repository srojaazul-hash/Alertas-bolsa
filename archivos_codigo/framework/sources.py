"""framework.sources — Fetchers genéricos (RSS, scraping, ACLED, NewsAPI, GNews).

Cada fetcher recibe la `requests.Session` y los descriptores de fuente desde
el asset orquestador. El framework no construye sus propios headers ni claves.
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

from framework.state import (
    is_source_degraded,
    is_url_processed,
    update_source_health,
)

log = logging.getLogger("framework.sources")


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

def make_session(bot_email: str) -> requests.Session:
    """Construye una `requests.Session` con headers educados (User-Agent identifica al bot)."""
    headers = {
        "User-Agent": f"CommoditySupplyMonitor/1.0 (research bot; contact: {bot_email})",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9,fr;q=0.8,pt;q=0.7,es;q=0.6",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "close",
    }
    session = requests.Session()
    session.headers.update(headers)
    return session


# ---------------------------------------------------------------------------
# Low-level URL fetch
# ---------------------------------------------------------------------------

def fetch_url(session: requests.Session, url: str, timeout: int = 15) -> Optional[str]:
    try:
        resp = session.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        log.debug("fetch_url error %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# RSS
# ---------------------------------------------------------------------------

def fetch_rss(source: dict, state: dict, session: requests.Session) -> list:
    """
    Fetches and parses an RSS feed. Returns list of article dicts:
        {url, title, body, pub_date, source_name}

    `source` debe tener: name, url, lang, full_text, timeout, rate_limit (opt).
    """
    name = source["name"]
    if is_source_degraded(state, name):
        log.debug("Saltando fuente DEGRADED: %s", name)
        return []

    try:
        feed = feedparser.parse(
            source["url"],
            request_headers=session.headers,
            agent=session.headers.get("User-Agent", ""),
        )
        if feed.bozo and not feed.entries:
            raise ValueError(f"bozo feed, sin entradas: {feed.bozo_exception}")

        articles = []
        for entry in feed.entries:
            url = getattr(entry, "link", "") or ""
            title = getattr(entry, "title", "") or ""
            summary = getattr(entry, "summary", "") or ""

            pub_date = None
            for date_attr in ("published_parsed", "updated_parsed", "created_parsed"):
                tp = getattr(entry, date_attr, None)
                if tp:
                    pub_date = datetime(*tp[:6], tzinfo=timezone.utc)
                    break
            if pub_date is None:
                pub_date = datetime.now(timezone.utc)

            # Full-text opcional: solo si la fuente lo marca y la URL no se procesó antes
            body = summary
            if source.get("full_text") and url and not is_url_processed(state, url):
                time.sleep(1)
                full = fetch_url(session, url, timeout=source.get("timeout", 15))
                if full:
                    soup = BeautifulSoup(full, "lxml")
                    for tag in soup(["script", "style", "nav", "footer", "header"]):
                        tag.decompose()
                    body = soup.get_text(separator=" ", strip=True)[:8000]

            # Filtro de edad: descartar artículos con más de 48h
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


# ---------------------------------------------------------------------------
# Scraping (portales sin RSS)
# ---------------------------------------------------------------------------

def fetch_scraping(source: dict, state: dict, session: requests.Session) -> list:
    """Scraping simple: extrae texto visible del portal como un único artículo."""
    name = source["name"]
    if is_source_degraded(state, name):
        return []
    try:
        html = fetch_url(session, source["url"], timeout=source.get("timeout", 20))
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


# ---------------------------------------------------------------------------
# ACLED
# ---------------------------------------------------------------------------

def fetch_acled(
    state: dict,
    session: requests.Session,
    acled_key: str,
    acled_email: str,
    countries: str = "Democratic Republic of Congo|Zambia|Tanzania|Mozambique|South Africa",
    region: str = "1",
    event_type: str = "Battles|Explosions/Remote violence|Violence against civilians",
    limit: int = 50,
) -> list:
    """
    Fetches ACLED conflict data. Genérico — el asset elige países y tipos.

    Defaults preservan el comportamiento histórico de cobalto (DRC + corredor).
    """
    if not acled_key or not acled_email:
        log.debug("ACLED: sin credenciales configuradas, saltando")
        return []
    if is_source_degraded(state, "acled"):
        return []
    try:
        params = {
            "key": acled_key,
            "email": acled_email,
            "region": region,
            "event_type": event_type,
            "country": countries,
            "limit": str(limit),
            "fields": "event_date|event_type|actor1|location|latitude|longitude|notes|source",
        }
        resp = session.get(
            "https://api.acleddata.com/acled/read",
            params=params, timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        articles = []
        for row in data.get("data", []):
            notes = row.get("notes", "") or ""
            location = row.get("location", "") or ""
            event_type_row = row.get("event_type", "") or ""
            actor = row.get("actor1", "") or ""
            event_date_str = row.get("event_date", "")
            try:
                pub_date = dateutil_parser.parse(event_date_str).replace(tzinfo=timezone.utc)
            except Exception:
                pub_date = datetime.now(timezone.utc)
            body = f"{event_type_row} {actor} {location} {notes}"
            url = f"acled://{row.get('data_id', 'unknown')}"
            articles.append({
                "url": url,
                "title": f"[ACLED] {event_type_row} — {location}",
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
# NewsAPI.org
# ---------------------------------------------------------------------------

# Endpoint estable de NewsAPI v2 /everything (búsqueda Boolean por keywords).
_NEWSAPI_ENDPOINT = "https://newsapi.org/v2/everything"


def _normalize_source_name(source_raw: str) -> str:
    """
    Normaliza el nombre de medio de NewsAPI a un identificador `snake_case`
    ASCII apto para usar como `source_name` y como key en SOURCE_CREDIBILITY.

    Ejemplos:
        "Reuters"                    → "reuters"
        "BBC News"                   → "bbc_news"
        "South China Morning Post"   → "south_china_morning_post"
        "Mining.com"                 → "mining_com"
        ""                           → "newsapi_unknown"
    """
    if not source_raw:
        return "newsapi_unknown"
    norm = source_raw.lower().strip()
    # Reemplazar todo carácter no-alfanumérico por underscore, colapsar duplicados
    norm = "".join(c if c.isalnum() else "_" for c in norm)
    norm = "_".join(filter(None, norm.split("_")))
    return norm or "newsapi_unknown"


def fetch_news_api(
    state: dict,
    session: requests.Session,
    api_key: str,
    queries: list,
    language: str = "en",
    days_back: int = 2,
    page_size: int = 100,
    full_text: bool = False,
) -> list:
    """
    Fetcher para NewsAPI.org (endpoint /v2/everything).

    `queries`: lista de strings de búsqueda Boolean (AND/OR/NOT, "frases literales").
    Cada query gasta 1 request del cuota del API key.

    `full_text`: si True, tras recibir cada artículo se descarga la URL completa
    para reemplazar el body con el cuerpo del artículo parseado. Mismo patrón
    que `fetch_rss` con `full_text=True`. Útil porque el free tier de NewsAPI
    trunca `content` a ~200ch.

    Free tier (relevante para nuestro uso):
      - 100 requests/día
      - artículos con delay de 24h (no real-time)
      - máximo 100 artículos por response
      - field `content` truncado a ~200 chars (usamos `description` + `content`)

    Devuelve artículos en el mismo formato que `fetch_rss`. El `source_name`
    se normaliza a snake_case del medio real (e.g. "reuters", "bbc_news"),
    permitiendo que el bonus multi-fuente del aggregator funcione correctamente:
    artículos del mismo evento en Reuters y BBC vía NewsAPI cuentan como 2
    fuentes distintas.

    Fail-safe: sin api_key, sin queries, o si el endpoint cae → returns [].
    """
    if not api_key or not queries:
        return []
    if is_source_degraded(state, "newsapi_org"):
        return []

    from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    articles_all: list = []
    any_success = False

    for query in queries:
        try:
            resp = session.get(
                _NEWSAPI_ENDPOINT,
                params={
                    "q": query,
                    "from": from_date,
                    "language": language,
                    "sortBy": "publishedAt",
                    "pageSize": page_size,
                },
                headers={"X-Api-Key": api_key},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != "ok":
                log.warning(
                    "NewsAPI error [q='%s']: %s",
                    query[:40], data.get("message", "?"),
                )
                continue

            arts_this_query = data.get("articles", []) or []
            for art in arts_this_query:
                pub_date_str = art.get("publishedAt", "")
                try:
                    pub_date = dateutil_parser.parse(pub_date_str)
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=timezone.utc)
                except Exception:
                    pub_date = datetime.now(timezone.utc)

                # Filtro de edad (consistente con fetch_rss): descartar > 48h
                age_hours = (datetime.now(timezone.utc) - pub_date).total_seconds() / 3600
                if age_hours > 48:
                    continue

                source_raw = (art.get("source") or {}).get("name", "")
                source_norm = _normalize_source_name(source_raw)

                # NewsAPI free tier corta `content` a 200ch. Combinamos description+content
                # para tener algo más que solo el título.
                parts = [p for p in (art.get("description"), art.get("content")) if p]
                body = " ".join(parts)[:8000]

                url = art.get("url", "") or ""

                # Si `full_text` está activo, descargamos la página completa
                # para superar el truncado de 200ch del free tier. Mismo patrón
                # que fetch_rss con full_text=True. Skip si ya está procesada
                # (segundo run sobre la misma URL no rebajan body más).
                if full_text and url and not is_url_processed(state, url):
                    time.sleep(1)  # politeness
                    full_html = fetch_url(session, url, timeout=20)
                    if full_html:
                        try:
                            soup = BeautifulSoup(full_html, "lxml")
                            for tag in soup(["script", "style", "nav", "footer", "header"]):
                                tag.decompose()
                            full_body = soup.get_text(separator=" ", strip=True)[:8000]
                            if full_body and len(full_body) > len(body):
                                body = full_body
                        except Exception as exc:
                            log.debug("NewsAPI full_text parse error [%s]: %s", url, exc)

                articles_all.append({
                    "url": url,
                    "title": art.get("title", "") or "",
                    "body": body,
                    "pub_date": pub_date,
                    "source_name": source_norm,
                })
            any_success = True
            kept_so_far = len(articles_all)
            log.info(
                "NewsAPI OK [q='%s']: %d articulos en respuesta, %d retenidos tras filtro 48h",
                query[:40], len(arts_this_query), kept_so_far,
            )
        except requests.HTTPError as exc:
            log.warning("NewsAPI HTTP error [q='%s']: %s", query[:40], exc)
        except Exception as exc:
            log.warning("NewsAPI FAIL [q='%s']: %s", query[:40], exc)

    if any_success:
        update_source_health(state, "newsapi_org", True)
    else:
        update_source_health(state, "newsapi_org", False)

    return articles_all


# ---------------------------------------------------------------------------
# GNews.io
# ---------------------------------------------------------------------------

# Endpoint estable de GNews v4 /search (búsqueda Boolean por keywords).
# Diferencia clave vs NewsAPI: real-time (sin delay de 24h del free tier).
_GNEWS_ENDPOINT = "https://gnews.io/api/v4/search"

# Pausa entre queries del mismo run. El free tier de GNews tiene rate limit
# por minuto/segundo además del límite diario de 100/día. En pruebas reales
# (2026-05-17) 3 queries consecutivas sin pausa devolvieron HTTP 429 en las
# queries 2 y 3 — solo la primera pasó. 2s entre queries da margen seguro.
# NewsAPI no requiere esto (probado empíricamente: 3 queries consecutivas sin
# pausa funcionan sin 429).
_GNEWS_INTER_QUERY_SLEEP = 2.0


def fetch_gnews(
    state: dict,
    session: requests.Session,
    api_key: str,
    queries: list,
    language: str = "en",
    days_back: int = 2,
    page_size: int = 100,
    full_text: bool = False,
) -> list:
    """
    Fetcher para GNews.io (endpoint /v4/search).

    `queries`: lista de strings de búsqueda Boolean (AND/OR/NOT, "frases literales").
    Sintaxis equivalente a NewsAPI por compatibilidad.

    `full_text`: si True, tras recibir cada artículo se descarga la URL completa
    para reemplazar el body con el cuerpo del artículo parseado. Mismo patrón
    que `fetch_news_api` con `full_text=True`. Necesario porque el free tier
    de GNews trunca `content` a ~250ch.

    Free tier (relevante para nuestro uso):
      - 100 requests/día
      - **REAL-TIME** (sin delay de 24h, diferencia principal vs NewsAPI)
      - máximo 100 artículos por response
      - field `content` truncado a ~250 chars

    Devuelve artículos en el mismo formato que `fetch_rss` / `fetch_news_api`.
    El `source_name` se normaliza a snake_case via `_normalize_source_name`,
    igual que NewsAPI, permitiendo que el bonus multi-fuente del aggregator
    cuente fuentes independientes correctamente.

    Fail-safe: sin api_key, sin queries, o si el endpoint cae → returns [].
    """
    if not api_key or not queries:
        return []
    if is_source_degraded(state, "gnews_io"):
        return []

    from_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    articles_all: list = []
    any_success = False

    for i, query in enumerate(queries):
        # Pausa entre queries (no antes de la primera) para no chocar con el
        # rate limit por minuto/segundo del free tier de GNews. Ver constante.
        if i > 0:
            time.sleep(_GNEWS_INTER_QUERY_SLEEP)
        try:
            resp = session.get(
                _GNEWS_ENDPOINT,
                params={
                    "q": query,
                    "from": from_date,
                    "lang": language,
                    "max": min(page_size, 100),
                    "sortby": "publishedAt",
                    "apikey": api_key,
                },
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()

            # GNews indica errores en distintos formatos según el caso
            if isinstance(data, dict) and ("errors" in data or "error" in data):
                log.warning("GNews error [q='%s']: %s", query[:40], data)
                continue

            arts_this_query = data.get("articles", []) or []
            for art in arts_this_query:
                pub_date_str = art.get("publishedAt", "")
                try:
                    pub_date = dateutil_parser.parse(pub_date_str)
                    if pub_date.tzinfo is None:
                        pub_date = pub_date.replace(tzinfo=timezone.utc)
                except Exception:
                    pub_date = datetime.now(timezone.utc)

                # Filtro de edad consistente con el resto del pipeline
                age_hours = (datetime.now(timezone.utc) - pub_date).total_seconds() / 3600
                if age_hours > 48:
                    continue

                source_raw = (art.get("source") or {}).get("name", "")
                source_norm = _normalize_source_name(source_raw)

                # GNews free tier corta `content` a ~250ch. description+content combinados
                parts = [p for p in (art.get("description"), art.get("content")) if p]
                body = " ".join(parts)[:8000]

                url = art.get("url", "") or ""

                # full_text fetch: idéntico al patrón de fetch_news_api/fetch_rss
                if full_text and url and not is_url_processed(state, url):
                    time.sleep(1)  # politeness
                    full_html = fetch_url(session, url, timeout=20)
                    if full_html:
                        try:
                            soup = BeautifulSoup(full_html, "lxml")
                            for tag in soup(["script", "style", "nav", "footer", "header"]):
                                tag.decompose()
                            full_body = soup.get_text(separator=" ", strip=True)[:8000]
                            if full_body and len(full_body) > len(body):
                                body = full_body
                        except Exception as exc:
                            log.debug("GNews full_text parse error [%s]: %s", url, exc)

                articles_all.append({
                    "url": url,
                    "title": art.get("title", "") or "",
                    "body": body,
                    "pub_date": pub_date,
                    "source_name": source_norm,
                })

            any_success = True
            kept_so_far = len(articles_all)
            log.info(
                "GNews OK [q='%s']: %d articulos en respuesta, %d retenidos tras filtro 48h",
                query[:40], len(arts_this_query), kept_so_far,
            )
        except requests.HTTPError as exc:
            log.warning("GNews HTTP error [q='%s']: %s", query[:40], exc)
        except Exception as exc:
            log.warning("GNews FAIL [q='%s']: %s", query[:40], exc)

    if any_success:
        update_source_health(state, "gnews_io", True)
    else:
        update_source_health(state, "gnews_io", False)

    return articles_all
