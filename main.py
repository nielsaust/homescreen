
import datetime
import json
import logging
import logger as log_setup
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
from device_states import DeviceStates
from app.services.music_service import MusicService
from app.ui.widgets.network_status_widget import NetworkStatusWidget
from settings import Settings
from sentry_setup import init_sentry
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
        init_sentry(self.settings)
        self.event_bus = EventBus()
        self.store = AppStore(AppState())
        self.event_bus.subscribe(self.store.dispatch)

        # Get the log level from settings and convert it to a logging level
        try:
            log_level_str = self.settings.log_level.upper()
            log_level = getattr(logging, log_level_str, logging.DEBUG)

            tmp_logger = logging.getLogger()
            tmp_logger.setLevel(log_level)
            logger.info(f"Log level set to: {log_level_str} ({log_level})")

            # Update handler levels
            for handler in tmp_logger.handlers:
                logger.debug(f"Log handlerlevel set to: {log_level_str} ({log_level})")
                handler.setLevel(log_level)
                
        except Exception as e:
            logger.error(f"Error setting log level: {e}")

        # Wait for an internet connection
        self.wait_for_internet_connection()

        # Set up the root window
        self.root = root
        self.root.geometry(f"{self.settings.screen_width}x{self.settings.screen_height}")
        self.mqtt_message_queue = Queue()
        self.mqtt_queue_poll_interval_ms = 50
        self.mqtt_controller = DeferredMqttController()
        self.mqtt_initialized = False
        self.music_service = MusicService()
        self.pending_music_payload = None
        self.music_update_after_id = None
        self.music_update_debounce_ms = int(getattr(self.settings, "music_update_debounce_ms", 150) or 150)
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
        from touch_controller import TouchController
        self.touch_controller = TouchController(self)
        from display_controller import DisplayController
        self.display_controller = DisplayController(self)
        self.touch_controller.bind_events(self.root)

        # Register the signal handler for Ctrl-C
        signal.signal(signal.SIGINT, self.signal_handler)

        self.switch_to_idle()
        self.start_mqtt_queue_pump()
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
        self.update_network_status_ui(online)
        self.maybe_init_mqtt_if_online(online)
        self.root.after(self.network_status_poll_interval_ms, self._poll_network_status)

    def update_network_status_ui(self, online):
        if hasattr(self, "network_status_widget") and self.network_status_widget:
            self.network_status_widget.set_online(bool(online))

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
        from mqtt_controller import MqttController
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
        self.display_controller.update_menu_states()

    def perform_action(self, interaction_type):
        self.publish_event("interaction.received", {"interaction_type": interaction_type})
        logger.debug(f"Perform_action: {interaction_type}")
        current_time = time.time()

        if self.touch_controller.ignore_next_click:
            logger.debug(f"Menu click done. Ignoring this next root click")
            self.touch_controller.ignore_next_click = False
            return
        
        if self.display_controller.cam_screen.is_showing:
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
                    page_info = self.display_controller.switch_menu_page(-1)
                elif interaction_type == "right":
                    page_info = self.display_controller.switch_menu_page(1)
                elif interaction_type == "down":
                    self.display_controller.exit_menu()

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
        self.publish_event("ui.screen.changed", {"screen": "weather" if self.settings.show_weather_on_idle else "off", "is_display_on": self.settings.show_weather_on_idle})
        if self.settings.show_weather_on_idle:
            self.display_controller.show_screen("weather", force=force)
        else:
            self.display_controller.turn_off()  

    def switch_to_music(self,force=False):
        if not self.display_controller.get_screen_state() == "menu" or force:
            self.publish_event("ui.screen.changed", {"screen": "music", "is_display_on": True})
            logger.debug(f"Switch_to_music, current screen: {self.display_controller.get_screen_state()}")
            self.display_controller.show_screen("music", force=force)


    def switch_to_menu(self):
        if self.display_controller.menu_ready():
            self.publish_event("ui.screen.changed", {"screen": "menu", "is_display_on": True})
            logger.debug(f"Menu ready; show menu")
            self.display_controller.show_screen("menu")
        else:
            logger.warning(f"Menu NOT ready; show idle instead")
            self.switch_to_idle()

    def exit_menu(self):
        if(self.music_object is not None and self.music_object.state=="playing"):
            self.switch_to_music(True)
        else:
            self.switch_to_idle()
    


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

    def check_print_status(self, data):
        progress = data.get('progress')
        if self.device_states:
            self.device_states.printer_progress = progress
        logger.info(f"Checking print status ({progress}%)")
        if self.settings.show_cam_on_print_percentage>0 and progress and progress >= self.settings.show_cam_on_print_percentage:
            self.display_controller.show_cam(data,self.settings.printer_url)
        else:
            self.display_controller.update_print_progress(progress)

    def on_mqtt_message(self, topic, data):
        # prevent initial messages @ startup
        time_since_boot = time.time()-self.boot_time
        self.publish_event("mqtt.message.received", {"topic": topic})
        logger.debug(f"On MQTT message: {topic}, with data: {data}")
        self.check_mqtt_message_queue(topic)

        if topic==self.settings.mqtt_topic_music:
            self.queue_music_update(data)
            return
        elif topic==self.settings.mqtt_topic_devices:
            try:
                self.device_states.update_states(data)
                self.publish_event(
                    "device.state.updated",
                    {
                        "in_bed": self.device_states.in_bed,
                        "printer_progress": self.device_states.printer_progress,
                    },
                )
                self.display_controller.update_menu_states()
                self.check_bed_time()
                return
            except Exception as e:
                logger.error(f"Something went wrong when updating device states or buttons: {e}")
                return 

        # don't accept certain messages shortly after boot
        logger.debug(f"time since boot: {round(time_since_boot)}s ({round(time_since_boot/60/60,1)}h)")
        if time_since_boot<self.settings.mqtt_accept_nonessential_messages_after:
            logger.warning(f"only accepting non-essential messages afer {self.settings.mqtt_accept_nonessential_messages_after}s")
            return
        
        # octoPrint/progress/printing = mqtt_topic_printer_progress
        if topic==self.settings.mqtt_topic_doorbell:
            self.display_controller.show_cam(data,f'http://{self.settings.doorbell_url}{self.settings.doorbell_path}',self.settings.doorbell_username,self.settings.doorbell_password)
        elif topic==self.settings.mqtt_topic_printer_progress:
            self.check_print_status(data)           
        elif topic==self.settings.mqtt_topic_calendar:
            self.display_controller.show_calendar(data)
        elif topic==self.settings.mqtt_topic_alert:
            logger.debug(f"Received alert: {data}")
            self.display_controller.show_alert(data)
        elif topic==self.settings.mqtt_topic_print_start:
            self.display_controller.show_print_status(self.device_states.printer_progress,True)
        elif topic==self.settings.mqtt_topic_print_done:
            self.display_controller.print_screen_attention()
        elif topic==self.settings.mqtt_topic_print_cancelled:
            self.display_controller.close_print_screen()
        elif topic==self.settings.mqtt_topic_print_change_filament:
            self.display_controller.print_screen_attention()
        elif topic==self.settings.mqtt_topic_print_change_z:
            self.display_controller.cancel_attention()
        else:
            logger.warning(f"Unknown or untimely topic received: {topic}")
        




    ###### MEDIA ######
    def show_music_overlays(self):
        self.display_controller.show_music_overlays()

    def media_play_pause(self):
        data = {
            "action": "media-play-pause"
        }
        payload = json.dumps(data)
        self.mqtt_controller.publish_action("media-play-pause")
        if self.music_object and self.music_object.state=="playing":
            self.display_controller.place_action_label(image="pause-white.png")
        else:
            self.display_controller.place_action_label(image="play-white.png")

    def media_skip_song(self,next_previous):
        if self.music_object and self.music_object.channel is None:
            if next_previous=="next":
                self.mqtt_controller.publish_action("media-next")
                self.display_controller.place_action_label(image="forward-white.png")
            else:
                self.mqtt_controller.publish_action("media-previous")
                self.display_controller.place_action_label(image="backward-white.png")
        else:
            logger.info("Can't skip song; radio is playing.")

    def media_volume(self,up_down):
        if up_down=="up":
            self.mqtt_controller.publish_action("media-volume-up")
            self.display_controller.place_action_label(image="volume-up-white.png")
        else:
            self.mqtt_controller.publish_action("media-volume-down")
            self.display_controller.place_action_label(image="volume-down-white.png")

    def update_music_object(self, data):
        state = data.get('state')
        title = data.get('title')
        artist = data.get('artist')
        channel = data.get('channel')
        album = data.get('album')
        album_art_api_url = data.get('album_art_api_url')

        if(self.music_object is None):
            from music_object import MusicObject
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
            },
        )

        if(state!="playing"):
            self.switch_to_idle()
        else:
            self.switch_to_music()

        self.print_memory_usage()


    def wait_till_pause(self,startnew=True):
        if self.music_pause_timeout:
            self.root.after_cancel(self.music_pause_timeout)

        if(startnew):
            self.music_pause_timeout = self.root.after(500, lambda: self.switch_to_idle())

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

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = MainApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Unhandled exception: {e}")
        sys.exit(1)
