from homeassistant import data_entry_flow, config_entries
from .const import (
    DOMAIN,
    VERSION,
    NAME
)

@config_entries.HANDLERS.register(DOMAIN)

class HeatingAutomationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    # (this is not implemented yet)

    def __init__(self):
        """Initialize HACS options flow."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        return self.async_create_entry(
            title = NAME,
            data = {},
        )
