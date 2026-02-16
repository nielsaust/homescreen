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

    def update_states(self, data, mapping=None):
        self.data = data or {}
        fields = {}
        if isinstance(mapping, dict):
            fields = mapping.get("fields", {}) if isinstance(mapping.get("fields"), dict) else {}

        if not fields:
            fields = {
                "harmony_state": {"source": "harmony_state", "type": "string", "default": "Off"},
                "cover_kitchen": {"source": "cover_kitchen", "type": "float", "default": 0},
                "living_room_temp": {"source": "living_room_temp", "type": "float", "default": 15},
                "light_tafel": {"source": "light_tafel", "type": "light"},
                "light_keuken": {"source": "light_keuken", "type": "light"},
                "light_kleur": {"source": "light_kleur", "type": "light"},
                "light_woonkamer": {"source": "light_woonkamer", "type": "light"},
                "in_bed": {"source": "in_bed", "type": "on_off_bool", "default": False, "track_original": True},
                "trash_warning": {"source": "trash_warning", "type": "on_off_bool", "default": False},
                "bed_heating_on": {"source": "bed_heating_on", "type": "on_off_bool", "default": False},
                "playstation_power": {"source": "playstation_power", "type": "on_off_bool", "default": False},
                "playstation_available": {
                    "source": "playstation_power",
                    "type": "availability",
                    "unavailable_value": "unavailable",
                    "default": True,
                },
            }

        for attr, spec in fields.items():
            if not isinstance(spec, dict):
                continue
            source = str(spec.get("source", attr)).strip() or attr
            raw_value = self.data.get(source)
            if spec.get("track_original"):
                self._track_original_change(attr, raw_value)
            value = self._coerce_value(raw_value, spec)
            setattr(self, attr, value)

        self.devices_inited = True

    def _track_original_change(self, attr, raw_value):
        original_attr = f"{attr}_original"
        changed_attr = f"{attr}_changed"
        previous_original = getattr(self, original_attr, None)
        current_changed = getattr(self, changed_attr, None)
        if current_changed in (None, False):
            setattr(self, changed_attr, previous_original != raw_value)
        setattr(self, original_attr, raw_value)

    def _coerce_value(self, value, spec):
        value_type = str(spec.get("type", "string")).strip().lower()
        default = spec.get("default")
        if value_type == "float":
            return self._as_float(value, default if default is not None else 0)
        if value_type == "on_off_bool":
            return self._as_on_off_bool(value, default=bool(default))
        if value_type == "light":
            return self._normalize_light(value)
        if value_type == "availability":
            unavailable_value = str(spec.get("unavailable_value", "unavailable")).strip().lower()
            normalized = str(value).strip().lower()
            if normalized == "":
                return bool(default) if default is not None else True
            return normalized != unavailable_value
        if value_type == "string":
            if value is None or value == "":
                return default
            return str(value)
        return value if value is not None else default

    def _as_float(self, value, default):
        try:
            if value is None or value == "":
                return float(default)
            return float(value)
        except (TypeError, ValueError):
            logger.error("Could not convert value '%s' to float; using default=%s", value, default)
            return float(default)

    def _as_on_off_bool(self, value, default=False):
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

    def _normalize_light(self, value):
        if isinstance(value, dict):
            state = str(value.get("state", "off")).strip().lower()
            brightness_raw = value.get("brightness", 0)
            try:
                brightness = int(brightness_raw or 0)
            except (TypeError, ValueError):
                brightness = 0
            return {"state": state, "brightness": max(0, brightness)}
        return {"state": "off", "brightness": 0}
