
import datetime
import json
import logging
import pathlib
from queue import Empty, Queue
import time
import sys

import platform
import psutil
import signal
import ping3

from core.event_bus import EventBus
from core.events import AppEvent
from core.state import AppState
from core.store import AppStore
from app.models.device_states import DeviceStates
from app.controllers.mqtt_message_router import MqttMessageRouter
from app.controllers.media_controller import MediaController
from app.controllers.screen_state_controller import ScreenStateController
from app.controllers.ui_intent_handler import UiIntentHandler
from app.observability import logger as log_setup
from app.services.music_service import MusicService
from app.ui.widgets.network_status_widget import NetworkStatusWidget
from app.config.settings import Settings
from app.observability.sentry_setup import init_sentry
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

import tkinter as tk

# Initialize logging
log_setup.setup_logging()
logger = logging.getLogger(__name__)


class DeferredMqttController:
    """No-op MQTT controller used until network is available."""

    def publish_action(self, action, value=None):
        logger.warning("MQTT not initialized yet; skipping action '%s'", action)

    def publish_message(self, payload=None, topic="screen_commands/outgoing"):
        logger.warning("MQTT not initialized yet; skipping publish to '%s'", topic)

    def start(self):
        return None

    def stop(self):
        return None


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

class MainApp:
    def __init__(self, root):
        logger.info(f"========= NEW STARTUP @ {self.print_current_datetime()} =========")
        # load settings
        self.settings = Settings("settings.json")
        log_setup.apply_runtime_logging_policy(self.settings)
        init_sentry(self.settings)
        self.event_bus = EventBus()
        self.store = AppStore(AppState())
        self.event_bus.subscribe(self.store.dispatch)

        logger.info(
            "Log policy applied (root=%s, console=%s, file=%s)",
            getattr(self.settings, "log_level", "INFO"),
            getattr(self.settings, "console_log_level", "INFO"),
            getattr(self.settings, "file_log_level", "DEBUG"),
        )

        # Wait for an internet connection
        self.wait_for_internet_connection()

        # Set up the root window
        self.root = root
        self.root.geometry(f"{self.settings.screen_width}x{self.settings.screen_height}")
        self.mqtt_message_queue = Queue()
        self.ui_intent_queue = Queue()
        self.ui_intent_poll_interval_ms = 50
        self.ui_trace_logging = _to_bool(getattr(self.settings, "ui_trace_logging", False), False)
        self.ui_trace_followup_ms = int(getattr(self.settings, "ui_trace_followup_ms", 80) or 80)
        self.mqtt_queue_poll_interval_ms = 50
        self.mqtt_controller = DeferredMqttController()
        self.mqtt_initialized = False
        self.music_service = MusicService()
        self.pending_music_payload = None
        self.music_update_after_id = None
        self.music_update_debounce_ms = int(getattr(self.settings, "music_update_debounce_ms", 150) or 150)
        self.music_pause_grace_ms = int(getattr(self.settings, "music_pause_grace_ms", 1200) or 1200)
        self.music_drop_duplicate_payloads = _to_bool(getattr(self.settings, "music_drop_duplicate_payloads", True), True)
        self.music_apply_transport_immediately = _to_bool(
            getattr(self.settings, "music_apply_transport_immediately", True),
            True,
        )
        self.music_debug_logging = _to_bool(getattr(self.settings, "music_debug_logging", False), False)
        self.music_update_seq = 0
        self.music_metrics = {
            "received": 0,
            "coalesced": 0,
            "dropped": 0,
            "applied": 0,
            "art_requests": 0,
            "art_success": 0,
            "art_stale_dropped": 0,
            "art_placeholder": 0,
            "art_errors": 0,
        }
        self.music_metrics_interval_ms = int(
            (getattr(self.settings, "music_metrics_log_interval_seconds", 30) or 30) * 1000
        )
        logger.info("[music] debug logging enabled=%s", self.music_debug_logging)
        self.network_status_widget = NetworkStatusWidget(self.root, self.settings.feedback_icon_size)
        self.store.subscribe(self._on_state_changed)
        self._enqueue_ui_intent(
            {
                "type": "network.status",
                "online": self.store.get_state().network_online,
            }
        )
        network_interval = int(
            getattr(
                self.settings,
                "network_status_poll_interval_seconds",
                getattr(self.settings, "network_indicator_check_interval_seconds", 5),
            )
            or 5
        )
        self.network_status_poll_interval_ms = max(1, network_interval) * 1000

        # Set up system info
        self.system_info = self.checksystem()
        self.publish_event(
            "app.started",
            {
                "system_platform": self.system_info["system_platform"],
                "is_desktop": self.system_info["is_desktop"],
                "startup_queue_size": 0,
                "version": getattr(self.settings, "version", None),
            },
        )
        self.music_object = None
        self.boot_time = time.time()
        self.time_last_action = time.time()
        self.bed_time_timeout_future = None
        self.music_pause_timeout = None
        self.startup_mqtt_messages = {self.settings.mqtt_topic_devices: self.update_device_states, self.settings.mqtt_topic_music: self.check_music_status}
        self.publish_event("startup.queue.size", {"size": len(self.startup_mqtt_messages)})

        # LOGGING asyncio - Check to see if still needed
        asyncio_logger = logging.getLogger('asyncio')
        asyncio_logger.setLevel(logging.WARNING)
        sys.excepthook = self.log_unhandled_exception

        self.device_states = DeviceStates()
        from app.controllers.touch_controller import TouchController
        self.touch_controller = TouchController(self)
        from app.controllers.display_controller import DisplayController
        self.display_controller = DisplayController(self)
        self.screen_state_controller = ScreenStateController(self)
        self.mqtt_message_router = MqttMessageRouter(self)
        self.media_controller = MediaController(self)
        self.ui_intent_handler = UiIntentHandler(self)
        self.touch_controller.bind_events(self.root)

        # Register the signal handler for Ctrl-C
        signal.signal(signal.SIGINT, self.signal_handler)

        self.switch_to_idle()
        self.start_mqtt_queue_pump()
        self.start_ui_intent_pump()
        self.start_network_status_poll()
        self.start_music_metrics_log()
        self.maybe_init_mqtt_if_online()


    def is_internet_connected(self,host="8.8.8.8", port=53, timeout=3):
        try:
            return ping3.ping(host,timeout=timeout) is not None
        except Exception as e:
            logger.info(f"Error checking internet connection: {e}")
            return False

    def wait_for_internet_connection(self):
        timeout_seconds = int(getattr(self.settings, "startup_wait_for_internet_seconds", 0) or 0)
        check_interval_seconds = int(getattr(self.settings, "startup_wait_check_interval_seconds", 5) or 5)

        if timeout_seconds <= 0:
            online = self.is_network_available(timeout=2)
            self.publish_event("network.status", {"online": online})
            if online:
                logger.info("Internet connection is available.")
            else:
                logger.warning("Startup continues in degraded mode (no internet at boot).")
            return

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if self.is_network_available(timeout=2):
                self.publish_event("network.status", {"online": True})
                logger.info("Internet connection is available.")
                return

            self.publish_event("network.status", {"online": False})
            remaining = max(0, int(deadline - time.time()))
            logger.warning("Waiting for internet connection... %ss remaining", remaining)
            time.sleep(check_interval_seconds)

        self.publish_event("network.status", {"online": False})
        logger.warning(
            "No internet after %ss startup wait. Continuing in degraded mode.",
            timeout_seconds,
        )

    def start_network_status_poll(self):
        self.root.after(self.network_status_poll_interval_ms, self._poll_network_status)

    def _poll_network_status(self):
        online = self.is_network_available(timeout=1)
        self.publish_event("network.status", {"online": online}, source="network_poll")
        self.maybe_init_mqtt_if_online(online)
        self.root.after(self.network_status_poll_interval_ms, self._poll_network_status)

    def update_network_status_ui(self, online):
        if hasattr(self, "network_status_widget") and self.network_status_widget:
            self.network_status_widget.set_online(bool(online))

    def _on_state_changed(self, state, event):
        if event.event_type == "network.status":
            self._enqueue_ui_intent(
                {
                    "type": "network.status",
                    "online": state.network_online,
                }
            )
        elif event.event_type == "weather.updated":
            self._enqueue_ui_intent(
                {
                    "type": "weather.cache.status",
                    "source": state.weather_source,
                    "cached_at_text": state.weather_cached_at_text,
                }
            )
        elif event.event_type == "music.updated":
            self._enqueue_ui_intent(
                {
                    "type": "music.render",
                    "state": state.music_state,
                    "title": state.music_title,
                    "artist": state.music_artist,
                    "channel": state.music_channel,
                    "album": state.music_album,
                    "album_art_api_url": state.music_album_art_api_url,
                }
            )
            self._enqueue_ui_intent(
                {
                    "type": "ui.music.playback",
                    "state": state.music_state,
                }
            )
        elif event.event_type == "ui.screen.changed":
            self._enqueue_ui_intent(
                {
                    "type": "ui.screen.changed",
                    "screen": state.screen_state,
                    "is_display_on": state.is_display_on,
                    "force": bool(event.payload.get("force", False)),
                }
            )
            if state.screen_state == "menu":
                self._enqueue_ui_intent(
                    {
                        "type": "menu.refresh",
                    }
                )
        elif event.event_type == "menu.refresh.requested":
            self._enqueue_ui_intent(
                {
                    "type": "menu.refresh",
                }
            )
        elif event.event_type == "menu.navigation.requested":
            self._enqueue_ui_intent(
                {
                    "type": "menu.navigate",
                    "command": event.payload.get("command"),
                }
            )
        elif event.event_type == "ui.overlay.requested":
            self._enqueue_ui_intent(
                {
                    "type": "ui.overlay.requested",
                    "command": event.payload.get("command"),
                    "data": event.payload.get("data"),
                    "url": event.payload.get("url"),
                    "username": event.payload.get("username"),
                    "password": event.payload.get("password"),
                    "progress": event.payload.get("progress"),
                    "reset": bool(event.payload.get("reset", False)),
                }
            )

    def _enqueue_ui_intent(self, intent):
        self.ui_intent_queue.put(intent)

    def start_ui_intent_pump(self):
        self.root.after(self.ui_intent_poll_interval_ms, self._pump_ui_intents)

    def _pump_ui_intents(self):
        handled = 0
        while handled < 100:
            try:
                intent = self.ui_intent_queue.get_nowait()
            except Empty:
                break
            try:
                self._apply_ui_intent(intent)
            except Exception as exc:
                logger.error("Error applying UI intent (%s): %s", intent, exc)
            handled += 1
        if handled > 0:
            self.trace_ui_event(
                "ui.intent.pump",
                handled=handled,
                pending=self.ui_intent_queue.qsize(),
            )
        self.root.after(self.ui_intent_poll_interval_ms, self._pump_ui_intents)

    def _apply_ui_intent(self, intent):
        self.ui_intent_handler.apply(intent)

    def _network_sim_flag_path(self):
        return pathlib.Path(__file__).parent / ".sim" / "network_down.flag"

    def is_network_simulated_down(self):
        if not bool(getattr(self.settings, "enable_network_simulation", True)):
            return False
        return self._network_sim_flag_path().exists()

    def is_network_available(self, timeout=2):
        if self.is_network_simulated_down():
            return False
        return self.is_internet_connected(timeout=timeout)

    def init_mqtt(self):
        if self.mqtt_initialized:
            return
        from app.controllers.mqtt_controller import MqttController
        self.mqtt_controller = MqttController(self, self.settings.mqtt_broker, self.settings.mqtt_port, self.settings.mqtt_user, self.settings.mqtt_password)
        self.mqtt_initialized = True

    def maybe_init_mqtt_if_online(self, online=None):
        if self.mqtt_initialized:
            return
        if online is None:
            online = self.is_network_available(timeout=1)
        if not online:
            return
        logger.info("Network available; initializing MQTT controller.")
        self.init_mqtt()

    def enqueue_mqtt_message(self, topic, data):
        self.mqtt_message_queue.put((topic, data))

    def start_mqtt_queue_pump(self):
        self.root.after(self.mqtt_queue_poll_interval_ms, self._pump_mqtt_queue)

    def _pump_mqtt_queue(self):
        handled = 0
        while handled < 50:
            try:
                topic, data = self.mqtt_message_queue.get_nowait()
            except Empty:
                break

            try:
                self.on_mqtt_message(topic, data)
            except Exception as exc:
                logger.error(f"Error handling queued MQTT message ({topic}): {exc}")
            handled += 1

        self.root.after(self.mqtt_queue_poll_interval_ms, self._pump_mqtt_queue)

    def queue_music_update(self, data):
        self.record_music_metric("received")
        self.music_update_seq += 1
        update_seq = self.music_update_seq
        self.log_music_debug(
            f"[music] queue start seq={update_seq} raw_keys={sorted((data or {}).keys())}",
            data,
        )
        normalized = self.music_service.normalize_payload(data or {})
        self.log_music_debug(f"[music] normalized seq={update_seq}", normalized)
        has_transport = self.music_service.has_transport_update(normalized)
        if has_transport and self.music_apply_transport_immediately:
            self.log_music_debug(f"[music] transport-priority seq={update_seq}")
            self.pending_music_payload = normalized
            if self.music_update_after_id:
                self.root.after_cancel(self.music_update_after_id)
                self.music_update_after_id = None
            self.flush_music_update(reason="transport")
            return

        if self.pending_music_payload is None:
            self.pending_music_payload = normalized
        else:
            # Merge partial updates so fast event bursts don't drop fields.
            self.record_music_metric("coalesced")
            self.pending_music_payload.update(normalized)
        self.log_music_debug(f"[music] pending merged seq={update_seq}", self.pending_music_payload)
        if self.music_update_after_id:
            self.root.after_cancel(self.music_update_after_id)
            self.log_music_debug(f"[music] debounce reset seq={update_seq}")
        self.music_update_after_id = self.root.after(self.music_update_debounce_ms, self.flush_music_update)

    def flush_music_update(self, reason="debounced"):
        self.music_update_after_id = None
        payload = self.pending_music_payload
        self.pending_music_payload = None
        if payload is None:
            self.log_music_debug("[music] flush skipped: no pending payload")
            return
        self.log_music_debug(f"[music] flush pending payload reason={reason}", payload)
        resolved_payload = self.music_service.resolve_payload(self.music_object, payload)
        self.log_music_debug("[music] resolved payload", resolved_payload)
        if not self.music_service.should_process(resolved_payload, drop_duplicates=self.music_drop_duplicate_payloads):
            self.log_music_debug("[music] duplicate payload dropped", resolved_payload)
            self.record_music_metric("dropped")
            return
        self.log_music_debug("[music] applying payload", resolved_payload)
        self.record_music_metric("applied")
        self.update_music_object(resolved_payload)
        self.publish_event(
            "menu.refresh.requested",
            {"reason": "music.update.applied"},
            source="main",
        )

    def perform_action(self, interaction_type):
        self.publish_event("interaction.received", {"interaction_type": interaction_type})
        logger.debug(f"Perform_action: {interaction_type}")
        current_time = time.time()

        if self.touch_controller.ignore_next_click:
            logger.debug(f"Menu click done. Ignoring this next root click")
            self.touch_controller.ignore_next_click = False
            return
        
        if self.display_controller.is_cam_showing():
            logger.debug(f"Cam is showing; so all interactions prohibited")
            return
        
        time_between_actions = current_time - self.time_last_action
        if time_between_actions<self.settings.min_time_between_actions:
            logger.warning(f"Too many actions more or less simultaniously ({time_between_actions}ms); could result in errors so abording. Mostly this is to prevent a button press registered both from TouchController as MenuScreen.")
            return

        self.time_last_action = current_time
        screen_state = self.display_controller.get_screen_state()

        self.check_idle_timer()
        if(not self.display_controller.is_showing):
            if self.settings.show_weather_on_idle and not self.display_controller.is_showing:
                self.display_controller.check_idle(True)
                return
        
        if screen_state is not None:
            # check if we have to wake up screen        
            if screen_state == "weather" or screen_state == "off":
                if interaction_type == "single_click":
                    self.switch_to_menu()
                elif interaction_type == "hold":
                    pass
            elif screen_state == "music":
                if interaction_type == "single_click":
                    self.switch_to_menu()
                elif interaction_type == "hold":
                    self.media_play_pause()
                elif interaction_type == "left":
                    self.media_skip_song("previous")
                elif interaction_type == "right":
                    self.media_skip_song("next")
                elif interaction_type == "up":
                    self.media_volume("up")
                elif interaction_type == "down":
                    self.media_volume("down")
            elif screen_state == "menu":
                if interaction_type == "left":
                    self.publish_event(
                        "menu.navigation.requested",
                        {"command": "page_prev"},
                        source="gesture",
                    )
                elif interaction_type == "right":
                    self.publish_event(
                        "menu.navigation.requested",
                        {"command": "page_next"},
                        source="gesture",
                    )
                elif interaction_type == "down":
                    self.publish_event(
                        "menu.navigation.requested",
                        {"command": "exit"},
                        source="gesture",
                    )

            self.print_memory_usage()

    def check_bed_time(self,force=False):
        if self.device_states.in_bed_changed or force:
            if self.device_states.in_bed:
                self.display_controller.turn_off()  
            else:          
                self.display_controller.turn_on()
            self.device_states.in_bed_changed = False

        self.display_controller.check_idle()

    def check_idle_timer(self,startnew=True):
        if self.bed_time_timeout_future:
            self.root.after_cancel(self.bed_time_timeout_future)

        if(startnew):
            self.bed_time_timeout_future = self.root.after(self.settings.in_bed_turn_off_timeout, lambda: self.check_bed_time(True))

    ###### SCREEENS ######
    def switch_to_idle(self,force=False):
        self.screen_state_controller.switch_to_idle(force)

    def switch_to_music(self,force=False):
        self.screen_state_controller.switch_to_music(force)


    def switch_to_menu(self):
        self.screen_state_controller.switch_to_menu()

    def exit_menu(self):
        self.screen_state_controller.exit_menu()

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
    


    ###### MQTT ######
    def start_mqtt(self):
        self.mqtt_controller.start()

    def stop_mqtt(self):
        self.mqtt_controller.stop()

    def on_mqtt_connected(self):
        self.check_mqtt_message_queue()
    
    def check_mqtt_message_queue(self,topic=None):
        if self.startup_mqtt_messages:
            if topic:
                processes_queue_item = self.startup_mqtt_messages.pop(topic,None)
                if processes_queue_item is not None:
                    logger.debug(f"Removed {topic} from startup_mqtt_messages queue.")
                else:
                    logger.warning(f"Could not remove {topic} from startup_mqtt_messages, because it does not exist.")
                    return
            
            try:
                next_mqtt_queue_item_key, next_mqtt_queue_item_value = next(iter(self.startup_mqtt_messages.items()))
                logger.debug(f"Next item in the self.startup_mqtt_messages queue is: (key) {next_mqtt_queue_item_key}, (value) {next_mqtt_queue_item_value}")
                next_mqtt_queue_item_value()
            except StopIteration:
                logger.debug("The self.startup_mqtt_messages dictionary is empty.")

            logger.debug(f"Checked mqtt message queue (size: {len(self.startup_mqtt_messages)})")
            self.publish_event("startup.queue.size", {"size": len(self.startup_mqtt_messages)})
    
    def update_device_states(self):
        logger.debug(f"Asking mqtt for device states")
        self.mqtt_controller.publish_action("update_device_states")
    
    def check_music_status(self):
        logger.debug(f"Asking mqtt for music state")
        self.mqtt_controller.publish_message(topic="screen_commands/update_music")

    def on_mqtt_message(self, topic, data):
        self.mqtt_message_router.handle(topic, data)
        




    ###### MEDIA ######
    def show_music_overlays(self):
        self.media_controller.show_music_overlays()

    def media_play_pause(self):
        self.media_controller.media_play_pause()

    def media_skip_song(self,next_previous):
        self.media_controller.media_skip_song(next_previous)

    def media_volume(self,up_down):
        self.media_controller.media_volume(up_down)

    def update_music_object(self, data):
        state = data.get('state')
        title = data.get('title')
        artist = data.get('artist')
        channel = data.get('channel')
        album = data.get('album')
        album_art_api_url = data.get('album_art_api_url')

        if(self.music_object is None):
            from app.models.music_object import MusicObject
            self.music_object = MusicObject(
                state, 
                title, 
                artist, 
                channel, 
                album, 
                album_art_api_url
            )
        else:
            self.music_object.state = state
            self.music_object.title = title
            self.music_object.artist = artist
            self.music_object.channel = channel
            self.music_object.album = album
            self.music_object.album_art_api_url = album_art_api_url
        
        self.log_music_debug(
            "[music] object after update",
            {
                "state": self.music_object.state,
                "title": self.music_object.title,
                "artist": self.music_object.artist,
                "channel": self.music_object.channel,
                "album": self.music_object.album,
                "album_art_api_url": self.music_object.album_art_api_url,
            },
        )
        logging.debug("========= Music object updated =========")
        obj = self.music_object
        for key, value in vars(obj).items():
            logging.info("music_object.%s = %r", key, value)
        
        logger.debug(f'{state} - {title}')
        self.publish_event(
            "music.updated",
            {
                "state": state,
                "title": title,
                "artist": artist,
                "channel": channel,
                "album": album,
                "album_art_api_url": album_art_api_url,
            },
        )

        self.print_memory_usage()


    def wait_till_pause(self,startnew=True):
        if self.music_pause_timeout:
            self.root.after_cancel(self.music_pause_timeout)

        if(startnew):
            self.music_pause_timeout = self.root.after(500, lambda: self.switch_to_idle())

    def _cancel_music_pause_timeout(self):
        if self.music_pause_timeout is None:
            return
        self.root.after_cancel(self.music_pause_timeout)
        self.music_pause_timeout = None

    def _schedule_music_pause_idle(self):
        self._cancel_music_pause_timeout()
        if self.music_pause_grace_ms <= 0:
            self.switch_to_idle()
            return

        self.music_pause_timeout = self.root.after(
            self.music_pause_grace_ms,
            self._apply_music_pause_idle,
        )

    def _apply_music_pause_idle(self):
        self.music_pause_timeout = None
        if self.display_controller.get_screen_state() == "menu":
            return
        state = getattr(self.music_object, "state", None)
        if state == "playing":
            return
        self.switch_to_idle()

    ###### SYSTEM ######
    def checksystem(self):
        system_platform = platform.system()
        system_info = {}

        if system_platform == "Darwin":
            logger.info("You are on a Mac (macOS).")
            system_info["is_desktop"] = True
            system_info["system_platform"] = system_platform
        elif system_platform == "Windows":
            logger.info("You are on a Windows system.")
            system_info["is_desktop"] = True
            system_info["system_platform"] = system_platform
        elif system_platform == "Linux":
            try:
                with open('/proc/cpuinfo', 'r') as cpuinfo:
                    for line in cpuinfo:
                        if line.startswith('Hardware'):
                            if 'BCM' in line or 'Raspberry Pi' in line:
                                logger.info("You are on a Raspberry Pi (Linux).")
                                break
            except FileNotFoundError:
                logger.info("You are on a Linux system, but not a Raspberry Pi.")
            system_info["is_desktop"] = False
            system_info["system_platform"] = system_platform
        else:
            logger.info(f"You are on an unknown system with platform: {system_platform}")
            system_info["is_desktop"] = False
            system_info["system_platform"] = system_platform
        
        return system_info
    
    def print_memory_usage(self):
        memory = psutil.virtual_memory()
        memory_usage = self.get_memory_usage()
        available_memory = memory.available
        available_memory_gb = available_memory / (1024 ** 3)
        available_memory_mb = available_memory / (1024 * 1024)
        used_memory_mb = memory_usage / (1024 * 1024)
        memory_percentage = used_memory_mb / available_memory_mb * 100
        logger.debug(f"Memory usage: {used_memory_mb:.2f}/{available_memory_mb:.2f} MB ({memory_percentage:.2f}%)")

    def get_memory_usage(self):
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss
        except Exception as e:
            logger.error(f"Could not get memory usage: {e}")
            return 0

    def signal_handler(self, sig, frame):
        # Perform cleanup and exit gracefully
        logger.info(f"Exited gracefully by user (ctrl+c) request.")
        sys.exit(0)

    def log_unhandled_exception(exc_type, exc_value, exc_traceback):
        logger.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

    def print_current_datetime(self):
        current_datetime = datetime.datetime.now()
        formatted_datetime = current_datetime.strftime("%d %b %Y - %H:%M")
        return formatted_datetime

    def publish_event(self, event_type, payload=None, source="main"):
        try:
            event = AppEvent(
                event_type=event_type,
                payload=payload or {},
                source=source,
            )
            self.event_bus.publish(event)
        except Exception as exc:
            logger.debug(f"Could not publish event '{event_type}': {exc}")

    def log_music_debug(self, message, payload=None):
        if not self.music_debug_logging:
            return
        if payload is None:
            logger.info(message)
            return
        try:
            logger.info("%s :: %s", message, json.dumps(payload, default=str, ensure_ascii=False))
        except Exception:
            logger.info("%s :: %s", message, payload)

    def record_music_metric(self, key, amount=1):
        if key not in self.music_metrics:
            self.music_metrics[key] = 0
        self.music_metrics[key] += amount

    def start_music_metrics_log(self):
        self.root.after(self.music_metrics_interval_ms, self._log_music_metrics)

    def _log_music_metrics(self):
        if self.music_debug_logging:
            self.log_music_debug("[music] metrics", self.music_metrics)
        self.root.after(self.music_metrics_interval_ms, self._log_music_metrics)

    def trace_ui_event(self, event_name, **fields):
        if not self.ui_trace_logging:
            return
        payload = {
            "event": event_name,
            "ts_ms": int(time.time() * 1000),
            **fields,
        }
        try:
            logger.info("[ui-trace] %s", json.dumps(payload, default=str, ensure_ascii=False))
        except Exception:
            logger.info("[ui-trace] %s", payload)

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = MainApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Unhandled exception: {e}")
        sys.exit(1)
