"""framework.sources — Fetchers genéricos (RSS, scraping, ACLED).

Cada fetcher recibe la `requests.Session` y los descriptores de fuente desde
el asset orquestador. El framework no construye sus propios headers ni claves.
"""

import logging
import time
from datetime import datetime, timezone
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
