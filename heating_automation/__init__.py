"""
Custom integration to provide adaptive scheduling in Home Assistant.

For more details about this integration, please refer to URL
"""

import asyncio
import logging

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    NAME,
    PLATFORMS
)

from .helpers import (
    get_room_entities
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=10)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):

    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    coordinator = HeatingAutomationCoordinator(hass, entry)
    _LOGGER.debug("Coordinator refresh triggered")
    await coordinator.async_refresh()
    _LOGGER.debug("Coordinator refresh completed")

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Setup platforms
    for platform in PLATFORMS:
        coordinator.platforms.append(platform)
        hass.async_add_job(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    entry.add_update_listener(async_reload_entry)
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

class HeatingAutomationCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, config):
        self.platforms = []
        self.hass = hass
        self._rooms = get_room_entities(hass)
        self._flow_temp = hass.data['sensor'].get_entity('sensor.panasonic_heat_pump_main_main_target_temp')
        self._ambient_temp = hass.data['sensor'].get_entity('sensor.panasonic_heat_pump_main_outside_temp')
        super().__init__(
            hass,
            _LOGGER,
            name = NAME,
            update_interval = SCAN_INTERVAL
        )

    async def _async_update_data(self):
        _LOGGER.debug("Heating Automation polled")
        return True

    @property 
    def rooms(self):
        return self._rooms
    
    @property
    def flow_temperature(self):
        return self._flow_temp.state
        
    @property    
    def outside_temperature(self):
        return self._ambient_temp.state
