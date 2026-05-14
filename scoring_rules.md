# scoring_rules.md
# Sistema de Alerta Temprana de Riesgo de Suministro — Cobalto
# Versión: 1.0 | Mineral: Cobalto | Horizonte: Swing Corto (1-2 sem) + Swing Macro (1-3 meses)

---

## 1. PRINCIPIOS DE DISEÑO

### 1.1 Premisa Central
El sistema NO predice precios. Detecta **cuellos de botella logísticos y geopolíticos** en la cadena de suministro de cobalto antes de que su efecto físico se propague. La ventaja competitiva es la asimetría temporal entre el flujo de información (horas) y el flujo físico de mercancías (semanas/meses).

### 1.2 Limitaciones Explícitas del Sistema Heurístico
- **Falsos positivos esperados:** Un texto con alta densidad de keywords no implica evento real. Las reglas de validación (Sección 6) son obligatorias, no opcionales.
- **Ceguera de contexto:** El sistema no entiende ironía, negación compleja ni contexto histórico. "No habrá huelga en Katanga" puntúa igual que "Habrá huelga en Katanga" si no se aplica el filtro de negación (Sección 6.3).
- **Latencia de fuentes:** RSS de Reuters puede tener 15-30 min de retraso. Las fuentes gubernamentales africanas pueden tardar 24-48h. El score refleja lo publicado, no lo ocurrido.
- **Sesgo de idioma:** Eventos en zonas francófonas (DRC, Mali) tienen menor cobertura en inglés. El diccionario multilingüe mitiga esto parcialmente.

### 1.3 Lo Que Este Sistema No Reemplaza
- Análisis fundamental de empresas individuales
- Due diligence antes de ejecutar una posición
- Criterio humano sobre el contexto macroeconómico global

---

## 2. GEOGRAFÍAS CRÍTICAS Y PESOS BASE

El cobalto tiene una concentración geográfica extrema. Los pesos base reflejan el % de producción mundial y la irreemplazabilidad logística de cada zona.

| Código | Región | País Principal | % Producción Mundial | Peso Base |
|--------|--------|----------------|----------------------|-----------|
| GEO-01 | Cinturón Cuprífero (Copperbelt) | DRC (Katanga, Lualaba) | ~70% | 1.80 |
| GEO-02 | Zambia (Copperbelt Norte) | Zambia | ~4% | 1.20 |
| GEO-03 | Rutas de Tránsito África Oriental | Tanzania, Mozambique | 0% producción, crítico en tránsito | 1.40 |
| GEO-04 | Rutas de Tránsito África Austral | Sudáfrica, Zimbabwe | 0% producción, crítico en tránsito | 1.30 |
| GEO-05 | Australia | Australia Occidental | ~4% | 0.90 |
| GEO-06 | Filipinas | Palawan | ~3% | 0.80 |
| GEO-07 | Refinación China | Provincias costeras (Zhejiang, Guangdong) | ~70% refinación | 1.60 |
| GEO-08 | Puertos de Exportación Primarios | Durban (ZA), Dar es Salaam (TZ), Beira (MZ) | N/A | 1.50 |
| GEO-09 | Litoral Chileno/Argentino | — | Cobalto marginal como subproducto | 0.40 |

**Nota crítica sobre GEO-07:** China no produce cobalto significativo pero refina ~70% del cobalto mundial. Un evento en refinación china (regulación ambiental, corte energético, disputa comercial) es tan disruptivo como un evento en DRC.

**Nota crítica sobre GEO-03/GEO-04:** Las rutas de tránsito son el cuello de botella más subestimado. El cobalto de DRC sale principalmente por:
- Corredor Norte: DRC → Tanzania → Puerto Dar es Salaam
- Corredor Sur: DRC → Zimbabwe/Zambia → Puerto Durban
- Corredor Beira: DRC/Zambia → Mozambique → Puerto Beira

Un evento en estos corredores afecta el 70% del suministro aunque no haya ningún problema en la mina.

---

## 3. CATEGORÍAS DE IMPACTO Y PESOS CATEGÓRICOS

Cada evento detectado pertenece a una o más categorías. El score final de un evento es:

```
score_evento = peso_keyword × peso_geografico × multiplicador_categoria × modificador_fuente
```

### 3.1 Categoría LOGÍSTICA (LOG)
Disrupciones en el movimiento físico de la mercancía.

| Subcategoría | Descripción | Multiplicador |
|---|---|---|
| LOG-PORT | Congestión, cierre o huelga portuaria | 2.0 |
| LOG-RAIL | Interrupción ferroviaria (corredores críticos) | 1.8 |
| LOG-ROAD | Bloqueo de carreteras principales | 1.5 |
| LOG-CUSTOMS | Retención aduanera o nueva regulación de exportación | 1.7 |
| LOG-FLOOD | Inundación de infraestructura de transporte | 1.6 |
| LOG-VESSEL | Escasez de buques, demoras en flete marítimo | 1.3 |

**Justificación:** Los eventos logísticos tienen el mayor multiplicador porque su efecto es inmediato, medible en días, y la oferta no puede redirigirse rápidamente (no hay rutas alternativas de bajo coste para el cobalto africano).

### 3.2 Categoría GEOPOLÍTICA (GEO)
Inestabilidad política, conflicto armado, sanciones.

| Subcategoría | Descripción | Multiplicador |
|---|---|---|
| GEO-CONFLICT | Conflicto armado activo en zona minera o de tránsito | 2.2 |
| GEO-COUP | Golpe de estado o cambio de gobierno abrupto | 2.0 |
| GEO-SANCTION | Sanciones internacionales a país productor o refinador | 1.9 |
| GEO-PROTEST | Protestas civiles que afectan operaciones | 1.4 |
| GEO-ELECTION | Período electoral con riesgo de inestabilidad | 0.8 |
| GEO-DIPLO | Ruptura de relaciones diplomáticas relevantes | 1.2 |

**Nota:** GEO-ELECTION tiene multiplicador bajo porque el riesgo es difuso y anticipado por el mercado. Solo sube a 1.6 si se combina con GEO-PROTEST o GEO-CONFLICT en la misma región dentro de la misma ventana de 72h.

### 3.3 Categoría LABORAL (LAB)
Huelgas, conflictos sindicales, condiciones de trabajo.

| Subcategoría | Descripción | Multiplicador |
|---|---|---|
| LAB-STRIKE-ACT | Huelga activa confirmada en mina o puerto | 2.1 |
| LAB-STRIKE-THR | Amenaza de huelga con fecha anunciada | 1.5 |
| LAB-STRIKE-NEG | Negociaciones sindicales en curso (sin fecha) | 0.9 |
| LAB-ACCIDENT | Accidente laboral grave que paraliza operaciones | 1.8 |
| LAB-PROTEST | Protesta laboral sin paralización formal | 1.1 |

**Distinción crítica LAB-STRIKE-ACT vs LAB-STRIKE-THR:** El sistema debe diferenciar estos dos estados. Una amenaza que no se materializa en 14 días debe reducir su score en un 50% (ver Sección 6.4 — Decaimiento Temporal).

### 3.4 Categoría REGULATORIA (REG)
Cambios de política, licencias, impuestos, regulación ambiental.

| Subcategoría | Descripción | Multiplicador |
|---|---|---|
| REG-EXPORT-BAN | Prohibición o restricción de exportación | 2.3 |
| REG-TAX | Nuevo impuesto o royalty sobre minería | 1.6 |
| REG-LICENSE | Suspensión o revocación de licencias mineras | 1.9 |
| REG-ENV | Cierre por incumplimiento ambiental | 1.7 |
| REG-NATIONAL | Amenaza de nacionalización | 1.8 |
| REG-TARIFF | Nuevo arancel de importación en país refinador | 1.4 |

**Advertencia sobre REG-EXPORT-BAN:** Indonesia (níquel) e Indonesia (bauxita) han demostrado que los países productores usan este mecanismo con creciente frecuencia. En DRC existe el precedente de la "taxe sur les super-profits" de 2022. Este es el evento regulatorio con mayor probabilidad de ocurrencia en el horizonte 2024-2026.

### 3.5 Categoría RESOLUCIÓN (RES)
Términos que indican resolución o mejora de un evento activo. Llevan **peso negativo** para reducir el score cuando la situación mejora. Complementan el filtro de negación (±5 palabras) para capturar frases de resolución más largas.

| Subcategoría | Descripción | Multiplicador |
|---|---|---|
| RES-RESOLVE | Resolución confirmada de huelga, cierre o conflicto | 1.5 |

**Comportamiento por horizonte:**
- SSC: peso completo (×1.0) — la resolución tiene efecto inmediato en flujo físico
- SMC: peso reducido (×0.5) — la tensión estructural puede persistir aunque el evento se resuelva

**Ejemplos de activación:** "strike ended at Katanga", "port reopened in Durban", "workers return to work at Tenke Fungurume"

### 3.6 Categoría DEMANDA (DEM)
Cambios abruptos en demanda que alteran el equilibrio. Puntúan en dirección INVERSA (reducen el riesgo de escasez pero pueden indicar oportunidades de posición corta).

| Subcategoría | Descripción | Multiplicador |
|---|---|---|
| DEM-SURGE | Anuncio de demanda masiva inesperada (contrato gigafactory) | +1.5 (suma al score) |
| DEM-DROP | Caída de demanda por sustitución tecnológica | -1.3 (resta del score) |
| DEM-STOCK | Anuncio de acumulación estratégica de reservas (gobierno) | +1.2 |
| DEM-SUBSITUTE | Avance tecnológico en baterías sin cobalto (LFP, sodium-ion) | -1.5 |

**Nota sobre DEM-SUBSTITUTE:** Noticias sobre baterías LFP o sodium-ion son ruido estructural a largo plazo, no señal de trading a corto. Se registran pero no activan alertas de swing corto. Solo afectan al score de swing macro.

### 3.6 Categoría CLIMÁTICA/FUERZA MAYOR (FMA)
Eventos naturales o de fuerza mayor.

| Subcategoría | Descripción | Multiplicador |
|---|---|---|
| FMA-FLOOD | Inundación en zona de producción o tránsito | 1.7 |
| FMA-DROUGHT | Sequía que afecta energía hidroeléctrica (DRC depende de ella) | 1.4 |
| FMA-SEISMIC | Actividad sísmica en zona minera | 1.3 |
| FMA-DISEASE | Brote de enfermedad que paraliza operaciones | 1.5 |

**Nota sobre FMA-DROUGHT:** Específicamente relevante para DRC, cuya minería depende críticamente de la energía del río Congo (Inga). Una sequía severa reduce la capacidad eléctrica y puede forzar paradas de plantas de procesamiento.

---

## 4. SISTEMA DE SCORING DUAL (SWING CORTO vs SWING MACRO)

Los mismos eventos puntúan de forma diferente según el horizonte temporal.

### 4.1 Score de Swing Corto (SSC) — Ventana 1-2 semanas

**Filosofía:** Detecta disrupciones con efecto inmediato en el flujo físico. Prioriza eventos confirmados sobre amenazas. Alta sensibilidad a logística y eventos laborales activos.

**Categorías que puntúan en SSC:**
- LOG: peso completo (×1.0)
- LAB (solo ACT y ACCIDENT): peso completo (×1.0)
- GEO-CONFLICT, GEO-COUP: peso completo (×1.0)
- REG-EXPORT-BAN, REG-LICENSE: peso completo (×1.0)
- FMA: peso completo (×1.0)
- LAB-STRIKE-THR: peso reducido (×0.6)
- GEO-PROTEST, GEO-ELECTION: peso reducido (×0.4)
- DEM-SUBSTITUTE: NO puntúa en SSC

**Umbrales SSC:**
```
0  — 15 : VERDE    — Sin alerta. Ruido normal de mercado.
16 — 30 : AMARILLO — Monitoreo elevado. Revisar fuentes primarias manualmente.
31 — 50 : NARANJA  — Alerta activa. Evaluar posición en activos secundarios.
51+     : ROJO     — Alerta máxima. Disrupción probable en < 2 semanas.
```

### 4.2 Score de Swing Macro (SMC) — Ventana 1-3 meses

**Filosofía:** Detecta acumulación de tensiones estructurales. Prioriza tendencias sobre eventos puntuales. Alta sensibilidad a regulación, geopolítica y demanda.

**Categorías que puntúan en SMC:**
- Todas las categorías puntúan (×1.0)
- LAB-STRIKE-NEG y LAB-STRIKE-THR: peso completo (×1.0) — importan porque pueden materializarse
- GEO-ELECTION: peso aumentado (×1.2) — importa el ciclo político de medio plazo
- DEM-SUBSTITUTE: puntúa en SMC (×1.0) con signo negativo
- REG (todas): peso aumentado (×1.2) — los cambios regulatorios tienen efecto prolongado

**Umbrales SMC:**
```
0  — 20 : VERDE    — Sin tendencia de riesgo estructural.
21 — 40 : AMARILLO — Tensión acumulándose. Vigilar.
41 — 65 : NARANJA  — Riesgo estructural moderado. Revisar tesis de posición macro.
66+     : ROJO     — Riesgo estructural alto. Alta probabilidad de disrupción en horizonte 1-3m.
```

### 4.3 Score Compuesto y Señal de Alerta

```
ALERTA_EMAIL se dispara cuando:
  (SSC >= 31) OR (SMC >= 41) OR (SSC >= 20 AND SMC >= 30)
```

La tercera condición captura situaciones donde ningún score supera su umbral individual pero la combinación indica tensión en ambos horizontes.

---

## 5. PESOS POR FUENTE (MODIFICADOR DE CREDIBILIDAD)

No todas las fuentes tienen igual fiabilidad. Este modificador se aplica al score del evento.

| Tipo de Fuente | Ejemplos | Modificador |
|---|---|---|
| Agencia internacional de primer nivel | Reuters, Bloomberg, AP, AFP | 1.00 |
| Medio especializado en commodities | Mining.com, S&P Global Commodity, Fastmarkets | 1.00 |
| Organismo gubernamental/multilateral | USGS, World Bank, UN OCHA, DRC gobierno | 0.95 |
| Medio regional africano establecido | AllAfrica, The East African, Daily Maverick | 0.85 |
| Medio generalista de segundo nivel | BBC África, RFI, VOA África | 0.80 |
| Portal portuario oficial | Port of Durban, TPA (Tanzania), CFM (Mozambique) | 1.00 |
| Blog especializado / newsletter | Benchmark Mineral Intelligence (free tier) | 0.70 |
| Red social (Twitter/X, Telegram) | Cualquiera | 0.40 |
| Fuente no identificada o agregador | Google News sin fuente clara | 0.50 |

**Regla crítica:** Si el mismo evento aparece en 3 o más fuentes independientes de modificador >= 0.80, aplicar un **multiplicador de confirmación de 1.30** al score total del evento (no se apilan los scores individuales, se toma el más alto y se multiplica).

---

## 6. REGLAS DE VALIDACIÓN (FILTROS ANTI-RUIDO)

Estas reglas se aplican DESPUÉS del cálculo del score bruto. Son la diferencia entre una alerta útil y spam.

### 6.1 Filtro de Antigüedad
- Artículos con fecha de publicación > 72 horas en categorías LOG y LAB: score reducido al 30%.
- Artículos con fecha > 7 días en cualquier categoría: score reducido al 10%.
- Artículos sin fecha identificable: score reducido al 20%.
- **Excepción:** REG y GEO-SANCTION no decaen por antigüedad si el evento sigue activo (ausencia de noticia de resolución).

### 6.2 Filtro de Contexto Geográfico
- Un artículo solo puntúa si contiene al menos UN término geográfico de la lista GEO-01 a GEO-09 (ver keyword_dictionary.md).
- Menciones genéricas ("Africa", "emerging markets", "developing countries") sin especificidad geográfica: score reducido al 40%.

### 6.3 Filtro de Negación
El script debe detectar patrones de negación en una ventana de ±5 palabras alrededor de cada keyword. Lista de negadores que reducen el score del evento al 15%:

**Inglés:** no, not, never, ended, resolved, cancelled, avoided, prevented, denied, resumed, lifted, withdrawn, rejected

**Francés:** non, pas, jamais, terminé, résolu, annulé, évité, empêché, nié, repris, levé, retiré

**Portugués:** não, nunca, terminado, resolvido, cancelado, evitado, impedido, negado, retomado, levantado, retirado

**Español:** no, nunca, terminado, resuelto, cancelado, evitado, impedido, negado, reanudado, levantado, retirado

**Nota de implementación:** La negación de doble alcance es compleja. El filtro opera con ventana de ±5 palabras, lo que significa que "the strike was not avoided" (negación de negación) puede fallar. Aceptar este error como limitación conocida del sistema v1.0.

### 6.4 Decaimiento Temporal de Amenazas
Para eventos en estado de AMENAZA (no confirmados):

```
Si LAB-STRIKE-THR no tiene evento LAB-STRIKE-ACT correlacionado en 14 días:
  score_LAB-STRIKE-THR = score_original × 0.50

Si GEO-PROTEST no tiene evento GEO-CONFLICT correlacionado en 21 días:
  score_GEO-PROTEST = score_original × 0.40
```

### 6.5 Filtro de Duplicados
- Si el mismo evento (misma región + misma categoría + ventana de 48h) aparece en múltiples fuentes, NO sumar los scores.
- Aplicar regla de confirmación multi-fuente (Sección 5) en su lugar.
- Identificador de duplicado: hash de (region_code + category_code + fecha_normalizada).

### 6.6 Umbral Mínimo de Activación
Un evento no entra al scoring si su score bruto (antes de modificadores) es inferior a 3.0 puntos. Esto elimina menciones incidentales de keywords sin contexto de disrupción.

---

## 7. FÓRMULA DE SCORING COMPLETA

```python
# Pseudocódigo de referencia para implementación

def calcular_score_evento(evento):
    # Componentes base
    score_bruto = peso_keyword(evento.keyword)
    score_bruto *= peso_geografico(evento.region)  # GEO-01 a GEO-09
    score_bruto *= multiplicador_categoria(evento.categoria)
    score_bruto *= modificador_fuente(evento.fuente)

    # Validaciones
    if score_bruto < UMBRAL_MINIMO_ACTIVACION:  # 3.0
        return 0, 0

    if tiene_negacion(evento.texto, evento.keyword):
        score_bruto *= 0.15

    score_bruto *= factor_antiguedad(evento.fecha)

    if not tiene_contexto_geografico_especifico(evento.texto):
        score_bruto *= 0.40

    # Confirmación multi-fuente
    if count_fuentes_independientes(evento) >= 3:
        score_bruto *= 1.30

    # Bifurcación por horizonte
    score_ssc = calcular_ssc(score_bruto, evento.categoria)
    score_smc = calcular_smc(score_bruto, evento.categoria)

    return score_ssc, score_smc


def calcular_score_total_sesion(lista_eventos):
    # No sumar linealmente: usar agregación con cap de saturación
    # Razón: 10 noticias menores no equivalen a 1 crisis real
    scores_ssc = [e.score_ssc for e in lista_eventos if not es_duplicado(e)]
    scores_smc = [e.score_smc for e in lista_eventos if not es_duplicado(e)]

    # Fórmula de agregación con raíz cuadrada (reduce saturación)
    total_ssc = scores_ssc[0] + sum(s * 0.5 for s in scores_ssc[1:])
    total_smc = scores_smc[0] + sum(s * 0.5 for s in scores_smc[1:])

    return round(total_ssc, 2), round(total_smc, 2)
```

**Justificación de la fórmula de agregación:** La suma lineal de eventos genera inflación de score cuando hay cobertura mediática alta (muchos artículos, mismo evento). La fórmula da peso completo al evento de mayor score y mitad de peso a los adicionales, lo que mejor refleja la realidad: 5 artículos sobre la misma huelga no es 5 veces más grave que 1 artículo.

---

## 8. TABLA DE REFERENCIA RÁPIDA — SCORES DE EJEMPLO

Para calibración y testing del script.

| Escenario | Categoría | Región | Score SSC Esperado | Score SMC Esperado | Nivel |
|---|---|---|---|---|---|
| Huelga activa en Puerto de Durban (Reuters) | LOG-PORT + LAB-STRIKE-ACT | GEO-08 | 38-45 | 30-38 | NARANJA/ROJO |
| Golpe de estado en DRC | GEO-COUP | GEO-01 | 55+ | 60+ | ROJO |
| Amenaza de huelga en Katanga (AllAfrica) | LAB-STRIKE-THR | GEO-01 | 18-24 | 22-28 | AMARILLO |
| Nueva ley de royalties en DRC (Reuters) | REG-TAX | GEO-01 | 20-26 | 35-42 | AMARILLO/NARANJA |
| Inundación en corredor Beira | FMA-FLOOD + LOG-RAIL | GEO-03/GEO-04 | 28-35 | 22-30 | AMARILLO/NARANJA |
| Tweet sin verificar sobre "protests in Lualaba" | GEO-PROTEST | GEO-01 | 4-7 | 5-8 | VERDE (ruido) |
| Prohibición exportación cobalto DRC (confirmada) | REG-EXPORT-BAN | GEO-01 | 65+ | 75+ | ROJO MÁXIMO |
| Anuncio batería sin cobalto por CATL | DEM-SUBSTITUTE | N/A | 0 | -12 a -18 | N/A (SMC baja) |

---

## 9. MANTENIMIENTO Y VERSIONADO

### 9.1 Revisión Periódica Obligatoria
Este archivo debe revisarse cuando ocurra:
- Cambio en el % de producción mundial de DRC superior a ±5 puntos
- Apertura de nueva ruta de tránsito significativa
- Cambio de régimen en DRC, Zambia o cualquier GEO-01/GEO-02
- Nueva tecnología de batería que altere la demanda estructural de cobalto
- Cadencia recomendada de revisión: cada 6 meses mínimo

### 9.2 Registro de Cambios
```
v1.1 — 2026-05 — Revisión de calibración y cobertura.
  FALSOS POSITIVOS corregidos:
    - "state of emergency", "état d'urgence", "estado de emergencia" → requires_context: True
    - "civil unrest", "troubles civils" → requires_context: True
    - "armed conflict" y equivalentes FR/ES/PT → geo_boost GEO-03 eliminado
    - Bug fix: "estado de emergencia" estaba duplicado en KEYWORDS
  SUBVALUACIÓN corregida:
    - Términos ASM (creuseurs, artisanal mining ban, asm suspension, etc.) añadidos
    - Términos Swahili iniciales: mgomo, mgomo wa wachimbaji, mgodi kufungwa, bandari kufungwa
    - Señales de mercado DEM-SURGE: cobalt shortage, cobalt supply deficit, lme cobalt inventory, etc.
    - DEM-SUBSTITUTE "lfp battery": peso -2.0 → -3.0 (dominio real en mercado chino)
    - DEM-SUBSTITUTE nuevos: lmfp battery, lithium iron phosphate, batterie lfp, sodium ion battery
  NUEVA CATEGORÍA:
    - RES-RESOLVE: términos de resolución con peso negativo (EN/FR/ES/PT)
      Multiplicador: 1.5 | SSC weight: 1.0 | SMC override: 0.5

v1.0 — 2025-05 — Versión inicial. Mineral: Cobalto. Horizonte: SSC + SMC.
                  4 idiomas. Mercados globales. 6 categorías de impacto.
```

### 9.3 Archivos Dependientes
Este archivo es referenciado por:
- `keyword_dictionary.md` — usa los códigos de categoría (LOG-PORT, GEO-COUP, etc.)
- `asset_map.md` — usa los niveles de alerta (NARANJA, ROJO) para mapear activos
- `data_sources.md` — usa los modificadores de fuente (Sección 5)
- `main_scorer.py` — implementa las fórmulas de la Sección 7
