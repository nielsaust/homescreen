from __future__ import annotations


class MqttLifecycleService:
    """Owns MQTT controller lifecycle (init/start/stop)."""

    def __init__(self, main_app):
        self.main_app = main_app

    def init_mqtt(self) -> None:
        if self.main_app.mqtt_initialized:
            return
        from app.controllers.mqtt_controller import MqttController

        self.main_app.mqtt_controller = MqttController(
            self.main_app,
            self.main_app.settings.mqtt_broker,
            self.main_app.settings.mqtt_port,
            self.main_app.settings.mqtt_user,
            self.main_app.settings.mqtt_password,
        )
        self.main_app.mqtt_initialized = True

    def start_mqtt(self) -> None:
        self.main_app.mqtt_controller.start()

    def stop_mqtt(self) -> None:
        self.main_app.mqtt_controller.stop()
