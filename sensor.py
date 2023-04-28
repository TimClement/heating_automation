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

"""
    The possible states of the automation.
        HOLDING     the target temperature has been achieved and the underlying heting controller maintains it.
        COOLING     the underlying controller is not expected to call for heat, as the room is cooling to the target.
        HEATING     the schedule has been advanced so that the target temperature will be met at the scheduled time.
"""

HEATING = 3
COOLING = 1
HOLDING = 2

async def async_setup_entry(hass, config, async_add_entities):
    coordinator = hass.data[DOMAIN][config.entry_id]
    entities = [AutomationRoom(room, coordinator, config) for room in coordinator.rooms]
    for e in entities:
        _LOGGER.error("Set up " + e.name)
    async_add_entities(entities)

class AutomationRoom(CoordinatorEntity, SensorEntity):
    def __init__(self, room, coordinator, config):
        super().__init__(coordinator)
        self._room = room
        self._control_state = HOLDING
        self._ha_next_schedule_change = string_to_date(self.next_schedule_change)
        self._ha_current_target = self.target_temperature
        self._ontime = None
        self._ontemp = None
        self._offtime = None
        self._offtemp = None
        self._flow_temp = None
        self._ambient_temp = None
        self.coordinator = coordinator
        self.config_entry = config

    def log_phase_end(self):
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

    def log_phase_start(self):
        """
            The off time and temperature are not reset because a phase start may immdiately follow a phase end,
            which would overwrite the logged off values. In processing them, we may have to associate te off values with the previous on values.
            The alternative would be to separate off and on across update cycles, going via HOLDING, which would provide at least a small window for the
            off values.
        """
        self._ontime = datetime.now()
        self._ontemp = self.current_temperature
        self._flow_temp = float(self.flow_temp)
        self._ambient_temp = float(self.outside_temp)

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
        """
            The extra attributes provide the session logging data for later analysis.
            During development, we can add debugging information from the room state.
        """
        attrs = {}
        attrs["next_target_temp"] = self.next_target_temp
        attrs["next_schedule_change"] = self.next_schedule_change
        attrs["control_state"] = self._control_state
        attrs["on_temperature"] = self._ontemp
        attrs["on_time"] = self._ontime
        attrs["off_temperature"] = self._offtemp
        attrs["off_time"] = self._offtime
        attrs["target_temperature"] = self._ha_current_target
        attrs["flow_temp"] = self._flow_temp
        attrs["ambient_temp"] = self._ambient_temp
        attrs["planned_schedule_change"] = self._ha_next_schedule_change
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
        """
            Handles periodic updates to the heating automation state for each room.
            Assumes a system without cooling capability, where the schedule is set to give comfortable
            temperatures when the rooms are expected to be occupied, and set back when they are not.
            Hence heating is triggered in advance of a schedule change to allow the room to warm up.
            Cooling is passive in the set back periods, and tracked only to gather thermal performance data.

            The conditions are not mutually exclusive, but the code deals with only one on each cycle.
        """
        next_sched_change = string_to_date(self.next_schedule_change)
        ontime = next_sched_change - timedelta(minutes = self.state)

        if self._ha_next_schedule_change < datetime.now():
            """
                Passed the expected schedule change time. (A user schedule change may mean that this is not the actual one.)
                Log the end of an active phase, and start a new COOLING phase if necessary
            """
            if self._control_state != HOLDING:
                self.log_phase_end()
                self._control_state = HOLDING

            if self.current_temperature > self.target_temperature:
                self.log_phase_start()
                self._control_state = COOLING

            self._ha_next_schedule_change = next_sched_change
            self._ha_current_target = self.target_temperature

        elif self._ha_next_schedule_change != next_sched_change:
            """
                A user change in the schedule affecting the next schedule change.
                The previous case ensures that these events are in the future but we may have used the previous value to
                move to the HEATING state. In this case, we reset to HOLDING, cancel the override, and let the 
                planning resume on the next call.
            """
            if self._ha_next_schedule_change < datetime.now():
                _LOGGER.warning("Assertion that next schedule change is in future violated")
            if self._control_state == HEATING:
                self.log_phase_end()    
                self._control_state = HOLDING
                self.coordinator.hass.bus.fire(DOMAIN + "_event",{"action": "Cancel Overrides", "room":self._room.entity_id})

            self._ha_next_schedule_change = next_sched_change

        elif  (
                (self._control_state == HEATING and self.current_temperature >= self.target_temperature) or
                (self._control_state == COOLING and self.current_temperature <= self.target_temperature)
            ):
            """
                End an active phase when the current target temperature is reached.
                The target can be changed by entering the HEATING state (Advance Schedule), or by the user. Schedule steps are already accounted for.
                If the user raises the target above the current temperature, the underlying controller will provide heat (HOLDING state).
                User changes may result in re-entry to the HEATING state on the next cycle, if the planning time is passed.
            """
            self.log_phase_end()
            self._ha_current_target = self.target_temperature
            self._control_state = HOLDING

        elif self._ha_current_target != self.target_temperature:
            """
                The user has changed the target temperature (since schedule steps are already dealt with).
                HOLDING needs no action - we contine to hold.
                COOLING needs no action, as the previous condition ensures the target temperature is lower than current.
                HEATING is effectively terminated, so we go to HOLDING (and replan on the next cycle)
            """
            if self._control_state == HEATING:
                self.log_phase_end()
                self._control_state = HOLDING

            if self._control_state == COOLING and self.current_temperature <= self.target_temperature:
                _LOGGER.warning("Assertion that continued COOLING requires current temperature above target violated")

            self._ha_current_target = self.target_temperature

        elif ontime < datetime.now():
            """
                Planned schedule advance time has been reached.
            """

            if self._control_state != HOLDING:
                self.log_phase_end()
            self.log_phase_start()
            self._ha_current_target = self.next_target_temp
            self.coordinator.hass.bus.fire(DOMAIN + "_event",{"action": "Advance Schedule", "room":self._room.entity_id})
            self._control_state = HEATING

        self.async_write_ha_state()
