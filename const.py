# Base component constants
NAME = "Heating automation"
DOMAIN = "heating_automation"
DOMAIN_DATA = f"{DOMAIN}.data"
VERSION = "0.0.1"

ENTITY_PREFIX = "HeatingAutomation"
ROOM = "Room"

CONTROLNAME = "Wiser"

# Icons
ICON = "mdi:leaf"

# Platforms
ENTITY = "entity"
PLATFORMS = ["sensor"]

# Defaults
DEFAULT_NAME = DOMAIN
MIN_TEMP = 0

# Coefficients

HEATING_RATES = {
    "Chrissie's study": (0.72,0,0),
    "Clem's room": (1.0,0,0),
    "Dining room": (0.45, 0, 0),
    "En suite": (0.28, 0, 0),
    "Guest room": (0.83, 0, 0),
    "Hall": (0.27, 0, 0),
    "JJ's room": (0.76, 0, 0),
    "Kitchen": (0.19, 0, 0),
    "Landing": (0.26, 0, 0),
    "Living room": (0.34, 0, 0),
    "Main bathroom": (0.49, 0, 0),
    "Main bedroom": (0.62, 0, 0),
    "Music room": (0.71, 0, 0),
    "Utility room": (0.16, 0, 0),
    "Wet room UFH": (0.27, 0, 0)
} 
