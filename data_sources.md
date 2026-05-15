# data_sources.md
# Fuentes de Datos Gratuitas — Sistema de Alerta Temprana de Cobalto
# Versión: 1.0 | Referencia: scoring_rules.md v1.0, keyword_dictionary.md v1.0

---

## 1. PRINCIPIOS DE RECOLECCIÓN DE DATOS

### 1.1 Restricciones del Sistema
- **Sin APIs de pago.** Todas las fuentes son gratuitas o de acceso público.
- **Sin scraping agresivo.** El script se ejecuta 3 veces/día (cada 8h). Nunca hace más de 1 request por dominio por ejecución.
- **User-Agent honesto.** El script se identifica como bot legítimo de investigación, no suplanta un navegador. Esto reduce riesgo de ban y es la práctica correcta.
- **Timeout estricto.** Máximo 15 segundos por request. Si falla, se registra en log y se continúa.
- **Sin almacenamiento de artículos completos.** Solo se guarda: URL, título, fecha, score, keywords detectados. No se archiva el cuerpo del artículo (evita problemas de copyright y reduce uso de disco en e2-micro).

### 1.2 Estrategia de Rate Limiting
```
Ejecución 1: 00:00 UTC (medianoche Madrid = medianoche UTC+2 → 22:00 hora local)
Ejecución 2: 08:00 UTC (10:00 hora Madrid)
Ejecución 3: 16:00 UTC (18:00 hora Madrid)
```
Este horario captura: noticias asiáticas (madrugada UTC), noticias europeas/africanas (mañana UTC), y cierre de mercados americanos (tarde UTC). Es también el horario de menor carga en los servidores de noticias.

### 1.3 Manejo de Errores por Fuente
Cada fuente tiene un contador de fallos. Si una fuente falla 3 ejecuciones consecutivas, se marca como `DEGRADED` y se excluye del scoring hasta que vuelva a responder. Esto evita que una fuente caída genere falsos negativos sistemáticos.

---

## 2. FUENTES RSS (PRIORIDAD 1 — Más Fiables)

Los feeds RSS son la fuente más robusta: estructura predecible, sin JavaScript, sin captcha, actualización frecuente. Son el núcleo del sistema.

### 2.1 Agencias de Primer Nivel

```python
RSS_TIER1 = [
    {
        "name": "Reuters Commodities",
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "credibility_modifier": 1.00,
        "language": "en",
        "update_frequency_min": 15,
        "notes": "Feed general. Filtrar por keywords de mineral. Reuters tiene feed específico de commodities pero está detrás de paywall. Este es el free tier.",
        "requires_full_text_fetch": True,  # El RSS solo da título + resumen, necesitas fetch del artículo
        "rate_limit_seconds": 30,          # Pausa mínima entre requests al mismo dominio
        "timeout": 10
    },
    {
        "name": "Reuters Africa",
        "url": "https://feeds.reuters.com/Reuters/AfricaNews",
        "credibility_modifier": 1.00,
        "language": "en",
        "update_frequency_min": 15,
        "notes": "Más relevante que el feed general para eventos en DRC, Zambia, Mozambique, Sudáfrica.",
        "requires_full_text_fetch": True,
        "rate_limit_seconds": 30,
        "timeout": 10
    },
    {
        "name": "AP News — Business",
        "url": "https://rsshub.app/apnews/topics/business",  # RSSHub proxy — AP no tiene RSS oficial libre
        "credibility_modifier": 1.00,
        "language": "en",
        "update_frequency_min": 30,
        "notes": "AP bloquea scraping directo. RSSHub es un proxy legítimo y gratuito. Alternativa: usar https://apnews.com/hub/africa directamente con BeautifulSoup si RSSHub cae.",
        "requires_full_text_fetch": True,
        "fallback_url": "https://apnews.com/hub/africa",
        "rate_limit_seconds": 45,
        "timeout": 15
    }
]
```

**Advertencia sobre Reuters RSS:** Reuters ha modificado sus feeds varias veces. Si el feed devuelve error 404, verificar la URL actual en https://www.reuters.com/tools/rss. La URL correcta puede cambiar sin aviso.

### 2.2 Medios Especializados en Minería y Commodities

```python
RSS_MINING_SPECIALIZED = [
    {
        "name": "Mining.com",
        "url": "https://www.mining.com/feed/",
        "credibility_modifier": 1.00,
        "language": "en",
        "update_frequency_min": 60,
        "notes": "El mejor feed gratuito para noticias mineras. Cubre DRC, Zambia, precios de cobalto. Feed completo sin paywall.",
        "requires_full_text_fetch": False,  # El RSS incluye texto completo
        "rate_limit_seconds": 60,
        "timeout": 15,
        "cobalt_specific_feed": "https://www.mining.com/tag/cobalt/feed/"  # Feed filtrado por cobalto
    },
    {
        "name": "Mining.com — Cobalt tag",
        "url": "https://www.mining.com/tag/cobalt/feed/",
        "credibility_modifier": 1.00,
        "language": "en",
        "update_frequency_min": 120,
        "notes": "Feed ya filtrado por cobalto. Usar este en LUGAR del feed general para reducir procesamiento.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 60,
        "timeout": 15
    },
    {
        "name": "Mining Weekly",
        "url": "https://www.miningweekly.com/rss",
        "credibility_modifier": 0.90,
        "language": "en",
        "update_frequency_min": 120,
        "notes": "Buena cobertura de Sudáfrica y Zambia. A veces requiere JavaScript para carga completa — verificar que el RSS sea accesible sin JS.",
        "requires_full_text_fetch": True,
        "rate_limit_seconds": 60,
        "timeout": 15
    },
    {
        "name": "Kitco Metals — Cobalt",
        "url": "https://www.kitco.com/rss/kitconews.rss",
        "credibility_modifier": 0.85,
        "language": "en",
        "update_frequency_min": 60,
        "notes": "Buena cobertura de precios de metales. Menos cobertura geopolítica pero útil para confirmar movimientos de precio que correlacionan con eventos detectados.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 45,
        "timeout": 10
    },
    {
        "name": "USGS — Mineral Resources",
        "url": "https://www.usgs.gov/news/science-explorer-categories/mineral-resources/news/rss.xml",
        "credibility_modifier": 0.95,
        "language": "en",
        "update_frequency_min": 1440,  # Actualización diaria
        "notes": "USGS publica datos de producción y alertas de escasez mineral. Baja frecuencia pero altísima credibilidad. Útil para confirmar tendencias SMC.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 120,
        "timeout": 15
    }
]
```

### 2.3 Fuentes Regionales Africanas

```python
RSS_AFRICAN_REGIONAL = [
    {
        "name": "AllAfrica",
        "url": "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf",
        "credibility_modifier": 0.85,
        "language": "en",  # También tiene artículos en FR y PT
        "update_frequency_min": 30,
        "notes": "Agregador de medios africanos. Cobertura excelente de DRC, Zambia, Tanzania, Mozambique. Los artículos son de medios locales re-publicados — verificar fuente original antes de usar credibility_modifier alto.",
        "requires_full_text_fetch": True,
        "rate_limit_seconds": 45,
        "timeout": 15,
        "geographic_relevance": ["GEO-01", "GEO-02", "GEO-03", "GEO-04"]
    },
    {
        "name": "The East African",
        "url": "https://www.theeastafrican.co.ke/rss",
        "credibility_modifier": 0.85,
        "language": "en",
        "update_frequency_min": 120,
        "notes": "Buena cobertura de Tanzania, Kenya, corredor oriental (GEO-03). Propiedad del grupo Nation Media.",
        "requires_full_text_fetch": True,
        "rate_limit_seconds": 60,
        "timeout": 15,
        "geographic_relevance": ["GEO-03"]
    },
    {
        "name": "Daily Maverick (Sudáfrica)",
        "url": "https://www.dailymaverick.co.za/feed/",
        "credibility_modifier": 0.85,
        "language": "en",
        "update_frequency_min": 120,
        "notes": "El medio independiente más importante de Sudáfrica. Excelente cobertura de Transnet, Puerto de Durban, política minera sudafricana.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 60,
        "timeout": 15,
        "geographic_relevance": ["GEO-04", "GEO-08"]
    },
    {
        "name": "Radio France Internationale — Afrique",
        "url": "https://www.rfi.fr/fr/rss/rfi-afrique.xml",
        "credibility_modifier": 0.80,
        "language": "fr",
        "update_frequency_min": 60,
        "notes": "RFI es la fuente francófona más fiable para DRC y Mali. El feed es en francés — el sistema necesita procesar con el diccionario FR. Excelente para eventos que tardan en llegar a medios anglosajones.",
        "requires_full_text_fetch": True,
        "rate_limit_seconds": 45,
        "timeout": 15,
        "geographic_relevance": ["GEO-01"]
    },
    {
        "name": "VOA Africa",
        "url": "https://www.voanews.com/podcast/rss/4473983",
        "credibility_modifier": 0.80,
        "language": "en",
        "update_frequency_min": 120,
        "notes": "Buena cobertura general de África subsahariana. Útil como confirmación secundaria.",
        "requires_full_text_fetch": True,
        "rate_limit_seconds": 60,
        "timeout": 15,
        "geographic_relevance": ["GEO-01", "GEO-02", "GEO-03"]
    },
    {
        "name": "Club of Mozambique",
        "url": "https://clubofmozambique.com/feed/",
        "credibility_modifier": 0.80,
        "language": "en",
        "update_frequency_min": 240,
        "notes": "Mejor fuente en inglés para noticias de Mozambique (corredor Beira, Puerto de Nacala). Indispensable para GEO-03.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 90,
        "timeout": 15,
        "geographic_relevance": ["GEO-03"]
    },
    {
        "name": "Zambia Reports",
        "url": "https://zambiareports.com/feed/",
        "credibility_modifier": 0.75,
        "language": "en",
        "update_frequency_min": 240,
        "notes": "Cobertura de GEO-02. Medio local — aplicar credibility_modifier conservador. Útil para noticias laborales en minas zambianas antes de que lleguen a Reuters.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 90,
        "timeout": 15,
        "geographic_relevance": ["GEO-02"]
    }
]
```

### 2.4 Fuentes para Cadena de Suministro y Refinación China

```python
RSS_CHINA_SUPPLY_CHAIN = [
    {
        "name": "S&P Global — Commodity Insights (free)",
        "url": "https://www.spglobal.com/commodityinsights/en/rss-feed/metals",
        "credibility_modifier": 1.00,
        "language": "en",
        "update_frequency_min": 240,
        "notes": "S&P Global tiene paywall para la mayoría de contenido. El feed RSS gratuito es limitado pero los títulos + resúmenes son suficientes para detectar señales. NO hacer fetch del artículo completo (paywall).",
        "requires_full_text_fetch": False,  # Solo título y resumen — suficiente para keywords
        "rate_limit_seconds": 120,
        "timeout": 10
    },
    {
        "name": "Reuters China Business",
        "url": "https://feeds.reuters.com/Reuters/ChinaNews",
        "credibility_modifier": 1.00,
        "language": "en",
        "update_frequency_min": 30,
        "notes": "Crítico para detectar eventos en GEO-07 (refinación china). Regulaciones ambientales, cortes energéticos, sanciones.",
        "requires_full_text_fetch": True,
        "rate_limit_seconds": 30,
        "timeout": 10
    },
    {
        "name": "Benchmark Mineral Intelligence — Blog",
        "url": "https://benchmarkminerals.com/feed/",
        "credibility_modifier": 0.70,
        "language": "en",
        "update_frequency_min": 1440,
        "notes": "BMI es la referencia de precios de minerales para baterías. El blog gratuito publica análisis de mercado ocasionalmente. Contenido valioso pero baja frecuencia.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 120,
        "timeout": 15
    }
]
```

### 2.5 Fuentes para Indonesia / Sulawesi (GEO-10)

Indonesia produce ~5% del cobalto mundial vía HPAL como subproducto del níquel laterítico (Sulawesi, Halmahera, Obi). Es la zona de mayor crecimiento estructural del cobalto: ramp-ups proyectados en 2026 (Pomalaa, Bahodopi, Huafei, Halmahera Persada Lygend) elevan la producción ~21% anual. Las disrupciones reales ya observadas (landslides en IMIP febrero 2026, fallos en dry-stack tailings, escasez de azufre que recorta MHP) confirman que la zona genera eventos de alta señal con regularidad. Las fuentes siguientes han sido validadas en 2026.

```python
RSS_INDONESIA = [
    {
        "name": "ANTARA — Business & Investment",
        "url": "https://en.antaranews.com/rss/business-investment.xml",
        "credibility_modifier": 0.85,
        "language": "en",
        "update_frequency_min": 60,
        "notes": "Agencia nacional de noticias de Indonesia, edición inglesa. Cobertura sólida de regulación minera, RKAB (cuotas), políticas del Ministerio ESDM, sindicatos. El feed business-investment captura noticias de cobalto y níquel cuando aparecen. NO publica feed minero específico — usar este feed business y filtrar por keywords.",
        "requires_full_text_fetch": True,
        "rate_limit_seconds": 60,
        "timeout": 15,
        "geographic_relevance": ["GEO-10"]
    },
    {
        "name": "ANTARA — Press Release",
        "url": "https://en.antaranews.com/rss/press-release.xml",
        "credibility_modifier": 0.85,
        "language": "en",
        "update_frequency_min": 120,
        "notes": "Comunicados oficiales reproducidos por ANTARA. Útil para detectar anuncios del Ministerio ESDM (cuotas, royalty, reclasificación de cobalto como mineral independiente). Volumen bajo pero alta señal.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 90,
        "timeout": 15,
        "geographic_relevance": ["GEO-10"]
    },
    {
        "name": "Mining Technology",
        "url": "https://www.mining-technology.com/feed/",
        "credibility_modifier": 0.90,
        "language": "en",
        "update_frequency_min": 240,
        "notes": "Publicación industrial con cobertura analítica de Indonesia (proyectos HPAL, capacidad MHP, política de cuotas). Volumen medio. Útil para detectar tendencias estructurales (SMC) y cierres operacionales de plantas.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 60,
        "timeout": 15,
        "geographic_relevance": ["GEO-10", "GEO-05", "GEO-06"]
    },
    {
        "name": "Mongabay — Conservation News",
        "url": "https://news.mongabay.com/feed/",
        "credibility_modifier": 0.80,
        "language": "en",
        "update_frequency_min": 360,
        "notes": "Mongabay es la fuente más fiable para impactos ambientales/sociales de la minería de níquel en Indonesia (Raja Ampat, Gebe, Halmahera, Sulawesi). Detecta moratorias, revocación de permisos, protestas comunitarias y fallos de tailings ANTES de que lleguen a Reuters. Feed global — filtrar por geographic_terms de GEO-10.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 90,
        "timeout": 15,
        "geographic_relevance": ["GEO-10", "GEO-01"]
    }
]
```

**Notas de cobertura:**
- **Jakarta Post, Tempo English:** No exponen feeds RSS estables (404/redirección). Excluidos. La cobertura equivalente la proporciona ANTARA + Google News (Fase 5).
- **ESDM (Ministerio):** No tiene RSS oficial. Las decisiones llegan vía ANTARA Press Release o Mining Technology dentro de las 24-48h.
- **Argus Media / S&P Platts:** Tienen titulares accesibles pero contenido completo de pago. No incluidos para evitar inestabilidad.

### 2.6 Fuentes para Refino Europeo (GEO-11)

GEO-11 cubre los refinadores europeos no-chinos: Umicore (Olen, Bélgica + Kokkola, Finlandia), Glencore Nikkelverk (Kristiansand, Noruega), Nornickel Harjavalta (Finlandia, intermitente por sanciones), Terrafame (Sotkamo, Finlandia). Su peso geográfico es bajo (0.80) porque representan capacidad estructural relevante para diversificación pero no son cuello de botella inmediato. Las disrupciones aquí afectan principalmente al SMC (horizonte 1-3 meses). Por eso las fuentes se ubican en **Fase 4 (complementaria)**: solo se consultan si el score tras fases 1-3 está bajo NARANJA.

```python
RSS_EUROPE_REFINING = [
    {
        "name": "Yle News — English",
        "url": "https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_NEWS",
        "credibility_modifier": 0.90,
        "language": "en",
        "update_frequency_min": 120,
        "notes": "Servicio público finlandés (equivalente BBC). Cobertura de Harjavalta, Kokkola, Terrafame y política minera finlandesa. Solo edición inglesa del feed. Volumen general — keywords GEO-11 filtrarán contenido relevante.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 90,
        "timeout": 15,
        "geographic_relevance": ["GEO-11"]
    },
    {
        "name": "Energy-Storage.News",
        "url": "https://www.energy-storage.news/feed/",
        "credibility_modifier": 0.85,
        "language": "en",
        "update_frequency_min": 180,
        "notes": "Publicación especializada en almacenamiento de energía y cadena de suministro de baterías en Europa. Cubre Umicore, EBA (European Battery Alliance), regulación EU sobre materias primas críticas. Útil para SMC (señales estructurales).",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 90,
        "timeout": 15,
        "geographic_relevance": ["GEO-11"]
    }
]
```

**Notas de cobertura:**
- **Umicore / Glencore / Terrafame newsrooms:** No tienen feeds RSS públicos estables. Sus comunicados corporativos llegan vía Reuters, Mining.com o agregadores europeos dentro de horas.
- **European Commission (RESourceEU, Battery Regulation):** Sin RSS dedicado para materias primas críticas. Cobertura vía Reuters + Mining.com.
- **Cobalt Institute (Bruselas):** Web sin feed RSS detectable. Publica trimestralmente — baja frecuencia.

---

## 3. FUENTES DE SCRAPING DIRECTO (PRIORIDAD 2)

Para fuentes sin RSS. Scraping solo de páginas de índice o listados, nunca de artículos completos masivamente.

### 3.1 Portales Portuarios Oficiales

```python
PORT_STATUS_SOURCES = [
    {
        "name": "Transnet Port Terminals — Port of Durban",
        "url": "https://www.transnet.net/BusinessWithTransnet/TPT/Pages/PortofDurban.aspx",
        "type": "scraping",
        "credibility_modifier": 1.00,
        "language": "en",
        "scraping_method": "BeautifulSoup — buscar texto en divs de estado operacional",
        "target_elements": ["port status", "operational update", "notice"],
        "update_frequency_min": 480,  # 3 veces/día es suficiente
        "notes": "Transnet publica avisos de operaciones en su web. Si hay huelga o disrupción, suele aparecer aquí antes que en Reuters. CRÍTICO para GEO-04/GEO-08.",
        "rate_limit_seconds": 300,
        "timeout": 20,
        "fallback": "Buscar 'Transnet port update' en Google News RSS si la web no carga"
    },
    {
        "name": "Tanzania Ports Authority",
        "url": "https://www.tanzaniaports.go.tz/index.php/news",
        "type": "scraping",
        "credibility_modifier": 1.00,
        "language": "en",
        "scraping_method": "BeautifulSoup — lista de noticias recientes",
        "update_frequency_min": 480,
        "notes": "TPA publica comunicados oficiales de operaciones en el Puerto de Dar es Salaam. Actualización lenta pero alta credibilidad.",
        "rate_limit_seconds": 300,
        "timeout": 20
    },
    {
        "name": "CFM Mozambique",
        "url": "https://www.cfmnet.co.mz/noticias",
        "type": "scraping",
        "credibility_modifier": 1.00,
        "language": "pt",
        "scraping_method": "BeautifulSoup — sección noticias",
        "update_frequency_min": 480,
        "notes": "CFM opera los puertos de Beira y Nacala y el corredor ferroviario hacia Zambia/DRC. Publica en portugués. Usar diccionario PT.",
        "rate_limit_seconds": 300,
        "timeout": 20
    }
]
```

**Nota crítica sobre scraping de portales portuarios:** Estos portales son gubernamentales y tienen uptime bajo. Es normal que fallen 1-2 veces/semana. El sistema debe tratar sus errores con más tolerancia que los feeds RSS comerciales. Si un portal portuario falla, no significa que haya disrupción — solo que la web no carga.

### 3.2 Fuentes de Conflicto y Seguridad

```python
SECURITY_SOURCES = [
    {
        "name": "ACLED — Africa Crisis Data",
        "url": "https://acleddata.com/data-export-tool/",
        "type": "api_free",
        "credibility_modifier": 1.00,
        "language": "en",
        "api_endpoint": "https://api.acleddata.com/acled/read",
        "api_params": {
            "key": "REQUIERE_REGISTRO_GRATUITO",
            "email": "TU_EMAIL",
            "region": "1",          # Africa
            "event_type": "Battles|Explosions/Remote violence|Violence against civilians",
            "country": "Democratic Republic of Congo|Zambia|Tanzania|Mozambique|South Africa",
            "limit": 50,
            "fields": "event_date|event_type|actor1|location|latitude|longitude|notes|source"
        },
        "update_frequency_min": 480,
        "notes": "ACLED es GRATUITO con registro académico/investigador. Es la fuente más precisa para eventos de conflicto en zonas mineras de DRC. El API devuelve JSON. Indispensable para GEO-01. REGISTRARSE EN: https://developer.acleddata.com",
        "rate_limit_seconds": 300,
        "timeout": 20,
        "data_format": "JSON",
        "requires_registration": True,
        "registration_url": "https://developer.acleddata.com"
    },
    {
        "name": "ReliefWeb — DRC",
        "url": "https://reliefweb.int/updates?source=reliefweb&country=cod&format=rss",
        "type": "rss",
        "credibility_modifier": 0.90,
        "language": "en",
        "update_frequency_min": 240,
        "notes": "ReliefWeb agrega informes humanitarios de OCHA, UNHCR, etc. sobre DRC. Señal excelente para conflictos que afectan la zona minera. El feed RSS es gratuito.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 120,
        "timeout": 15
    },
    {
        "name": "GDACS — Global Disaster Alert",
        "url": "https://www.gdacs.org/xml/rss.xml",
        "type": "rss",
        "credibility_modifier": 1.00,
        "language": "en",
        "update_frequency_min": 240,
        "notes": "GDACS es el sistema de alerta de desastres de la ONU. Detecta ciclones, inundaciones, terremotos. Crítico para FMA events en GEO-03 (Mozambique — ciclones) y GEO-01 (inundaciones en DRC).",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 120,
        "timeout": 10
    }
]
```

### 3.3 Google News RSS (Búsquedas Específicas)

Google News permite RSS de búsquedas específicas. Son inconsistentes (Google los puede cambiar sin aviso) pero muy potentes cuando funcionan.

```python
GOOGLE_NEWS_RSS = [
    {
        "name": "Google News — Cobalt supply",
        "url": "https://news.google.com/rss/search?q=cobalt+supply+disruption&hl=en-US&gl=US&ceid=US:en",
        "credibility_modifier": 0.50,  # Agregador — fuente real determina credibilidad real
        "language": "en",
        "update_frequency_min": 480,
        "notes": "Google News RSS de búsqueda. Credibility_modifier bajo porque Google agrega cualquier fuente. Usar solo para detectar si hay cobertura de un evento, luego buscar la fuente original. NO usar el score de Google News directamente.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 300,
        "timeout": 10
    },
    {
        "name": "Google News — DRC cobalt",
        "url": "https://news.google.com/rss/search?q=DRC+cobalt+mine&hl=en-US&gl=US&ceid=US:en",
        "credibility_modifier": 0.50,
        "language": "en",
        "update_frequency_min": 480,
        "notes": "Búsqueda específica DRC. Útil para detectar eventos no cubiertos por feeds especializados.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 300,
        "timeout": 10
    },
    {
        "name": "Google News — Durban port",
        "url": "https://news.google.com/rss/search?q=Durban+port+strike+disruption&hl=en-US&gl=US&ceid=US:en",
        "credibility_modifier": 0.50,
        "language": "en",
        "update_frequency_min": 480,
        "notes": "Monitoreo específico de Puerto de Durban. Alta densidad de falsos positivos — aplicar filtros geográfico y de negación antes de puntuar.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 300,
        "timeout": 10
    },
    {
        "name": "Google News — cobalt cobalto FR",
        "url": "https://news.google.com/rss/search?q=cobalt+greve+mine+RDC&hl=fr-FR&gl=FR&ceid=FR:fr",
        "credibility_modifier": 0.50,
        "language": "fr",
        "update_frequency_min": 480,
        "notes": "Búsqueda en francés para eventos en DRC. Captura noticias de medios francófonos africanos que no tienen RSS propio.",
        "requires_full_text_fetch": False,
        "rate_limit_seconds": 300,
        "timeout": 10
    }
]
```

---

## 4. FUENTES DE PRECIO (CONFIRMACIÓN, NO SEÑAL PRIMARIA)

Estas fuentes NO generan score de disrupción. Se usan para CONFIRMAR que un evento ya detectado está teniendo impacto real en el mercado. Son un segundo paso de validación humana, no parte del scoring automático.

```python
PRICE_CONFIRMATION_SOURCES = [
    {
        "name": "LME Cobalt Price — macrotrends proxy",
        "url": "https://www.macrotrends.net/1378/cobalt-price-today",
        "type": "scraping",
        "notes": "LME no ofrece precio gratuito vía API. Macrotrends tiene histórico público pero actualización lenta (1-2 días de retraso). Útil solo para contexto, no para timing.",
        "use_case": "Incluir precio actual aproximado en el email como contexto",
        "rate_limit_seconds": 600,  # Solo 1 vez/día
        "timeout": 20
    },
    {
        "name": "InfoMine — Cobalt Price",
        "url": "http://www.infomine.com/investment/metal-prices/cobalt/",
        "type": "scraping",
        "notes": "InfoMine tiene precios de metales gratuitos. Verificar disponibilidad — el sitio tiene uptime intermitente.",
        "use_case": "Precio de respaldo si macrotrends falla",
        "rate_limit_seconds": 600,
        "timeout": 20
    },
    {
        "name": "Trading Economics — Cobalt",
        "url": "https://tradingeconomics.com/commodity/cobalt",
        "type": "scraping",
        "notes": "Trading Economics bloquea scraping agresivo con Cloudflare. Solo intentar con headers normales y aceptar fallo si responde 403. NO reintentar.",
        "use_case": "Fallback de precio",
        "rate_limit_seconds": 600,
        "timeout": 10,
        "expect_failure": True  # El sistema no debe depender de esta fuente
    }
]
```

**Nota importante:** El sistema de scoring NO necesita el precio del cobalto para funcionar. El precio es contexto informativo para el email. Si todas las fuentes de precio fallan, el email se envía igualmente sin la sección de precio. No bloquear la alerta por indisponibilidad de precio.

---

## 5. FUENTES DESACONSEJADAS (Y POR QUÉ)

Fuentes que parecen obvias pero no deben incluirse en el sistema:

```python
SOURCES_EXCLUDED = [
    {
        "name": "Twitter/X",
        "reason": "API de pago desde 2023. Scraping web extremadamente inestable. Alto ratio de desinformación. Credibility_modifier 0.40 haría que su impacto en el score fuera irrelevante de todas formas. No vale el coste de mantenimiento.",
        "alternative": "Los eventos importantes en Twitter llegan en horas a Reuters/AllAfrica."
    },
    {
        "name": "Bloomberg / Financial Times",
        "reason": "Paywall total. No tienen RSS gratuito con contenido. Solo títulos sin texto.",
        "alternative": "Reuters cubre los mismos eventos con acceso gratuito."
    },
    {
        "name": "Fastmarkets (datos de precio)",
        "reason": "Paywall para datos de precio en tiempo real. El blog gratuito tiene cobertura esporádica.",
        "alternative": "Mining.com para contexto de precio sin paywall."
    },
    {
        "name": "Telegram channels (grupos mineros)",
        "reason": "No existe API gratuita estable. Alta desinformación. Imposible verificar fuente.",
        "alternative": "ACLED y ReliefWeb para eventos de seguridad."
    },
    {
        "name": "Reddit (r/investing, r/commodities)",
        "reason": "API de pago desde 2023. Credibilidad muy baja para señales operacionales.",
        "alternative": "Ninguno — no hay equivalente gratuito de valor."
    },
    {
        "name": "Seeking Alpha",
        "reason": "Paywall para artículos completos. Scraping bloqueado activamente.",
        "alternative": "Mining.com cubre las mismas empresas."
    }
]
```

---

## 6. ARQUITECTURA DE PROCESAMIENTO DE FUENTES

### 6.1 Orden de Procesamiento en Cada Ejecución

```python
PROCESSING_ORDER = [
    # Fase 1: Fuentes de alta señal (ejecutar siempre)
    "reuters_africa",       # 1a — mayor credibilidad
    "reuters_commodities",  # 1b
    "mining_com_cobalt",    # 1c — más específico
    "acled_drc",            # 1d — conflicto armado
    "reliefweb_drc",        # 1e — humanitario/catástrofe

    # Fase 2: Fuentes regionales (ejecutar siempre)
    "allafrica",            # 2a
    "rfi_afrique",          # 2b — francófono
    "daily_maverick",       # 2c — Sudáfrica/Durban
    "club_mozambique",      # 2d — corredor Beira
    "east_african",         # 2e — corredor Tanzania
    "zambia_reports",       # 2f — GEO-02
    # GEO-10 (Indonesia, peso 1.10) — fuentes robustas, ejecutar siempre
    "antara_business",      # 2g — agencia nacional Indonesia
    "antara_press",         # 2h — comunicados oficiales ESDM
    "mining_technology",    # 2i — analítica industrial Indonesia/HPAL
    "mongabay",             # 2j — disrupciones ambientales/sociales

    # Fase 3: Portales portuarios (ejecutar siempre — baja carga)
    "transnet_durban",      # 3a
    "tpa_tanzania",         # 3b
    "cfm_mozambique",       # 3c

    # Fase 4: Fuentes complementarias (ejecutar si score < NARANJA tras fases 1-3)
    "gdacs",                # 4a — desastres naturales
    "mining_weekly",        # 4b
    "usgs",                 # 4c
    "voa_africa",           # 4d
    "reuters_china",        # 4e
    # GEO-11 (Refino europeo, peso 0.80) — afecta principalmente a SMC
    "yle_news_en",          # 4f — Finlandia (Harjavalta, Kokkola, Terrafame)
    "energy_storage_news",  # 4g — cadena de suministro baterías EU

    # Fase 5: Google News RSS (ejecutar siempre como red de seguridad)
    "gnews_cobalt_en",      # 5a
    "gnews_cobalt_fr",      # 5b
    "gnews_drc",            # 5c
    "gnews_durban",         # 5d
    "gnews_indonesia_nickel",  # 5e — GEO-10 disrupciones
    "gnews_europe_refining"    # 5f — GEO-11 Umicore/Glencore/Terrafame
]
```

**Lógica de la Fase 4:** Si las fases 1-3 ya generan un score NARANJA o ROJO, las fuentes complementarias probablemente no añaden nueva información (el evento ya está cubierto). Ejecutar la Fase 4 solo si el score sigue en VERDE o AMARILLO bajo ahorra tiempo de ejecución y requests.

### 6.2 Deduplicación de Artículos

```python
# Un artículo se considera duplicado si:
# 1. Mismo dominio + misma URL (obvio)
# 2. Mismo dominio + título con similitud > 85% (Levenshtein o similar)
# 3. Fuentes distintas + mismos keywords de alto peso en ventana de 48h

# Implementación simplificada para e2-micro (sin librerías pesadas):
def es_duplicado(articulo_nuevo, articulos_procesados):
    # Check 1: URL exacta
    if articulo_nuevo.url in [a.url for a in articulos_procesados]:
        return True
    # Check 2: Título muy similar en mismo dominio (últimas 48h)
    for a in articulos_procesados:
        if a.dominio == articulo_nuevo.dominio:
            if similitud_simple(a.titulo, articulo_nuevo.titulo) > 0.85:
                return True
    return False

def similitud_simple(s1, s2):
    # Implementación sin librerías: palabras en común / total palabras
    palabras1 = set(s1.lower().split())
    palabras2 = set(s2.lower().split())
    if not palabras1 or not palabras2:
        return 0
    interseccion = palabras1 & palabras2
    return len(interseccion) / max(len(palabras1), len(palabras2))
```

### 6.3 Gestión de Estado entre Ejecuciones

El script debe recordar qué artículos ya procesó para no re-puntuar el mismo evento en la siguiente ejecución.

```python
# Archivo de estado: /home/usuario/cobalt_alert/state.json
STATE_FILE_STRUCTURE = {
    "last_run": "2025-05-15T08:00:00Z",
    "processed_urls": [
        # Lista de URLs procesadas en las últimas 72h
        # Se purga automáticamente lo anterior a 72h para no crecer indefinidamente
    ],
    "active_events": [
        # Eventos activos (score > UMBRAL_MINIMO) que no han sido resueltos
        # Incluye: event_id, categoria, region, score, primera_deteccion, ultima_deteccion
        # Se purga cuando aparece noticia de resolución del evento
    ],
    "source_health": {
        # Estado de cada fuente: last_success, consecutive_failures, status (OK/DEGRADED)
        "reuters_africa": {"last_success": "2025-05-15T08:00:00Z", "consecutive_failures": 0, "status": "OK"},
    },
    "score_history": [
        # Últimos 30 scores diarios (SSC, SMC) para tracking de tendencia
        {"date": "2025-05-15", "max_ssc": 12.4, "max_smc": 18.2, "nivel": "AMARILLO"}
    ]
}
```

---

## 7. CONFIGURACIÓN DE HEADERS HTTP

```python
# Headers para requests — identificación honesta como bot de investigación
REQUEST_HEADERS = {
    "User-Agent": "CobaltSupplyMonitor/1.0 (research bot; contact: tu_email@gmail.com)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8,pt;q=0.7,es;q=0.6",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "close"  # No mantener conexiones abiertas — reduce huella en e2-micro
}

# Importante: Incluir tu email real en User-Agent.
# Los administradores de servidores pueden contactarte si hay problemas
# en lugar de banearte directamente. Es práctica estándar para bots legítimos.
```

---

## 8. CONSIDERACIONES ESPECÍFICAS PARA GCP e2-micro

```python
E2_MICRO_CONSTRAINTS = {
    "ram_mb": 1024,         # 1 GB RAM — suficiente pero ajustado
    "cpu_shared": True,     # CPU compartida — no hacer procesamiento pesado en paralelo
    "disk_gb": 10,          # Disco gratuito — no almacenar artículos completos
    "network_egress_free_gb_month": 1,  # 1 GB egress gratuito/mes — más que suficiente

    "recomendaciones": [
        "Procesar fuentes secuencialmente, no en paralelo (threading puede saturar CPU compartida)",
        "Usar feedparser para RSS (ligero, sin dependencias pesadas)",
        "Usar requests + BeautifulSoup para scraping (no Selenium — demasiado pesado)",
        "Almacenar state.json en disco local, no en base de datos (sqlite es excesivo para este volumen)",
        "Limpiar /tmp después de cada ejecución",
        "Logging a archivo con rotación diaria (máximo 7 días de logs)"
    ],

    "librerias_recomendadas": {
        "feedparser": "2.0.0+",     # Parsing RSS/Atom — pip install feedparser
        "requests": "2.28+",         # HTTP requests — viene con Python
        "beautifulsoup4": "4.11+",   # Scraping HTML — pip install beautifulsoup4
        "lxml": "4.9+",              # Parser para BS4 — pip install lxml
        "python-dateutil": "2.8+",   # Parsing de fechas — pip install python-dateutil
        "unicodedata": "stdlib",     # Normalización de tildes/diacríticos — no instalar
        "smtplib": "stdlib",         # Envío de email — no instalar
        "json": "stdlib",            # Estado del sistema — no instalar
        "logging": "stdlib"          # Logging — no instalar
    },

    "librerias_a_evitar": {
        "pandas": "Demasiado pesado para e2-micro. Usar listas/dicts nativos de Python.",
        "numpy": "Innecesario para este volumen de datos.",
        "selenium": "Requiere Chrome/Firefox — imposible en e2-micro free tier.",
        "scrapy": "Framework completo — demasiado para este caso de uso.",
        "transformers": "Modelos NLP — memoria insuficiente.",
        "spacy": "Demasiado pesado para NLP básico. Usar regex y string matching."
    }
}
```

---

## 9. PRUEBA DE DISPONIBILIDAD DE FUENTES

Antes de desplegar el script en producción, verificar que cada fuente responde correctamente:

```bash
# Script de verificación rápida (ejecutar manualmente antes del primer deploy)
# Guardar como: verify_sources.sh

#!/bin/bash
echo "=== Verificando disponibilidad de fuentes RSS ==="

feeds=(
    "https://feeds.reuters.com/Reuters/AfricaNews"
    "https://www.mining.com/tag/cobalt/feed/"
    "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf"
    "https://www.rfi.fr/fr/rss/rfi-afrique.xml"
    "https://www.dailymaverick.co.za/feed/"
    "https://reliefweb.int/updates?source=reliefweb&country=cod&format=rss"
    "https://www.gdacs.org/xml/rss.xml"
    "https://clubofmozambique.com/feed/"
    "https://zambiareports.com/feed/"
    # GEO-10 (Indonesia)
    "https://en.antaranews.com/rss/business-investment.xml"
    "https://en.antaranews.com/rss/press-release.xml"
    "https://www.mining-technology.com/feed/"
    "https://news.mongabay.com/feed/"
    # GEO-11 (Refino europeo)
    "https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_NEWS"
    "https://www.energy-storage.news/feed/"
)

for feed in "${feeds[@]}"; do
    status=$(curl -o /dev/null -s -w "%{http_code}" --max-time 10 "$feed")
    echo "$status — $feed"
done

echo ""
echo "=== Verificando portales portuarios ==="
ports=(
    "https://www.transnet.net/BusinessWithTransnet/TPT/Pages/PortofDurban.aspx"
    "https://www.tanzaniaports.go.tz/index.php/news"
    "https://www.cfmnet.co.mz/noticias"
)

for port in "${ports[@]}"; do
    status=$(curl -o /dev/null -s -w "%{http_code}" --max-time 15 "$port")
    echo "$status — $port"
done
```

**Códigos esperados:** 200 = OK, 301/302 = redirección (puede funcionar), 403 = bloqueado (revisar headers), 404 = URL incorrecta (buscar URL actual), 503 = caído temporalmente.

---

## NOTAS DE MANTENIMIENTO

### URLs que cambian con frecuencia
- Reuters RSS: verificar trimestralmente en https://www.reuters.com/tools/rss
- Google News RSS: formato de URL puede cambiar sin aviso — verificar mensualmente
- AllAfrica RDF: URL ha cambiado 2 veces en los últimos 3 años — verificar si deja de responder

### Registro de cambios
```
v1.0 — 2025-05 — Versión inicial.
                  20 fuentes RSS activas.
                  3 portales portuarios.
                  1 API REST (ACLED — requiere registro gratuito).
                  4 Google News RSS de búsqueda.
                  Optimizado para GCP e2-micro free tier.

v1.1 — 2026-05 — Cobertura para nuevas zonas geográficas GEO-10 y GEO-11.
                  + GEO-10 (Indonesia/Sulawesi, peso 1.10): añadidos ANTARA
                    Business & Investment, ANTARA Press Release, Mining
                    Technology, Mongabay Conservation News (Fase 2).
                  + GEO-11 (Refino europeo, peso 0.80): añadidos Yle News
                    English (Finlandia) y Energy-Storage.News (Fase 4 —
                    complementaria, ya que la zona afecta mayoritariamente
                    al SMC).
                  + 2 Google News RSS de búsqueda: indonesia_nickel y
                    europe_refining.
                  Total: 26 fuentes RSS activas, 6 Google News, 3 portales
                  portuarios, 1 API REST.
                  Fuentes evaluadas y excluidas: Jakarta Post (sin RSS
                  estable), Tempo English (404), ESDM Ministry (sin RSS
                  oficial), Cobalt Institute (sin RSS), Argus/S&P Platts
                  (titulares libres pero contenido de pago).
```

### Archivos dependientes
- `main_scorer.py` — implementa el procesamiento de todas las fuentes aquí definidas
- `scoring_rules.md` — define los modificadores de credibilidad por fuente (Sección 5)
- `keyword_dictionary.md` — define los términos buscados en el contenido de cada fuente
