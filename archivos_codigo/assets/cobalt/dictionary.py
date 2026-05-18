"""assets.cobalt.dictionary — Datos específicos del sistema de alerta de cobalto.

Toda la lógica de scoring vive en `framework/`. Este módulo solo exporta los
datos del asset y los empaqueta en una instancia `COBALT_CONFIG: AssetConfig`.

Para añadir un asset nuevo (cobre, litio, …): copiar este archivo, adaptar
listas y umbrales. No tocar `framework/`.

Referencias spec:
  - `archivos codigo/keyword_dictionary.md`  → terminología y categorías
  - `archivos codigo/scoring_rules.md`       → multiplicadores y fórmulas
  - `archivos codigo/data_sources.md`        → fuentes y credibilidad
"""

import math

from framework.scoring import AssetConfig

# ---------------------------------------------------------------------------
# 1. ANCLAS — términos que filtran requires_context
# ---------------------------------------------------------------------------

ANCHOR_TERMS = [
    "cobalt", "cobalt ore", "cobalt hydroxide", "cobalt sulfate",
    "cobalt carbonate", "cobalt metal", "cobalt refining",
    "battery-grade cobalt", "cobalt supply", "cobalt market",
    "cobalt mining", "cobalt production", "cobalt export",
    "cobalt price", "cobalt demand", "critical mineral",
    "critical metals", "battery metals", "ev battery supply",
    # FR
    "minerai de cobalt", "hydroxyde de cobalt", "sulfate de cobalt",
    "raffinage du cobalt", "cobalt brut", "production de cobalt",
    "exportation de cobalt", "minerais critiques", "metaux de batterie",
    # PT
    "cobalto", "minerio de cobalto", "hidroxido de cobalto",
    "sulfato de cobalto", "refinacao de cobalto",
    "producao de cobalto", "exportacao de cobalto",
    "minerais criticos", "metais para baterias",
    # ES
    "mineral de cobalto", "hidroxido de cobalto",
    "sulfato de cobalto", "refinacion de cobalto",
    "produccion de cobalto", "exportacion de cobalto",
    "minerales criticos", "metales para baterias",
]

# ---------------------------------------------------------------------------
# 2. GEOGRAFÍAS — códigos GEO con sus términos identificativos
# ---------------------------------------------------------------------------

GEOGRAPHIC_TERMS = {
    "GEO-01": [
        "democratic republic of congo", "drc", "congo kinshasa",
        "katanga", "lualaba", "haut-katanga", "kolwezi", "likasi",
        "lubumbashi", "fungurume", "tenke fungurume", "mutanda",
        "boss mining", "kamoto", "kamoa-kakula",
        "cmoc", "kisanfu", "kfm mine",
        "north kivu", "south kivu", "nord-kivu", "sud-kivu",
        "goma", "bukavu", "ituri", "beni", "butembo",
        "copperbelt", "copper belt", "central african copperbelt",
        "republique democratique du congo", "rdc",
        "ceinture cuivriere", "province du lualaba",
        "republica democratica do congo",
        "republica democratica del congo", "cinturon cuprifero",
    ],
    "GEO-02": [
        "zambia", "zambian copperbelt", "ndola", "kitwe",
        "chingola", "mufulira", "chambishi", "nchanga",
        "konkola", "lumwana", "first quantum zambia",
        "mopani copper mines", "vedanta zambia",
        "zambie", "copperbelt zambiano",
    ],
    "GEO-03A": [
        "tanzania", "dar es salaam", "tpa", "tanzania ports authority",
        "central corridor", "tazara", "tazara railway",
        "northern corridor", "mombasa", "kenya",
        "east african corridor", "corredor central",
        "africa oriental",
    ],
    "GEO-03B": [
        "mozambique", "beira", "beira corridor", "nacala",
        "nacala corridor", "cfm", "porto de beira", "porto de nacala",
        "corridor de beira", "corredor de beira",
        "corredor de nacala",
    ],
    "GEO-04": [
        "south africa", "durban", "port of durban",
        "transnet", "transnet freight rail",
        "zimbabwe", "beitbridge",
        "southern african corridor", "southern corridor",
        "botswana", "maputo corridor", "maputo port",
        "richards bay",
        "afrique du sud", "corridor sud",
        "africa do sul", "porto de durban", "corredor sul",
        "sudafrica", "zimbabue", "corredor de maputo",
    ],
    "GEO-05": [
        "australia", "western australia", "murrin murrin",
        "nickel west", "cobalt blue holdings",
        "australian cobalt", "queensland cobalt",
        "australie", "australia occidental",
    ],
    "GEO-06": [
        "philippines", "palawan", "rio tuba", "coral bay",
        "taganito", "philippine nickel", "philippine cobalt",
        "mindanao mining", "filipinas",
    ],
    "GEO-07": [
        "china cobalt refining", "chinese cobalt",
        "zhejiang cobalt", "guangdong cobalt", "huayou cobalt",
        "gem co", "ganzhou cobalt", "jiangxi cobalt",
        "chinese battery supply chain", "china battery metals",
        "chine cobalt", "raffinage chinois",
        "china cobalto", "refinacion china",
    ],
    "GEO-08": [
        "port of durban", "durban port", "durban harbour",
        "dar es salaam port", "tpa port", "port of dar es salaam",
        "beira port", "porto de beira", "port of beira",
        "nacala port", "port of nacala",
        "mombasa port", "port of mombasa",
        "lobito corridor", "lobito port", "angola port",
        "benguela railway", "lobito atlantic terminal",
        "port de durban", "port de dar es salaam",
        "port de beira", "puerto de durban",
        "puerto de dar es salaam", "puerto de beira",
        "corredor de lobito",
    ],
    "GEO-10": [
        "indonesia", "sulawesi", "morowali", "imip",
        "indonesia morowali industrial park", "weda bay",
        "iwip", "halmahera",
        "vale indonesia", "ptvi", "huayou indonesia",
        "tsingshan", "harita nickel", "indonesian nickel cobalt",
        "high pressure acid leach", "hpal",
        "indonesien", "indonesie",
    ],
    "GEO-11": [
        "umicore", "umicore belgium", "kokkola refinery",
        "nornickel finland", "harjavalta", "terrafame",
        "glencore nikkelverk", "kristiansand refinery",
        "european cobalt refining", "european battery alliance",
        "belgium cobalt", "finland cobalt", "norway cobalt",
        "raffinage europeen", "raffinerie europe",
        "refinacion europea",
    ],
}

GEO_WEIGHTS = {
    "GEO-01": 1.80, "GEO-02": 1.20,
    "GEO-03A": 1.40, "GEO-03B": 1.40,
    "GEO-04": 1.30, "GEO-05": 0.90, "GEO-06": 0.80,
    "GEO-07": 1.60, "GEO-08": 1.50,
    "GEO-10": 1.10, "GEO-11": 0.80,
}

# ---------------------------------------------------------------------------
# 3. MULTIPLICADORES POR CATEGORÍA
# ---------------------------------------------------------------------------

CATEGORY_MULTIPLIERS = {
    # LOG
    "LOG-PORT": 2.0, "LOG-RAIL": 1.8, "LOG-ROAD": 1.5,
    "LOG-CUSTOMS": 1.7, "LOG-FLOOD": 1.6, "LOG-VESSEL": 1.3,
    # GEO
    "GEO-CONFLICT": 2.2, "GEO-COUP": 2.0, "GEO-SANCTION": 1.9,
    "GEO-PROTEST": 1.4, "GEO-ELECTION": 0.8, "GEO-DIPLO": 1.2,
    # LAB
    "LAB-STRIKE-ACT": 2.1, "LAB-STRIKE-THR": 1.5,
    "LAB-STRIKE-NEG": 0.9, "LAB-ACCIDENT": 1.8, "LAB-PROTEST": 1.1,
    # REG
    "REG-EXPORT-BAN": 2.3, "REG-TAX": 1.6, "REG-LICENSE": 1.9,
    "REG-ENV": 1.7, "REG-NATIONAL": 1.8, "REG-TARIFF": 1.4,
    # DEM
    "DEM-SURGE": 1.5, "DEM-STOCK": 1.2, "DEM-SUBSTITUTE": -1.5,
    # FMA
    "FMA-FLOOD": 1.7, "FMA-DROUGHT": 1.4,
    "FMA-SEISMIC": 1.3, "FMA-DISEASE": 1.5,
    # RES
    "RES-RESOLVE": 1.5,
}

SSC_CATEGORY_WEIGHTS = {
    "LOG-PORT": 1.0, "LOG-RAIL": 1.0, "LOG-ROAD": 1.0,
    "LOG-CUSTOMS": 1.0, "LOG-FLOOD": 1.0, "LOG-VESSEL": 1.0,
    "LAB-STRIKE-ACT": 1.0, "LAB-ACCIDENT": 1.0,
    "GEO-CONFLICT": 1.0, "GEO-COUP": 1.0,
    "REG-EXPORT-BAN": 1.0, "REG-LICENSE": 1.0,
    "FMA-FLOOD": 1.0, "FMA-DROUGHT": 1.0,
    "FMA-SEISMIC": 1.0, "FMA-DISEASE": 1.0,
    "LAB-STRIKE-THR": 0.6,
    "GEO-PROTEST": 0.4, "GEO-ELECTION": 0.4,
    "DEM-SUBSTITUTE": 0.0,    # No participa en SSC
    "RES-RESOLVE": 1.0,
    # Defaults a 0.4 si no está listado
}

SMC_CATEGORY_OVERRIDES = {
    "GEO-ELECTION": 1.2,
    "REG-EXPORT-BAN": 1.2, "REG-TAX": 1.2,
    "REG-LICENSE": 1.2, "REG-ENV": 1.2,
    "REG-NATIONAL": 1.2, "REG-TARIFF": 1.2,
    "DEM-SUBSTITUTE": 1.0,
    "RES-RESOLVE": 0.5,
}

# Categorías que no decaen por edad (REG y sanciones — la tensión persiste)
NO_DECAY_CATEGORIES = {
    "REG-EXPORT-BAN", "REG-TAX", "REG-LICENSE", "REG-ENV",
    "REG-NATIONAL", "REG-TARIFF", "GEO-SANCTION",
}

# ---------------------------------------------------------------------------
# 4. NEGACIÓN
# ---------------------------------------------------------------------------

NEGATION_TERMS_BY_LANG = {
    "en": ["no", "not", "never", "ended", "resolved", "cancelled", "avoided",
           "prevented", "denied", "resumed", "lifted", "withdrawn", "rejected"],
    "fr": ["non", "pas", "jamais", "termine", "resolu", "annule", "evite",
           "empeche", "nie", "repris", "leve", "retire"],
    "pt": ["nao", "nunca", "terminado", "resolvido", "cancelado", "evitado",
           "impedido", "negado", "retomado", "levantado", "retirado"],
    "es": ["no", "nunca", "terminado", "resuelto", "cancelado", "evitado",
           "impedido", "negado", "reanudado", "levantado", "retirado"],
}
ALL_NEGATION_TERMS: set = set()
for _terms in NEGATION_TERMS_BY_LANG.values():
    ALL_NEGATION_TERMS.update(_terms)

# Para "coup" sin estos términos cerca, no puntúa
COUP_CONTEXT_TERMS = [
    "drc", "congo", "zambia", "africa", "katanga", "lualaba",
    "government", "military", "president", "junta",
]

# Patrones que invalidan una ocurrencia de su keyword
FALSE_POSITIVE_FILTERS = {
    "LAB-STRIKE-ACT": ["bowling strike", "lightning strike", "airstrike",
                       "air strike", "hunger strike"],
    "GEO-COUP": ["coup de grace", "coup de theatre", "hat trick",
                 "coup de main"],
    "FMA-FLOOD": ["market flooding", "flooding the market",
                  "flood of orders", "flood of investment"],
    "GEO-SANCTION": ["academic sanction", "sports sanction",
                     "sanctioned move"],
    "LAB-ACCIDENT": ["market collapse", "price collapse",
                     "currency collapse", "economic collapse"],
}

# Términos vagos sin GEO específico (penalización ×0.40, no descarte)
GENERIC_GEO_TERMS = ["africa", "emerging markets", "developing countries"]

# Términos contexto débiles para Path B Gemini
CONTEXT_TRIGGER_TERMS = [
    "supply chain", "critical mineral", "battery supply", "processing capacity",
    "export control", "refinery", "smelter", "feedstock", "offtake agreement",
    "artisanal mining", "upstream", "downstream processing", "mineral processing",
    "strategic reserve", "battery metals", "ev supply", "cathode material",
    "precursor", "hydrometallurgy", "concentrate shipment", "raw material supply",
    "chaîne d'approvisionnement", "minerai critique", "traitement mineral",
    "cadena de suministro", "mineral critico", "procesamiento mineral",
]

# ---------------------------------------------------------------------------
# 5. KEYWORDS — (term, category, weight, requires_context, context_window, geo_boost)
# ---------------------------------------------------------------------------

KEYWORDS = [
    # --- LOG-PORT ---
    ("port closure",              "LOG-PORT", 4.5, False, 50,  ["GEO-08","GEO-03A","GEO-03B","GEO-04"]),
    ("port congestion",           "LOG-PORT", 3.5, False, 50,  ["GEO-08"]),
    ("port strike",               "LOG-PORT", 4.2, False, 50,  ["GEO-08"]),
    ("dock workers strike",       "LOG-PORT", 4.2, False, 50,  ["GEO-08"]),
    ("stevedores strike",         "LOG-PORT", 4.0, False, 50,  ["GEO-08"]),
    ("port backlog",              "LOG-PORT", 3.2, True,  80,  ["GEO-08"]),
    ("vessel queuing",            "LOG-PORT", 3.0, True,  80,  ["GEO-08"]),
    ("port shutdown",             "LOG-PORT", 4.5, False, 50,  ["GEO-08"]),
    ("terminal closure",          "LOG-PORT", 4.0, False, 50,  ["GEO-08"]),
    ("fermeture du port",         "LOG-PORT", 4.5, False, 50,  ["GEO-08"]),
    ("greve portuaire",           "LOG-PORT", 4.2, False, 50,  ["GEO-08"]),
    ("congestion portuaire",      "LOG-PORT", 3.5, False, 50,  ["GEO-08"]),
    ("bloqueio portuario",        "LOG-PORT", 4.2, False, 50,  ["GEO-08"]),
    ("encerramento do porto",     "LOG-PORT", 4.5, False, 50,  ["GEO-08"]),
    ("greve portuaria",           "LOG-PORT", 4.2, False, 50,  ["GEO-08"]),
    ("cierre portuario",          "LOG-PORT", 4.5, False, 50,  ["GEO-08"]),
    ("huelga portuaria",          "LOG-PORT", 4.2, False, 50,  ["GEO-08"]),
    ("congestion portuaria",      "LOG-PORT", 3.5, False, 50,  ["GEO-08"]),

    # --- LOG-RAIL ---
    ("railway disruption",        "LOG-RAIL", 3.8, False, 50,  ["GEO-03A","GEO-03B","GEO-04","GEO-08"]),
    ("rail shutdown",             "LOG-RAIL", 4.0, False, 50,  ["GEO-03A","GEO-03B","GEO-04"]),
    ("freight rail suspension",   "LOG-RAIL", 3.8, False, 50,  ["GEO-04"]),
    ("rail sabotage",             "LOG-RAIL", 4.5, False, 50,  ["GEO-04"]),
    ("cable theft railway",       "LOG-RAIL", 3.5, False, 50,  ["GEO-04"]),
    ("derailment",                "LOG-RAIL", 3.2, True,  80,  ["GEO-03A","GEO-03B","GEO-04"]),
    ("perturbation ferroviaire",  "LOG-RAIL", 3.8, False, 50,  ["GEO-03A","GEO-03B","GEO-04"]),
    ("interruption du chemin de fer","LOG-RAIL",4.0, False, 50, ["GEO-03A","GEO-03B","GEO-04"]),
    ("sabotagem ferroviaria",     "LOG-RAIL", 4.5, False, 50,  ["GEO-04"]),
    ("interrupcao ferroviaria",   "LOG-RAIL", 3.8, False, 50,  ["GEO-03A","GEO-03B","GEO-04"]),
    ("interrupcion ferroviaria",  "LOG-RAIL", 3.8, False, 50,  ["GEO-03A","GEO-03B","GEO-04"]),
    ("sabotaje ferroviario",      "LOG-RAIL", 4.5, False, 50,  ["GEO-04"]),

    # --- LOG-ROAD ---
    ("road blockade",             "LOG-ROAD", 3.2, True,  60,  ["GEO-01","GEO-02","GEO-03A","GEO-03B"]),
    ("border crossing closed",    "LOG-ROAD", 3.5, False, 50,  ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("border blockage",           "LOG-ROAD", 3.5, False, 50,  ["GEO-01","GEO-02"]),
    ("kasumbalesa",               "LOG-ROAD", 4.0, False, 100, ["GEO-01","GEO-02"]),
    ("beitbridge closure",        "LOG-ROAD", 3.8, False, 80,  ["GEO-04"]),
    ("truckers strike",           "LOG-ROAD", 3.0, True,  60,  ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("blocage routier",           "LOG-ROAD", 3.2, True,  60,  ["GEO-01","GEO-02"]),
    ("frontiere fermee",          "LOG-ROAD", 3.5, False, 50,  ["GEO-01","GEO-02"]),
    ("bloqueio rodoviario",       "LOG-ROAD", 3.2, True,  60,  ["GEO-03B","GEO-04"]),
    ("fronteira fechada",         "LOG-ROAD", 3.5, False, 50,  ["GEO-03B","GEO-04"]),
    ("bloqueo de carretera",      "LOG-ROAD", 3.2, True,  60,  ["GEO-01","GEO-02"]),
    ("frontera cerrada",          "LOG-ROAD", 3.5, False, 50,  ["GEO-01","GEO-02"]),

    # --- LOG-CUSTOMS ---
    ("customs delay",             "LOG-CUSTOMS", 3.0, True,  60, ["GEO-01","GEO-02","GEO-08"]),
    ("export permit suspended",   "LOG-CUSTOMS", 4.0, True,  80, ["GEO-01","GEO-02","GEO-07"]),
    ("export documentation",      "LOG-CUSTOMS", 2.5, True,  60, ["GEO-01"]),
    ("mineral export freeze",     "LOG-CUSTOMS", 4.2, False, 50, ["GEO-01","GEO-02","GEO-07"]),
    ("retard douanier",           "LOG-CUSTOMS", 3.0, True,  60, ["GEO-01"]),
    ("suspension permis exportation","LOG-CUSTOMS",4.0,True, 80, ["GEO-01","GEO-02"]),
    ("atraso alfandegario",       "LOG-CUSTOMS", 3.0, True,  60, ["GEO-03B","GEO-04"]),
    ("retraso aduanero",          "LOG-CUSTOMS", 3.0, True,  60, ["GEO-01","GEO-02"]),
    ("permiso de exportacion suspendido","LOG-CUSTOMS",4.0,True,80,["GEO-01"]),

    # --- LOG-VESSEL ---
    ("shipping delay",            "LOG-VESSEL", 2.8, True,  80, ["GEO-08"]),
    ("freight rates surge",       "LOG-VESSEL", 2.5, True,  80, []),
    ("vessel shortage",           "LOG-VESSEL", 3.0, True,  80, []),
    ("bulk carrier shortage",     "LOG-VESSEL", 3.2, True,  80, []),

    # --- GEO-CONFLICT ---
    ("armed conflict",            "GEO-CONFLICT", 4.5, False, 50, ["GEO-01","GEO-02"]),
    ("militia attack",            "GEO-CONFLICT", 4.8, False, 50, ["GEO-01"]),
    ("rebel attack",              "GEO-CONFLICT", 4.5, False, 50, ["GEO-01","GEO-03A","GEO-03B"]),
    ("m23",                       "GEO-CONFLICT", 4.0, True,  50, ["GEO-01"]),
    ("mai-mai",                   "GEO-CONFLICT", 3.8, False, 80, ["GEO-01"]),
    ("mine attack",               "GEO-CONFLICT", 5.0, False, 80, ["GEO-01","GEO-02"]),
    ("security incident mine",    "GEO-CONFLICT", 4.0, True,  60, ["GEO-01","GEO-02"]),
    ("operations suspended security","GEO-CONFLICT",4.5,True, 60, ["GEO-01","GEO-02"]),
    ("conflit arme",              "GEO-CONFLICT", 4.5, False, 50, ["GEO-01"]),
    ("attaque de milice",         "GEO-CONFLICT", 4.8, False, 50, ["GEO-01"]),
    ("attaque rebelle",           "GEO-CONFLICT", 4.5, False, 50, ["GEO-01"]),
    ("conflicto armado",          "GEO-CONFLICT", 4.5, False, 50, ["GEO-01"]),
    ("ataque a mina",             "GEO-CONFLICT", 5.0, False, 80, ["GEO-01","GEO-02"]),
    ("conflito armado",           "GEO-CONFLICT", 4.5, False, 50, ["GEO-01"]),
    ("ataque de milicia",         "GEO-CONFLICT", 4.8, False, 50, ["GEO-01"]),

    # --- GEO-CONFLICT: despliegue militar / militarización (cobertura añadida
    # tras audit forense de NewsAPI 2026-05-17). El sistema no detectaba señales
    # de militarización PREVENTIVA en zonas mineras (vs. ataques activos que ya
    # cubrían los keywords anteriores). Caso real perdido: "DRC sending in the
    # military to guard mines and critical minerals" — anchor + geo OK pero
    # ningún keyword disparaba. Test #10 en synthetic_articles.py bloquea regresión.
    ("military deployment",       "GEO-CONFLICT", 4.0, True,  60, ["GEO-01","GEO-02"]),
    ("military to guard mines",   "GEO-CONFLICT", 4.5, False, 80, ["GEO-01","GEO-02"]),
    ("military to guard",         "GEO-CONFLICT", 3.8, True,  60, ["GEO-01","GEO-02"]),
    ("soldiers deployed",         "GEO-CONFLICT", 3.5, True,  60, ["GEO-01","GEO-02"]),
    ("army deployed",             "GEO-CONFLICT", 3.5, True,  60, ["GEO-01","GEO-02"]),
    ("army to guard",             "GEO-CONFLICT", 3.5, True,  60, ["GEO-01","GEO-02"]),
    ("militarization of mines",   "GEO-CONFLICT", 4.5, False, 80, ["GEO-01","GEO-02"]),
    ("armed escort mining",       "GEO-CONFLICT", 4.0, False, 80, ["GEO-01","GEO-02"]),
    ("security forces deployed",  "GEO-CONFLICT", 3.5, True,  60, ["GEO-01","GEO-02"]),
    # FR (RFI Afrique, Radio Okapi cuando vuelva)
    ("deploiement militaire",     "GEO-CONFLICT", 4.0, True,  60, ["GEO-01"]),
    ("militaires deployes",       "GEO-CONFLICT", 3.5, True,  60, ["GEO-01"]),
    ("armee proteger mines",      "GEO-CONFLICT", 4.5, False, 80, ["GEO-01"]),
    ("militarisation mines",      "GEO-CONFLICT", 4.5, False, 80, ["GEO-01"]),
    # ES
    ("despliegue militar",        "GEO-CONFLICT", 4.0, True,  60, ["GEO-01","GEO-02"]),
    ("militares desplegados",     "GEO-CONFLICT", 3.5, True,  60, ["GEO-01","GEO-02"]),
    ("ejercito proteger minas",   "GEO-CONFLICT", 4.5, False, 80, ["GEO-01","GEO-02"]),
    ("militarizacion minas",      "GEO-CONFLICT", 4.5, False, 80, ["GEO-01","GEO-02"]),
    # PT (Mozambique, Club Mozambique cuando vuelva)
    ("destacamento militar",      "GEO-CONFLICT", 4.0, True,  60, ["GEO-03B","GEO-04"]),
    ("militares destacados",      "GEO-CONFLICT", 3.5, True,  60, ["GEO-03B","GEO-04"]),
    ("militarizacao minas",       "GEO-CONFLICT", 4.5, False, 80, ["GEO-03B","GEO-04"]),

    # --- GEO-COUP ---
    ("coup",                      "GEO-COUP", 4.5, True,  40, ["GEO-01","GEO-02"]),
    ("military takeover",         "GEO-COUP", 5.0, False, 50, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("government overthrown",     "GEO-COUP", 5.0, False, 50, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("state of emergency",        "GEO-COUP", 4.0, True,  80, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("coup d'etat",               "GEO-COUP", 5.0, False, 50, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("prise de pouvoir militaire","GEO-COUP", 5.0, False, 50, ["GEO-01"]),
    ("etat d'urgence",            "GEO-COUP", 4.0, True,  80, ["GEO-01"]),
    ("golpe de estado",           "GEO-COUP", 5.0, False, 50, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("golpe militar",             "GEO-COUP", 5.0, False, 50, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("estado de emergencia",      "GEO-COUP", 4.0, True,  80, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),

    # --- GEO-SANCTION ---
    ("sanctions",                 "GEO-SANCTION", 3.8, True,  80, ["GEO-01","GEO-02","GEO-07"]),
    ("trade embargo",             "GEO-SANCTION", 4.5, False, 50, ["GEO-01","GEO-07"]),
    ("asset freeze",              "GEO-SANCTION", 4.0, True,  60, ["GEO-01","GEO-07"]),
    ("ofac sanctions",            "GEO-SANCTION", 4.2, True,  80, ["GEO-01","GEO-07"]),
    ("sanctions commerciales",    "GEO-SANCTION", 3.8, True,  80, ["GEO-01"]),
    ("embargo comercial",         "GEO-SANCTION", 4.5, False, 50, ["GEO-01","GEO-07"]),
    ("sancoes comerciais",        "GEO-SANCTION", 3.8, True,  80, ["GEO-01","GEO-07"]),

    # --- GEO-PROTEST ---
    ("protests",                  "GEO-PROTEST", 2.2, True,  60, ["GEO-01","GEO-02","GEO-08"]),
    ("civil unrest",              "GEO-PROTEST", 2.8, True,  60, ["GEO-01","GEO-02"]),
    ("demonstrations",            "GEO-PROTEST", 2.0, True,  60, ["GEO-01","GEO-02"]),
    ("manifestations",            "GEO-PROTEST", 2.0, True,  60, ["GEO-01"]),
    ("troubles civils",           "GEO-PROTEST", 2.8, True,  60, ["GEO-01"]),
    ("protestos",                 "GEO-PROTEST", 2.2, True,  60, ["GEO-03B","GEO-04"]),
    ("protestas",                 "GEO-PROTEST", 2.2, True,  60, ["GEO-01","GEO-02"]),

    # --- LAB-STRIKE-ACT ---
    ("strike",                    "LAB-STRIKE-ACT", 4.0, True,  60, ["GEO-01","GEO-02","GEO-08"]),
    ("workers on strike",         "LAB-STRIKE-ACT", 4.5, False, 60, ["GEO-01","GEO-02","GEO-08"]),
    ("mining strike",             "LAB-STRIKE-ACT", 4.8, False, 50, ["GEO-01","GEO-02"]),
    ("walkout",                   "LAB-STRIKE-ACT", 4.2, True,  60, ["GEO-01","GEO-02","GEO-08"]),
    ("work stoppage",             "LAB-STRIKE-ACT", 4.2, True,  60, ["GEO-01","GEO-02","GEO-08"]),
    ("production halted",         "LAB-STRIKE-ACT", 4.5, True,  60, ["GEO-01","GEO-02"]),
    ("operations suspended",      "LAB-STRIKE-ACT", 4.3, True,  60, ["GEO-01","GEO-02"]),
    ("greve",                     "LAB-STRIKE-ACT", 4.0, True,  60, ["GEO-01","GEO-08"]),
    ("greve miniere",             "LAB-STRIKE-ACT", 4.8, False, 50, ["GEO-01"]),
    ("arret de travail",          "LAB-STRIKE-ACT", 4.2, True,  60, ["GEO-01","GEO-08"]),
    ("production suspendue",      "LAB-STRIKE-ACT", 4.5, True,  60, ["GEO-01"]),
    ("greve mineira",             "LAB-STRIKE-ACT", 4.8, False, 50, ["GEO-02"]),
    ("paralisacao",               "LAB-STRIKE-ACT", 4.2, True,  60, ["GEO-03B","GEO-04"]),
    ("huelga",                    "LAB-STRIKE-ACT", 4.0, True,  60, ["GEO-01","GEO-02","GEO-08"]),
    ("huelga minera",             "LAB-STRIKE-ACT", 4.8, False, 50, ["GEO-01","GEO-02"]),
    ("paro laboral",              "LAB-STRIKE-ACT", 4.2, True,  60, ["GEO-01","GEO-02"]),

    # --- LAB-STRIKE-THR ---
    ("strike threat",             "LAB-STRIKE-THR", 3.0, True, 60, ["GEO-01","GEO-02","GEO-08"]),
    ("strike notice",             "LAB-STRIKE-THR", 3.5, True, 60, ["GEO-01","GEO-02","GEO-08"]),
    ("workers threaten",          "LAB-STRIKE-THR", 2.8, True, 60, ["GEO-01","GEO-02"]),
    ("menace de greve",           "LAB-STRIKE-THR", 3.0, True, 60, ["GEO-01","GEO-08"]),
    ("preavis de greve",          "LAB-STRIKE-THR", 3.5, True, 60, ["GEO-01"]),
    ("ameaca de greve",           "LAB-STRIKE-THR", 3.0, True, 60, ["GEO-03B","GEO-04"]),
    ("amenaza de huelga",         "LAB-STRIKE-THR", 3.0, True, 60, ["GEO-01","GEO-02"]),

    # --- Kiswahili (DRC Oriental, Tanzania) ---
    ("mgomo",                    "LAB-STRIKE-ACT", 3.5, True,  60, ["GEO-01","GEO-02","GEO-03A"]),
    ("mgomo wa wachimbaji",      "LAB-STRIKE-ACT", 4.5, False, 50, ["GEO-01","GEO-02"]),
    ("mgodi kufungwa",           "LAB-STRIKE-ACT", 4.0, False, 60, ["GEO-01","GEO-02"]),
    ("bandari kufungwa",         "LOG-PORT",        4.0, False, 50, ["GEO-03A","GEO-08"]),

    # --- LAB-ACCIDENT ---
    ("mine collapse",             "LAB-ACCIDENT", 5.0, False, 50, ["GEO-01","GEO-02"]),
    ("artisanal mine collapse",   "LAB-ACCIDENT", 4.0, False, 50, ["GEO-01"]),
    ("flooding mine",             "LAB-ACCIDENT", 4.5, False, 50, ["GEO-01","GEO-02"]),
    ("mine explosion",            "LAB-ACCIDENT", 4.8, False, 50, ["GEO-01","GEO-02"]),
    ("mining accident",           "LAB-ACCIDENT", 3.8, True,  60, ["GEO-01","GEO-02"]),
    ("effondrement de mine",      "LAB-ACCIDENT", 5.0, False, 50, ["GEO-01"]),
    ("inondation de mine",        "LAB-ACCIDENT", 4.5, False, 50, ["GEO-01"]),
    ("acidente de mineracao",     "LAB-ACCIDENT", 3.8, True,  60, ["GEO-02","GEO-03B"]),
    ("colapso de mina",           "LAB-ACCIDENT", 5.0, False, 50, ["GEO-01","GEO-02"]),
    ("accidente minero",          "LAB-ACCIDENT", 3.8, True,  60, ["GEO-01","GEO-02"]),

    # --- LAB-ASM: Minería Artesanal / Small-Scale Mining ---
    ("creuseurs",                     "LAB-ACCIDENT", 3.0, True,  80, ["GEO-01"]),
    ("mineurs artisanaux",            "LAB-ACCIDENT", 2.8, True,  80, ["GEO-01"]),
    ("informal cobalt mining",        "LAB-ACCIDENT", 2.8, True,  80, ["GEO-01"]),
    ("artisanal mining ban",          "REG-LICENSE",  4.0, False, 60, ["GEO-01"]),
    ("asm suspension",                "REG-LICENSE",  3.8, False, 60, ["GEO-01"]),
    ("suspension exploitation artisanale", "REG-LICENSE", 4.0, False, 60, ["GEO-01"]),
    ("interdiction exploitation artisanale","REG-LICENSE",4.2, False, 60, ["GEO-01"]),
    ("mineria artesanal prohibida",   "REG-LICENSE",  4.0, False, 60, ["GEO-01"]),

    # --- REG-EXPORT-BAN ---
    ("export ban",                "REG-EXPORT-BAN", 5.0, True,  80, ["GEO-01","GEO-02","GEO-07"]),
    ("export restriction",        "REG-EXPORT-BAN", 4.5, True,  80, ["GEO-01","GEO-02","GEO-07"]),
    ("export quota",              "REG-EXPORT-BAN", 4.0, True,  80, ["GEO-01","GEO-07"]),
    ("raw mineral export ban",    "REG-EXPORT-BAN", 5.0, False, 80, ["GEO-01","GEO-02"]),
    ("interdiction d'exportation","REG-EXPORT-BAN", 5.0, True,  80, ["GEO-01"]),
    ("restriction a l'exportation","REG-EXPORT-BAN",4.5, True,  80, ["GEO-01"]),
    ("proibicao de exportacao",   "REG-EXPORT-BAN", 5.0, True,  80, ["GEO-02","GEO-03B"]),
    ("prohibicion de exportacion","REG-EXPORT-BAN", 5.0, True,  80, ["GEO-01","GEO-02"]),
    ("veda exportacion mineral",  "REG-EXPORT-BAN", 5.0, False, 80, ["GEO-01"]),

    # --- REG-TAX ---
    ("windfall tax",              "REG-TAX", 3.5, True,  80, ["GEO-01","GEO-02"]),
    ("mining royalty increase",   "REG-TAX", 3.8, False, 60, ["GEO-01","GEO-02"]),
    ("super profits tax",         "REG-TAX", 3.5, True,  80, ["GEO-01","GEO-02"]),
    ("taxe sur les super-profits","REG-TAX", 3.8, False, 80, ["GEO-01"]),
    ("redevance miniere",         "REG-TAX", 3.8, True,  80, ["GEO-01"]),
    ("royalty minerario",         "REG-TAX", 3.8, True,  80, ["GEO-02"]),
    ("impuesto minero",           "REG-TAX", 3.5, True,  80, ["GEO-01","GEO-02"]),

    # --- REG-LICENSE ---
    ("mining license suspended",  "REG-LICENSE", 4.5, False, 60, ["GEO-01","GEO-02"]),
    ("license revoked",           "REG-LICENSE", 4.5, True,  60, ["GEO-01","GEO-02"]),
    ("permit cancelled",          "REG-LICENSE", 4.0, True,  60, ["GEO-01","GEO-02"]),
    ("licence miniere suspendue", "REG-LICENSE", 4.5, False, 60, ["GEO-01"]),
    ("licenca mineira suspensa",  "REG-LICENSE", 4.5, False, 60, ["GEO-02"]),
    ("licencia minera suspendida","REG-LICENSE", 4.5, False, 60, ["GEO-01","GEO-02"]),

    # --- REG-NATIONAL ---
    ("nationalization",           "REG-NATIONAL", 4.8, True, 80, ["GEO-01","GEO-02"]),
    ("nationalisation",           "REG-NATIONAL", 4.8, True, 80, ["GEO-01"]),
    ("nacionalizacao",            "REG-NATIONAL", 4.8, True, 80, ["GEO-02"]),
    ("nacionalizacion",           "REG-NATIONAL", 4.8, True, 80, ["GEO-01","GEO-02"]),

    # --- FMA-FLOOD ---
    ("flooding",                  "FMA-FLOOD", 3.5, True,  60, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("flash flood",               "FMA-FLOOD", 4.0, False, 50, ["GEO-01","GEO-02","GEO-03A","GEO-03B"]),
    ("road washed out",           "FMA-FLOOD", 4.2, False, 50, ["GEO-01","GEO-02","GEO-03A","GEO-03B"]),
    ("cyclone",                   "FMA-FLOOD", 4.5, False, 50, ["GEO-03A","GEO-03B","GEO-04"]),
    ("inundacao",                 "FMA-FLOOD", 3.5, True,  60, ["GEO-03B","GEO-04"]),
    ("ciclone",                   "FMA-FLOOD", 4.5, False, 50, ["GEO-03B"]),
    ("inundacion",                "FMA-FLOOD", 3.5, True,  60, ["GEO-01","GEO-02","GEO-03A","GEO-03B"]),

    # --- FMA-DROUGHT ---
    ("power outage",              "FMA-DROUGHT", 3.8, True,  60, ["GEO-01"]),
    ("load shedding",             "FMA-DROUGHT", 3.5, True,  60, ["GEO-01","GEO-04"]),
    ("hydroelectric shortage",    "FMA-DROUGHT", 4.0, True,  80, ["GEO-01"]),
    ("inga dam",                  "FMA-DROUGHT", 4.5, False, 100,["GEO-01"]),
    ("delestage",                 "FMA-DROUGHT", 3.5, True,  60, ["GEO-01"]),
    ("coupure d'electricite",     "FMA-DROUGHT", 3.8, True,  60, ["GEO-01"]),
    ("corte electrico",           "FMA-DROUGHT", 3.8, True,  60, ["GEO-01"]),

    # --- DEM-SUBSTITUTE ---
    ("cobalt-free battery",       "DEM-SUBSTITUTE", -2.5, False, 80, []),
    ("lfp battery",               "DEM-SUBSTITUTE", -3.0, False, 80, []),
    ("lithium iron phosphate",    "DEM-SUBSTITUTE", -1.5, False, 80, []),
    ("lmfp battery",              "DEM-SUBSTITUTE", -2.0, False, 80, []),
    ("batterie lfp",              "DEM-SUBSTITUTE", -2.0, False, 80, []),
    ("bateria lfp",               "DEM-SUBSTITUTE", -2.0, False, 80, []),
    ("sodium-ion battery",        "DEM-SUBSTITUTE", -2.5, False, 80, []),
    ("sodium ion battery",        "DEM-SUBSTITUTE", -2.5, False, 80, []),
    ("solid state battery",       "DEM-SUBSTITUTE", -1.5, False, 80, []),
    ("batterie sans cobalt",      "DEM-SUBSTITUTE", -2.5, False, 80, []),
    ("bateria sin cobalto",       "DEM-SUBSTITUTE", -2.5, False, 80, []),
    ("bateria sem cobalto",       "DEM-SUBSTITUTE", -2.5, False, 80, []),

    # --- DEM-SURGE ---
    ("gigafactory",               "DEM-SURGE", 2.5, True,  80, []),
    ("battery supply contract",   "DEM-SURGE", 3.0, True,  80, []),
    ("strategic reserve cobalt",  "DEM-SURGE", 3.5, False, 80, []),
    ("cobalt stockpile",          "DEM-SURGE", 3.2, False, 60, []),
    ("cobalt supply deficit",     "DEM-SURGE", 2.5, False, 80, []),
    ("cobalt shortage",           "DEM-SURGE", 2.8, False, 60, []),
    ("cobalt inventory low",      "DEM-SURGE", 2.5, False, 80, []),
    ("cobalt price spike",        "DEM-SURGE", 2.0, False, 80, []),
    ("lme cobalt inventory",      "DEM-SURGE", 2.2, False, 80, []),
    ("penurie de cobalt",         "DEM-SURGE", 2.8, False, 60, []),
    ("deficit de cobalto",        "DEM-SURGE", 2.5, False, 80, []),
    ("escassez de cobalto",       "DEM-SURGE", 2.8, False, 60, []),

    # --- RES-RESOLVE ---
    ("strike ended",              "RES-RESOLVE", -3.0, True,  80, []),
    ("strike called off",         "RES-RESOLVE", -3.0, True,  80, []),
    ("workers return to work",    "RES-RESOLVE", -3.0, True,  80, []),
    ("agreement reached",         "RES-RESOLVE", -2.5, True,  80, []),
    ("operations resumed",        "RES-RESOLVE", -3.0, True,  80, []),
    ("port reopened",             "RES-RESOLVE", -3.5, False, 60, ["GEO-08","GEO-03A","GEO-03B","GEO-04"]),
    ("mine reopened",             "RES-RESOLVE", -3.0, False, 60, ["GEO-01","GEO-02"]),
    ("border reopened",           "RES-RESOLVE", -3.0, False, 60, ["GEO-01","GEO-02","GEO-03A","GEO-03B","GEO-04"]),
    ("greve terminee",            "RES-RESOLVE", -3.0, True,  80, []),
    ("reprise des operations",    "RES-RESOLVE", -3.0, True,  80, []),
    ("accord conclu",             "RES-RESOLVE", -2.5, True,  80, []),
    ("huelga terminada",          "RES-RESOLVE", -3.0, True,  80, []),
    ("operaciones reanudadas",    "RES-RESOLVE", -3.0, True,  80, []),
    ("acuerdo alcanzado",         "RES-RESOLVE", -2.5, True,  80, []),
    ("greve encerrada",           "RES-RESOLVE", -3.0, True,  80, []),
    ("operacoes retomadas",       "RES-RESOLVE", -3.0, True,  80, []),
]

# ---------------------------------------------------------------------------
# 6. FUENTES — credibilidad + RSS + scraping
# ---------------------------------------------------------------------------

# Audit 2026-05-17: las antiguas "reuters_*" nunca apuntaron a Reuters real:
# los URLs eran northernminer.com, africanews.com y rfi.fr/en/rss. Renombradas
# para que el nombre refleje el host real y bajada la credibilidad de 1.00 a
# un rango realista (era un sobrepeso falso que contaminaba el bonus multifuente).
SOURCE_CREDIBILITY = {
    # Tier 1 — generales internacionales (renombradas en audit 2026-05-17)
    "northern_miner":     0.85,   # antes "reuters_africa" → northernminer.com
    "africanews_general": 0.75,   # antes "reuters_commodities" → africanews.com
    "rfi_english_world":  0.85,   # antes "reuters_china" → rfi.fr/en/rss
    # Placeholders no usados actualmente — se conservan por si vuelven al config
    "mining_com_general": 1.00,
    "ap_news":            1.00,
    # African regional / general
    "allafrica":          0.85,
    "bbc_africa":         0.90,
    "miningmx":           0.90,
    "rfi_afrique":        0.80,
    "club_mozambique":    0.80,
    "lusaka_times":       0.75,
    "transnet_durban":    1.00,
    "tpa_tanzania":       1.00,
    "cfm_mozambique":     1.00,
    "reliefweb_drc":      0.90,
    "gdacs":              1.00,
    "acled":              1.00,
    "kitco":              0.85,
    # GEO-10 (Indonesia / Sulawesi)
    "antara_business":    0.85,
    "antara_press":       0.85,
    "mining_technology":  0.90,
    "mongabay":           0.80,
    # GEO-11 (Refino europeo)
    "yle_news_en":        0.90,
    "energy_storage_news":0.85,
    # Google News (agregador). Audit 2026-05-17: 5 de 6 búsquedas devuelven 0
    # artículos consistentemente (Google ha restringido el RSS de Google News
    # desde 2024). Eliminadas del config. Solo sobrevive indonesia_nickel.
    "gnews_indonesia_nickel": 0.50,
    # ---------------------------------------------------------------------
    # Fuentes nuevas (Fase 1.5, 2026-05-17). Curl-tested desde IP de GCP,
    # las 7 confirmadamente accesibles tras audit forense.
    # (cleantechnica_cobalt y radio_okapi eliminadas: publicaban con frecuencia
    # demasiado baja para el filtro de 48h — ver comentario en RSS_SOURCES.)
    # ---------------------------------------------------------------------
    "cobalt_institute":   0.90,  # institución oficial del sector
    "australian_mining":  0.85,  # publicación industrial AU
    "cnbc_commodities":   0.85,  # medio financiero mainstream
    "resource_world":     0.80,  # mining magazine canadiense
    "ns_energy":          0.75,  # energy + mining specialist
    "oilprice_main":      0.70,  # focus oil, mining secundario
    "investing_commodities": 0.65,  # aggregator commodities, contenido variable

    # ---------------------------------------------------------------------
    # NewsAPI.org (Fase 1.5+, 2026-05-17). Los artículos vienen con el nombre
    # del medio normalizado a snake_case (ver framework/sources._normalize_source_name).
    # Esto permite que el bonus multi-fuente del aggregator distinga Reuters
    # vía NewsAPI de BBC vía NewsAPI como fuentes independientes.
    # Si un medio no aparece aquí, score_article cae al default 0.70.
    # ---------------------------------------------------------------------
    "reuters":               1.00,  # idem a reuters_africa cuando era válido
    "bloomberg":             0.95,
    "the_wall_street_journal": 0.95,
    "financial_times":       0.95,
    "associated_press":      0.95,
    "bbc_news":              0.90,
    "the_economist":         0.95,
    "the_guardian":          0.85,
    "mining_com":            0.95,  # mining.com via NewsAPI (sortea bloqueo IP de GCP)
    "south_china_morning_post": 0.80,
    "cnbc":                  0.85,
    "reuters_uk":            1.00,
    "ft":                    0.95,
    "newsapi_unknown":       0.65,  # fallback explícito si NewsAPI no especifica medio
    # Detectados en logs reales del cron (añadir aquí si vemos source_names nuevos)
    "the_conversation":         0.85,  # plataforma académica/periodística establecida
    "the_conversation_africa":  0.85,  # edición regional, mismo nivel
}

RSS_SOURCES = [
    # --- Tier 1 — generales internacionales ---
    # Audit 2026-05-17: estos tres nombres eran engañosos. No son Reuters.
    # Renombrados para reflejar el host real; credibilidad corregida en SOURCE_CREDIBILITY.
    {"name": "northern_miner",
     "url":  "https://www.northernminer.com/feed/",
     "lang": "en", "full_text": True, "rate_limit": 30, "timeout": 10},
    {"name": "africanews_general",
     "url":  "https://www.africanews.com/feed/",
     "lang": "en", "full_text": True, "rate_limit": 30, "timeout": 10},
    {"name": "rfi_english_world",
     "url":  "https://www.rfi.fr/en/rss",
     "lang": "en", "full_text": True, "rate_limit": 30, "timeout": 10},
    # --- Mining specialized ---
    # mining_com_cobalt eliminada en audit 2026-05-17: AWS WAF de mining.com
    # bloquea con HTTP 403 toda la IP de GCP (homepage incluida). No recuperable
    # client-side. Reemplazo pendiente en Fase 1.5 (roadmap).
    {"name": "kitco",
     "url":  "https://im-mining.com/feed/",
     "lang": "en", "full_text": False, "rate_limit": 45, "timeout": 10},
    # --- African regional ---
    {"name": "allafrica",
     "url":  "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf",
     "lang": "en", "full_text": True, "rate_limit": 45, "timeout": 15},
    {"name": "bbc_africa",
     "url":  "https://feeds.bbci.co.uk/news/world/africa/rss.xml",
     "lang": "en", "full_text": False, "rate_limit": 60, "timeout": 15},
    {"name": "miningmx",
     "url":  "https://www.miningmx.com/feed/",
     "lang": "en", "full_text": False, "rate_limit": 60, "timeout": 15},
    {"name": "rfi_afrique",
     "url":  "https://www.rfi.fr/fr/afrique/rss",
     "lang": "fr", "full_text": True, "rate_limit": 45, "timeout": 15},
    {"name": "club_mozambique",
     "url":  "https://clubofmozambique.com/feed/",
     "lang": "en", "full_text": False, "rate_limit": 90, "timeout": 15},
    {"name": "lusaka_times",
     "url":  "https://www.lusakatimes.com/feed/",
     "lang": "en", "full_text": False, "rate_limit": 90, "timeout": 15},
    # --- GEO-10: Indonesia / Sulawesi ---
    {"name": "antara_business",
     "url":  "https://en.antaranews.com/rss/business-investment.xml",
     "lang": "en", "full_text": True, "rate_limit": 60, "timeout": 15},
    {"name": "antara_press",
     "url":  "https://en.antaranews.com/rss/press-release.xml",
     "lang": "en", "full_text": False, "rate_limit": 90, "timeout": 15},
    {"name": "mining_technology",
     "url":  "https://www.mining-technology.com/feed/",
     "lang": "en", "full_text": False, "rate_limit": 60, "timeout": 15},
    {"name": "mongabay",
     "url":  "https://news.mongabay.com/feed/",
     "lang": "en", "full_text": False, "rate_limit": 90, "timeout": 15},
    # --- Relief/Conflict ---
    {"name": "reliefweb_drc",
     "url":  "https://reliefweb.int/updates/rss.xml?country=cod",
     "lang": "en", "full_text": False, "rate_limit": 120, "timeout": 15},
    {"name": "gdacs",
     "url":  "https://www.gdacs.org/xml/rss.xml",
     "lang": "en", "full_text": False, "rate_limit": 120, "timeout": 10},
    # --- GEO-11: Refino europeo ---
    {"name": "yle_news_en",
     "url":  "https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_NEWS",
     "lang": "en", "full_text": False, "rate_limit": 90, "timeout": 15},
    {"name": "energy_storage_news",
     "url":  "https://www.energy-storage.news/feed/",
     "lang": "en", "full_text": False, "rate_limit": 90, "timeout": 15},
    # --- Google News ---
    # Audit 2026-05-17: 5 de 6 búsquedas devuelven 0 artículos consistentemente
    # (gnews_cobalt_en, gnews_cobalt_fr, gnews_drc, gnews_durban, gnews_europe_refining).
    # Google ha estado restringiendo el RSS de Google News progresivamente desde
    # 2024. Eliminadas del config. Solo se conserva la que sí entrega contenido.
    {"name": "gnews_indonesia_nickel",
     "url":  "https://news.google.com/rss/search?q=Indonesia+nickel+cobalt+HPAL+disruption&hl=en-US&gl=US&ceid=US:en",
     "lang": "en", "full_text": False, "rate_limit": 300, "timeout": 10},

    # --- Fase 1.5 (2026-05-17): fuentes nuevas tras curl-test desde GCP ---
    # Las 9 candidatas que devolvieron HTTP 200 + RSS válido en la auditoría.
    # Ver feedback_no_flattery.md y el commit de Fase 1.5 para metodología.

    # Tier 1: cobalto-específicas / mining specialist
    {"name": "cobalt_institute",
     "url":  "https://www.cobaltinstitute.org/category/news/feed/",
     "lang": "en", "full_text": True, "rate_limit": 60, "timeout": 15},
    # cleantechnica_cobalt eliminada (audit forense 2026-05-17): el feed devolvía
    # 45 artículos en archivo pero el más reciente tenía 20 días. CleanTechnica
    # publica sobre cobalto ~1 vez cada 20 días, fuera del filtro útil de 48h.
    {"name": "australian_mining",
     "url":  "https://www.australianmining.com.au/feed/",
     "lang": "en", "full_text": False, "rate_limit": 60, "timeout": 15},
    {"name": "resource_world",
     "url":  "https://resourceworld.com/feed/",
     "lang": "en", "full_text": False, "rate_limit": 60, "timeout": 15},
    {"name": "ns_energy",
     "url":  "https://www.nsenergybusiness.com/feed/",
     "lang": "en", "full_text": False, "rate_limit": 60, "timeout": 15},

    # Tier 2: commodities financieras / generales
    {"name": "cnbc_commodities",
     "url":  "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147",
     "lang": "en", "full_text": False, "rate_limit": 90, "timeout": 15},
    # oilprice_main: audit forense del anchor cobalt (2026-05-17) detectó GAP=4
    # en 10 artículos. El summary del RSS (~550ch) era demasiado corto y se
    # perdían menciones cobalto presentes en el cuerpo. full_text=True añade
    # ~30s al run pero captura 4× más anchors de esta fuente específicamente.
    {"name": "oilprice_main",
     "url":  "https://oilprice.com/rss/main",
     "lang": "en", "full_text": True, "rate_limit": 90, "timeout": 15},
    {"name": "investing_commodities",
     "url":  "https://www.investing.com/rss/news_25.rss",
     "lang": "en", "full_text": False, "rate_limit": 90, "timeout": 15},

    # radio_okapi eliminada (audit forense 2026-05-17): el feed devolvía 30 items
    # pero el más reciente tenía 644h (27 días). Probablemente esa URL apunta a
    # un archivo histórico, no al feed en vivo del sitio. Sin saber la URL real
    # del feed actual (requeriría inspección manual del sitio), eliminada del config.
]

SCRAPING_SOURCES = [
    {"name": "transnet_durban",
     "url":  "https://www.transnet.net/BusinessWithTransnet/TPT/Pages/PortofDurban.aspx",
     "lang": "en", "timeout": 20, "rate_limit": 300},
    {"name": "tpa_tanzania",
     "url":  "https://www.tanzaniaports.go.tz/index.php/news",
     "lang": "en", "timeout": 20, "rate_limit": 300},
    {"name": "cfm_mozambique",
     "url":  "https://www.cfmnet.co.mz/noticias",
     "lang": "pt", "timeout": 20, "rate_limit": 300},
]

# ---------------------------------------------------------------------------
# NewsAPI.org queries (Fase 1.5+, 2026-05-17)
# ---------------------------------------------------------------------------
# Cada query gasta 1 request del free tier (100/día). 3 runs/día × 3 queries
# = 9 req/día, sobra margen para iterar las queries sin agotar cuota.
#
# Diseño: 3 queries complementarias que cubren los 3 vectores principales:
#   1. Cobalto explícito + signals de disrupción/supply chain
#   2. Geografías cobalto-críticas + minería (captura artículos donde "cobalt"
#      no aparece literal pero el contexto geo-mining lo implica)
#   3. Tecnologías sustitutas (DEM-SUBSTITUTE: LFP, sodium-ion, etc.) que
#      reducen demanda de cobalto
#
# Sintaxis NewsAPI Boolean: https://newsapi.org/docs/endpoints/everything
# AND/OR/NOT, "frases entre comillas", paréntesis para precedencia.
# ---------------------------------------------------------------------------

NEWS_API_QUERIES = [
    # Vector 1: cobalto explícito + signals de disrupción/supply
    '"cobalt" AND (mining OR refining OR supply OR export OR shortage OR price OR strike OR ban OR sanctions)',

    # Vector 2: geografías cobalto-críticas + minería
    # (captura artículos sobre DRC/Zambia/Indonesia mining donde "cobalt" no
    # aparece pero el contexto sí: militias en Katanga, huelgas en Kolwezi,
    # huracanes en Mozambique con corredor, etc.)
    '("Katanga" OR "Kolwezi" OR "Lualaba" OR "DRC mining" OR "Congo mining" OR "Zambia Copperbelt" OR "Sulawesi nickel") AND (strike OR conflict OR export OR ban OR closure OR disruption)',

    # Vector 3: tecnologías sustitutas (DEM-SUBSTITUTE)
    '("LFP battery" OR "cobalt-free battery" OR "sodium-ion battery" OR "solid state battery") AND (production OR adoption OR breakthrough OR commercial)',
]

# ---------------------------------------------------------------------------
# GNews.io queries (Fase 1.5+, 2026-05-17)
# ---------------------------------------------------------------------------
# Estructura idéntica a NEWS_API_QUERIES — sintaxis Boolean compatible. Las
# mismas 3 queries vectores. La diferencia operacional con NewsAPI:
#   - GNews es real-time (sin delay 24h)
#   - GNews tiene ~60K fuentes vs ~150K de NewsAPI (menos cobertura)
#   - Mismas 100 req/día free tier
# Tener ambos APIs activos = 200 req/día efectivos con cobertura complementaria
# (GNews fresca + NewsAPI más profunda). Los duplicados que devuelven ambos
# son filtrados por `is_duplicate_article` (URL match).
# ---------------------------------------------------------------------------

GNEWS_QUERIES = [
    # Vector 1: cobalto explícito + signals de disrupción/supply
    '"cobalt" AND (mining OR refining OR supply OR export OR shortage OR price OR strike OR ban OR sanctions)',

    # Vector 2: geografías cobalto-críticas + minería
    '("Katanga" OR "Kolwezi" OR "Lualaba" OR "DRC mining" OR "Congo mining" OR "Zambia Copperbelt" OR "Sulawesi nickel") AND (strike OR conflict OR export OR ban OR closure OR disruption)',

    # Vector 3: tecnologías sustitutas (DEM-SUBSTITUTE)
    '("LFP battery" OR "cobalt-free battery" OR "sodium-ion battery" OR "solid state battery") AND (production OR adoption OR breakthrough OR commercial)',
]

# ---------------------------------------------------------------------------
# 7. NIVELES (semáforo) — formato [(umbral_max_excluyente, NOMBRE, color), …]
# ---------------------------------------------------------------------------

SSC_LEVELS = [
    (16,            "VERDE",    "verde"),
    (31,            "AMARILLO", "amarillo"),
    (51,            "NARANJA",  "naranja"),
    (math.inf,      "ROJO",     "rojo"),
]
SMC_LEVELS = [
    (21,            "VERDE",    "verde"),
    (41,            "AMARILLO", "amarillo"),
    (66,            "NARANJA",  "naranja"),
    (math.inf,      "ROJO",     "rojo"),
]

ALERT_THRESHOLDS = {
    "ssc_min": 31,
    "smc_min": 41,
    "combined_ssc": 20,
    "combined_smc": 30,
}

# ---------------------------------------------------------------------------
# 8. PROMPTS GEMINI — templates con placeholders {title} y {body}
# ---------------------------------------------------------------------------

GEMINI_VALIDATE_PROMPT = (
    "You are an analyst monitoring cobalt supply chain disruptions.\n"
    "Title: {title}\n"
    "Text: {body}\n\n"
    "Does this article describe a real, current disruption or significant risk "
    "to cobalt supply chains (mining, transport, export, conflict, labor, regulation)?\n"
    "Answer only: YES or NO"
)

GEMINI_MULTIPLIER_PROMPT = (
    "You are an analyst monitoring cobalt supply chain disruptions.\n"
    "Title: {title}\n"
    "Text: {body}\n\n"
    "Rate the relevance of this article to cobalt supply chain disruption risk:\n"
    "0.0 = not relevant\n"
    "0.5 = marginally relevant\n"
    "1.0 = clearly relevant\n"
    "1.5 = highly relevant and urgent\n"
    "Answer only with one of these numbers: 0.0, 0.5, 1.0, or 1.5"
)

# ---------------------------------------------------------------------------
# 9. AssetConfig — instancia única que se pasa al framework
# ---------------------------------------------------------------------------

COBALT_CONFIG = AssetConfig(
    asset_name="cobalt",
    asset_display="COBALTO",
    anchor_terms=ANCHOR_TERMS,
    geographic_terms=GEOGRAPHIC_TERMS,
    geo_weights=GEO_WEIGHTS,
    keywords=KEYWORDS,
    category_multipliers=CATEGORY_MULTIPLIERS,
    ssc_category_weights=SSC_CATEGORY_WEIGHTS,
    smc_category_overrides=SMC_CATEGORY_OVERRIDES,
    all_negation_terms=ALL_NEGATION_TERMS,
    coup_context_terms=COUP_CONTEXT_TERMS,
    false_positive_filters=FALSE_POSITIVE_FILTERS,
    source_credibility=SOURCE_CREDIBILITY,
    rss_sources=RSS_SOURCES,
    scraping_sources=SCRAPING_SOURCES,
    ssc_levels=SSC_LEVELS,
    smc_levels=SMC_LEVELS,
    alert_thresholds=ALERT_THRESHOLDS,
    generic_geo_terms=GENERIC_GEO_TERMS,
    generic_only_penalty=0.40,
    raw_min_threshold=3.0,
    final_min_threshold=1.0,
    negation_attenuation=0.15,
    gemini_score_threshold=8.0,
    gemini_context_min=3,
    context_trigger_terms=CONTEXT_TRIGGER_TERMS,
    gemini_validate_prompt=GEMINI_VALIDATE_PROMPT,
    gemini_multiplier_prompt=GEMINI_MULTIPLIER_PROMPT,
    no_decay_categories=NO_DECAY_CATEGORIES,
    news_api_queries=NEWS_API_QUERIES,
    # Activado tras audit forense 2026-05-17: el truncado del free tier perdía
    # 5 de 6 anchors cobalto. fetch_url completa la página de cada artículo.
    news_api_full_text=True,
    # GNews.io (Fase 1.5+, 2026-05-17): API complementaria a NewsAPI, real-time
    # (sin delay de 24h). Mismas queries por simplicidad — dedup filtra los que
    # coinciden con NewsAPI. full_text=True desde el primer momento (lección
    # aprendida del truncado del free tier).
    gnews_queries=GNEWS_QUERIES,
    gnews_full_text=True,
)
