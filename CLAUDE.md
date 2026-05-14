# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A cobalt supply-chain early-warning system. `main_scorer.py` runs 3×/day, scrapes RSS feeds and web sources, scores each article against a multilingual keyword dictionary, and fires an HTML email alert when disruption thresholds are exceeded. Designed to run on a GCP e2-micro free-tier instance (1 GB RAM, shared CPU, 10 GB disk).

## Running the script

```bash
python3 main_scorer.py
```

Cron schedule (UTC): `0 0,8,16 * * * /usr/bin/python3 /home/usuario/cobalt-alert/main_scorer.py`

## Configuration

All secrets live in `~/cobalt-alert/.env` (never committed):

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=app-password
ALERT_TO=you@gmail.com
ACLED_KEY=your-acled-key        # free registration at developer.acleddata.com
ACLED_EMAIL=you@gmail.com
BOT_EMAIL=you@gmail.com         # used in User-Agent header
GEMINI_API_KEY=your-gemini-key  # Google AI Studio → aistudio.google.com/apikey
```

State is persisted in `~/cobalt-alert/state.json`. Logs rotate daily at `~/cobalt-alert/logs/scorer.log` (7-day retention).

## Dependencies

```bash
pip install feedparser requests beautifulsoup4 lxml python-dateutil google-genai
```

Intentionally excluded (too heavy for e2-micro): pandas, numpy, selenium, scrapy, spacy, transformers.

## Architecture

### Scoring pipeline

Each article goes through:

```
score = peso_keyword × peso_geografico × multiplicador_categoria × modificador_fuente
```

Then validation filters are applied (negation window ±5 words, age decay, geo-context check, minimum threshold 3.0). Surviving events are aggregated with half-weight for duplicates:

```
total = score[0] + Σ(score[i] × 0.5)   # i > 0, deduped
```

This produces two independent scores per run:
- **SSC** (Swing Corto, 1–2 weeks, max ~50): logistic and acute events
- **SMC** (Swing Macro, 1–3 months, max ~65): structural/regulatory trends

Alert fires when: `SSC >= 31 OR SMC >= 41 OR (SSC >= 20 AND SMC >= 30)`

### Geographic weights (GEO codes)

DRC Copperbelt (GEO-01, ~70% world production) has the highest weight (1.80). China refining (GEO-07, ~70% world refining) is second (1.60). Transit corridors (GEO-03/04/08) have no production weight but are logistically critical.

### Source processing order

Sources run **sequentially** (no threading — shared CPU constraint). Phase 4 sources are skipped if the score already reaches NARANJA after phases 1–3.

1. Reuters Africa/Commodities, Mining.com cobalt, ACLED, ReliefWeb
2. AllAfrica, RFI (FR), Daily Maverick, Club Mozambique, East African, Zambia Reports
3. Port portals: Transnet Durban, TPA Tanzania, CFM Mozambique
4. Supplementary: GDACS, Mining Weekly, USGS, VOA Africa, Reuters China *(skipped if score already NARANJA+)*
5. Google News RSS searches (EN + FR)

Source credibility modifiers: 1.00 (Reuters, official ports) → 0.85 (regional African media) → 0.50 (Google News aggregator) → 0.40 (social). Three independent sources ≥0.80 on the same event apply a ×1.30 confirmation multiplier.

### Spec documents (not code)

The `.md` files are the authoritative specification for the scoring logic — `main_scorer.py` implements them:

| File | Role |
|------|------|
| `scoring_rules.md` | Category multipliers, SSC/SMC formulas, alert thresholds, validation filters |
| `keyword_dictionary.md` | ~280 terms across EN/FR/PT/ES in 9 blocks (anchors, GEO, LOG, GEO-political, LAB, REG, FMA, DEM, false-positive filters) |
| `data_sources.md` | RSS URLs, credibility modifiers, scraping methods, rate limits, source health logic |
| `asset_map.md` | Secondary asset tickers by impact direction, HTML email template, asset-selection rules by event category |

When modifying scoring behavior, update the relevant `.md` first, then update `main_scorer.py` to match. Version both together.

### Key invariants

- `requires_context: true` keywords only score if an anchor term (BLOQUE 0) appears within `context_window` words.
- `DEM-SUBSTITUTE` terms (cobalt-free batteries, LFP, sodium-ion) carry **negative** weight and only affect SMC, not SSC.
- `REG` and `GEO-SANCTION` events do **not** decay by age if there is no resolution notice.
- Port portal failures (HTTP errors) must not be treated as disruption signals — these sites have inherently low uptime.
