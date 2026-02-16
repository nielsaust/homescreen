from __future__ import annotations

from core.event_bus import EventBus
from core.state import AppState
from core.store import AppStore

from app.models.device_states import DeviceStates
from app.controllers.mqtt_message_router import MqttMessageRouter
from app.controllers.media_controller import MediaController
from app.controllers.screen_state_controller import ScreenStateController
from app.controllers.ui_intent_handler import UiIntentHandler
from app.services.app_lifecycle_service import AppLifecycleService
from app.services.app_observability_service import AppObservabilityService
from app.services.event_dispatch_service import EventDispatchService
from app.services.interaction_service import InteractionService
from app.services.mqtt_lifecycle_service import MqttLifecycleService
from app.services.music_playback_policy_service import MusicPlaybackPolicyService
from app.services.music_state_service import MusicStateService
from app.services.music_update_service import MusicUpdateService
from app.services.power_policy_service import PowerPolicyService
from app.services.startup_sync_service import StartupSyncService
from app.services.startup_action_service import StartupActionService
from app.services.ui_intent_mapper_service import UiIntentMapperService


class AppCompositionService:
    """Composes app event pipeline and runtime components."""

    def __init__(self, main_app):
        self.main_app = main_app

    def compose_event_pipeline(self) -> None:
        self.main_app.event_bus = EventBus()
        self.main_app.store = AppStore(AppState())
        self.main_app.event_bus.subscribe(self.main_app.store.dispatch)
        self.main_app.event_dispatch_service = EventDispatchService(self.main_app)
        self.main_app.observability_service = AppObservabilityService(self.main_app)

    def compose_runtime_components(self) -> None:
        self.main_app.device_states = DeviceStates()

        from app.controllers.touch_controller import TouchController
        self.main_app.touch_controller = TouchController(self.main_app)

        from app.controllers.display_controller import DisplayController
        self.main_app.display_controller = DisplayController(self.main_app)

        self.main_app.screen_state_controller = ScreenStateController(self.main_app)
        self.main_app.mqtt_message_router = MqttMessageRouter(self.main_app)
        self.main_app.mqtt_lifecycle_service = MqttLifecycleService(self.main_app)
        self.main_app.media_controller = MediaController(self.main_app)
        self.main_app.ui_intent_handler = UiIntentHandler(self.main_app)
        self.main_app.interaction_service = InteractionService(self.main_app)
        self.main_app.music_state_service = MusicStateService(self.main_app)
        self.main_app.music_update_service = MusicUpdateService(self.main_app)
        self.main_app.music_playback_policy_service = MusicPlaybackPolicyService(self.main_app)
        self.main_app.power_policy_service = PowerPolicyService(self.main_app)
        self.main_app.startup_sync_service = StartupSyncService(self.main_app)
        self.main_app.startup_action_service = StartupActionService(self.main_app)
        self.main_app.ui_intent_mapper_service = UiIntentMapperService()
        self.main_app.app_lifecycle_service = AppLifecycleService(self.main_app)
