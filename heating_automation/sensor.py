"""WiserAutomationRoomEntity class"""
from datetime import date, time, datetime, timedelta
import logging

_LOGGER = logging.getLogger(__name__)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
    SensorEntity,
)

from homeassistant.helpers.entity import EntityCategory

from homeassistant.core import callback

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION, NAME, MIN_TEMP, HEATING_RATES

from .helpers import (
    string_to_date,
    room_name_from_control_entity,
    heating_time
)

HEATING = 1
COOLING = 2
HOLDING = 3

async def async_setup_entry(hass, config, async_add_entities):
    coordinator = hass.data[DOMAIN][config.entry_id]
    entities = [AutomationRoom(room, coordinator, config) for room in coordinator.rooms]
    async_add_entities(entities)

class AutomationRoom(CoordinatorEntity, SensorEntity):
    def __init__(self, room, coordinator, config):
        super().__init__(coordinator)
        self._room = room
        self._control_state = HOLDING
        self._planned_sched_change = string_to_date(self.next_schedule_change)
        self._planned_target = self.next_target_temp
        self._ontime = None 
        self._ontemp = None
        self._offtime = None
        self._offtemp = None
        self._flow_temp = None
        self._ambient_temp = None
        self.coordinator = coordinator
        self.config_entry = config
 
    @property
    def room_name(self):
        """Return the name of the sensor."""
        return room_name_from_control_entity(self._room) 

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{NAME} {self.room_name}" 

    @property
    def state(self):
        curr_temp = self.current_temperature
        curr_target = self.target_temperature
        next_target = self.next_target_temp
        if next_target != curr_target:
            heat_delay = heating_time(self.room_name, curr_temp, next_target, float(self.flow_temp), float(self.outside_temp))
        else:
            heat_delay = 0
            
        return int(heat_delay+0.5)

    @property
    def unique_id(self):
        return f"{self.config_entry.entry_id}{self._room.name}"

    @property
    def extra_state_attributes(self):
        attrs = {}
        attrs["next_target_temp"] = self.next_target_temp
        attrs["next_schedule_change"] = self.next_schedule_change
        attrs["control_state"] = self._control_state
        attrs["on_temperature"] = self._ontemp
        attrs["on_time"] = self._ontime
        attrs["off_temperature"] = self._offtemp
        attrs["off_time"] = self._offtime
        attrs["target_temperature"] = self._planned_target
        attrs["flow_temp"] = self._flow_temp
        attrs["ambient_temp"] = self._ambient_temp
        attrs["predicted_time"] = self._planned_sched_change - timedelta(minutes = self.state)
        return attrs

    @property
    def current_temperature(self):
        return self._room.current_temperature

    @property
    def target_temperature(self):
        if self._room.target_temperature is None:
            return self._room.min_temp
        else:
            return self._room.target_temperature

    @property
    def next_target_temp(self):
        return self._room.extra_state_attributes.get("next_schedule_temp", self.target_temperature)
            
    @property
    def next_schedule_change(self):
        return self._room.extra_state_attributes.get("next_schedule_datetime", datetime.now()+timedelta(days=36))
 
    @property
    def flow_temp(self):
        return self.coordinator.flow_temperature

    @property
    def outside_temp(self):
        return self.coordinator.outside_temperature

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        
        ontime = self._planned_sched_change - timedelta(minutes = self.state)

        if self._control_state == HEATING and self.current_temperature >= self._planned_target:
            self._control_state = HOLDING
            self._offtime = datetime.now()
            self._offtemp = self.current_temperature
            if self._flow_temp is None:
                self._flow_temp = float(self.flow_temp)
            else:
                self._flow_temp = (self._flow_temp + float(self.flow_temp))/2
            if self._ambient_temp is None:
                self._ambient_temp = float(self.outside_temp)
            else:
                self._ambient_temp = (self._ambient_temp + float(self.outside_temp))/2

        if self._control_state == COOLING and self.current_temperature <= self._planned_target:
            self._control_state = HOLDING
            self._offtime = datetime.now()
            self._offtemp = self.current_temperature
            if self._flow_temp is None:
                self._flow_temp = float(self.flow_temp)
            else:
                self._flow_temp = (self._flow_temp + float(self.flow_temp))/2
            if self._ambient_temp is None:
                self._ambient_temp = float(self.outside_temp)
            else:
                self._ambient_temp = (self._ambient_temp + float(self.outside_temp))/2
            
        if self.state > 0 and ontime < datetime.now() and self._control_state != HEATING:
            self._control_state = HEATING
            self._ontime = datetime.now()
            self._ontemp = self.current_temperature
            self._flow_temp = float(self.flow_temp)
            self._ambient_temp = float(self.outside_temp)
            
            """hass.services.async_call("climate", "set_preset_mode", {"preset_mode": "Advance Schedule"}, False, None, None, {"entity_id": "climate.wiser_chrissie_s_study"}) fails withou logged error """
            """self._room.async_set_preset_mode("Advance Schedule") fails without logged error"""

            self.coordinator.hass.bus.fire(DOMAIN + "_event",{"room":self._room.entity_id})

        next_sched_change = string_to_date(self.next_schedule_change)
        if self._planned_sched_change < next_sched_change:
            if self._control_state != HOLDING:
                self._offtime = datetime.now()
                self._offtemp = self.current_temperature
                if self._flow_temp is None:
                    self._flow_temp = float(self.flow_temp)
                else:
                    self._flow_temp = (self._flow_temp + float(self.flow_temp))/2
                if self._ambient_temp is None:
                    self._ambient_temp = float(self.outside_temp)
                else:
                    self._ambient_temp = (self._ambient_temp + float(self.outside_temp))/2
                    self._control_state = HOLDING
                
            if self._planned_target < self.current_temperature:
                self._ontime = datetime.now()
                self._ontemp = self.current_temperature
                self._flow_temp = float(self.flow_temp)
                self._ambient_temp = float(self.outside_temp)
                self.control_state = COOLING

            self._planned_sched_change = next_sched_change
            self._planned_target = self.next_target_temp
            
        self.async_write_ha_state()