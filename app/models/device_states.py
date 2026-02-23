from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class DeviceStates:
    def __init__(self, mapping=None):
        self.devices_inited = False
        self.data = None
        self.printer_progress = 0
        self._field_specs = {}

        # Runtime-critical defaults; mapping fields are declarative and optional.
        self.sleep_mode_changed = False
        self.sleep_mode_original = None
        self.sleep_mode = False

        self._configure_fields(mapping)

    def _configure_fields(self, mapping=None):
        fields = {}
        if isinstance(mapping, dict):
            candidate = mapping.get("fields")
            if isinstance(candidate, dict):
                fields = candidate

        self._field_specs = fields
        for attr, spec in fields.items():
            if not isinstance(spec, dict):
                continue
            default = spec.get("default")
            if not hasattr(self, attr):
                setattr(self, attr, default)

            if spec.get("track_original"):
                original_attr = f"{attr}_original"
                changed_attr = f"{attr}_changed"
                if not hasattr(self, original_attr):
                    setattr(self, original_attr, None)
                if not hasattr(self, changed_attr):
                    setattr(self, changed_attr, False)

    def update_states(self, data, mapping=None):
        self.data = data or {}

        if mapping is not None:
            self._configure_fields(mapping)

        for attr, spec in self._field_specs.items():
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
