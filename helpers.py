from datetime import date, time, datetime, timedelta
from custom_components.wiser.const import DOMAIN, ENTITY_PREFIX

from .const import HEATING_RATES, CONTROLNAME

def get_room_entities(hass):
    return [e for e in hass.data.get('climate').entities if DOMAIN in e.entity_id and room_name_from_control_entity(e) in HEATING_RATES]
    
def room_name_from_control_entity(e):
    return e.name.replace(CONTROLNAME,'').strip()

def string_to_date(s):
    return datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    
def heating_time(room, curr, target, flow, oat):
    mid = (curr + target)/2
    gain = target - curr
    hf = flow - mid
    cf = mid - oat
    if gain > 0:
        if hf > 0 and room in HEATING_RATES:
            coeffs = HEATING_RATES[room]
            heatdelay = (gain / (coeffs[0] + coeffs[1]*hf - coeffs[2]*cf)) * 60
        else:
            heatdelay = 0
    elif gain < 0 and cf > 0 and room in HEATING_RATES:
        coeffs = HEATING_RATES[room]
        heatdelay = (coeffs[0] + coeffs[2]*cf) * gain * 60
    else:
        heatdelay = 0
    
    return heatdelay
