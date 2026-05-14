# asset_map.md
# Mapa de Activos Secundarios y Plantilla de Alerta Email — Sistema de Cobalto
# Versión: 1.0 | Referencia: scoring_rules.md v1.0, keyword_dictionary.md v1.0

---

## 1. LÓGICA DEL "EFECTO DOMINÓ"

La estrategia NO opera en la minera directamente afectada. Cuando hay una disrupción en la cadena de suministro de cobalto, el precio del activo directo ya ha absorbido la noticia en horas. La ventaja competitiva está en los activos secundarios que tardan días o semanas en reflejar el impacto en cadena.

### Mapa de propagación del impacto

```
EVENTO DE DISRUPCIÓN
        │
        ▼
[Cobalto físico escasea o precio sube]
        │
        ├──► IMPACTO POSITIVO (precio sube):
        │    ├── Productores con inventario o producción no afectada
        │    ├── Recicladores de cobalto (sustituto de oferta primaria)
        │    ├── ETFs de metales críticos
        │    └── Empresas con sustitutos tecnológicos (LFP, Na-ion)
        │
        └──► IMPACTO NEGATIVO (precio sube = margen baja):
             ├── Fabricantes de baterías (coste de producción sube)
             ├── Fabricantes de VE (si no tienen cobertura de precio)
             └── Electrónica de consumo (menor margen en baterías)
```

**Regla clave:** La dirección del impacto sobre los fabricantes de baterías/VE depende de si tienen contratos a precio fijo o compran a mercado. En una alerta, el sistema indica ambas posibilidades.

---

## 2. MAPA DE ACTIVOS SECUNDARIOS

### 2.1 ETFs de Metales Críticos / Cobalto / Baterías

| Ticker | Nombre | Bolsa | Exposición Cobalto | Dirección en Alerta ROJA | Liquidez |
|--------|--------|-------|-------------------|--------------------------|----------|
| COBALT | Sprott Physical Cobalt | TSX | Directa (cobalto físico) | ↑ SUBE | Baja — usar con cautela |
| LIT | Global X Lithium & Battery Tech | NYSE | Indirecta (cadena baterías) | ↑ SUBE (oferta general baterías se tensa) | Alta |
| REMX | VanEck Rare Earth/Strategic Metals | NYSE | Indirecta (metales críticos) | ↑ SUBE | Media |
| BATT | Amplify Lithium & Battery Technology | NYSE | Indirecta | ↑ SUBE | Media |
| COPX | Global X Copper Miners | NYSE | Indirecta (copperbelt — DRC produce cobre+cobalto juntos) | ↑ SUBE si evento en GEO-01/02 | Alta |
| PICK | iShares MSCI Global Metals & Mining | NYSE | Indirecta | ↑ SUBE leve | Alta |
| DRIV | Global X Autonomous & EV | NYSE | Indirecta negativa (coste baterías sube) | ↓ BAJA si disrupción severa | Alta |
| IDRV | iShares Self-Driving EV and Tech | NYSE | Indirecta negativa | ↓ BAJA si disrupción severa | Alta |

**Nota sobre COBALT (TSX):** Baja liquidez. Para posiciones pequeñas puede ser interesante pero el spread bid-ask puede ser grande. Verificar volumen antes de operar.

### 2.2 Empresas Productoras No Afectadas (Beneficiarias de Precio Alto)

Estas empresas se benefician cuando hay disrupción en DRC porque su producción sube de precio sin verse afectada por el evento.

| Ticker | Empresa | Bolsa | Razón de Exposición | Dirección | Notas |
|--------|---------|-------|---------------------|-----------|-------|
| GLEN.L | Glencore | LSE | Mayor productor mundial. Si el evento NO le afecta a ella directamente, se beneficia del precio | ↑ SUBE (si evento no es en sus activos) | Verificar si el evento afecta a Kamoto o Mutanda directamente |
| ERG (privada) | Eurasian Resources Group | No cotiza | Segundo productor DRC | N/A | No operable directamente |
| 603993.SS | CMOC Group | Shanghai/HKEx | Segundo productor DRC (Tenke Fungurume) | Complejo — si evento en sus activos: ↓ BAJA | Solo accesible desde brokers con acceso a HKEx |
| 6060.HK | Huayou Cobalt | HKEx | Mayor refinador chino | ↑ SUBE si evento en producción; ↓ BAJA si evento en refinación China | |
| JRV | Jervois Global | ASX | Productor emergente fuera de DRC | ↑ SUBE (beneficiario de precio) | Baja liquidez, alta volatilidad |
| FQM | First Quantum Minerals | TSX | Productor en Zambia | ↑ SUBE leve (GEO-02 no afectado) | Principalmente cobre, cobalto secundario |

### 2.3 Recicladores de Cobalto (Beneficiarios Directos de Escasez)

Cuando el cobalto primario escasea, el reciclado sube de valor. Estos activos reaccionan con 1-3 semanas de retardo respecto al evento, lo que los hace ideales para swing.

| Ticker | Empresa | Bolsa | Razón de Exposición | Dirección |
|--------|---------|-------|---------------------|-----------|
| UMI.BR | Umicore | Euronext Bruselas | Mayor reciclador de cobalto de baterías en Europa | ↑ SUBE — precio de reciclado sube con cobalto primario |
| LI.V | Lithium Americas | NYSE/TSX | Exposición indirecta a metales de batería | ↑ SUBE leve |
| CBAT | CBAK Energy Technology | NASDAQ | Fabricante baterías con exposición a precios | Complejo |

### 2.4 Fabricantes de Baterías (Impacto Negativo en Disrupciones Severas)

Solo puntúan en alertas ROJO con Score SSC > 45 o SMC > 60. En disrupciones moderadas, tienen contratos a precio fijo que los protegen a corto plazo.

| Ticker | Empresa | Bolsa | Exposición | Dirección en ROJO | Retardo Esperado |
|--------|---------|-------|------------|-------------------|-----------------|
| 300750.SZ | CATL | Shenzhen | Mayor fabricante baterías mundo. Comprador masivo de cobalto | ↓ BAJA (margen comprimido) | 2-4 semanas |
| 051910.KS | LG Energy Solution | Korea SE | Gran fabricante baterías para VE | ↓ BAJA | 2-4 semanas |
| 006400.KS | Samsung SDI | Korea SE | Baterías para VE y electrónica | ↓ BAJA | 2-4 semanas |
| PCRFY | Panasonic | OTC/NYSE | Socio de Tesla en baterías | ↓ BAJA | 3-5 semanas |

**Advertencia:** Posición corta en estos activos es compleja. Solo considerar si el score es ROJO MÁXIMO y el horizonte es SMC. No para swing corto.

### 2.5 Fabricantes de VE (Impacto Negativo Retardado)

El impacto llega más tarde que en fabricantes de baterías porque tienen inventario de baterías y contratos a largo plazo.

| Ticker | Empresa | Bolsa | Dirección en ROJO | Retardo Esperado |
|--------|---------|-------|-------------------|-----------------|
| TSLA | Tesla | NASDAQ | ↓ BAJA leve (tiene acuerdos directos de suministro) | 4-8 semanas |
| VWAGY | Volkswagen | OTC/NYSE | ↓ BAJA (menos integrado que Tesla) | 3-6 semanas |
| GM | General Motors | NYSE | ↓ BAJA | 4-8 semanas |
| STLA | Stellantis | NYSE | ↓ BAJA | 4-8 semanas |

### 2.6 Empresas de Logística Africana (Impacto Directo en Alertas LOG)

Solo relevantes en alertas de categoría LOG (disrupciones portuarias/ferroviarias).

| Ticker | Empresa | Bolsa | Relevancia | Dirección |
|--------|---------|-------|------------|-----------|
| TFG (Transnet) | Transnet SOC Ltd | No cotiza (estatal) | Opera Puerto de Durban y Transnet Freight Rail | N/A — no operable |
| MSC Industrial | N/A | N/A | Naviera — no cotiza | N/A |
| MAERSK-B.CO | A.P. Moller-Maersk | Copenhagen | Naviera con rutas África. Disrupción en puertos africanos les afecta | ↓ BAJA en disrupciones prolongadas (costes operativos) | 

**Nota:** La mayoría de operadores logísticos africanos críticos son estatales y no cotizan. La exposición logística se juega mejor a través de ETFs de commodities o las mineras directamente beneficiadas.

---

## 3. PLANTILLA DE ALERTA EMAIL

### 3.1 Especificaciones de Formato

- **Asunto:** Codificado para filtrar fácilmente en Gmail con etiquetas
- **Cuerpo:** HTML estructurado (legible en móvil)
- **Secciones:** Fijas y en orden de importancia para tomar decisión rápida
- **Longitud máxima:** Diseñado para leer en 3 minutos

### 3.2 Plantilla HTML del Email

```python
EMAIL_TEMPLATE = """
Subject: [COBALT-ALERT] {nivel_alerta} | SSC:{score_ssc} SMC:{score_smc} | {fecha}

Body (HTML):
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; color: #1a1a1a; }}
    .header-rojo {{ background: #c0392b; color: white; padding: 16px; border-radius: 6px; }}
    .header-naranja {{ background: #e67e22; color: white; padding: 16px; border-radius: 6px; }}
    .header-amarillo {{ background: #f39c12; color: white; padding: 16px; border-radius: 6px; }}
    .header-verde {{ background: #27ae60; color: white; padding: 16px; border-radius: 6px; }}
    .score-box {{ display: inline-block; background: #f4f4f4; border: 1px solid #ddd;
                  padding: 8px 16px; border-radius: 4px; margin: 4px; font-size: 14px; }}
    .event-card {{ border-left: 4px solid #c0392b; padding: 12px; margin: 12px 0;
                   background: #fafafa; border-radius: 0 4px 4px 0; }}
    .event-card-naranja {{ border-left: 4px solid #e67e22; padding: 12px; margin: 12px 0;
                           background: #fafafa; border-radius: 0 4px 4px 0; }}
    .asset-table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
    .asset-table th {{ background: #2c3e50; color: white; padding: 8px; text-align: left; font-size: 13px; }}
    .asset-table td {{ padding: 8px; border-bottom: 1px solid #eee; font-size: 13px; }}
    .up {{ color: #27ae60; font-weight: bold; }}
    .down {{ color: #c0392b; font-weight: bold; }}
    .source-link {{ color: #2980b9; text-decoration: none; font-size: 13px; }}
    .disclaimer {{ font-size: 11px; color: #888; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px; }}
    .section-title {{ font-size: 13px; text-transform: uppercase; color: #888;
                      letter-spacing: 1px; margin: 16px 0 8px 0; }}
  </style>
</head>
<body>

<!-- CABECERA DE ALERTA -->
<div class="header-{color_nivel}">
  <h2 style="margin:0">⚠ ALERTA DE RIESGO DE SUMINISTRO — COBALTO</h2>
  <p style="margin:4px 0 0 0; font-size:14px">{fecha_hora} UTC | Ejecución #{num_ejecucion_dia}/3</p>
</div>

<!-- SCORES -->
<div style="margin: 16px 0;">
  <div class="score-box">
    <strong>SWING CORTO (1-2 sem)</strong><br>
    <span style="font-size:24px; font-weight:bold">{score_ssc}</span>/50
    <br><span style="color:{color_ssc}">{nivel_ssc}</span>
  </div>
  <div class="score-box">
    <strong>SWING MACRO (1-3 meses)</strong><br>
    <span style="font-size:24px; font-weight:bold">{score_smc}</span>/65
    <br><span style="color:{color_smc}">{nivel_smc}</span>
  </div>
</div>

<!-- RESUMEN EJECUTIVO -->
<p class="section-title">¿Qué está pasando?</p>
<p style="font-size:15px; line-height:1.6">{resumen_ejecutivo}</p>
<!-- Generado automáticamente: "Se han detectado N eventos de disrupción en [regiones].
     El evento más significativo es [descripción del evento de mayor score]:
     [categoría] en [región geográfica], reportado por [fuente] hace [tiempo].
     Nivel de confirmación: [número] fuentes independientes." -->

<!-- EVENTOS DETECTADOS (ordenados por score) -->
<p class="section-title">Eventos Detectados ({num_eventos} total)</p>

{bloque_eventos}
<!-- Para cada evento, generar un bloque como este: -->
<!--
<div class="event-card">
  <strong>[LOG-PORT] Huelga portuaria activa — Puerto de Durban</strong>
  <p style="margin:4px 0; font-size:14px">
    <strong>Fuente:</strong> Reuters Africa | <strong>Publicado:</strong> hace 3 horas<br>
    <strong>Región afectada:</strong> GEO-08 (Puerto Durban) → impacta corredor sur DRC-Zambia<br>
    <strong>Score contribución:</strong> +18.4 puntos SSC | +14.2 puntos SMC<br>
    <strong>Resumen:</strong> [Primeras 200 palabras del artículo o descripción generada]
  </p>
  <a class="source-link" href="{url_articulo}">→ Leer artículo completo</a>
</div>
-->

<!-- MAPA DE IMPACTO EN LA CADENA -->
<p class="section-title">¿Dónde se propagará el impacto?</p>
<div style="background:#f9f9f9; padding:12px; border-radius:4px; font-size:14px; line-height:1.8">
  <strong>Punto de origen:</strong> {region_origen} ({codigo_geo})<br>
  <strong>Ruta logística afectada:</strong> {ruta_afectada}<br>
  <strong>Estimación de retardo hasta precio:</strong> {retardo_estimado}<br>
  <strong>Volumen de suministro en riesgo:</strong> {pct_suministro_afectado}% producción mundial estimada
</div>

<!-- ACTIVOS A VIGILAR -->
<p class="section-title">Activos a Vigilar — Posicionamiento Sugerido</p>
<table class="asset-table">
  <tr>
    <th>Ticker</th>
    <th>Nombre</th>
    <th>Dirección</th>
    <th>Horizonte</th>
    <th>Por qué</th>
  </tr>
  {filas_activos}
  <!-- Ejemplo de fila generada:
  <tr>
    <td><strong>LIT</strong></td>
    <td>Global X Lithium & Battery Tech ETF</td>
    <td class="up">↑ LARGO</td>
    <td>1-3 semanas</td>
    <td>Tensión en cadena de baterías eleva todo el sector de metales críticos</td>
  </tr>
  <tr>
    <td><strong>UMI.BR</strong></td>
    <td>Umicore (Reciclador)</td>
    <td class="up">↑ LARGO</td>
    <td>2-4 semanas</td>
    <td>Escasez de cobalto primario incrementa valor del reciclado de baterías</td>
  </tr>
  -->
</table>

<!-- FUENTES DE INFORMACIÓN PARA DUE DILIGENCE -->
<p class="section-title">Dónde Buscar Más Información Antes de Decidir</p>
<ul style="font-size:14px; line-height:2">
  {lista_fuentes_recomendadas}
  <!-- Generado dinámicamente según la categoría del evento:
  Si LOG-PORT: "→ Sitio web oficial Puerto de Durban (bit.ly/durban-port-status)"
               "→ Bloomberg Commodities: buscar 'Durban port strike'"
               "→ Fastmarkets: cobalt hydroxide CIF spot price"
  Si GEO-COUP: "→ ACLED (Armed Conflict Location & Event Data): acleddata.com"
               "→ Reuters Africa: reuters.com/world/africa"
               "→ AllAfrica: allafrica.com"
  Si REG-*:    "→ Journal Officiel RDC: leganet.cd"
               "→ Mining Weekly: miningweekly.com"
               "→ S&P Global Market Intelligence (free tier)"
  -->
</ul>

<!-- CONTEXTO PARA DECISIÓN -->
<p class="section-title">Contexto para Tomar la Decisión</p>
<div style="background:#eaf4fb; padding:12px; border-radius:4px; font-size:14px; line-height:1.6">
  <strong>¿Por qué actuar ahora y no esperar?</strong><br>
  {argumento_urgencia}
  <!-- Ejemplo: "El evento es de categoría LOG-PORT con confirmación en 2 fuentes de nivel A.
       El corredor sur (Durban) maneja ~35% del cobalto exportado de DRC/Zambia.
       El retardo histórico entre cierre portuario y reacción de precio de ETFs es 5-12 días hábiles.
       La ventana de entrada óptima es las primeras 48-72h desde el evento." -->
  <br><br>
  <strong>¿Por qué ser cauteloso?</strong><br>
  {argumento_cautela}
  <!-- Ejemplo: "Score SSC de 34 está en zona NARANJA, no ROJO. El evento tiene solo 1 fuente
       confirmada. Las huelgas portuarias en Durban tienen historial de resolución en <72h
       por intervención gubernamental. Esperar segunda fuente antes de ejecutar posición." -->
</div>

<!-- PIE -->
<div class="disclaimer">
  Sistema automático de alerta — no constituye asesoramiento financiero.<br>
  Ejecución: GCP e2-micro | Frecuencia: 3x/día (cada 8h) | Mineral: Cobalto v1.0<br>
  Scores calculados con scoring_rules.md v1.0 + keyword_dictionary.md v1.0
</div>

</body>
</html>
"""
```

---

## 4. LÓGICA DE GENERACIÓN DINÁMICA DEL EMAIL

### 4.1 Reglas de Selección de Activos para la Tabla

```python
def seleccionar_activos_para_alerta(eventos, score_ssc, score_smc):
    """
    Selecciona los activos a incluir en la tabla del email
    según el tipo de eventos detectados y el nivel de score.
    """
    activos_seleccionados = []

    categorias_presentes = set([e.categoria for e in eventos])
    regiones_presentes = set([e.region for e in eventos])

    # Regla 1: Si hay evento LOG en GEO-08 (puertos) → incluir ETFs
    if any(c.startswith("LOG") for c in categorias_presentes):
        if any(g in regiones_presentes for g in ["GEO-08", "GEO-03", "GEO-04"]):
            activos_seleccionados += ["LIT", "REMX", "UMI.BR"]

    # Regla 2: Si hay evento GEO-CONFLICT o GEO-COUP en GEO-01 → incluir Glencore y ETFs
    if "GEO-CONFLICT" in categorias_presentes or "GEO-COUP" in categorias_presentes:
        if "GEO-01" in regiones_presentes:
            activos_seleccionados += ["GLEN.L", "LIT", "COPX", "REMX"]

    # Regla 3: Si hay REG-EXPORT-BAN → máxima alerta, incluir todos los beneficiarios
    if "REG-EXPORT-BAN" in categorias_presentes:
        activos_seleccionados += ["LIT", "REMX", "GLEN.L", "UMI.BR", "BATT"]

    # Regla 4: Si score SMC > 50 → incluir también activos de impacto negativo (cortos)
    if score_smc > 50:
        activos_seleccionados += [
            ("300750.SZ", "BAJA", "Fabricante baterías: margen comprimido"),
            ("DRIV", "BAJA", "ETF VE: coste baterías sube")
        ]

    # Regla 5: Si hay DEM-SUBSTITUTE → incluir beneficiarios de sustitución
    if "DEM-SUBSTITUTE" in categorias_presentes:
        activos_seleccionados += [
            ("CATL", "SUBE", "Líder en baterías LFP sin cobalto"),
        ]

    return list(set(activos_seleccionados))  # deduplicar
```

### 4.2 Generación del Resumen Ejecutivo

```python
RESUMEN_TEMPLATES = {
    "LOG-PORT": "Se ha detectado una disrupción logística en {puerto} ({pais}). "
                "Este puerto maneja aproximadamente {pct}% del cobalto exportado desde "
                "{origen}. Una paralización en este punto afecta el corredor {corredor}, "
                "que es la ruta primaria de salida del cobalto de {origen} hacia los "
                "refinadores asiáticos.",

    "GEO-CONFLICT": "Se ha detectado actividad de conflicto armado en {region} ({pais}), "
                    "zona que representa aproximadamente {pct}% de la producción mundial "
                    "de cobalto. Los conflictos en esta zona tienen historial de paralizar "
                    "operaciones mineras entre {min_dias} y {max_dias} días.",

    "LAB-STRIKE-ACT": "Huelga activa confirmada en {ubicacion}. Las operaciones de "
                      "{empresa_o_sector} están suspendidas. Basado en precedentes "
                      "históricos en esta región, las huelgas mineras tienen duración "
                      "media de {duracion_media} días.",

    "REG-EXPORT-BAN": "ALERTA MÁXIMA: Se ha detectado una prohibición o restricción de "
                      "exportación de mineral en {pais}. Este tipo de medida, si se "
                      "confirma, tiene impacto inmediato sobre el {pct}% del suministro "
                      "mundial que pasa por {pais}. Verificar con fuentes primarias "
                      "oficiales antes de actuar.",

    "FMA-FLOOD": "Evento climático severo detectado en {region}. Las inundaciones en "
                 "esta zona afectan principalmente {infraestructura_afectada}. "
                 "La temporada de lluvias en {region} es {meses_riesgo}, "
                 "período de mayor riesgo para la cadena de suministro."
}
```

### 4.3 Fuentes Recomendadas por Categoría

```python
FUENTES_POR_CATEGORIA = {
    "LOG-PORT": [
        ("Portal oficial Puerto de Durban", "https://www.transnet.net/BusinessWithTransnet/TPT/Pages/PortofDurban.aspx"),
        ("Tanzania Ports Authority — tráfico en tiempo real", "https://www.tanzaniaports.go.tz"),
        ("CFM Mozambique", "https://www.cfmnet.co.mz"),
        ("Fastmarkets — Cobalt hydroxide CIF price", "https://www.fastmarkets.com/commodities/battery-raw-materials/cobalt"),
        ("Reuters África", "https://www.reuters.com/world/africa/")
    ],
    "GEO-CONFLICT": [
        ("ACLED — Armed Conflict Location & Event Data", "https://acleddata.com/dashboard/"),
        ("OCHA DRC — Humanitarian situation", "https://www.unocha.org/democratic-republic-congo"),
        ("AllAfrica", "https://allafrica.com/congo/"),
        ("Reuters África", "https://www.reuters.com/world/africa/"),
        ("Mining.com — DRC news", "https://www.mining.com/tag/democratic-republic-of-congo/")
    ],
    "LAB-STRIKE-ACT": [
        ("Mining Weekly — Labor news", "https://www.miningweekly.com/tag/labour"),
        ("AllAfrica", "https://allafrica.com/"),
        ("Reuters Commodities", "https://www.reuters.com/business/commodities/"),
        ("Fastmarkets — Cobalt price impact", "https://www.fastmarkets.com/commodities/battery-raw-materials/cobalt")
    ],
    "REG-EXPORT-BAN": [
        ("Journal Officiel RDC (legislación oficial DRC)", "https://www.leganet.cd"),
        ("S&P Global Commodity Insights", "https://www.spglobal.com/commodityinsights/en/market-insights/topics/cobalt"),
        ("Benchmark Mineral Intelligence — free tier", "https://benchmarkminerals.com/cobalt/"),
        ("Mining.com", "https://www.mining.com/tag/cobalt/"),
        ("Reuters Commodities", "https://www.reuters.com/business/commodities/")
    ],
    "REG-TAX": [
        ("Journal Officiel RDC", "https://www.leganet.cd"),
        ("African Development Bank — Policy tracker", "https://www.afdb.org"),
        ("Mining Weekly", "https://www.miningweekly.com"),
        ("S&P Global", "https://www.spglobal.com/commodityinsights")
    ],
    "FMA-FLOOD": [
        ("ReliefWeb — Humanitarian & climate events Africa", "https://reliefweb.int/country/cod"),
        ("OCHA DRC", "https://www.unocha.org/democratic-republic-congo"),
        ("GDACS — Global Disaster Alert", "https://www.gdacs.org"),
        ("Mozambique INGC (Instituto Nacional de Gestão de Calamidades)", "https://www.ingc.gov.mz")
    ],
    "GEO-COUP": [
        ("Reuters Africa", "https://www.reuters.com/world/africa/"),
        ("BBC Africa", "https://www.bbc.com/news/world/africa"),
        ("ACLED", "https://acleddata.com/dashboard/"),
        ("AllAfrica", "https://allafrica.com/")
    ]
}
```

---

## 5. TABLA DE RETARDOS HISTÓRICOS ESTIMADOS

Para el campo `{retardo_estimado}` del email. Basado en casos documentados.

| Tipo Evento | Región | Retardo hasta precio spot cobalto | Retardo hasta ETFs/acciones |
|-------------|--------|-----------------------------------|-----------------------------|
| Huelga portuaria (Durban) | GEO-08 | 3-7 días | 5-10 días hábiles |
| Conflicto armado zona minera (DRC) | GEO-01 | 1-3 días | 3-7 días hábiles |
| Inundación corredor tránsito | GEO-03/04 | 5-14 días | 7-14 días hábiles |
| Prohibición exportación | GEO-01/07 | Inmediato (0-24h) | 1-3 días hábiles |
| Huelga minera activa | GEO-01/02 | 2-5 días | 5-10 días hábiles |
| Nueva regulación impositiva | GEO-01 | 3-10 días | 7-14 días hábiles |
| Corte energético DRC (Inga) | GEO-01 | 5-10 días | 7-12 días hábiles |
| Ciclón corredor Beira | GEO-03 | 7-14 días | 10-21 días hábiles |

---

## 6. BROKER RECOMENDADO (RESIDENTE EN ESPAÑA)

### Recomendación para tu perfil (swing trading macro, global, fiscal española)

**Interactive Brokers (IBKR)** es la opción óptima para este sistema por las siguientes razones concretas:

| Criterio | IBKR | DEGIRO | Trading 212 |
|----------|------|--------|-------------|
| Acceso a TSX (Toronto) | Sí | No | No |
| Acceso a HKEx (Hong Kong) | Sí | Limitado | No |
| Acceso a LSE (Londres) | Sí | Sí | Sí |
| Acceso a NYSE/NASDAQ | Sí | Sí | Sí |
| Acceso a Euronext Bruselas | Sí | Sí | Sí |
| Opciones sobre ETFs | Sí | No | No |
| Cuenta en EUR (sin cambio divisa forzado) | Sí | Sí | Sí |
| Comisiones en ETFs EE.UU. | $0 (IBKR Lite no disponible en ES, pero IBKR Pro tiene mínimos muy bajos) | ~€2/trade | 0% (con spread) |
| Modelo de negocio (conflicto de interés) | Market maker externo | Cobra por orden | Creador de mercado interno (cuidado con spreads) |
| Reportes fiscales para España (Mod. 720, IRPF) | Genera informe de ganancias | Manual | Manual |

**Recomendación concreta:** Abrir cuenta en **IBKR Pro** (no Lite, no disponible en España). La cuenta mínima es $0 pero cobra $10/mes si no generas $10 en comisiones. Con operaciones de swing (pocas pero de tamaño) eso se cubre fácilmente.

**Nota fiscal importante para España:** Las ganancias de trading tributan como rendimientos del capital mobiliario (base del ahorro) al 19-28% según tramos. Los ETFs y acciones extranjeras deben declararse en Modelo 720 si superan 50.000€ en cuentas en el extranjero. IBKR genera el informe de ganancias/pérdidas automáticamente para la declaración de la renta.

---

## NOTAS DE MANTENIMIENTO

```
v1.0 — 2025-05 — Versión inicial.
                  Activos: Global sin restricción de bolsa.
                  Email: HTML con 7 secciones.
                  Broker: IBKR recomendado para residente en España.
```

### Revisión periódica obligatoria
- Verificar tickers cada 6 meses (fusiones, delistings)
- Actualizar retardos históricos cuando el sistema genere alertas reales (aprendizaje empírico)
- Añadir nuevos ETFs de metales críticos según se listen (sector en crecimiento)
