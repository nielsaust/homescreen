
import logging
from queue import Queue
import time
import sys

from app.controllers.deferred_mqtt_controller import DeferredMqttController
from app.observability import logger as log_setup
from app.services.app_runtime_config_service import AppRuntimeConfigService
from app.services.music_service import MusicService
from app.services.app_composition_service import AppCompositionService
from app.services.music_metrics_service import MusicMetricsService
from app.services.network_bootstrap_service import NetworkBootstrapService
from app.services.queue_pump_service import QueuePumpService
from app.services.system_info_service import SystemInfoService
from app.ui.widgets.network_status_widget import NetworkStatusWidget
from app.config.settings import Settings
from app.config.mqtt_topics import apply_mqtt_topics_to_settings
from app.config.mqtt_routes import load_mqtt_routes, resolve_topic_routes
from app.config.device_state_mapping import load_device_state_mapping
from app.config.settings_paths import resolve_settings_path
from app.observability.sentry_setup import init_sentry
from app.observability.domain_logger import log_event

import tkinter as tk

# Initialize logging
log_setup.setup_logging()
logger = logging.getLogger(__name__)

class MainApp:
    def __init__(self, root):
        log_event(logger, logging.INFO, "app", "startup.begin", at=self.print_current_datetime())
        self.settings = Settings(str(resolve_settings_path()))
        self.mqtt_topics = apply_mqtt_topics_to_settings(self.settings)
        self.mqtt_routes = resolve_topic_routes(self.mqtt_topics, load_mqtt_routes())
        self.device_state_mapping = load_device_state_mapping()
        log_setup.apply_runtime_logging_policy(self.settings)
        init_sentry(self.settings)
        self.composition_service = AppCompositionService(self)
        self.composition_service.compose_event_pipeline()
        self._log_runtime_policy()
        self._init_bootstrap_services()
        self._init_runtime_context(root)
        self._init_state_and_timestamps()
        self.publish_event(
            "app.started",
            {
                "system_platform": self.system_info["system_platform"],
                "is_desktop": self.system_info["is_desktop"],
                "startup_queue_size": 0,
                "version": getattr(self.settings, "version", None),
            },
        )

        asyncio_logger = logging.getLogger('asyncio')
        asyncio_logger.setLevel(logging.WARNING)
        self.observability_service.install_global_exception_hook()
        self.app_lifecycle_service.start()

    def _log_runtime_policy(self):
        log_event(
            logger,
            logging.INFO,
            "app",
            "logging.policy_applied",
            root=getattr(self.settings, "log_level", "AUTO"),
            console=getattr(self.settings, "log_console_level", getattr(self.settings, "console_log_level", "INFO")),
            file=getattr(self.settings, "log_file_level", getattr(self.settings, "file_log_level", "DEBUG")),
        )

    def _init_bootstrap_services(self):
        self.network_bootstrap_service = NetworkBootstrapService(self)
        self.system_info_service = SystemInfoService()
        self.network_bootstrap_service.wait_for_internet_connection()

    def _init_runtime_context(self, root):
        self.root = root
        self.root.geometry(f"{self.settings.screen_width}x{self.settings.screen_height}")
        self.mqtt_message_queue = Queue()
        self.ui_intent_queue = Queue()
        self.runtime_config_service = AppRuntimeConfigService(self.settings)
        self.runtime_config_service.apply_to(self)

        self.queue_pump_service = QueuePumpService(self)
        self.mqtt_controller = DeferredMqttController()
        self.mqtt_initialized = False
        self.mqtt_connected = False
        setattr(self.settings, "mqtt_runtime_connected", False)
        self.music_service = MusicService()
        self.music_metrics_service = MusicMetricsService(self, self.music_metrics_interval_ms)
        self.network_status_widget = NetworkStatusWidget(self.root, self.settings.feedback_icon_size)
        self.system_info = self.system_info_service.detect_platform()
        self.composition_service.compose_runtime_components()
        self.store.subscribe(self._on_state_changed)
        self._enqueue_ui_intent({"type": "network.status", "online": self.store.get_state().network_online})

        log_event(logger, logging.INFO, "music", "debug_logging", enabled=self.music_debug_logging)
        log_event(
            logger,
            logging.INFO,
            "music",
            "metrics_logging.mode",
            purpose="observability_only",
            affects_runtime_behavior=False,
        )
        log_event(logger, logging.INFO, "mqtt", "feature.enabled", enabled=self.enable_mqtt)
        log_event(logger, logging.INFO, "music", "feature.enabled", enabled=self.enable_music)
        log_event(logger, logging.INFO, "weather", "feature.enabled", enabled=self.enable_weather)

    def _init_state_and_timestamps(self):
        self.music_object = None
        self.boot_time = time.time()
        self.time_last_action = time.time()

    def update_network_status_ui(self, online):
        if hasattr(self, "network_status_widget") and self.network_status_widget:
            self.network_status_widget.set_online(bool(online))

    def _on_state_changed(self, state, event):
        intents = self.ui_intent_mapper_service.map_event(state, event)
        for intent in intents:
            self._enqueue_ui_intent(intent)

    def _enqueue_ui_intent(self, intent):
        self.queue_pump_service.enqueue_ui_intent(intent)

    def is_network_available(self, timeout=2):
        return self.network_bootstrap_service.is_network_available(timeout=timeout)

    def is_mqtt_enabled(self):
        return bool(getattr(self, "enable_mqtt", False))

    def is_mqtt_connected(self):
        return bool(getattr(self, "mqtt_connected", False))

    def is_music_enabled(self):
        return bool(getattr(self, "enable_music", False))

    def is_weather_enabled(self):
        return bool(getattr(self, "enable_weather", False))

    def is_any_feature_enabled(self):
        return self.is_mqtt_enabled() or self.is_music_enabled() or self.is_weather_enabled()

    def is_any_visual_feature_enabled(self):
        return self.is_music_enabled() or self.is_weather_enabled()

    def get_topic(self, key: str, default: str = "") -> str:
        value = ""
        if hasattr(self, "mqtt_topics") and isinstance(self.mqtt_topics, dict):
            value = str(self.mqtt_topics.get(key, "")).strip()
        if value:
            return value
        return str(default or "").strip()

    def notify_setup_required(self, setup_name: str):
        message = f"First complete {setup_name} setup"
        log_event(logger, logging.WARNING, "app", "setup.required", setup=setup_name)
        if hasattr(self, "display_controller") and self.display_controller:
            self.display_controller.place_action_label(text=message)

    def init_mqtt(self):
        self.mqtt_lifecycle_service.init_mqtt()

    def request_menu_navigation(self, command: str, source: str = "main"):
        self.publish_event(
            "menu.navigation.requested",
            {"command": command},
            source=source,
        )

    def request_overlay(self, command: str, payload=None, source: str = "main"):
        event_payload = {"command": command}
        if payload:
            event_payload.update(payload)
        self.publish_event("ui.overlay.requested", event_payload, source=source)
    ###### SYSTEM ######
    def print_memory_usage(self):
        self.system_info_service.log_memory_usage()

    def signal_handler(self, sig, frame):
        # Perform cleanup and exit gracefully
        log_event(logger, logging.INFO, "app", "shutdown.requested", reason="ctrl_c")
        sys.exit(0)

    def print_current_datetime(self):
        observability = getattr(self, "observability_service", None)
        if observability is not None:
            return observability.startup_timestamp()
        return time.strftime("%d %b %Y - %H:%M")

    def publish_event(self, event_type, payload=None, source="main"):
        self.event_dispatch_service.publish_event(event_type, payload=payload, source=source)

    def log_music_debug(self, message, payload=None):
        self.observability_service.log_music_debug(message, payload)

    def record_music_metric(self, key, amount=1):
        self.music_metrics_service.record(key, amount)

    def trace_ui_event(self, event_name, **fields):
        self.observability_service.trace_ui_event(event_name, **fields)

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = MainApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Unhandled exception: {e}")
        sys.exit(1)
