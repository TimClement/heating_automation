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

# Codefficients

HEATING_RATES = {
    "Chrissie's study": (1,0,0)
} 
