# 🗺️ MAPA DE main_scorer.py — Referencia rápida para modificaciones

---

## ESTRUCTURA GLOBAL

| # | Sección | Líneas | Para modificar… |
|---|---------|--------|-----------------|
| **0** | PATHS Y CONFIGURACIÓN | 34–44 | Rutas de archivos (state, logs, .env) |
| **1** | LOGGING | 46–61 | Formato de logs, retención (7 días) |
| **2** | CREDENCIALES | 63–100 | Variables SMTP, ACLED, User-Agent |
| **3** | ESTADO PERSISTENTE | 103–162 | Deduplicación por URL, salud de fuentes |
| **4** | UTILIDADES DE TEXTO | 164–179 | Normalización, similitud de títulos |
| **5** | DICCIONARIO BASE | 181–385 | ⬇️ ver tabla detallada |
| **6** | KEYWORD ENTRIES | 387–685 | ⬇️ ver tabla detallada |
| **7** | FUENTES RSS | 687–760 | ⬇️ ver tabla detallada |
| **8** | FETCHING | 762–922 | Cómo se descarga cada fuente |
| **9** | DEDUPLICACIÓN | 923–939 | Umbral similitud de títulos (0.85) |
| **10** | SCORING CORE | 940–1209 | ⬇️ ver tabla detallada |
| **11** | ASSET SELECTION | 1210–1276 | Qué tickers aparecen en el email |
| **12** | EMAIL HTML | 1277–1559 | Plantilla y contenido del email |
| **13** | MAIN LOOP | 1560–1657 | Orquestación de fases, early-exit NARANJA |

---

## SECCIÓN 5 — DICCIONARIO BASE `(líneas 181–385)`

| Sub-bloque | Líneas | Para modificar… | Ejemplo |
|---|---|---|---|
| `ANCHOR_TERMS` | 184–205 | Añadir/quitar términos ancla EN/FR/PT/ES | `"cobalt hydroxide"`, `"minerai de cobalt"` |
| `GEOGRAPHIC_TERMS` | 208–292 | Añadir zonas, minas, ciudades por GEO code | GEO-01 = DRC · GEO-07 = China · GEO-08 = Puertos |
| `GEO_WEIGHTS` | 294–298 | Cambiar el peso de una zona geográfica | GEO-01=**1.80** · GEO-07=**1.60** · GEO-09=**0.40** |
| `CATEGORY_MULTIPLIERS` | 300–321 | Cambiar importancia de una categoría de evento | REG-EXPORT-BAN=**2.3** · GEO-CONFLICT=**2.2** |
| `SSC_CATEGORY_WEIGHTS` | 324–339 | Qué categorías afectan al SSC y cuánto | DEM-SUBSTITUTE=**0.0** · LAB-STRIKE-THR=**0.6** |
| `SMC_CATEGORY_OVERRIDES` | 342–351 | Override de categorías en SMC | REG-*=**1.2** · RES-RESOLVE=**0.5** |
| `NEGATION_TERMS` | 353–365 | Añadir palabras negadoras por idioma | `"resolved"`, `"lifted"`, `"resolu"` |
| `COUP_CONTEXT_TERMS` | 369–372 | Términos requeridos cerca de "coup" (±40 palabras) | `"military"`, `"junta"`, `"katanga"` |
| `FALSE_POSITIVE_FILTERS` | 374–385 | Patrones que anulan un hit por categoría | `"bowling strike"` cancela LAB-STRIKE-ACT |

### Tabla de pesos GEO rápida

| Código | Zona | Peso |
|--------|------|------|
| GEO-01 | DRC Copperbelt | **1.80** |
| GEO-07 | China refinación | **1.60** |
| GEO-08 | Puertos africanos | **1.50** |
| GEO-03 | Corredores Este (Tanzania/Mozambique) | **1.40** |
| GEO-04 | Corredor Sur (Sudáfrica/Zimbabwe) | **1.30** |
| GEO-02 | Zambia | **1.20** |
| GEO-05 | Australia | **0.90** |
| GEO-06 | Filipinas | **0.80** |
| GEO-09 | Latinoamérica | **0.40** |

### Tabla de multiplicadores por categoría rápida

| Categoría | Mult. | Categoría | Mult. |
|-----------|-------|-----------|-------|
| REG-EXPORT-BAN | **2.3** | LAB-STRIKE-ACT | **2.1** |
| GEO-CONFLICT | **2.2** | LAB-ACCIDENT | **1.8** |
| GEO-COUP | **2.0** | REG-LICENSE | **1.9** |
| GEO-SANCTION | **1.9** | REG-NATIONAL | **1.8** |
| LOG-PORT | **2.0** | REG-ENV | **1.7** |
| LOG-RAIL | **1.8** | LOG-CUSTOMS | **1.7** |
| LOG-ROAD | **1.5** | FMA-FLOOD | **1.7** |
| LAB-STRIKE-THR | **1.5** | DEM-SUBSTITUTE | **−1.5** |
| GEO-ELECTION | **0.8** | DEM-DROP | **−1.3** |

---

## SECCIÓN 6 — KEYWORD ENTRIES `(líneas 387–685)`

> Formato de cada entrada: `("término", "CATEGORÍA", peso, requires_context, ventana_palabras, [GEO-boost])`

| Sub-bloque | Líneas | Categoría | Idiomas | Notas |
|---|---|---|---|---|
| Puertos | 393–411 | `LOG-PORT` | EN FR PT ES | GEO-boost: GEO-08 |
| Ferrocarril | 413–425 | `LOG-RAIL` | EN FR PT ES | GEO-boost: GEO-03/04 |
| Carretera | 427–439 | `LOG-ROAD` | EN FR PT ES | Incluye `kasumbalesa` (l.431) |
| Aduanas | 441–450 | `LOG-CUSTOMS` | EN FR PT ES | `requires_context: True` |
| Buques | 452–456 | `LOG-VESSEL` | EN | Sin geo-boost |
| Conflicto armado | 458–473 | `GEO-CONFLICT` | EN FR ES PT | GEO-boost: GEO-01/02 |
| Golpe de estado | 475–485 | `GEO-COUP` | EN FR ES | Validado por `COUP_CONTEXT_TERMS` |
| Sanciones | 487–494 | `GEO-SANCTION` | EN FR ES PT | No decaen por edad |
| Protestas | 496–503 | `GEO-PROTEST` | EN FR ES PT | `requires_context: True` |
| Huelga activa | 505–521 | `LAB-STRIKE-ACT` | EN FR PT ES | GEO-boost: GEO-01/02/08 |
| Amenaza huelga | 523–530 | `LAB-STRIKE-THR` | EN FR PT ES | SSC weight = 0.6 |
| Kiswahili | 532–536 | `LAB-STRIKE-ACT` / `LOG-PORT` | SW | DRC oriental + Tanzania |
| Accidentes mineros | 538–548 | `LAB-ACCIDENT` | EN FR PT ES | GEO-boost: GEO-01/02 |
| Minería artesanal (ASM) | 550–558 | `LAB-ACCIDENT` / `REG-LICENSE` | EN FR ES | GEO-01 únicamente |
| Ban de exportación | 560–569 | `REG-EXPORT-BAN` | EN FR PT ES | Mayor peso del sistema (5.0) |
| Impuestos mineros | 571–578 | `REG-TAX` | EN FR PT ES | No decaen por edad |
| Licencias mineras | 580–586 | `REG-LICENSE` | EN FR PT ES | No decaen por edad |
| Nacionalización | 588–592 | `REG-NATIONAL` | EN FR PT ES | No decaen por edad |
| Inundaciones | 594–601 | `FMA-FLOOD` | EN FR PT ES | Incluye ciclones GEO-03/04 |
| Cortes eléctricos | 603–610 | `FMA-DROUGHT` | EN FR ES | Incluye `inga dam` (l.607) |
| Sustitutos cobalto | 612–624 | `DEM-SUBSTITUTE` | EN FR ES PT | ⚠️ pesos **negativos** — solo SMC |
| Demanda/mercado | 626–638 | `DEM-SURGE` | EN FR ES | Sin geo-boost |
| Resoluciones | 641–658 | `RES-RESOLVE` | EN FR ES PT | ⚠️ pesos **negativos** — reduce score activo |
| Credibilidad fuentes | 661–685 | `SOURCE_CREDIBILITY` | — | Reuters/ACLED=1.00 → Google News=0.50 |

---

## SECCIÓN 7 — FUENTES RSS `(líneas 687–760)`

> Campos por fuente: `name · url · lang · full_text · rate_limit (seg) · timeout (seg)`

### RSS_SOURCES `(líneas 691–748)`

| Grupo | Nombre clave | Línea | Lang | full_text | Credibilidad |
|-------|-------------|-------|------|-----------|-------------|
| **Tier 1** | `reuters_africa` | 693 | EN | ✅ | 1.00 |
| **Tier 1** | `reuters_commodities` | 696 | EN | ✅ | 1.00 |
| **Tier 1** | `reuters_china` | 699 | EN | ✅ | 1.00 |
| **Mining** | `mining_com_cobalt` | 703 | EN | ❌ | 1.00 |
| **Mining** | `kitco` | 706 | EN | ❌ | 0.85 |
| **África** | `allafrica` | 710 | EN | ✅ | 0.85 |
| **África** | `bbc_africa` | 713 | EN | ❌ | 0.90 |
| **África** | `miningmx` | 716 | EN | ❌ | 0.90 |
| **África FR** | `rfi_afrique` | 719 | FR | ✅ | 0.80 |
| **África** | `club_mozambique` | 722 | EN | ❌ | 0.80 |
| **África** | `lusaka_times` | 725 | EN | ❌ | 0.75 |
| **Conflicto** | `reliefweb_drc` | 729 | EN | ❌ | 0.90 |
| **Desastres** | `gdacs` | 732 | EN | ❌ | 1.00 |
| **Google News** | `gnews_cobalt_en` | 736 | EN | ❌ | 0.50 |
| **Google News** | `gnews_cobalt_fr` | 739 | FR | ❌ | 0.50 |
| **Google News** | `gnews_drc` | 742 | EN | ❌ | 0.50 |
| **Google News** | `gnews_durban` | 745 | EN | ❌ | 0.50 |

### SCRAPING_SOURCES — Puertos `(líneas 750–760)`

| Nombre clave | Línea | Lang | País | Timeout |
|-------------|-------|------|------|---------|
| `transnet_durban` | 751 | EN | Sudáfrica | 20s |
| `tpa_tanzania` | 754 | EN | Tanzania | 20s |
| `cfm_mozambique` | 757 | PT | Mozambique | 20s |

> **ACLED** no está en estas listas — se configura vía `.env` (`ACLED_KEY`, `ACLED_EMAIL`) y se llama en `fetch_acled()` (l.872)

---

## SECCIÓN 10 — SCORING CORE `(líneas 940–1209)`

| Función | Líneas | Para modificar… |
|---------|--------|-----------------|
| `tokenize()` | 944–946 | Cómo se parten las palabras |
| `has_anchor()` | 948–953 | Lógica de detección de ancla |
| `has_coup_context()` | 955–961 | Ventana de contexto para "coup" (actualmente ±40 palabras) |
| `has_negation_near()` | 963–972 | Ventana de negación (actualmente ±5 palabras) |
| `check_false_positive()` | 974–980 | Lógica de filtro de falsos positivos |
| `detect_geo()` | 982–991 | Cómo se detectan los GEO codes en el texto |
| `age_factor()` | 993–1009 | ⬇️ ver tabla de decaimiento |
| **`score_article()`** | 1011–1116 | ⚠️ **Función central del scoring** — itera keywords y aplica todos los filtros |
| `calc_ssc()` | 1118–1121 | Aplica `SSC_CATEGORY_WEIGHTS` al score bruto |
| `calc_smc()` | 1123–1126 | Aplica `SMC_CATEGORY_OVERRIDES` al score bruto |
| `aggregate_scores()` | 1128–1185 | Agrupa en eventos, aplica bonus ×1.30 confirmación, suma con fórmula |
| `level_ssc()` | 1187–1195 | Umbrales de nivel SSC |
| `level_smc()` | 1197–1204 | Umbrales de nivel SMC |
| `should_alert()` | 1206–1208 | Condición de disparo de alerta |

### Decaimiento por edad — `age_factor()` `(l.993–1009)`

| Edad del artículo | Categorías afectadas | Factor |
|---|---|---|
| ≤ 72 horas | Todas | **1.0** (sin decay) |
| > 72 horas | LOG-* y LAB-* | **0.30** |
| > 72 horas | Resto de categorías | **0.60** |
| > 7 días | Todas | **0.10** |
| Cualquier edad | REG-* y GEO-SANCTION | **1.0** (nunca decaen) |

### Fórmula de scoring en `score_article()` `(l.1081)`

```
score_bruto = |peso_keyword| × geo_weight × cat_multiplicador × credibilidad_fuente
              × age_factor  × [×0.15 si negación]  × [×0.40 si geo genérico]
```
> Descartado si `score_bruto < 3.0`

### Fórmula de agregación en `aggregate_scores()` `(l.1174–1181)`

```
total = score[0] + Σ(score[i] × 0.5)    ← i > 0, ordenados de mayor a menor
```
> Bonus ×1.30 si ≥ 3 fuentes con credibilidad ≥ 0.80 reportan el mismo evento

### Umbrales de nivel y alerta

| Score | SSC | SMC |
|-------|-----|-----|
| VERDE | < 16 | < 21 |
| AMARILLO | 16–30 | 21–40 |
| NARANJA | 31–50 | 41–65 |
| ROJO | > 50 | > 65 |

**Alerta dispara cuando:** `SSC ≥ 31` **OR** `SMC ≥ 41` **OR** `(SSC ≥ 20 AND SMC ≥ 30)`
