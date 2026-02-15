from __future__ import annotations


class MenuStateResolver:
    """Resolves button visual state from app/settings/device/music state."""

    def __init__(self, main_app):
        self.main_app = main_app

    def resolve(self):
        device_states = self.main_app.device_states
        settings = self.main_app.settings

        harmony_state = device_states.harmony_state or "Off"
        cover_kitchen = device_states.cover_kitchen if device_states.cover_kitchen is not None else 0
        in_bed = bool(device_states.in_bed) if device_states.in_bed is not None else False
        trash_warning = bool(device_states.trash_warning) if device_states.trash_warning is not None else False
        playstation_power = bool(device_states.playstation_power) if device_states.playstation_power is not None else False
        playstation_available = (
            bool(device_states.playstation_available) if device_states.playstation_available is not None else True
        )

        light_tafel = self._light_state(device_states.light_tafel)
        light_keuken = self._light_state(device_states.light_keuken)
        light_kleur = self._light_state(device_states.light_kleur)
        light_woonkamer = self._light_state(device_states.light_woonkamer)

        playing = self.main_app.music_object is not None and self.main_app.music_object.state == "playing"

        return [
            self._spec("cinema", harmony_state != "Off", action_text="[cinema_action]", on_text="uit", off_text="aan"),
            self._spec("cover_kitchen", cover_kitchen < 50, action_text="[cover_action]", on_text="open", off_text="dicht"),
            self._spec("in_bed_toggle", in_bed, action_text="[sleep_mode_action]", on_text="uit", off_text="aan"),
            self._spec("sleep_mode_toggle_option", in_bed, action_text="[sleep_mode_action]", on_text="uit", off_text="aan"),
            self._spec("trash_warning_toggle", trash_warning, action_text="[trash_action]", on_text="uit", off_text="aan"),
            self._spec("music_play_pause", playing, action_text="[music_action]", on_text="Pauzeer", off_text="Speel"),
            self._spec(
                "ps_toggle",
                playstation_power,
                action_text="[ps_action]",
                on_text="uit",
                off_text="aan",
                available=playstation_available,
            ),
            self._spec(
                "light_woonkamer",
                light_woonkamer["state"] == "on",
                action_text="[woonkamer_licht_action]",
                on_text=f"({self._brightness(light_woonkamer['brightness'])}%) uit",
                off_text="aan",
            ),
            self._spec(
                "light_keuken",
                light_keuken["state"] == "on",
                action_text="[keuken_licht_action]",
                on_text=f"({self._brightness(light_keuken['brightness'])}%) uit",
                off_text="aan",
            ),
            self._spec(
                "light_tafel",
                light_tafel["state"] == "on",
                action_text="[tafel_licht_action]",
                on_text=f"({self._brightness(light_tafel['brightness'])}%) uit",
                off_text="aan",
            ),
            self._spec(
                "light_kleur",
                light_kleur["state"] == "on",
                action_text="[kleur_licht_action]",
                on_text=f"({self._brightness(light_kleur['brightness'])}%) uit",
                off_text="aan",
            ),
            self._spec("show_weather_on_idle", bool(settings.show_weather_on_idle)),
            self._spec("media_show_titles", bool(settings.media_show_titles)),
            self._spec("media_sanitize_titles", bool(settings.media_sanitize_titles)),
            self._spec("store_settings", bool(getattr(settings, "store_settings", True))),
        ]

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
