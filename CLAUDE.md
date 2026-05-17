# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Strategic source of truth

**Before any substantial change, read the strategic roadmap.** There are two versions:

- **`Hoja de ruta publica.md`** (versioned in Git, available on every machine) — the operative source of truth: project vision, phases, design principles, anti-patterns, progress tracking. **This is the primary reference for any Claude session.**
- **`Hoja de ruta proyecto.md`** (gitignored, owner's local PC only) — the owner's private extended version with additional personal context (career strategy, CV framing). If you find it locally, it complements the public one but never contradicts it.

Both define:
- Current phase and the next concrete task
- Non-negotiable design principles (end-to-end feo > parte perfecta; auditable > inteligente; paper trading is the truth)
- Anti-patterns to avoid
- Tracking checklist with concrete tasks per phase

The two reference documents have distinct roles:

- **`Hoja de ruta publica.md`** = the **strategic** reference. What we're building, in what order, and why.
- **`CLAUDE.md`** (this file) = the **operational** reference. How to work in the codebase, conventions, constraints, technical specs.

If they ever contradict, the public Hoja de ruta wins and CLAUDE.md should be updated to align.

## Reference documents

| File | Tracked? | Purpose |
|---|---|---|
| `Hoja de ruta publica.md` (repo root) | ✅ | Strategic roadmap, phases, principles, daily tracking |
| `Hoja de ruta proyecto.md` (repo root) | ❌ private | Owner's extended local version (career context) |
| `CLAUDE.md` (this file) | ✅ | Operational guidance for Claude sessions |
| `archivos_codigo/framework/` | ✅ | Generic core: scoring, aggregator, sources, state, llm_validator |
| `archivos_codigo/assets/cobalt/dictionary.py` | ✅ | Cobalt-specific data + `COBALT_CONFIG` instance |
| `archivos_codigo/assets/cobalt/main.py` | ✅ | Cobalt orchestrator (cron entry point) |
| `archivos_codigo/tests/synthetic_articles.py` | ✅ | Regression suite (9 articles + 4 clustering cases) |
| `archivos_codigo/legacy/main_scorer.py` | ✅ | Pre-extraction monolith, kept as behavioural reference |
| `archivos_codigo/MAPA_SCORER.html` | ✅ | Visual map of the legacy monolith (open in browser) |
| `scoring_rules.md` (repo root) | ✅ | Spec: category multipliers, SSC/SMC formulas |
| `keyword_dictionary.md` (repo root) | ✅ | Spec: keyword categories and meanings |
| `data_sources.md` (repo root) | ✅ | Spec: RSS sources, credibility modifiers |
| `asset_map.md` (repo root) | ✅ | Spec: asset tickers and event-to-asset rules |

## What this project is

A **multi-asset commodity early-warning system in active evolution**. The first implementation (cobalt) is operational and serves as the reference architecture. The project is evolving into a generalizable framework with an LLM analyst layer and paper trading validation — see `Hoja de ruta proyecto.md` for current phase.

The current cobalt-specific system: `archivos_codigo/assets/cobalt/main.py` runs 3×/day, scrapes RSS feeds and web sources, scores each article against a multilingual keyword dictionary (via the generic `archivos_codigo/framework/` package), validates ambiguous matches via Gemini API, and fires an HTML email alert when disruption thresholds are exceeded. Designed to run on a GCP e2-micro free-tier instance (1 GB RAM, shared CPU, 10 GB disk).

## Running the script

```bash
cd archivos_codigo
python3 -m assets.cobalt.main
```

Cron schedule (UTC):
```
0 0,8,16 * * * cd /home/usuario/cobalt-alert/archivos_codigo && /usr/bin/python3 -m assets.cobalt.main
```

The `cd` is required: `python -m assets.cobalt.main` resolves imports relative to the
current directory, which must be `archivos_codigo/` so that `framework/`, `assets/` and
`tests/` are importable as top-level packages.

The legacy monolith (`archivos_codigo/legacy/main_scorer.py`) is kept as a behavioural
reference for the extraction — do **not** run it in production; the cron always points
at the new entry point.

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

The `.md` files at the repo root are the authoritative specification for the scoring logic — `archivos_codigo/framework/` + `archivos_codigo/assets/cobalt/dictionary.py` implement them:

| File | Role |
|------|------|
| `scoring_rules.md` | Category multipliers, SSC/SMC formulas, alert thresholds, validation filters |
| `keyword_dictionary.md` | ~280 terms across EN/FR/PT/ES in 9 blocks (anchors, GEO, LOG, GEO-political, LAB, REG, FMA, DEM, false-positive filters) |
| `data_sources.md` | RSS URLs, credibility modifiers, scraping methods, rate limits, source health logic |
| `asset_map.md` | Secondary asset tickers by impact direction, HTML email template, asset-selection rules by event category |

When modifying scoring behavior:
1. Update the relevant `.md` first.
2. Update `archivos_codigo/assets/cobalt/dictionary.py` (data) or `archivos_codigo/framework/*.py` (logic) to match.
3. Add a synthetic test case in `archivos_codigo/tests/synthetic_articles.py` if a bug was fixed.
4. Version all changes together.

### Testing infrastructure

Two test modes available via env flags:

- **`COBALT_TEST_MODE=1`** — bypasses RSS fetching and runs a synthetic test suite instead. Currently covers 9 synthetic articles + 4 aggregate-clustering test cases, each designed to detect a specific class of bug (find-first-occurrence, FP-global, threshold ordering, sign-on-negation, UTC-bucket boundary). Each historical fix is locked in by its own test article.
- **`COBALT_TEST_NO_GEMINI=1`** — skips real Gemini API calls (preserves free-tier daily quota during iteration). Combine with `COBALT_TEST_MODE=1` for offline regression testing.

Default iteration command (run from `archivos_codigo/`):
```bash
cd archivos_codigo
COBALT_TEST_MODE=1 COBALT_TEST_NO_GEMINI=1 python3 -m assets.cobalt.main
```

Full validation command (consumes Gemini quota):
```bash
cd archivos_codigo
COBALT_TEST_MODE=1 python3 -m assets.cobalt.main
```

**When fixing any bug, add a synthetic test article (or aggregate test case) that would have caught it.** The test suite is the permanent regression coverage; never delete cases or skip them silently.

### Key invariants

- `requires_context: true` keywords only score if an anchor term (BLOQUE 0) appears within `context_window` words.
- `DEM-SUBSTITUTE` terms (cobalt-free batteries, LFP, sodium-ion) carry **negative** weight and only affect SMC, not SSC.
- `REG` and `GEO-SANCTION` events do **not** decay by age if there is no resolution notice.
- Port portal failures (HTTP errors) must not be treated as disruption signals — these sites have inherently low uptime.

## Operational constraints (MUST follow — applies to all Claude sessions)

These are absolute rules for any Claude instance working on this repo. Do not break them, do not negotiate them.

### Secret handling
- **Never** commit, push, copy, log, paste, transmit, or otherwise expose the **value** of any secret stored in `.env` (`GEMINI_API_KEY`, `SMTP_PASS`, `ACLED_KEY`, etc.). Reading the **variable name** for diagnostic purposes is fine (e.g., `grep -oE "^[A-Z_]+="`); reading or showing the **value** is not.
- `.env` files are excluded by `.gitignore`. Never `git add` or `git commit` them, not even by accident or "just this once".
- If the user asks you to inspect a `.env`, only confirm presence/absence of expected variables. Never echo the value back.

### Cost authorization
- **No paid actions without explicit user authorization.** Anything that may incur a cost — paid API tiers, enabling billing on a cloud project, paid model upgrades, paid plugins/services, anything that exits a free tier — must be flagged to the user in advance with an estimated cost, and only proceed after the user explicitly says yes.
- Default to free-tier alternatives whenever possible (e.g., `gemini-1.5-flash` over paid models; Google AI Studio free quota over billed Google Cloud).
- If a free option is being exhausted or hits quota, **stop and notify the user** rather than silently failing over to a paid path.

## Working principles

Practical patterns refined through many sessions. Follow them by default; deviate only with explicit user instruction.

### Project execution
- **End-to-end feo antes que parte perfecta.** Don't optimize an individual component until the full flow works, even if poorly. The Hoja de ruta enforces this with phased ordering.
- **One logical change per commit.** Different conceptual changes go in separate commits, even if they touch the same file. Easier to revert and bisect.
- **Test before pushing.** Validate syntax (`python -c "import ast; ast.parse(open('FILE').read())"`) and run `COBALT_TEST_MODE=1 COBALT_TEST_NO_GEMINI=1` to confirm no regression.
- **Document the why, not the what.** In-line comments should explain the *reasoning* behind a fix or design decision, not restate what the code does. The git commit message captures the *what*; the comment captures *why future-Claude shouldn't undo this*.

### Bug fixes
- **One synthetic test per fix.** Every bug fixed must be covered by a test case that would detect it if it reappears. This is non-negotiable.
- **Use the "dame explicación Pro" format** for non-trivial fixes (see Trigger phrases below). It forces structured reasoning before applying changes.

### Commits
- **Never add `Co-Authored-By: Claude` (or any form of self-coauthorship) to commits or PRs in this project.** Permanent project policy. Applies to every branch, every commit, every push.
- Commit message in Spanish or English, but consistent within a single message.
- Body should describe: problem, solution, validation outcome (e.g., "9/9 tests pass, signed_sum=+1.22 confirms expected sign inversion").

### Working pace
- When uncertain about user intent or scope, **ask** rather than guess. The Hoja de ruta defines priorities; if a request seems to deviate, surface it.
- When iterating on something the user is testing manually (cron output, paper trading results), **wait for their report** before assuming success.

## Trigger phrases (canonical response formats)

These are user-defined phrases that demand a SPECIFIC response structure. When the user uses one of these phrases — verbatim or near-verbatim — the response MUST follow the documented format exactly, in order, with all sections present, using clear headings or numbered blocks (never paragraph walls).

### "dame explicación Pro"

Used primarily when a code error or design flaw has been identified and needs full explanation before fixing. The response MUST contain these nine sections, in this exact order:

**1. Dónde está el fallo**
Identify the specific location (function name, file, line range, structural issue) and name the problem in one phrase.
Example: *"La función `score_article` está duplicada entre las líneas 1011 y 1280."*

**2. Qué pasa con cada error**
Explain the technical nature of the problem. What does the broken code actually do internally? Why is it broken? Use code references where they help.
Example: *"Python al cargar el módulo retiene solo la segunda definición, sobrescribiendo la primera; las dos versiones difieren en cómo aplican el factor de credibilidad."*

**3. Qué errores causa**
Describe the OBSERVABLE consequences in the running system — la manifestación concreta del bug, no la teoría. Qué artículos puntúan mal, qué alertas se disparan o pierden, qué números salen inflados, etc.
Example: *"Las noticias de Reuters están aplicando credibilidad 0.70 (fallback) en lugar de 1.00, infrapuntuando sistemáticamente las fuentes tier 1."*

**4. Cuál es la solución**
Propose the precise code change. Function-level o line-level si aplica. Indicar qué se añade, qué se elimina, qué se modifica.
Example: *"Borrar la segunda definición de `score_article` (líneas 1240–1280) y conservar la primera, que es la que respeta la spec."*

**5. Esfuerzo estimado**
Cuantifica el tamaño y complejidad de la solución propuesta. Sirve para decidir si arreglarlo "ahora" o "luego", o si conviene meterlo en un commit aparte por seguridad.
Formato: nº de líneas/archivos tocados + rating (trivial / medio / complejo) + tiempo aproximado.
Example: *"2 líneas en una sola función · trivial · ~30 segundos."* o *"Refactor de scoring core, 4 funciones, posible regresión · complejo · ~30 minutos + sesión de validación."*

**6. Riesgo del cambio**
Probabilidad de que el fix rompa algo más en el sistema. Sirve para decidir estrategia de testing y momento de despliegue (ej. no mergear un cambio alto-riesgo justo antes de una ejecución del cron).
Formato: nivel (bajo / medio / alto) + descripción del peor escenario posible + qué validar antes de pushear.
Example: *"Bajo — solo afecta la rama Path A de Gemini, no toca scoring keyword ni agregación. Validar con `COBALT_TEST_MODE=1` antes de push."* o *"Alto — modifica la fórmula de `score_bruto`, podría desplazar todos los umbrales del sistema. Validar contra `state.json` histórico antes de pushear y vigilar el primer cron tras el merge."*

**7. Cómo verificar que el fix funciona**
Comando concreto o procedimiento manual para confirmar que el bug está resuelto y que no aparecieron regresiones. Aprovechar el `COBALT_TEST_MODE=1` cuando aplique.
Example: *"Ejecutar `cd archivos_codigo && COBALT_TEST_MODE=1 python3 -m assets.cobalt.main` y verificar que el Path A del artículo 2 (chocolatería) sigue devolviendo NO. Si devuelve YES, el fix introdujo una regresión."*

**8. Prioridad recomendada**
Sugerencia de cuándo aplicar el fix relativa a otros pendientes.
Formato: 🔴 inmediato / 🟠 esta sesión / 🟡 esta semana / ⚪ backlog. Justificación breve.
Example: *"🔴 inmediato — el bug está corrompiendo el scoring de cada ejecución del cron; cada hora perdida son alertas reales que pueden estar fallando o disparando mal."*

**9. Mejoras en el análisis**
Describe how the system's analysis improves after the fix. Be concrete: qué tipo de artículos ahora puntúan correctamente, qué falsos positivos desaparecen, qué señales se amplifican, qué umbrales se vuelven a respetar.
Example: *"Tras el fix, los artículos de Reuters volverán a tener su peso real (×1.00 en lugar de ×0.70), recuperando aprox. un 43% del score de las disrupciones detectadas por estas fuentes."*
