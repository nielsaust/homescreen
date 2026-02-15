from __future__ import annotations


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


class AppRuntimeConfigService:
    """Normalizes runtime settings values used by MainApp/services."""

    def __init__(self, settings):
        self.settings = settings

    def apply_to(self, main_app) -> None:
        main_app.ui_intent_poll_interval_ms = 50
        main_app.mqtt_queue_poll_interval_ms = 50
        main_app.enable_mqtt = _to_bool(getattr(self.settings, "enable_mqtt", False), False)
        main_app.enable_music = _to_bool(getattr(self.settings, "enable_music", False), False)
        main_app.enable_weather = _to_bool(getattr(self.settings, "enable_weather", False), False)

        main_app.ui_trace_logging = _to_bool(getattr(self.settings, "ui_trace_logging", False), False)
        main_app.ui_trace_followup_ms = int(getattr(self.settings, "ui_trace_followup_ms", 80) or 80)

        main_app.music_update_debounce_ms = int(getattr(self.settings, "music_update_debounce_ms", 150) or 150)
        main_app.music_pause_grace_ms = int(getattr(self.settings, "music_pause_grace_ms", 1200) or 1200)
        main_app.music_drop_duplicate_payloads = _to_bool(
            getattr(self.settings, "music_drop_duplicate_payloads", True),
            True,
        )
        main_app.music_apply_transport_immediately = _to_bool(
            getattr(self.settings, "music_apply_transport_immediately", True),
            True,
        )
        main_app.music_debug_logging = _to_bool(getattr(self.settings, "music_debug_logging", False), False)
        main_app.music_metrics_interval_ms = int(
            (getattr(self.settings, "music_metrics_log_interval_seconds", 30) or 30) * 1000
        )

        network_interval = int(
            getattr(
                self.settings,
                "network_status_poll_interval_seconds",
                getattr(self.settings, "network_indicator_check_interval_seconds", 5),
            )
            or 5
        )
        main_app.network_status_poll_interval_ms = max(1, network_interval) * 1000
