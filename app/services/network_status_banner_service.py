from __future__ import annotations


class NetworkStatusBannerService:
    """Builds and applies connectivity banner entries for the top status widget."""

    def __init__(self, main_app):
        self.main_app = main_app

    def refresh(self, online=None) -> None:
        widget = getattr(self.main_app, "network_status_widget", None)
        if widget is None:
            return
        disconnected = self._disconnected_connections(online)
        extra_messages = self._extra_messages()
        widget.set_status(disconnected, extra_messages)

    def _resolved_online(self, online):
        if online is not None:
            return bool(online)
        store = getattr(self.main_app, "store", None)
        if store is None:
            return None
        try:
            state_online = store.get_state().network_online
            return None if state_online is None else bool(state_online)
        except Exception:
            return None

    def _disconnected_connections(self, online) -> list[str]:
        disconnected: list[str] = []
        resolved_online = self._resolved_online(online)
        if resolved_online is False:
            disconnected.append(self.main_app.t("network_banner.connection.internet"))
        if self.main_app.is_mqtt_enabled() and not self.main_app.is_mqtt_connected():
            disconnected.append(self.main_app.t("network_banner.connection.mqtt"))
        return disconnected

    def _extra_messages(self) -> list[dict[str, str]]:
        if not self.main_app.is_weather_enabled():
            return []
        store = getattr(self.main_app, "store", None)
        if store is None:
            return []
        try:
            state = store.get_state()
            if state.weather_source == "cache" and state.weather_cached_at_text:
                return [
                    {
                        "key": "weather:cache",
                        "text": self.main_app.t(
                            "network_banner.weather_last_cached",
                            timestamp=state.weather_cached_at_text,
                        ),
                    }
                ]
        except Exception:
            return []
        return []

