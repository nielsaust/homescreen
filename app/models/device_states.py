import logging
logger = logging.getLogger(__name__)

class DeviceStates:
    def __init__(self):
        self.devices_inited = False
        self.data = None
        self.printer_progress = 0
        self.harmony_state = None
        self.cover_kitchen = None
        self.living_room_temp = None
        self.light_tafel = None
        self.light_keuken = None
        self.light_kleur = None
        self.light_woonkamer = None
        self.in_bed_changed = None
        self.in_bed_original = None
        self.in_bed = None
        self.trash_warning = None
        self.bed_heating_on = None
        self.playstation_power = None
        self.playstation_available = None

    def update_states(self,data):
        def _as_float(value, default):
            try:
                if value is None or value == "":
                    return float(default)
                return float(value)
            except (TypeError, ValueError):
                logger.error("Could not convert value '%s' to float; using default=%s", value, default)
                return float(default)

        def _as_on_off_bool(value, default=False):
            if value is None:
                return bool(default)
            if isinstance(value, bool):
                return value
            lowered = str(value).strip().lower()
            if lowered in ("on", "true", "1", "yes"):
                return True
            if lowered in ("off", "false", "0", "no", "unavailable", ""):
                return False
            return bool(default)

        def _normalize_light(value):
            if isinstance(value, dict):
                state = str(value.get("state", "off")).strip().lower()
                brightness_raw = value.get("brightness", 0)
                try:
                    brightness = int(brightness_raw or 0)
                except (TypeError, ValueError):
                    brightness = 0
                return {"state": state, "brightness": max(0, brightness)}
            return {"state": "off", "brightness": 0}

        self.data = data or {}
        self.harmony_state = self.data.get('harmony_state') or "Off"
        self.cover_kitchen = _as_float(self.data.get('cover_kitchen'), 0)
        self.living_room_temp = _as_float(self.data.get('living_room_temp'), 15)
        self.light_tafel = _normalize_light(self.data.get('light_tafel'))
        self.light_keuken = _normalize_light(self.data.get('light_keuken'))
        self.light_kleur = _normalize_light(self.data.get('light_kleur'))
        self.light_woonkamer = _normalize_light(self.data.get('light_woonkamer'))

        next_in_bed_raw = self.data.get('in_bed')
        if hasattr(self, 'in_bed') and self.in_bed_changed in (None, False):
            self.in_bed_changed = self.in_bed_original != next_in_bed_raw
        self.in_bed_original = next_in_bed_raw
        self.in_bed = _as_on_off_bool(next_in_bed_raw, default=False)
        self.trash_warning = _as_on_off_bool(self.data.get('trash_warning'), default=False)
        self.bed_heating_on = _as_on_off_bool(self.data.get('bed_heating_on'), default=False)

        playstation_state = self.data.get('playstation_power')
        self.playstation_power = _as_on_off_bool(playstation_state, default=False)
        self.playstation_available = str(playstation_state).strip().lower() != "unavailable"
        self.devices_inited = True
