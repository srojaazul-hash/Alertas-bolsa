# keyword_dictionary.md
# Diccionario Heurístico Multilingüe — Sistema de Alerta Temprana de Cobalto
# Versión: 1.0 | Idiomas: EN, FR, PT, ES | Referencia: scoring_rules.md v1.0

---

## INSTRUCCIONES DE USO PARA EL SCRIPT

### Estructura de cada entrada
```python
# Formato interno del diccionario en Python
{
    "term": "string",           # Término a buscar (lowercase, sin tildes en la clave)
    "display": "string",        # Término original con tildes/capitalización
    "lang": "en|fr|pt|es",
    "category": "LOG-PORT",     # Código de scoring_rules.md Sección 3
    "weight": float,            # Peso base del keyword (0.5 — 5.0)
    "requires_context": bool,   # True = solo puntúa si hay keyword de contexto cobalt/cobalto cerca
    "context_window": int,      # Palabras de distancia para considerar contexto (default: 50)
    "geographic_boost": list,   # Códigos GEO que amplifican este término si aparecen juntos
    "notes": "string"           # Advertencias de falsos positivos conocidos
}
```

### Regla de búsqueda
1. Convertir texto a lowercase antes de buscar.
2. Eliminar tildes/diacríticos para matching (normalización NFC → ASCII).
3. Para `requires_context: true`, verificar presencia de al menos 1 término del BLOQUE 0 en ventana de `context_window` palabras.
4. Aplicar filtro de negación (scoring_rules.md Sección 6.3) antes de asignar peso.

---

## BLOQUE 0 — TÉRMINOS ANCLA (MINERAL OBJETIVO)

Estos términos NO puntúan por sí solos. Son el requisito de contexto para todos los términos con `requires_context: true`. Si ninguno aparece en el artículo, el artículo no es relevante para el sistema.

**Peso como ancla: N/A (no generan score, habilitan scoring de otros)**

```python
ANCHOR_TERMS = [
    # Inglés
    "cobalt", "cobalt ore", "cobalt hydroxide", "cobalt sulfate",
    "cobalt carbonate", "cobalt metal", "cobalt refining",
    "battery-grade cobalt", "cobalt supply", "cobalt market",
    "cobalt mining", "cobalt production", "cobalt export",
    "cobalt price", "cobalt demand", "critical mineral",
    "critical metals", "battery metals", "EV battery supply",

    # Francés
    "cobalt", "minerai de cobalt", "hydroxyde de cobalt",
    "sulfate de cobalt", "raffinage du cobalt", "cobalt brut",
    "production de cobalt", "exportation de cobalt",
    "minerais critiques", "métaux de batterie",

    # Portugués
    "cobalto", "minério de cobalto", "hidróxido de cobalto",
    "sulfato de cobalto", "refinação de cobalto",
    "produção de cobalto", "exportação de cobalto",
    "minerais críticos", "metais para baterias",

    # Español
    "cobalto", "mineral de cobalto", "hidróxido de cobalto",
    "sulfato de cobalto", "refinación de cobalto",
    "producción de cobalto", "exportación de cobalto",
    "minerales críticos", "metales para baterías"
]
```

---

## BLOQUE 1 — GEOGRAFÍAS CRÍTICAS

Términos geográficos vinculados a códigos GEO de scoring_rules.md. Cuando aparecen junto a términos de evento, activan el peso geográfico correspondiente.

```python
GEOGRAPHIC_TERMS = {

    "GEO-01": {  # DRC — Cinturón Cuprífero, peso_base: 1.80
        "en": [
            "democratic republic of congo", "drc", "congo kinshasa",
            "katanga", "lualaba", "haut-katanga", "kolwezi", "likasi",
            "lubumbashi", "fungurume", "tenke fungurume", "mutanda",
            "boss mining", "kamoto", "kamoa-kakula",
            "copperbelt", "copper belt", "central african copperbelt"
        ],
        "fr": [
            "république démocratique du congo", "rdc", "congo kinshasa",
            "katanga", "lualaba", "haut-katanga", "kolwezi", "likasi",
            "lubumbashi", "fungurume", "tenke fungurume", "mutanda",
            "ceinture cuivrière", "province du lualaba"
        ],
        "pt": [
            "república democrática do congo", "rdc", "congo",
            "katanga", "lualaba", "kolwezi", "lubumbashi"
        ],
        "es": [
            "república democrática del congo", "rdc", "congo",
            "katanga", "lualaba", "kolwezi", "lubumbashi",
            "cinturón cuprífero"
        ]
    },

    "GEO-02": {  # Zambia, peso_base: 1.20
        "en": [
            "zambia", "zambian copperbelt", "ndola", "kitwe",
            "chingola", "mufulira", "chambishi", "nchanga",
            "konkola", "lumwana", "first quantum zambia",
            "mopani copper mines", "vedanta zambia"
        ],
        "fr": [
            "zambie", "ceinture cuivrière zambienne", "ndola", "kitwe"
        ],
        "pt": ["zâmbia", "copperbelt zambiano"],
        "es": ["zambia", "copperbelt zambiano", "ndola", "kitwe"]
    },

    "GEO-03": {  # Rutas tránsito África Oriental, peso_base: 1.40
        "en": [
            "tanzania", "dar es salaam", "dar-es-salaam",
            "tanzania port", "tpa", "tanzania ports authority",
            "central corridor", "tazara", "tazara railway",
            "mozambique", "beira", "beira corridor", "nacala",
            "nacala corridor", "mozambique port", "cfm",
            "porto de beira", "porto de nacala",
            "northern corridor", "mombasa", "kenya",
            "east african corridor", "east africa transit"
        ],
        "fr": [
            "tanzanie", "dar es salaam", "corridor central",
            "mozambique", "beira", "corridor de beira",
            "corridor nord", "mombasa", "afrique orientale"
        ],
        "pt": [
            "tanzânia", "dar es salaam", "corredor central",
            "moçambique", "beira", "corredor da beira",
            "nacala", "corredor de nacala", "porto de beira"
        ],
        "es": [
            "tanzania", "dar es salaam", "corredor central",
            "mozambique", "beira", "corredor de beira",
            "nacala", "corredor de nacala", "africa oriental"
        ]
    },

    "GEO-04": {  # Rutas tránsito África Austral, peso_base: 1.30
        "en": [
            "south africa", "durban", "port of durban",
            "transnet", "transnet freight rail", "south african port",
            "zimbabwe", "zimbabwean border", "beitbridge",
            "southern african corridor", "southern corridor",
            "botswana", "maputo corridor", "maputo port",
            "richards bay"
        ],
        "fr": [
            "afrique du sud", "durban", "port de durban",
            "transnet", "zimbabwe", "corridor sud",
            "corridor du maputo", "port de maputo"
        ],
        "pt": [
            "áfrica do sul", "durban", "porto de durban",
            "transnet", "zimbabwe", "corredor sul",
            "corredor de maputo", "porto de maputo"
        ],
        "es": [
            "sudáfrica", "durban", "puerto de durban",
            "transnet", "zimbabue", "corredor sur",
            "corredor de maputo", "puerto de maputo"
        ]
    },

    "GEO-05": {  # Australia, peso_base: 0.90
        "en": [
            "australia", "western australia", "wa cobalt",
            "murrin murrin", "nickel west", "cleantech lithium australia",
            "cobalt blue holdings", "australian cobalt",
            "queensland cobalt"
        ],
        "fr": ["australie", "australie occidentale"],
        "pt": ["austrália", "austrália ocidental"],
        "es": ["australia", "australia occidental"]
    },

    "GEO-06": {  # Filipinas, peso_base: 0.80
        "en": [
            "philippines", "palawan", "rio tuba", "coral bay",
            "taganito", "philippine nickel", "philippine cobalt",
            "mindanao mining"
        ],
        "fr": ["philippines", "palawan"],
        "pt": ["filipinas", "palawan"],
        "es": ["filipinas", "palawan", "río tuba"]
    },

    "GEO-07": {  # Refinación China, peso_base: 1.60
        "en": [
            "china cobalt refining", "chinese cobalt", "cmoc china",
            "zhejiang cobalt", "guangdong cobalt", "huayou cobalt",
            "gem co", "ganzhou cobalt", "jiangxi cobalt",
            "chinese battery supply chain", "china battery metals",
            "china export restriction", "china export ban",
            "rare earth china", "critical minerals china",
            "china environmental shutdown", "china power cut",
            "china energy rationing"
        ],
        "fr": [
            "chine cobalt", "raffinage chinois", "huayou cobalt",
            "restriction export chine", "interdiction export chine",
            "coupure d'énergie chine", "rationnement énergétique chine"
        ],
        "pt": [
            "china cobalto", "refinação china", "huayou cobalt",
            "restrição exportação china", "corte energia china"
        ],
        "es": [
            "china cobalto", "refinación china", "huayou cobalt",
            "restricción exportación china", "corte energético china",
            "racionamiento energético china"
        ]
    },

    "GEO-08": {  # Puertos de exportación primarios, peso_base: 1.50
        "en": [
            "port of durban", "durban port", "durban harbour",
            "dar es salaam port", "tpa port", "port of dar es salaam",
            "beira port", "porto de beira", "port of beira",
            "nacala port", "port of nacala",
            "mombasa port", "port of mombasa",
            "lobito corridor", "lobito port", "angola port",
            "benguela railway", "lobito atlantic terminal"
        ],
        "fr": [
            "port de durban", "port de dar es salaam",
            "port de beira", "port de nacala", "port de mombasa",
            "corridor de lobito", "terminal atlantique lobito"
        ],
        "pt": [
            "porto de durban", "porto de dar es salaam",
            "porto de beira", "porto de nacala", "porto de mombaça",
            "corredor do lobito", "porto do lobito",
            "caminho de ferro de benguela"
        ],
        "es": [
            "puerto de durban", "puerto de dar es salaam",
            "puerto de beira", "puerto de nacala", "puerto de mombasa",
            "corredor de lobito", "puerto de lobito",
            "ferrocarril de benguela"
        ]
    },

    "GEO-09": {  # Chile/Argentina — cobalto marginal, peso_base: 0.40
        "en": [
            "chile cobalt", "argentina cobalt", "latin america cobalt",
            "atacama cobalt", "codelco cobalt byproduct"
        ],
        "fr": ["chili cobalt", "argentine cobalt"],
        "pt": ["chile cobalto", "argentina cobalto"],
        "es": [
            "chile cobalto", "argentina cobalto",
            "cobalto atacama", "subproducto cobalto codelco"
        ]
    }
}
```

---

## BLOQUE 2 — EMPRESAS CRÍTICAS

Términos de empresas mineras, refinadoras y traders. Puntúan SOLO si aparecen junto a términos de evento de los Bloques 3-8. `requires_context: false` — su sola mención en contexto de disrupción activa el scoring.

```python
COMPANY_TERMS = {

    # PRODUCTORES PRIMARIOS DRC (peso_empresa: 1.70)
    "tier1_drc": [
        # Glencore — mayor productor mundial de cobalto
        "glencore", "glencore cobalt", "glencore katanga",
        "kamoto copper company", "kcc", "mutanda mining",
        "glencore lualaba",

        # CMOC (China Molybdenum) — segundo mayor productor
        "cmoc", "china molybdenum", "tenke fungurume mining",
        "tfm", "cmoc drc", "kisanfu",

        # Eurasian Resources Group
        "erg", "eurasian resources", "boss mining",
        "metalkol", "rtr cobalt",

        # Ivanhoe Mines
        "ivanhoe mines", "kamoa-kakula", "western foreland",

        # Altres
        "chemaf", "chemaf sarl", "shalina resources",
        "gecamines", "gécamines",  # empresa estatal DRC
        "sok", "société des mines de kabolela"
    ],

    # REFINADORES CHINOS (peso_empresa: 1.60)
    "tier1_china_refining": [
        "huayou cobalt", "huayou", "zhejiang huayou",
        "gem co", "gem co ltd", "greenmaterials",
        "ganfeng lithium",  # también refina cobalto
        "zoomwe zhejiang", "brunp", "brunp recycling",
        "cngr advanced material", "cngr",
        "freeport cobalt",  # refinería en Finlandia, supply chain china
        "umicore",  # refinería belga, suministro DRC
        "freeport mcmoran cobalt"
    ],

    # PRODUCTORES SECUNDARIOS (peso_empresa: 1.10)
    "tier2_producers": [
        # Australia
        "cobalt blue holdings", "cbh resources",
        "first cobalt", "jervois global", "jervois mining",
        "australian cobalt", "clean teq",

        # Filipinas
        "coral bay nickel", "taganito mining",
        "rio tuba nickel mining",

        # Canadá
        "vale canada", "vale sudbury",  # cobalto como subproducto níquel
        "glencore sudbury",

        # Zambia
        "first quantum minerals", "fqm",
        "mopani copper mines", "vedanta zambia",
        "konkola copper mines", "kcm"
    ],

    # TRADERS Y COMERCIALIZADORES (peso_empresa: 1.30)
    "traders": [
        "traxys", "traxys cobalt",
        "darton commodities",
        "cobalt 27", "nickel 28",  # royalty/streaming
        "trafigura cobalt", "trafigura",
        "mercuria", "vitol metals",
        "gerald metals"
    ],

    # USUARIOS FINALES CRÍTICOS (peso_empresa: 0.90 — señal de demanda)
    "end_users": [
        # Fabricantes de baterías
        "catl", "contemporary amperex",
        "lg energy solution", "lges",
        "samsung sdi",
        "panasonic energy", "panasonic battery",
        "sk on", "sk innovation",
        "byd battery", "byd",
        "northvolt",
        "svolt energy",

        # Fabricantes de vehículos eléctricos
        "tesla battery supply", "tesla cobalt",
        "volkswagen cobalt", "vw battery supply",
        "ford cobalt", "gm cobalt",
        "stellantis battery supply",

        # Electrónica
        "apple cobalt supply", "samsung cobalt supply"
    ],

    # EMPRESAS DE LOGÍSTICA CRÍTICA (peso_empresa: 1.40)
    "logistics_companies": [
        # Transnet — operador portuario y ferroviario Sudáfrica
        "transnet", "transnet port terminals",
        "transnet freight rail", "transnet national ports",

        # Tanzania Ports Authority
        "tanzania ports authority", "tpa",
        "tanzania railway", "trl",

        # CFM Mozambique
        "cfm", "portos e caminhos de ferro de mocambique",
        "cfm mozambique",

        # Benguela Railway — corredor Lobito
        "benguela railway", "cfl", "caminho de ferro de benguela",
        "lobito atlantic terminal", "lat",

        # Navieras relevantes para ruta africana
        "msc cobalt", "maersk africa", "cma cgm africa",
        "hapag-lloyd africa"
    ]
}
```

---

## BLOQUE 3 — KEYWORDS DE EVENTOS LOGÍSTICOS (LOG)

```python
LOGISTICS_KEYWORDS = [

    # LOG-PORT: Congestión, cierre o huelga portuaria (weight: 3.5-4.5)
    {"term": "port closure", "lang": "en", "category": "LOG-PORT", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08", "GEO-03", "GEO-04"], "notes": "Verificar que es cierre, no cierre programado por mantenimiento"},
    {"term": "port congestion", "lang": "en", "category": "LOG-PORT", "weight": 3.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08"], "notes": "Falso positivo frecuente: congestión estacional sin impacto en commodities"},
    {"term": "port strike", "lang": "en", "category": "LOG-PORT", "weight": 4.2, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08"], "notes": ""},
    {"term": "dock workers strike", "lang": "en", "category": "LOG-PORT", "weight": 4.2, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08"], "notes": ""},
    {"term": "stevedores strike", "lang": "en", "category": "LOG-PORT", "weight": 4.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08"], "notes": ""},
    {"term": "port backlog", "lang": "en", "category": "LOG-PORT", "weight": 3.2, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-08"], "notes": "Solo relevante si hay ancla mineral cerca"},
    {"term": "vessel queuing", "lang": "en", "category": "LOG-PORT", "weight": 3.0, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-08"], "notes": ""},
    {"term": "port shutdown", "lang": "en", "category": "LOG-PORT", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08"], "notes": ""},
    {"term": "terminal closure", "lang": "en", "category": "LOG-PORT", "weight": 4.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08"], "notes": ""},
    {"term": "fermeture du port", "lang": "fr", "category": "LOG-PORT", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08"], "notes": ""},
    {"term": "grève portuaire", "lang": "fr", "category": "LOG-PORT", "weight": 4.2, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08"], "notes": ""},
    {"term": "congestion portuaire", "lang": "fr", "category": "LOG-PORT", "weight": 3.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08"], "notes": ""},
    {"term": "bloqueio portuário", "lang": "pt", "category": "LOG-PORT", "weight": 4.2, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08"], "notes": ""},
    {"term": "encerramento do porto", "lang": "pt", "category": "LOG-PORT", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08"], "notes": ""},
    {"term": "greve portuária", "lang": "pt", "category": "LOG-PORT", "weight": 4.2, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08"], "notes": ""},
    {"term": "cierre portuario", "lang": "es", "category": "LOG-PORT", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08"], "notes": ""},
    {"term": "huelga portuaria", "lang": "es", "category": "LOG-PORT", "weight": 4.2, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08"], "notes": ""},
    {"term": "congestión portuaria", "lang": "es", "category": "LOG-PORT", "weight": 3.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-08"], "notes": ""},

    # LOG-RAIL: Interrupción ferroviaria (weight: 3.0-4.0)
    {"term": "railway disruption", "lang": "en", "category": "LOG-RAIL", "weight": 3.8, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-03", "GEO-04", "GEO-08"], "notes": "Corredores críticos: TAZARA, Benguela, Transnet Freight Rail"},
    {"term": "rail shutdown", "lang": "en", "category": "LOG-RAIL", "weight": 4.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-03", "GEO-04"], "notes": ""},
    {"term": "freight rail suspension", "lang": "en", "category": "LOG-RAIL", "weight": 3.8, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-04"], "notes": "Transnet Freight Rail es crítico para Durban"},
    {"term": "rail sabotage", "lang": "en", "category": "LOG-RAIL", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-04"], "notes": "Sudáfrica tiene historial de sabotajes a Transnet"},
    {"term": "cable theft railway", "lang": "en", "category": "LOG-RAIL", "weight": 3.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-04"], "notes": "Problema recurrente en Sudáfrica, impacto real en Transnet"},
    {"term": "derailment", "lang": "en", "category": "LOG-RAIL", "weight": 3.2, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-03", "GEO-04"], "notes": "Solo relevante en corredores críticos"},
    {"term": "perturbation ferroviaire", "lang": "fr", "category": "LOG-RAIL", "weight": 3.8, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-03", "GEO-04"], "notes": ""},
    {"term": "interruption du chemin de fer", "lang": "fr", "category": "LOG-RAIL", "weight": 4.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-03", "GEO-04"], "notes": ""},
    {"term": "sabotagem ferroviária", "lang": "pt", "category": "LOG-RAIL", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-04"], "notes": ""},
    {"term": "interrupção ferroviária", "lang": "pt", "category": "LOG-RAIL", "weight": 3.8, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-03", "GEO-04"], "notes": ""},
    {"term": "interrupción ferroviaria", "lang": "es", "category": "LOG-RAIL", "weight": 3.8, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-03", "GEO-04"], "notes": ""},
    {"term": "sabotaje ferroviario", "lang": "es", "category": "LOG-RAIL", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-04"], "notes": ""},

    # LOG-ROAD: Bloqueo de carreteras (weight: 2.5-3.5)
    {"term": "road blockade", "lang": "en", "category": "LOG-ROAD", "weight": 3.2, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03"], "notes": ""},
    {"term": "border crossing closed", "lang": "en", "category": "LOG-ROAD", "weight": 3.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03", "GEO-04"], "notes": "Cruces críticos: Kasumbalesa (DRC-Zambia), Beitbridge (ZA-Zimbabwe)"},
    {"term": "border blockage", "lang": "en", "category": "LOG-ROAD", "weight": 3.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "kasumbalesa", "lang": "en", "category": "LOG-ROAD", "weight": 4.0, "requires_context": False, "context_window": 100, "geographic_boost": ["GEO-01", "GEO-02"], "notes": "Principal cruce DRC-Zambia para minerales. Sola mención en contexto negativo es señal fuerte"},
    {"term": "beitbridge closure", "lang": "en", "category": "LOG-ROAD", "weight": 3.8, "requires_context": False, "context_window": 80, "geographic_boost": ["GEO-04"], "notes": "Cruce crítico ZA-Zimbabwe para corredor sur"},
    {"term": "truckers strike", "lang": "en", "category": "LOG-ROAD", "weight": 3.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03", "GEO-04"], "notes": ""},
    {"term": "blocage routier", "lang": "fr", "category": "LOG-ROAD", "weight": 3.2, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "frontière fermée", "lang": "fr", "category": "LOG-ROAD", "weight": 3.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "bloqueio rodoviário", "lang": "pt", "category": "LOG-ROAD", "weight": 3.2, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-03", "GEO-04"], "notes": ""},
    {"term": "fronteira fechada", "lang": "pt", "category": "LOG-ROAD", "weight": 3.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-03", "GEO-04"], "notes": ""},
    {"term": "bloqueo de carretera", "lang": "es", "category": "LOG-ROAD", "weight": 3.2, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "frontera cerrada", "lang": "es", "category": "LOG-ROAD", "weight": 3.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},

    # LOG-CUSTOMS: Aduanas y regulación de exportación (weight: 3.0-4.0)
    {"term": "customs delay", "lang": "en", "category": "LOG-CUSTOMS", "weight": 3.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02", "GEO-08"], "notes": ""},
    {"term": "export permit suspended", "lang": "en", "category": "LOG-CUSTOMS", "weight": 4.0, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02", "GEO-07"], "notes": ""},
    {"term": "export documentation", "lang": "en", "category": "LOG-CUSTOMS", "weight": 2.5, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": "Bajo peso solo — señal débil"},
    {"term": "mineral export freeze", "lang": "en", "category": "LOG-CUSTOMS", "weight": 4.2, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02", "GEO-07"], "notes": ""},
    {"term": "retard douanier", "lang": "fr", "category": "LOG-CUSTOMS", "weight": 3.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "suspension permis exportation", "lang": "fr", "category": "LOG-CUSTOMS", "weight": 4.0, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "atraso alfandegário", "lang": "pt", "category": "LOG-CUSTOMS", "weight": 3.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-03", "GEO-04"], "notes": ""},
    {"term": "retraso aduanero", "lang": "es", "category": "LOG-CUSTOMS", "weight": 3.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "permiso de exportación suspendido", "lang": "es", "category": "LOG-CUSTOMS", "weight": 4.0, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01"], "notes": ""},

    # LOG-VESSEL: Flete marítimo (weight: 2.5-3.5)
    {"term": "shipping delay", "lang": "en", "category": "LOG-VESSEL", "weight": 2.8, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-08"], "notes": "Solo relevante si hay contexto mineral"},
    {"term": "freight rates surge", "lang": "en", "category": "LOG-VESSEL", "weight": 2.5, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": "Solo score en SMC — efecto en semanas, no días"},
    {"term": "vessel shortage", "lang": "en", "category": "LOG-VESSEL", "weight": 3.0, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "bulk carrier shortage", "lang": "en", "category": "LOG-VESSEL", "weight": 3.2, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": "El cobalto se transporta en bulk o contenedores, dependiendo del procesamiento"}
]
```

---

## BLOQUE 4 — KEYWORDS DE EVENTOS GEOPOLÍTICOS (GEO)

```python
GEOPOLITICAL_KEYWORDS = [

    # GEO-CONFLICT: Conflicto armado (weight: 4.0-5.0)
    {"term": "armed conflict", "lang": "en", "category": "GEO-CONFLICT", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02"], "notes": "GEO-03 eliminado: conflictos en Tanzania/Mozambique no suelen afectar zona minera de cobalt"},
    {"term": "militia attack", "lang": "en", "category": "GEO-CONFLICT", "weight": 4.8, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01"], "notes": "DRC tiene >120 grupos armados activos en zona minera"},
    {"term": "rebel attack", "lang": "en", "category": "GEO-CONFLICT", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-03"], "notes": ""},
    {"term": "m23", "lang": "en", "category": "GEO-CONFLICT", "weight": 4.0, "requires_context": True, "context_window": 100, "geographic_boost": ["GEO-01"], "notes": "Grupo armado activo en DRC oriental (Kivu Norte, no Katanga). requires_context evita sobrevaluación en zona no minera"},
    {"term": "mai-mai", "lang": "en", "category": "GEO-CONFLICT", "weight": 3.8, "requires_context": False, "context_window": 80, "geographic_boost": ["GEO-01"], "notes": "Milicias Mai-Mai activas en Katanga"},
    {"term": "mine attack", "lang": "en", "category": "GEO-CONFLICT", "weight": 5.0, "requires_context": False, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02"], "notes": "Ataque directo a infraestructura minera — máxima señal"},
    {"term": "security incident mine", "lang": "en", "category": "GEO-CONFLICT", "weight": 4.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "operations suspended security", "lang": "en", "category": "GEO-CONFLICT", "weight": 4.5, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "conflit armé", "lang": "fr", "category": "GEO-CONFLICT", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "attaque de milice", "lang": "fr", "category": "GEO-CONFLICT", "weight": 4.8, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "attaque rebelle", "lang": "fr", "category": "GEO-CONFLICT", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "conflit armado", "lang": "pt", "category": "GEO-CONFLICT", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "ataque de milícia", "lang": "pt", "category": "GEO-CONFLICT", "weight": 4.8, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "conflicto armado", "lang": "es", "category": "GEO-CONFLICT", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "ataque a mina", "lang": "es", "category": "GEO-CONFLICT", "weight": 5.0, "requires_context": False, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},

    # GEO-COUP: Golpe de estado (weight: 4.0-5.0)
    {"term": "coup", "lang": "en", "category": "GEO-COUP", "weight": 4.5, "requires_context": True, "context_window": 40, "geographic_boost": ["GEO-01", "GEO-02"], "notes": "requires_context=True + COUP_CONTEXT_TERMS check en ±40 palabras. geo_boost limitado a zonas mineras"},
    {"term": "military takeover", "lang": "en", "category": "GEO-COUP", "weight": 5.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03", "GEO-04"], "notes": ""},
    {"term": "government overthrown", "lang": "en", "category": "GEO-COUP", "weight": 5.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03", "GEO-04"], "notes": ""},
    {"term": "state of emergency", "lang": "en", "category": "GEO-COUP", "weight": 4.0, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03", "GEO-04"], "notes": "requires_context=True para filtrar emergencias por desastre natural sin relación con cobalt"},
    {"term": "coup d'état", "lang": "fr", "category": "GEO-COUP", "weight": 5.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03", "GEO-04"], "notes": ""},
    {"term": "prise de pouvoir militaire", "lang": "fr", "category": "GEO-COUP", "weight": 5.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "état d'urgence", "lang": "fr", "category": "GEO-COUP", "weight": 4.0, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "golpe de estado", "lang": "es", "category": "GEO-COUP", "weight": 5.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03", "GEO-04"], "notes": ""},
    {"term": "golpe militar", "lang": "pt", "category": "GEO-COUP", "weight": 5.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03", "GEO-04"], "notes": ""},
    {"term": "estado de emergência", "lang": "pt", "category": "GEO-COUP", "weight": 4.0, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-03", "GEO-04"], "notes": ""},
    {"term": "estado de emergencia", "lang": "es", "category": "GEO-COUP", "weight": 4.0, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03", "GEO-04"], "notes": "Bug fix: entrada única (estaba duplicada en código anterior)"},

    # GEO-SANCTION: Sanciones (weight: 3.5-4.5)
    {"term": "sanctions", "lang": "en", "category": "GEO-SANCTION", "weight": 3.8, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02", "GEO-07"], "notes": "Muy común — solo puntúa con ancla mineral o geografía crítica"},
    {"term": "trade embargo", "lang": "en", "category": "GEO-SANCTION", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-07"], "notes": ""},
    {"term": "asset freeze", "lang": "en", "category": "GEO-SANCTION", "weight": 4.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-07"], "notes": "Solo relevante si afecta empresa minera o trader de cobalto"},
    {"term": "ofac sanctions", "lang": "en", "category": "GEO-SANCTION", "weight": 4.2, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-07"], "notes": "OFAC sanciones de EE.UU. — muy relevante para empresas chinas"},
    {"term": "sanctions commerciales", "lang": "fr", "category": "GEO-SANCTION", "weight": 3.8, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "embargo comercial", "lang": "es", "category": "GEO-SANCTION", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-07"], "notes": ""},
    {"term": "sanções comerciais", "lang": "pt", "category": "GEO-SANCTION", "weight": 3.8, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-07"], "notes": ""},

    # GEO-PROTEST: Protestas (weight: 2.0-3.0)
    {"term": "protests", "lang": "en", "category": "GEO-PROTEST", "weight": 2.2, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02", "GEO-08"], "notes": "Peso bajo — solo señal si hay contexto mineral o logístico"},
    {"term": "civil unrest", "lang": "en", "category": "GEO-PROTEST", "weight": 2.8, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": "Cambiado a requires_context=True: consistencia con 'protests'; Sudáfrica tiene unrest frecuente no relacionado con cobalt"},
    {"term": "demonstrations", "lang": "en", "category": "GEO-PROTEST", "weight": 2.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "manifestations", "lang": "fr", "category": "GEO-PROTEST", "weight": 2.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "troubles civils", "lang": "fr", "category": "GEO-PROTEST", "weight": 2.8, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "protestos", "lang": "pt", "category": "GEO-PROTEST", "weight": 2.2, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-03", "GEO-04"], "notes": ""},
    {"term": "protestas", "lang": "es", "category": "GEO-PROTEST", "weight": 2.2, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""}
]
```

---

## BLOQUE 5 — KEYWORDS DE EVENTOS LABORALES (LAB)

```python
LABOR_KEYWORDS = [

    # LAB-STRIKE-ACT: Huelga activa confirmada (weight: 4.0-5.0)
    {"term": "strike", "lang": "en", "category": "LAB-STRIKE-ACT", "weight": 4.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02", "GEO-08"], "notes": "Muy común — requires_context obligatorio para evitar noticias de otros sectores"},
    {"term": "workers on strike", "lang": "en", "category": "LAB-STRIKE-ACT", "weight": 4.5, "requires_context": False, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02", "GEO-08"], "notes": ""},
    {"term": "mining strike", "lang": "en", "category": "LAB-STRIKE-ACT", "weight": 4.8, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02"], "notes": "Término específico — alta señal"},
    {"term": "walkout", "lang": "en", "category": "LAB-STRIKE-ACT", "weight": 4.2, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02", "GEO-08"], "notes": ""},
    {"term": "work stoppage", "lang": "en", "category": "LAB-STRIKE-ACT", "weight": 4.2, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02", "GEO-08"], "notes": ""},
    {"term": "production halted", "lang": "en", "category": "LAB-STRIKE-ACT", "weight": 4.5, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "operations suspended", "lang": "en", "category": "LAB-STRIKE-ACT", "weight": 4.3, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "grève", "lang": "fr", "category": "LAB-STRIKE-ACT", "weight": 4.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-08"], "notes": ""},
    {"term": "grève minière", "lang": "fr", "category": "LAB-STRIKE-ACT", "weight": 4.8, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "arrêt de travail", "lang": "fr", "category": "LAB-STRIKE-ACT", "weight": 4.2, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-08"], "notes": ""},
    {"term": "production suspendue", "lang": "fr", "category": "LAB-STRIKE-ACT", "weight": 4.5, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "greve", "lang": "pt", "category": "LAB-STRIKE-ACT", "weight": 4.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-03", "GEO-04", "GEO-08"], "notes": ""},
    {"term": "greve mineira", "lang": "pt", "category": "LAB-STRIKE-ACT", "weight": 4.8, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-02"], "notes": ""},
    {"term": "paralisação", "lang": "pt", "category": "LAB-STRIKE-ACT", "weight": 4.2, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-03", "GEO-04"], "notes": ""},
    {"term": "huelga", "lang": "es", "category": "LAB-STRIKE-ACT", "weight": 4.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02", "GEO-08"], "notes": ""},
    {"term": "huelga minera", "lang": "es", "category": "LAB-STRIKE-ACT", "weight": 4.8, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "paro laboral", "lang": "es", "category": "LAB-STRIKE-ACT", "weight": 4.2, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},

    # Kiswahili (DRC Oriental, Tanzania) — cobertura inicial
    {"term": "mgomo", "lang": "sw", "category": "LAB-STRIKE-ACT", "weight": 3.5, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03"], "notes": "Swahili: 'huelga'. requires_context filtra usos no relacionados con minería"},
    {"term": "mgomo wa wachimbaji", "lang": "sw", "category": "LAB-STRIKE-ACT", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02"], "notes": "Swahili: 'huelga de mineros'. Término compuesto, alta especificidad"},
    {"term": "mgodi kufungwa", "lang": "sw", "category": "LAB-STRIKE-ACT", "weight": 4.0, "requires_context": False, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": "Swahili: 'mina cerrada'"},
    {"term": "bandari kufungwa", "lang": "sw", "category": "LOG-PORT", "weight": 4.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-03", "GEO-08"], "notes": "Swahili: 'puerto cerrado'. Relevante para Dar es Salaam (TPA)"},

    # LAB-STRIKE-THR: Amenaza de huelga (weight: 2.5-3.5)
    {"term": "strike threat", "lang": "en", "category": "LAB-STRIKE-THR", "weight": 3.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02", "GEO-08"], "notes": ""},
    {"term": "strike notice", "lang": "en", "category": "LAB-STRIKE-THR", "weight": 3.5, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02", "GEO-08"], "notes": "Notice legal en muchos países implica fecha definida — más grave que amenaza genérica"},
    {"term": "workers threaten", "lang": "en", "category": "LAB-STRIKE-THR", "weight": 2.8, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "menace de grève", "lang": "fr", "category": "LAB-STRIKE-THR", "weight": 3.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-08"], "notes": ""},
    {"term": "préavis de grève", "lang": "fr", "category": "LAB-STRIKE-THR", "weight": 3.5, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": "Préavis = aviso legal formal — peso mayor"},
    {"term": "ameaça de greve", "lang": "pt", "category": "LAB-STRIKE-THR", "weight": 3.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-03", "GEO-04"], "notes": ""},
    {"term": "amenaza de huelga", "lang": "es", "category": "LAB-STRIKE-THR", "weight": 3.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},

    # LAB-ACCIDENT: Accidentes graves (weight: 3.5-5.0)
    {"term": "mine collapse", "lang": "en", "category": "LAB-ACCIDENT", "weight": 5.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02"], "notes": "Colapso de mina = paralización inmediata y prolongada"},
    {"term": "artisanal mine collapse", "lang": "en", "category": "LAB-ACCIDENT", "weight": 4.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01"], "notes": "DRC tiene alta proporción de minería artesanal (ASM). Colapsos frecuentes en Kolwezi"},
    {"term": "flooding mine", "lang": "en", "category": "LAB-ACCIDENT", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "mine explosion", "lang": "en", "category": "LAB-ACCIDENT", "weight": 4.8, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "mining accident", "lang": "en", "category": "LAB-ACCIDENT", "weight": 3.8, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "effondrement de mine", "lang": "fr", "category": "LAB-ACCIDENT", "weight": 5.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "inondation de mine", "lang": "fr", "category": "LAB-ACCIDENT", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "acidente de mineração", "lang": "pt", "category": "LAB-ACCIDENT", "weight": 3.8, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-02", "GEO-03"], "notes": ""},
    {"term": "colapso de mina", "lang": "es", "category": "LAB-ACCIDENT", "weight": 5.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "accidente minero", "lang": "es", "category": "LAB-ACCIDENT", "weight": 3.8, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},

    # LAB-ASM: Minería Artesanal / Small-Scale Mining (ASM produce ~20-25% cobalt DRC)
    {"term": "creuseurs", "lang": "fr", "category": "LAB-ACCIDENT", "weight": 3.0, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01"], "notes": "Término local DRC para mineros artesanales. Solo puntúa en contexto de accidente/bloqueo"},
    {"term": "mineurs artisanaux", "lang": "fr", "category": "LAB-ACCIDENT", "weight": 2.8, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "informal cobalt mining", "lang": "en", "category": "LAB-ACCIDENT", "weight": 2.8, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "artisanal mining ban", "lang": "en", "category": "REG-LICENSE", "weight": 4.0, "requires_context": False, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": "Prohibiciones gubernamentales de ASM son frecuentes en DRC — impacto inmediato en ~25% producción"},
    {"term": "asm suspension", "lang": "en", "category": "REG-LICENSE", "weight": 3.8, "requires_context": False, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "suspension exploitation artisanale", "lang": "fr", "category": "REG-LICENSE", "weight": 4.0, "requires_context": False, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "interdiction exploitation artisanale", "lang": "fr", "category": "REG-LICENSE", "weight": 4.2, "requires_context": False, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "mineria artesanal prohibida", "lang": "es", "category": "REG-LICENSE", "weight": 4.0, "requires_context": False, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": ""}
]
```

---

## BLOQUE 6 — KEYWORDS REGULATORIOS (REG)

```python
REGULATORY_KEYWORDS = [

    # REG-EXPORT-BAN: Prohibición de exportación (weight: 4.5-5.0)
    {"term": "export ban", "lang": "en", "category": "REG-EXPORT-BAN", "weight": 5.0, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02", "GEO-07"], "notes": "Señal máxima si afecta cobalto. Precedente: Indonesia níquel 2020, DRC posible"},
    {"term": "export restriction", "lang": "en", "category": "REG-EXPORT-BAN", "weight": 4.5, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02", "GEO-07"], "notes": ""},
    {"term": "export quota", "lang": "en", "category": "REG-EXPORT-BAN", "weight": 4.0, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-07"], "notes": "China usa cuotas como herramienta de política mineral"},
    {"term": "raw mineral export ban", "lang": "en", "category": "REG-EXPORT-BAN", "weight": 5.0, "requires_context": False, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02"], "notes": "DRC tiene presión política para procesar localmente antes de exportar"},
    {"term": "interdiction d'exportation", "lang": "fr", "category": "REG-EXPORT-BAN", "weight": 5.0, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "restriction à l'exportation", "lang": "fr", "category": "REG-EXPORT-BAN", "weight": 4.5, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "proibição de exportação", "lang": "pt", "category": "REG-EXPORT-BAN", "weight": 5.0, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-02", "GEO-03"], "notes": ""},
    {"term": "prohibición de exportación", "lang": "es", "category": "REG-EXPORT-BAN", "weight": 5.0, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "veda exportación mineral", "lang": "es", "category": "REG-EXPORT-BAN", "weight": 5.0, "requires_context": False, "context_window": 80, "geographic_boost": ["GEO-01"], "notes": ""},

    # REG-TAX: Nuevos impuestos y royalties (weight: 3.0-4.0)
    {"term": "windfall tax", "lang": "en", "category": "REG-TAX", "weight": 3.5, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02"], "notes": "DRC implementó 'taxe sur les super-profits' en 2022"},
    {"term": "mining royalty increase", "lang": "en", "category": "REG-TAX", "weight": 3.8, "requires_context": False, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "super profits tax", "lang": "en", "category": "REG-TAX", "weight": 3.5, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "taxe sur les super-profits", "lang": "fr", "category": "REG-TAX", "weight": 3.8, "requires_context": False, "context_window": 80, "geographic_boost": ["GEO-01"], "notes": "Término específico DRC — alta señal si aparece"},
    {"term": "redevance minière", "lang": "fr", "category": "REG-TAX", "weight": 3.8, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "royalty minerário", "lang": "pt", "category": "REG-TAX", "weight": 3.8, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-02"], "notes": ""},
    {"term": "impuesto minero", "lang": "es", "category": "REG-TAX", "weight": 3.5, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},

    # REG-LICENSE: Suspensión de licencias (weight: 3.5-4.5)
    {"term": "mining license suspended", "lang": "en", "category": "REG-LICENSE", "weight": 4.5, "requires_context": False, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "license revoked", "lang": "en", "category": "REG-LICENSE", "weight": 4.5, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "permit cancelled", "lang": "en", "category": "REG-LICENSE", "weight": 4.0, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "licence minière suspendue", "lang": "fr", "category": "REG-LICENSE", "weight": 4.5, "requires_context": False, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "licença mineira suspensa", "lang": "pt", "category": "REG-LICENSE", "weight": 4.5, "requires_context": False, "context_window": 60, "geographic_boost": ["GEO-02"], "notes": ""},
    {"term": "licencia minera suspendida", "lang": "es", "category": "REG-LICENSE", "weight": 4.5, "requires_context": False, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},

    # REG-NATIONAL: Nacionalización (weight: 4.0-5.0)
    {"term": "nationalization", "lang": "en", "category": "REG-NATIONAL", "weight": 4.8, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02"], "notes": "Riesgo latente en DRC y Zambia con gobiernos actuales"},
    {"term": "nationalisation", "lang": "fr", "category": "REG-NATIONAL", "weight": 4.8, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "nationalização", "lang": "pt", "category": "REG-NATIONAL", "weight": 4.8, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-02"], "notes": ""},
    {"term": "nacionalización", "lang": "es", "category": "REG-NATIONAL", "weight": 4.8, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""}
]
```

---

## BLOQUE 7 — KEYWORDS CLIMÁTICOS / FUERZA MAYOR (FMA)

```python
CLIMATE_KEYWORDS = [
    {"term": "flooding", "lang": "en", "category": "FMA-FLOOD", "weight": 3.5, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03", "GEO-04"], "notes": "Estación de lluvias DRC: octubre-mayo. Pico de riesgo: enero-marzo"},
    {"term": "flash flood", "lang": "en", "category": "FMA-FLOOD", "weight": 4.0, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03"], "notes": ""},
    {"term": "road washed out", "lang": "en", "category": "FMA-FLOOD", "weight": 4.2, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03"], "notes": ""},
    {"term": "cyclone", "lang": "en", "category": "FMA-FLOOD", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-03", "GEO-04"], "notes": "Mozambique tiene alta exposición a ciclones (Idai 2019 afectó corredor Beira)"},
    {"term": "power outage", "lang": "en", "category": "FMA-DROUGHT", "weight": 3.8, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": "En DRC, corte energético = paralización de plantas de procesamiento"},
    {"term": "load shedding", "lang": "en", "category": "FMA-DROUGHT", "weight": 3.5, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-04"], "notes": "Término sudafricano para cortes programados — frecuente en Eskom/Sudáfrica"},
    {"term": "hydroelectric shortage", "lang": "en", "category": "FMA-DROUGHT", "weight": 4.0, "requires_context": True, "context_window": 80, "geographic_boost": ["GEO-01"], "notes": "Inga dam shortage es señal crítica para DRC"},
    {"term": "inga dam", "lang": "en", "category": "FMA-DROUGHT", "weight": 4.5, "requires_context": False, "context_window": 100, "geographic_boost": ["GEO-01"], "notes": "Represa Inga suministra energía a Katanga. Sola mención en contexto negativo es señal fuerte"},
    {"term": "délestage", "lang": "fr", "category": "FMA-DROUGHT", "weight": 3.5, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": "Término francés para load shedding — muy usado en DRC"},
    {"term": "coupure d'électricité", "lang": "fr", "category": "FMA-DROUGHT", "weight": 3.8, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": ""},
    {"term": "inundação", "lang": "pt", "category": "FMA-FLOOD", "weight": 3.5, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-03", "GEO-04"], "notes": ""},
    {"term": "ciclone", "lang": "pt", "category": "FMA-FLOOD", "weight": 4.5, "requires_context": False, "context_window": 50, "geographic_boost": ["GEO-03"], "notes": ""},
    {"term": "inundación", "lang": "es", "category": "FMA-FLOOD", "weight": 3.5, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03"], "notes": ""},
    {"term": "corte eléctrico", "lang": "es", "category": "FMA-DROUGHT", "weight": 3.8, "requires_context": True, "context_window": 60, "geographic_boost": ["GEO-01"], "notes": ""}
]
```

---

## BLOQUE 8 — KEYWORDS DE DEMANDA (DEM)

```python
DEMAND_KEYWORDS = [
    # DEM-SURGE: Aumento de demanda (suma al score)
    {"term": "gigafactory", "lang": "en", "category": "DEM-SURGE", "weight": 2.5, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": "Solo relevante si hay mención de contratos de suministro de cobalto"},
    {"term": "battery supply contract", "lang": "en", "category": "DEM-SURGE", "weight": 3.0, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "strategic reserve cobalt", "lang": "en", "category": "DEM-SURGE", "weight": 3.5, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": "Acumulación de reservas estratégicas por gobiernos — señal de demanda estructural"},
    {"term": "cobalt stockpile", "lang": "en", "category": "DEM-SURGE", "weight": 3.2, "requires_context": False, "context_window": 60, "geographic_boost": [], "notes": ""},

    # DEM-SUBSTITUTE: Sustitución tecnológica (resta del score — SMC únicamente)
    {"term": "cobalt-free battery", "lang": "en", "category": "DEM-SUBSTITUTE", "weight": -2.5, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": "Solo afecta SMC, no SSC"},
    {"term": "lfp battery", "lang": "en", "category": "DEM-SUBSTITUTE", "weight": -3.0, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": "LFP domina ~65-70% nuevas baterías en China (2025). Peso subido de -2.0 a -3.0"},
    {"term": "lithium iron phosphate", "lang": "en", "category": "DEM-SUBSTITUTE", "weight": -1.5, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": "Forma larga de LFP — peso menor para evitar doble-conteo"},
    {"term": "lmfp battery", "lang": "en", "category": "DEM-SUBSTITUTE", "weight": -2.0, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": "Lithium Manganese Iron Phosphate — siguiente generación post-LFP, mayor densidad energética"},
    {"term": "batterie lfp", "lang": "fr", "category": "DEM-SUBSTITUTE", "weight": -2.0, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "bateria lfp", "lang": "es|pt", "category": "DEM-SUBSTITUTE", "weight": -2.0, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "sodium-ion battery", "lang": "en", "category": "DEM-SUBSTITUTE", "weight": -2.5, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "sodium ion battery", "lang": "en", "category": "DEM-SUBSTITUTE", "weight": -2.5, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": "Variante sin guion"},
    {"term": "solid state battery", "lang": "en", "category": "DEM-SUBSTITUTE", "weight": -1.5, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": "Peso bajo — tecnología no comercializada masivamente aún"},
    {"term": "batterie sans cobalt", "lang": "fr", "category": "DEM-SUBSTITUTE", "weight": -2.5, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "batería sin cobalto", "lang": "es", "category": "DEM-SUBSTITUTE", "weight": -2.5, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "bateria sem cobalto", "lang": "pt", "category": "DEM-SUBSTITUTE", "weight": -2.5, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": ""},

    # DEM-SURGE: Señales de mercado (tensión en oferta — confirman disrupciones físicas)
    {"term": "cobalt supply deficit", "lang": "en", "category": "DEM-SURGE", "weight": 2.5, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": "Señal de confirmación — indica tensión física ya en precio"},
    {"term": "cobalt shortage", "lang": "en", "category": "DEM-SURGE", "weight": 2.8, "requires_context": False, "context_window": 60, "geographic_boost": [], "notes": ""},
    {"term": "cobalt inventory low", "lang": "en", "category": "DEM-SURGE", "weight": 2.5, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": "LME o inventarios globales bajos"},
    {"term": "cobalt price spike", "lang": "en", "category": "DEM-SURGE", "weight": 2.0, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": "Peso bajo — precio es efecto, no causa. Usar como señal de confirmación"},
    {"term": "lme cobalt inventory", "lang": "en", "category": "DEM-SURGE", "weight": 2.2, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "pénurie de cobalt", "lang": "fr", "category": "DEM-SURGE", "weight": 2.8, "requires_context": False, "context_window": 60, "geographic_boost": [], "notes": ""},
    {"term": "déficit de cobalto", "lang": "es", "category": "DEM-SURGE", "weight": 2.5, "requires_context": False, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "escassez de cobalto", "lang": "pt", "category": "DEM-SURGE", "weight": 2.8, "requires_context": False, "context_window": 60, "geographic_boost": [], "notes": ""}
]
```

---

## BLOQUE 9 — KEYWORDS DE RESOLUCIÓN (RES)

Términos que indican resolución de eventos activos. Llevan **peso negativo** — reducen el score total cuando una situación mejora. Solo afectan SSC con peso completo; en SMC se aplica ×0.5 (la tensión estructural puede persistir aunque el evento específico se resuelva).

```python
RESOLUTION_KEYWORDS = [
    # Inglés
    {"term": "strike ended", "lang": "en", "category": "RES-RESOLVE", "weight": -3.0, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "strike called off", "lang": "en", "category": "RES-RESOLVE", "weight": -3.0, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "workers return to work", "lang": "en", "category": "RES-RESOLVE", "weight": -3.0, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "agreement reached", "lang": "en", "category": "RES-RESOLVE", "weight": -2.5, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "operations resumed", "lang": "en", "category": "RES-RESOLVE", "weight": -3.0, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "port reopened", "lang": "en", "category": "RES-RESOLVE", "weight": -3.5, "requires_context": False, "context_window": 60, "geographic_boost": ["GEO-08", "GEO-03", "GEO-04"], "notes": ""},
    {"term": "mine reopened", "lang": "en", "category": "RES-RESOLVE", "weight": -3.0, "requires_context": False, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02"], "notes": ""},
    {"term": "border reopened", "lang": "en", "category": "RES-RESOLVE", "weight": -3.0, "requires_context": False, "context_window": 60, "geographic_boost": ["GEO-01", "GEO-02", "GEO-03", "GEO-04"], "notes": ""},
    # Francés
    {"term": "grève terminée", "lang": "fr", "category": "RES-RESOLVE", "weight": -3.0, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "reprise des opérations", "lang": "fr", "category": "RES-RESOLVE", "weight": -3.0, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "accord conclu", "lang": "fr", "category": "RES-RESOLVE", "weight": -2.5, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": ""},
    # Español
    {"term": "huelga terminada", "lang": "es", "category": "RES-RESOLVE", "weight": -3.0, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "operaciones reanudadas", "lang": "es", "category": "RES-RESOLVE", "weight": -3.0, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "acuerdo alcanzado", "lang": "es", "category": "RES-RESOLVE", "weight": -2.5, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": ""},
    # Portugués
    {"term": "greve encerrada", "lang": "pt", "category": "RES-RESOLVE", "weight": -3.0, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": ""},
    {"term": "operações retomadas", "lang": "pt", "category": "RES-RESOLVE", "weight": -3.0, "requires_context": True, "context_window": 80, "geographic_boost": [], "notes": ""},
]
```

**Nota de implementación:** `CATEGORY_MULTIPLIERS["RES-RESOLVE"] = 1.5`. `SSC_CATEGORY_WEIGHTS["RES-RESOLVE"] = 1.0`. `SMC_CATEGORY_OVERRIDES["RES-RESOLVE"] = 0.5`. La mecánica de peso negativo es la misma que DEM-SUBSTITUTE: `sign = -1 if weight < 0`.

---

## BLOQUE 10 — FALSOS POSITIVOS CONOCIDOS

Lista de términos que activan keywords del diccionario pero NO corresponden a eventos de suministro. El script debe filtrarlos por contexto.

```python
FALSE_POSITIVE_FILTERS = [
    # "strike" en contexto deportivo
    {"pattern": "bowling strike", "filter_category": "LAB-STRIKE-ACT"},
    {"pattern": "lightning strike", "filter_category": "LAB-STRIKE-ACT"},
    {"pattern": "airstrike", "filter_category": "LAB-STRIKE-ACT"},  # excepto si es en zona GEO-01/02

    # "coup" en contexto no político
    {"pattern": "coup de grace", "filter_category": "GEO-COUP"},
    {"pattern": "coup de theatre", "filter_category": "GEO-COUP"},
    {"pattern": "hat trick", "filter_category": "GEO-COUP"},  # irrelevante pero previene ruido

    # "flooding" en contexto financiero
    {"pattern": "market flooding", "filter_category": "FMA-FLOOD"},
    {"pattern": "flooding the market", "filter_category": "FMA-FLOOD"},

    # "sanctions" en contexto deportivo o académico
    {"pattern": "academic sanctions", "filter_category": "GEO-SANCTION"},
    {"pattern": "sports sanctions", "filter_category": "GEO-SANCTION"},

    # "collapse" financiero vs físico
    {"pattern": "market collapse", "filter_category": "LAB-ACCIDENT"},  # collapse financiero no es colapso de mina
    {"pattern": "price collapse", "filter_category": "LAB-ACCIDENT"}
]
```

---

## NOTAS DE MANTENIMIENTO DEL DICCIONARIO

### Adiciones futuras prioritarias
1. Ampliar cobertura Swahili (actualmente solo 4 términos básicos): mgomo wa bandari, hali ya dharura, machafuko, nchi ya dharura
2. Términos de mercado de futuros adicionales: cobalt hydroxide CIF, cobalt sulfate price
3. Términos de corredor Lobito — emergente: tren de Lobito, Lobito rail, TELN corridor
4. Idioma portugués de DRC (Lingala transliterado) — zona norte del Copperbelt

### Versión
```
v1.1 — 2026-05 — Revisión de calibración. 5 idiomas (SW añadido básico).
                  10 bloques (RES-RESOLVE añadido). ~330 términos.
  Cambios: requires_context corregido en 6 keywords. Bug fix duplicado ES.
  Nuevos: ASM (8 términos), Swahili (4), mercado DEM-SURGE (8), RES-RESOLVE (16),
          DEM-SUBSTITUTE (5 variantes). LFP peso -2.0→-3.0.

v1.0 — 2025-05 — Versión inicial. 4 idiomas. 9 bloques. ~280 términos.
```
