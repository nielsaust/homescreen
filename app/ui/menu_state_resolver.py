from __future__ import annotations

from app.ui.menu_config_loader import get_state_specs


def _to_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off"):
            return False
    if value is None:
        return default
    return bool(value)


class MenuStateResolver:
    """Resolves button visual state from app/settings/device/music state."""

    def __init__(self, main_app):
        self.main_app = main_app

    def resolve(self):
        specs = get_state_specs()
        resolved = []
        for spec in specs:
            resolved_spec = self._resolve_spec(spec)
            if resolved_spec is not None:
                resolved.append(resolved_spec)
        return resolved

    def _resolve_spec(self, spec: dict):
        button_id = spec.get("button_id")
        if not button_id:
            return None

        spec_type = str(spec.get("type", "")).strip()
        active = False
        available = True

        if spec_type == "device_not_equals":
            current = self._get_device_value(spec.get("source"), spec.get("default"))
            active = current != spec.get("value")
        elif spec_type == "device_less_than":
            current = self._get_device_value(spec.get("source"), spec.get("default", 0))
            try:
                active = float(current) < float(spec.get("value", 0))
            except (TypeError, ValueError):
                active = False
        elif spec_type == "device_bool":
            current = self._get_device_value(spec.get("source"), spec.get("default", False))
            active = bool(current)
            available_source = spec.get("available_source")
            if available_source:
                available = bool(self._get_device_value(available_source, spec.get("available_default", True)))
        elif spec_type == "music_state":
            music = getattr(self.main_app, "music_object", None)
            active = music is not None and getattr(music, "state", None) == spec.get("state")
        elif spec_type == "setting_bool":
            active = _to_bool(self._get_settings_value(spec.get("source"), spec.get("default", False)), False)
        elif spec_type == "light":
            light = self._light_state(self._get_device_value(spec.get("source"), {}))
            active = light["state"] == "on"
            brightness = self._brightness(light["brightness"])
            on_text = str(spec.get("on_text", "")).replace("{brightness}", str(brightness))
            return self._spec(
                button_id,
                active,
                action_text=spec.get("action_text", ""),
                on_text=on_text,
                off_text=spec.get("off_text", ""),
                available=available,
            )
        else:
            return None

        return self._spec(
            button_id,
            active,
            action_text=spec.get("action_text", ""),
            on_text=spec.get("on_text", ""),
            off_text=spec.get("off_text", ""),
            available=available,
        )

    def _get_device_value(self, source: str | None, default=None):
        if not source:
            return default
        device_states = self.main_app.device_states
        value = getattr(device_states, source, default)
        return default if value is None else value

    def _get_settings_value(self, source: str | None, default=None):
        if not source:
            return default
        settings = self.main_app.settings
        return getattr(settings, source, default)

    @staticmethod
    def _spec(button_id, active, action_text="", on_text="", off_text="", available=True):
        return {
            "button_id": button_id,
            "active": bool(active),
            "action_text": action_text,
            "on_text": on_text,
            "off_text": off_text,
            "available": bool(available),
        }

    @staticmethod
    def _light_state(value):
        if isinstance(value, dict):
            return {
                "state": value.get("state", "off"),
                "brightness": value.get("brightness", 0) or 0,
            }
        return {"state": "off", "brightness": 0}

    @staticmethod
    def _brightness(brightness):
        if brightness > 0:
            return round((brightness / 256) * 100)
        return 0
