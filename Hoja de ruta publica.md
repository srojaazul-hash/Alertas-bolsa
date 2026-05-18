# 🗺️ HOJA DE RUTA — Sistema multi-asset

> Roadmap estratégico del proyecto. Versión pública (versionada en Git).
> Última revisión: 2026-05-16

---

## 🎯 Visión del proyecto

Sistema **multi-asset de alerta temprana sobre materias primas** con capa de analista LLM y validación por paper trading. La primera implementación (cobalto) está operativa y sirve como arquitectura de referencia.

**Meta final**: framework generalizable donde añadir un asset nuevo (cobre, litio, petróleo…) requiera solo cambiar el diccionario y la lista de fuentes — no reescribir la pipeline de scoring. El sistema alimenta eventos estructurados a un analista LLM que produce razonamiento auditable (factores, escenarios, riesgos) en JSON, que luego dirige paper trading automatizado vía Alpaca para medir performance objetivamente.

**Sin asunción de alpha desde el día 1.** El sistema se valida empíricamente mediante paper trading antes de cualquier consideración de capital real.

---

## 🏗️ Arquitectura objetivo

```
[Fuentes RSS/API multi-asset]  →  [Framework scoring + Gemini context]
                                          ↓
                                  [JSON acumulativo de eventos]
                                          ↓
                                  [Analista LLM — razonamiento estructurado JSON]
                                          ↓
                                  [Trader automatizado — Alpaca paper]
                                          ↓
                                  [Dashboard de métricas]
```

**Principio núcleo**: el analista LLM NO toma decisiones ciegas. Emite **razonamiento estructurado** (factores alcistas, factores bajistas, escenarios, probabilidades, riesgos). La decisión final combina ese razonamiento con reglas explícitas, lo que hace al sistema **auditable, debuggable y aprendible**.

---

## 📊 Estado del proyecto (2026-05-16)

### ✅ Completado
- Sistema cobalto end-to-end en GCP free tier (cron 3×/día)
- Scoring multilingüe (EN/FR/PT/ES + Kiswahili), ~280 keywords
- 11 zonas geográficas con pesos calibrados (GEO-01 DRC = 1.80, el más alto)
- Validación contextual vía Gemini 2.5 Flash Lite (free tier)
- 6 puntos auditados y resueltos sobre `score_article` / `aggregate_scores`:
  - A: `find()` primera ocurrencia → todas las ocurrencias evaluadas
  - B: filtro de falsos positivos global → por ocurrencia
  - C: umbral antes de multiplicadores → doble umbral
  - D: signo en negación de pesos negativos → invertir signo
  - E: `DEM-DROP` dead code → eliminado
  - F: bucket por día UTC → ventana deslizante 24h
- 9 artículos sintéticos + 4 casos de clustering como tests de regresión permanente
- Flag `COBALT_TEST_NO_GEMINI=1` para iterar sin gastar cuota
- Git workflow PC ↔ GitHub ↔ VM
- `.gitignore` protegiendo secretos en raíz del repo

### ❌ Pendiente (por orden de impacto)
1. **Extracción del framework como librería reutilizable** ← más crítico
2. Segundo asset (cobre, recomendado) implementado
3. Analista LLM con output JSON estructurado
4. Conexión a Alpaca paper trading
5. Loop end-to-end completo
6. Dashboard de métricas

---

## 🛣️ Roadmap por fases

**Regla de oro**: NO saltarse fases. End-to-end feo > parte perfecta.

---

### FASE 1 — Extraer framework como librería  *(estimado: 1-2 semanas)*

**Objetivo**: añadir un nuevo asset = cambiar UN diccionario, no copiar 1000 líneas.

**Por qué primero**: construir el segundo asset sin esta extracción genera dos copias divergentes del scorer en un mes.

**Estructura objetivo** (todo bajo `archivos_codigo/`):
```
archivos_codigo/
├── framework/
│   ├── sources.py       # clase base RSSFetcher, ScrapingFetcher, APIFetcher
│   ├── scoring.py       # score_article(article, cfg) genérico + AssetConfig
│   ├── aggregator.py    # aggregate_scores con clustering temporal
│   ├── llm_validator.py # capa Gemini (Path A / Path B / dispatcher)
│   └── state.py         # load_state, save_state, dedup, source_health
├── assets/
│   ├── cobalt/
│   │   ├── dictionary.py    # KEYWORDS, GEO_TERMS, multipliers + COBALT_CONFIG
│   │   └── main.py          # orquestador (cron point)
│   └── copper/              # se añade en FASE 2
├── tests/
│   └── synthetic_articles.py  # los 9 + casos de clustering
├── legacy/
│   └── main_scorer.py        # monolito pre-extracción (referencia)
└── MAPA_SCORER.html / .md    # mapa visual del monolito legacy
```

**Tareas concretas**:
- [ ] Crear estructura `archivos_codigo/framework/` y `archivos_codigo/assets/cobalt/`
- [ ] Extraer cada función genérica al módulo correspondiente
- [ ] Mover todo lo cobalto-específico a `archivos_codigo/assets/cobalt/dictionary.py`
- [ ] `archivos_codigo/assets/cobalt/main.py` solo importa del framework y del dictionary; cero lógica propia
- [ ] Ejecutar desde `archivos_codigo/`: `COBALT_TEST_MODE=1 COBALT_TEST_NO_GEMINI=1 python -m assets.cobalt.main` → 9/9 tests pasan
- [ ] Cron en VM apunta al nuevo entry point

**Criterio de éxito**: añadir un asset nuevo cuesta < 1 día de trabajo (solo escribir su diccionario y URLs).

---

### FASE 1.5 — Saneamiento del pipeline de fuentes  *(estimado: 4-8h)*

**Objetivo**: tener al menos 3 fuentes cobalto-específicas activas que entreguen contenido relevante de forma consistente. Sin esto, Fase 2-5 construyen sobre datos vacíos.

**Por qué surgió esta fase (audit 2026-05-17)**: Auditoría sistemática de las 25 fuentes RSS reveló:
- **13 fuentes confirmadamente rotas** (HTTP error, feed inválido, dominio bloqueado, Google News RSS muerto)
- **121-145 artículos en 48h**, de los cuales **solo 1 menciona "cobalt"** (0.7%)
- **0 hits en producción** durante varios días consecutivos — comportamiento correcto del scoring sobre input de basura
- Bug descubierto y corregido: las fuentes DEGRADED nunca se reintentaban (commit independiente)

**Hallazgos específicos sobre fuentes muertas**:
- `mining.com` bloquea con HTTP 403 toda la IP de GCP (AWS WAF) — no recuperable client-side
- Google News RSS devuelve vacío para búsquedas que antes funcionaban (Google restringe desde 2024)
- Varias fuentes "Tier 1" del config original (Northern Miner, IM Mining, Energy Storage News) responden HTTP 200 pero con 0 entradas o feed malformado

**Tareas concretas**:
- [x] Limpieza del config: eliminar 6 fuentes confirmadamente rotas, renombrar 3 con nombres engañosos (commit `cleanup config de fuentes RSS`)
- [x] Fix del bug DEGRADED-forever en `framework/state.py` (commit `Fix: source_health DEGRADED puede reintentarse`)
- [ ] Probar individualmente con curl: `kitco` (im-mining.com), `miningmx`, `mining_technology`, `energy_storage_news`. Eliminar o mantener según resultado real.
- [ ] Investigar feeds RSS activos en 2026 para cobalto. Candidatos a evaluar:
  - Cobalt Institute (cobaltinstitute.org) — sin RSS público confirmado, ver si hay
  - Fastmarkets cobalt — paywall probable, ver si tienen newsletter gratis
  - S&P Global Commodity Insights — paywall, ver alternativas
  - Argus Media — paywall
  - Benchmark Mineral Intelligence — paywall pero tienen blog público
  - Bloomberg via NewsAPI.org (free tier 100 req/día)
  - Reuters business RSS oficial (si todavía existe sin paywall)
- [ ] Decidir si justifica cambiar de proveedor de VM (Hetzner / OVH) para sortear bloqueos por IP-range de GCP. Coste vs beneficio.
- [ ] Añadir 5-10 fuentes nuevas al config con credibilidad calibrada
- [ ] Test de salud automático: añadir log de "fuentes muertas hoy" en cada run del cron, con umbral de aviso si >30% del config falla
- [ ] Considerar implementación de `framework/sources.py` opcional con TLS fingerprint de browser (`curl_cffi` o equivalente) para feeds que filtran por TLS
- [ ] **Dedup robusto cross-run con title similarity** (anotado 2026-05-17). La URL normalization añadida cubre variaciones triviales (utm tags, prefijo `www.`, trailing slash, query/fragment). Pero NO cubre el caso de "mismo contenido republicado en otro dominio" — Reuters→Yahoo Finance→MSN con URLs completamente distintas pero artículo equivalente. Para ese caso implementar matching por similitud de título contra `processed_urls`. Requiere extender el schema de `processed_urls` en `state.json` para guardar también el title (backwards-compat: entradas sin title se siguen tratando como hoy). Complejidad: media. Beneficio: incierto hasta tener 1-2 semanas de datos del cron real — si vemos que la duplicación cross-domain ocurre con frecuencia, justifica el esfuerzo; si no, queda en backlog.

**Criterio de éxito**: 
- ≥3 fuentes cobalto-específicas activas entregando ≥10 artículos cobalto-relevantes/semana en agregado
- Hits/día reales ≥1 en promedio durante 7 días consecutivos
- ≥80% del config en estado OK (no DEGRADED) durante 7 días consecutivos

**Anti-patrón a evitar**: investigar fuentes durante semanas sin avanzar al siguiente paso. Si tras 8h de research no se han encontrado ≥3 fuentes nuevas viables, **bajar el estándar** (aceptar fuentes con cobertura cobalto incidental pero alto volumen, como Reuters business general) y avanzar — siempre se pueden refinar después con paper trading real (Fase 6).

---

### FASE 2 — Segundo asset: COBRE  *(estimado: 1 semana)*

**Por qué cobre específicamente**:
- Mercado más líquido que cobalto → menor riesgo de proxy disfuncional en paper trading
- Hay futuros (CME) y ETFs (COPX) → instrumentos operables disponibles
- Misma geografía base que cobalto (Chile, Perú, DRC, Zambia) → mucha estructura geo reutilizable
- Correlación cobre/cobalto → tu sistema cobalto ya te informa parcialmente del cobre

**Tareas concretas**:
- [ ] Crear `assets/copper/dictionary.py` con ~100 keywords iniciales
- [ ] Identificar 8-10 fuentes RSS específicas de cobre (Reuters Metals, Mining.com Copper, Codelco news, etc.)
- [ ] Crear `assets/copper/main.py` (clon del cobalto, distinto dictionary)
- [ ] Configurar cron en VM para correr también el de cobre
- [ ] Verificar que produce alertas razonables (no obsesionarse con perfección)

**Criterio de éxito**: sistema corre para cobre sin errores y produce ≥ 3 alertas de ejemplo en primera semana.

---

### FASE 3 — Analista LLM con razonamiento estructurado  *(estimado: 1-2 semanas)*

**Objetivo crítico**: el analista NO es una caja negra que dice "compra X". Emite razonamiento auditable.

**Inputs al analista por evento**:
- Lista de hits del último run (scoring, geo, keyword, fecha)
- JSON acumulativo: historial de eventos relacionados últimos 30 días
- Snapshot de precios actuales (LME, ETFs relevantes)
- Posiciones actuales en paper trading

**Output JSON forzado (Gemini structured output)**:
```json
{
  "evento_detectado": "string corto descriptivo",
  "categoria_evento": "supply_disruption | demand_surge | regulatory | geopolitical | weather",
  "asset_principal": "cobalt | copper | …",
  "horizonte_estimado": "dias | semanas | meses",
  "probabilidad_materializacion": 0.0,
  "factores_alcistas": [{"factor": "string", "peso": 0.0}],
  "factores_bajistas": [{"factor": "string", "peso": 0.0}],
  "escenarios": [
    {"nombre": "base", "probabilidad": 0.6, "implicacion": "string"},
    {"nombre": "alcista", "probabilidad": 0.25, "implicacion": "string"},
    {"nombre": "bajista", "probabilidad": 0.15, "implicacion": "string"}
  ],
  "activos_afectados": [
    {"ticker": "LIT", "direccion": "alcista", "conviccion": 0.0, "razon": "string"}
  ],
  "riesgos_clave": ["string"],
  "necesita_seguimiento": true,
  "que_invalidaria_esta_lectura": "string"
}
```

**Tareas concretas**:
- [ ] Diseñar el `response_schema` formal en Pydantic o equivalente
- [ ] Implementar `framework/analyst.py` que reciba hits + memoria y devuelva este JSON
- [ ] Implementar `framework/event_memory.py` (qué guardar, qué truncar tras 30 días)
- [ ] Conectar al main loop: cada alerta → llamada al analista → guardar output
- [ ] Logging detallado: cada decisión registrada con su input completo

**Anti-patrón**: NUNCA usar Gemini en modo conversacional libre. SIEMPRE `response_schema`. SIEMPRE estructura forzada.

**Criterio de éxito**: mismo input dos veces → outputs con estructura idéntica y razonamiento coherente (los LLMs tienen variabilidad — buscamos coherencia, no identidad).

---

### FASE 4 — Paper trading mínimo viable  *(estimado: 1 semana)*

**Plataforma**: **Alpaca** (https://alpaca.markets/)
- Free tier: paper trading ilimitado
- API moderna, Python SDK bien documentado
- US stocks + crypto (cubre LIT, REMX, COPX, mining stocks)

**Tareas concretas**:
- [ ] Crear cuenta Alpaca, conseguir API keys de paper trading
- [ ] Implementar `framework/trader.py` que:
  - Lea el output JSON del analista
  - Aplique **reglas claras de sizing** (max 5% capital por trade, escritas en código)
  - Ejecute órdenes en Alpaca paper
  - Registre cada operación con: timestamp, ticker, dirección, sizing, razón, JSON del analista que la motivó
- [ ] Definir **reglas de salida** (no negociables):
  - Stop loss: -5% por trade
  - Take profit: +10% por trade
  - Tiempo máximo: 30 días por posición
- [ ] Logging exhaustivo: cada operación trazable hasta el evento que la causó

**Anti-patrones**:
- ❌ Operar sin stop loss
- ❌ Sizing arbitrario "según feeling"
- ❌ Cambiar reglas a mitad

**Criterio de éxito**: loop completo end-to-end funcionando, aunque pierda dinero virtual al principio.

---

### FASE 5 — Métricas y observabilidad  *(estimado: 1 semana)*

**Las tres preguntas críticas a poder responder**:

#### 1. Latencia signal → orden
Cuánto tarda el sistema desde que la noticia se publica hasta que se ejecuta la operación.
- ✅ < 1h → en el juego
- ⚠️ 1-4h → marginal, mejorable
- ❌ > 4h → demasiado lento para event-driven

#### 2. Consistencia del analista LLM
¿El mismo input produce outputs coherentes?
- Test: enviar 10× el mismo conjunto de hits, medir varianza de factores principales
- ✅ varianza < 20%
- ⚠️ 20-50%
- ❌ > 50% → prompt mal diseñado, requiere rediseño

#### 3. Performance paper trading
Win rate, Sharpe, drawdown.
- Necesitas ≥ 30 operaciones para que la muestra empiece a ser informativa

**Tareas concretas**:
- [ ] Dashboard simple (puede ser Jupyter notebook semanal)
- [ ] Tabla de operaciones: fecha, asset, dirección, sizing, P&L, razón
- [ ] Tabla de eventos: timestamp, asset, hits, decisión analista, ejecutado, resultado
- [ ] Gráficos: equity curve, drawdown, distribución de P&L por trade
- [ ] Test de consistencia automático (mismo input 10×/semana)

---

### FASE 6 — Optimización con datos reales  *(continua)*

Una vez las fases 1-5 estén funcionando, AHORA optimizar con datos reales, no con conjeturas.

**NO optimizar nada antes de tener métricas.**

Ciclo de mejora:
1. Mirar métricas → 2. Identificar cuello de botella → 3. Hipótesis de mejora → 4. Implementar → 5. Comparar pre/post → 6. Repetir

---

## 🧭 Principios de diseño (no negociables)

1. **End-to-end feo antes que parte perfecta.** No optimizar cobalto hasta tener el loop completo.
2. **Auditable > Inteligente.** Una IA que decide sin que entiendas el porqué es peor que un script mediocre pero explicable.
3. **Free tier hasta demostrar lo contrario.** Cada upgrade pagado debe justificarse con métricas.
4. **Paper trading es la verdad.** No "creo que funcionaría". Mide.
5. **El analista LLM no inventa datos.** Solo razona sobre los datos que le das. Si Gemini empieza a citar precios o eventos que no le pasaste, recorta el contexto.
6. **Reglas de sizing y stop antes de operar.** Sin excepción.
7. **Cada operación trazable al evento que la causó.** Si no, no puedes aprender.

---

## 📈 Métricas a vigilar (review semanal)

| Métrica | ✅ Bueno | ❌ Mal | Cómo medir |
|---|---|---|---|
| Latencia signal → orden | < 1h | > 4h | timestamp noticia vs orden Alpaca |
| Hits/día por asset | 5-20 | 0 o >100 | logs |
| Llamadas Gemini/día | < 1500 (free) | rate limit | logs Gemini |
| Consistencia analista | varianza < 20% | > 50% | test 10×/sem mismo input |
| Win rate paper | > 45% | < 30% | trades cerrados |
| Sharpe simulado | > 0.5 | < 0 | equity curve |
| Drawdown máximo | < 15% | > 30% | equity curve |

---

## 🚫 Anti-patrones a evitar

1. **Pulir cobalto eternamente.** Ya está suficientemente bueno. Pasarse a cobre cuanto antes.
2. **Añadir features antes del loop completo.** Si el end-to-end no funciona, una feature más no lo arregla.
3. **Decisiones del analista sin trazabilidad.** Cada operación debe rastrearse al evento. Si no, no puedes aprender.
4. **Sizing variable según "feeling".** Reglas definidas una vez, no se tocan.
5. **Operar con dinero real antes de 3+ meses de paper positivo.** No.
6. **Buscar la perfección del prompt antes de tener métricas.** Iterás más rápido con datos.
7. **Confundir actividad con progreso.** Commits diarios ≠ progreso si no avanzan en el roadmap.

---

## 🛠️ Recursos

### Documentación
- Gemini structured output: https://ai.google.dev/gemini-api/docs/structured-output
- Alpaca paper trading: https://alpaca.markets/docs/trading/paper-trading/
- LME cobalto: https://www.lme.com/Metals/EV/Cobalt
- LME cobre: https://www.lme.com/Metals/Non-ferrous/Copper
- Cobalt Institute: https://www.cobaltinstitute.org/

### Cuentas free tier
- ✅ Google AI Studio: aistudio.google.com/apikey
- ✅ ACLED: developer.acleddata.com
- ✅ NewsAPI.org: newsapi.org (100 req/día, delay 24h)
- ✅ GNews.io: gnews.io (100 req/día, real-time)
- ⏳ Alpaca: alpaca.markets/signup (Fase 4)
- ✅ GitHub
- ✅ GCP

---

## 📅 Tracking de progreso

> Marcar [x] al completar. NO saltarse fases.

### Fase 1 — Framework librería
- [x] Estructura `archivos_codigo/framework/` y `archivos_codigo/assets/cobalt/` creadas
- [x] `archivos_codigo/framework/sources.py` extraído
- [x] `archivos_codigo/framework/scoring.py` extraído (incluye `AssetConfig` dataclass)
- [x] `archivos_codigo/framework/aggregator.py` extraído
- [x] `archivos_codigo/framework/llm_validator.py` extraído
- [x] `archivos_codigo/framework/state.py` extraído
- [x] `archivos_codigo/assets/cobalt/dictionary.py` con todos los keywords y geo
- [x] `archivos_codigo/assets/cobalt/main.py` simplificado a orquestación
- [x] Tests sintéticos cobalto siguen pasando 9/9 (+ 4 casos de clustering)
- [ ] Cron en VM apunta al nuevo entry point

### Fase 1.5 — Saneamiento de fuentes
- [x] Limpieza de fuentes confirmadamente rotas (6 eliminadas, 3 renombradas)
- [x] Fix del bug DEGRADED-forever en `framework/state.py`
- [x] Tests sintéticos del fix DEGRADED (4 casos SH-1 a SH-4)
- [x] +9 fuentes nuevas curl-tested (cobalt_institute, australian_mining, cnbc_commodities, resource_world, ns_energy, oilprice_main, investing_commodities, +2 descartadas tras forensic audit)
- [x] **Integración NewsAPI.org** como fetcher genérico del framework (3 queries cobalto, full_text=True)
- [x] **Integración GNews.io** como segundo API (real-time, complementario, sleep 2s entre queries por rate limit)
- [x] **Observabilidad por hit**: log INFO con keyword/categoría/score/geo por cada artículo que dispara (`HIT [...]` en `scorer.log`)
- [x] **URL normalization** para dedup estable cross-API (`_normalize_url` strip query/fragment/www/slash + backwards-compat con state.json viejo)
- [x] **Gap militar deployment** cubierto en GEO-CONFLICT: +20 keywords EN/FR/ES/PT + artículo sintético #10 bloquea regresión
- [x] Fix logging: COBALT_TEST_MODE=1 ya NO contamina scorer.log de producción (solo consola en modo test)
- [ ] Observación durante 2-3 días naturales del cron para validar: (a) si FP de "port strike" se repite y justifica `requires_context=True`, (b) volumen real de hits/día, (c) si GNews trae artículos cuando NewsAPI tiene delay
- [ ] **Dedup robusto cross-run con title similarity** — la URL normalization no cubre el caso de "mismo contenido republicado en otro dominio". Anotado para implementar tras 1-2 semanas de datos
- [ ] Triaje individual con curl de fuentes sospechosas si persisten en 0 entradas
- [ ] Hits/día reales ≥1 en promedio durante 7 días consecutivos
- [ ] Decisión sobre activar Gemini en producción (espera a volumen ≥3 hits/run consistente)

### Fase 2 — Cobre
- [ ] `assets/copper/dictionary.py` con ~100 keywords
- [ ] Fuentes RSS de cobre identificadas (≥ 8)
- [ ] Sistema corre para cobre sin errores
- [ ] ≥ 3 alertas de ejemplo generadas en primera semana

### Fase 3 — Analista LLM
- [ ] Schema JSON definido y documentado
- [ ] Prompt template con `response_schema`
- [ ] `framework/analyst.py` implementado
- [ ] `framework/event_memory.py` implementado
- [ ] Integrado en main loop
- [ ] Cada decisión logueada con input completo

### Fase 4 — Paper trading
- [ ] Cuenta Alpaca creada
- [ ] `framework/trader.py` implementado
- [ ] Reglas de sizing en código (max 5% por trade)
- [ ] Reglas de salida en código (SL -5%, TP +10%, tiempo máx 30d)
- [ ] Primera operación paper end-to-end
- [ ] Loop completo corriendo en cron

### Fase 5 — Métricas
- [ ] Dashboard de operaciones funcional
- [ ] Latencia signal → orden medida automáticamente
- [ ] Test de consistencia analista automático (10×/sem)
- [ ] ≥ 30 operaciones acumuladas para análisis

### Fase 6 — Optimización
- [ ] Primera iteración de mejora basada en datos reales
- [ ] (continua, no se cierra)

---

## 📝 Notas / insights acumulados

> Espacio libre para aprendizajes a medida que el proyecto avanza. Datado.

- **2026-05-16**: Auditoría `score_article` completada (6/6 puntos). Tests de regresión cubren todos los fixes. Framework listo para empezar Fase 1.
- **2026-05-17**: Fase 1 ejecutada. `main_scorer.py` (2256 líneas, monolito) extraído en `archivos_codigo/framework/` (genérico, ~1037 líneas) + `archivos_codigo/assets/cobalt/` (datos + orquestador, ~1328 líneas) + `archivos_codigo/tests/synthetic_articles.py` (~355 líneas). `AssetConfig` dataclass encapsula los parámetros del asset; cada función del framework lo recibe en lugar de leer globals. 9/9 artículos sintéticos + 4/4 clusters pasan con los valores numéricos exactos del monolito (signed_sum=+1.22 para Art 9, SSC=23.40 para F3, etc.). Entry point nuevo: desde `archivos_codigo/`, `python -m assets.cobalt.main`. La carpeta original `archivos codigo` renombrada a `archivos_codigo` (sin espacio) para que sea un identificador Python válido; todo el código nuevo consolidado dentro. `main_scorer.py` movido a `archivos_codigo/legacy/` como referencia. Falta sincronizar cron en VM.
- **2026-05-17 (tarde)**: Auditoría del pipeline de fuentes en VM tras corte → 0 hits durante días. Hallazgo: el scoring no está roto, las fuentes sí. 13 de 25 fuentes confirmadamente rotas (mining.com bloqueada por AWS WAF a IPs de GCP, Google News RSS muerto sistémicamente desde 2024, varias mining specialty con feeds inválidos). Bug descubierto en `framework/state.py`: las fuentes DEGRADED nunca se reintentaban (saltadas indefinidamente). Cuatro commits: extracción Fase 1, reorg dentro de `archivos_codigo/`, fix DEGRADED-cooldown (con 4 tests sintéticos SH-1 a SH-4), cleanup de config (6 fuentes eliminadas, 3 renombradas porque "reuters_*" nunca fueron Reuters). Fase 1.5 añadida al roadmap: investigar y añadir ≥3 fuentes cobalto-específicas que funcionen en 2026.
- **2026-05-17/18 (sesión larga)**: Saneamiento completo de Fase 1.5. **+9 fuentes RSS** confirmadas tras curl-test desde IP de GCP (Cobalt Institute, Australian Mining, CNBC Commodities, Resource World, NS Energy, OilPrice, Investing.com, etc.) — 2 descartadas tras forensic audit con feedparser (cleantechnica publica <1/20 días, radio_okapi devuelve archivo histórico de 27 días). **Integración NewsAPI.org** como fetcher genérico (3 queries Boolean cobalto-específicas, free tier 100/día, delay 24h, full_text=True para superar truncado de 200ch). **Integración GNews.io** como segundo API en paralelo (real-time, 100 req/día separados, sleep 2s entre queries por rate limit per-segundo del free tier). **Observabilidad por hit** añadida: cada artículo que dispara genera log INFO con keyword/categoría/score/geo. **URL normalization** para dedup cross-API: `_normalize_url` strip query/fragment/www/slash, evita inflación de 50% en `aggregate_scores` cuando GNews día 1 + NewsAPI día 2 traen el mismo artículo con URLs ligeramente distintas. **Gap militar deployment** cubierto en GEO-CONFLICT (+20 keywords EN/FR/ES/PT, artículo sintético #10). **Fix logging**: COBALT_TEST_MODE=1 ahora solo escribe a consola, no contamina scorer.log de producción. Total **45 tests sintéticos** verdes. Primer hit real detectado en cron natural (artículo de protestas Kenia que disparó `port strike` LOG-PORT por incidental geo+keyword sin anchor — score 11.34, VERDE, no cruzó umbral — documentado como ejemplo del trade-off `requires_context=False`). **Decisiones rechazadas con explicación**: no relajar umbrales por motivación, no scraping directo de Google (ToS + bloqueo IP), no activar Gemini sin tráfico, no title similarity cross-run hasta tener datos reales. Estado: cron entrega 1-3 hits/run en condiciones favorables, observable end-to-end, listo para evaluación de 2-3 días naturales antes de pasar a Gemini activo.
