from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp

import logging
import socket
import sys
import time
import threading
import json
import re
import paho.mqtt.client as mqtt
from app.observability.domain_logger import log_event

logger = logging.getLogger(__name__)


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


class MqttController:
    def __init__(self, main_app: MainApp, broker_address, broker_port, username, password):
        self.main_app = main_app
        self.broker_address = broker_address
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.client = mqtt.Client()
        self.reconnect_interval = max(1, int(getattr(self.main_app.settings, "mqtt_reconnect_interval_seconds", 2)))
        self.reconnect_max_interval = max(
            self.reconnect_interval,
            int(getattr(self.main_app.settings, "mqtt_reconnect_max_interval_seconds", 60)),
        )
        self.running = True

        # Set up callback functions for MQTT events
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish

        self.client.enable_logger(logger=logger)
        self.client.username_pw_set(self.username, self.password)
        self._set_runtime_connected(False, reason="initializing")
        self._mqtt_sim_outage_logged = False
        self._reconnect_wakeup = threading.Event()
        self._last_simulated_outage_state = None
        self._last_client_connected_state = None
        self._awaiting_connack = False
        self._awaiting_connack_since = 0.0
        self._connack_timeout_seconds = max(
            3,
            int(getattr(self.main_app.settings, "mqtt_connack_timeout_seconds", 8) or 8),
        )

        # Initial connect is handled in background loop to avoid blocking app startup.
        self.custom_loop_start()

    def _is_mqtt_simulated_outage(self) -> bool:
        if not _to_bool(getattr(self.main_app.settings, "enable_network_simulation", True), True):
            return False
        return _to_bool(getattr(self.main_app.settings, "simulate_outage_mqtt", False), False)

    def _set_runtime_connected(self, connected: bool, reason: str = ""):
        state = bool(connected)
        prev = bool(getattr(self.main_app, "mqtt_connected", False))
        self.main_app.mqtt_connected = state
        self.main_app.mqtt_unavailable_reason = "" if state else str(reason or "")
        setattr(self.main_app.settings, "mqtt_runtime_connected", state)
        if prev != state and hasattr(self.main_app, "publish_event"):
            self.main_app.publish_event(
                "menu.refresh.requested",
                {"reason": "mqtt.connection.changed", "connected": state},
                source="mqtt",
            )
            # Refresh connectivity banner on MQTT state changes without mutating
            # canonical internet status.
            try:
                store = getattr(self.main_app, "store", None)
                online = getattr(store.get_state(), "network_online", None) if store else None
                banner_service = getattr(self.main_app, "network_status_banner_service", None)
                if online is not None and banner_service is not None:
                    self.main_app.root.after(0, lambda: banner_service.refresh(bool(online)))
            except Exception:
                pass
            log_event(logger, logging.INFO, "mqtt", "runtime.connection_state", connected=state, reason=reason)
            self._log_runtime_snapshot(logging.DEBUG, "runtime.snapshot", trigger="connection_state_changed")

    def _runtime_snapshot(self):
        return {
            "mqtt_enabled": _to_bool(getattr(self.main_app.settings, "enable_mqtt", False), False),
            "sim_enabled": _to_bool(getattr(self.main_app.settings, "enable_network_simulation", True), True),
            "sim_mqtt": _to_bool(getattr(self.main_app.settings, "simulate_outage_mqtt", False), False),
            "sim_internet": _to_bool(getattr(self.main_app.settings, "simulate_outage_internet", False), False),
            "runtime_connected": bool(getattr(self.main_app, "mqtt_connected", False)),
            "client_connected": bool(self.client.is_connected()),
            "unavailable_reason": str(getattr(self.main_app, "mqtt_unavailable_reason", "") or ""),
            "running": bool(self.running),
            "awaiting_connack": bool(self._awaiting_connack),
            "awaiting_connack_seconds": round(max(0.0, time.time() - self._awaiting_connack_since), 3)
            if self._awaiting_connack
            else 0.0,
        }

    def _log_runtime_snapshot(self, level, event_name: str, **extra):
        payload = self._runtime_snapshot()
        payload.update(extra or {})
        log_event(logger, level, "mqtt", event_name, **payload)

    def _sleep_before_retry(self, delay_seconds: int | float) -> None:
        wait_seconds = max(0, float(delay_seconds))
        self._reconnect_wakeup.wait(timeout=wait_seconds)
        self._reconnect_wakeup.clear()

    def nudge_reconnect(self, reason: str = "") -> None:
        if not self.running:
            return
        self._reconnect_wakeup.set()
        if reason:
            log_event(logger, logging.DEBUG, "mqtt", "reconnect.nudged", reason=reason)
        self._log_runtime_snapshot(logging.DEBUG, "reconnect.nudge_snapshot", reason=reason)

    def force_reconnect_cycle(self, reason: str = "") -> None:
        if not self.running:
            return
        self._log_runtime_snapshot(logging.DEBUG, "reconnect.force_cycle.begin", reason=reason)
        self._mqtt_sim_outage_logged = False
        self._awaiting_connack = False
        self._awaiting_connack_since = 0.0
        try:
            if self.client.is_connected():
                self.client.disconnect()
        except Exception:
            pass
        # Clear stale simulated_outage user feedback when simulation is toggled off.
        if not self._is_mqtt_simulated_outage():
            self._set_runtime_connected(False, reason="reconnecting")
        self.nudge_reconnect(reason=reason or "force_reconnect_cycle")
        self._log_runtime_snapshot(logging.DEBUG, "reconnect.force_cycle.end", reason=reason)

    def connect_to_broker(self):
        """Attempts to connect to the broker."""
        if self._awaiting_connack:
            return
        retry_delay = self.reconnect_interval
        while self.running:
            if self._is_mqtt_simulated_outage():
                self._set_runtime_connected(False, reason="simulated_outage")
                if not self._mqtt_sim_outage_logged:
                    log_event(logger, logging.WARNING, "mqtt", "connect.delayed.simulated_outage")
                    self._mqtt_sim_outage_logged = True
                self._sleep_before_retry(retry_delay)
                retry_delay = min(self.reconnect_max_interval, retry_delay * 2)
                continue
            self._mqtt_sim_outage_logged = False
            try:
                log_event(
                    logger,
                    logging.DEBUG,
                    "mqtt",
                    "connect.attempt",
                    broker=self.broker_address,
                    port=self.broker_port,
                    retry_delay_seconds=retry_delay,
                )
                self.client.connect(self.broker_address, self.broker_port, 60)
                log_event(
                    logger,
                    logging.INFO,
                    "mqtt",
                    "connect.success",
                    broker=self.broker_address,
                    port=self.broker_port,
                )
                self._awaiting_connack = True
                self._awaiting_connack_since = time.time()
                break
            except socket.error as e:
                self._set_runtime_connected(False, reason="socket_error")
                log_event(logger, logging.ERROR, "mqtt", "connect.socket_error", broker=self.broker_address, error=e)
            except Exception as e:
                self._set_runtime_connected(False, reason="connect_exception")
                log_event(logger, logging.ERROR, "mqtt", "connect.exception", error=e)
            self._sleep_before_retry(retry_delay)
            retry_delay = min(self.reconnect_max_interval, retry_delay * 2)
            log_event(logger, logging.WARNING, "mqtt", "connect.retry_scheduled", retry_delay_seconds=retry_delay)

    def custom_loop_start(self):
        self.thread = threading.Thread(target=self.custom_loop)
        self.thread.daemon = True
        self.thread.start()

    def custom_loop(self):
        """Custom loop to keep MQTT connection alive and reconnect if needed."""
        while self.running:
            sim_state = self._is_mqtt_simulated_outage()
            client_connected = bool(self.client.is_connected())
            if (
                sim_state != self._last_simulated_outage_state
                or client_connected != self._last_client_connected_state
            ):
                self._last_simulated_outage_state = sim_state
                self._last_client_connected_state = client_connected
                self._log_runtime_snapshot(logging.DEBUG, "loop.state_changed")
            if sim_state:
                if self.client.is_connected():
                    try:
                        self.client.disconnect()
                    except Exception:
                        pass
                self._awaiting_connack = False
                self._awaiting_connack_since = 0.0
                self._set_runtime_connected(False, reason="simulated_outage")
                self._sleep_before_retry(self.reconnect_interval)
                continue
            if not self.client.is_connected():
                if self._awaiting_connack:
                    elapsed = time.time() - self._awaiting_connack_since
                    if elapsed > self._connack_timeout_seconds:
                        log_event(
                            logger,
                            logging.WARNING,
                            "mqtt",
                            "connect.connack_timeout",
                            timeout_seconds=self._connack_timeout_seconds,
                            waited_seconds=round(elapsed, 3),
                        )
                        self._awaiting_connack = False
                        self._awaiting_connack_since = 0.0
                    else:
                        try:
                            self.client.loop(timeout=1.0)
                        except (TimeoutError, Exception) as e:
                            log_event(logger, logging.WARNING, "mqtt", "loop.error_reconnect", error=e)
                        time.sleep(0.1)
                        continue
                # Ensure we keep driving the MQTT state machine after connect(),
                # otherwise CONNACK may never be processed and state can stick on initializing.
                self.connect_to_broker()
            try:
                self.client.loop(timeout=1.0)
            except (TimeoutError, Exception) as e:
                log_event(logger, logging.WARNING, "mqtt", "loop.error_reconnect", error=e)
                self.reconnect()
            time.sleep(0.1)

    def reconnect(self):
        """Attempts to reconnect to the MQTT broker with retries."""
        retry_delay = self.reconnect_interval
        while self.running:
            try:
                log_event(
                    logger,
                    logging.DEBUG,
                    "mqtt",
                    "reconnect.attempt",
                    broker=self.broker_address,
                    port=self.broker_port,
                    retry_delay_seconds=retry_delay,
                )
                self.client.reconnect()
                log_event(
                    logger,
                    logging.INFO,
                    "mqtt",
                    "reconnect.success",
                    broker=self.broker_address,
                    port=self.broker_port,
                )
                break
            except Exception as e:
                self._set_runtime_connected(False, reason="reconnect_failed")
                log_event(logger, logging.ERROR, "mqtt", "reconnect.failed", error=e)
                self._log_runtime_snapshot(logging.DEBUG, "reconnect.failed_snapshot")
                self._sleep_before_retry(retry_delay)
                retry_delay = min(self.reconnect_max_interval, retry_delay * 2)

    def handle_message(self, topic, payload):
        """Processes incoming MQTT messages and logs any deserialization issues."""
        if payload:
            try:
                data = self._decode_payload(payload)
                if hasattr(self.main_app, "queue_pump_service"):
                    self.main_app.queue_pump_service.enqueue_mqtt_message(topic, data)
                else:
                    self.main_app.mqtt_message_router.handle(topic, data)
            except json.JSONDecodeError as e:
                payload_preview = payload if payload is not None else "None"
                log_event(logger, logging.ERROR, "mqtt", "payload.decode_error", payload=payload_preview, error=e)
                sanitized = self._sanitize_malformed_json(payload)
                if sanitized is not None:
                    try:
                        data = self._decode_payload(sanitized)
                        log_event(logger, logging.WARNING, "mqtt", "payload.decode_recovered", topic=topic)
                        if hasattr(self.main_app, "queue_pump_service"):
                            self.main_app.queue_pump_service.enqueue_mqtt_message(topic, data)
                        else:
                            self.main_app.mqtt_message_router.handle(topic, data)
                    except Exception as recover_error:
                        log_event(
                            logger,
                            logging.ERROR,
                            "mqtt",
                            "payload.decode_recovery_failed",
                            topic=topic,
                            error=recover_error,
                        )

    def _decode_payload(self, payload):
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", errors="replace")
        return json.loads(payload)

    def _sanitize_malformed_json(self, payload):
        if payload is None:
            return None
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", errors="replace")
        text = str(payload)
        # Repair common malformed payloads where a key has no value, e.g. '"brightness": }'
        # by injecting null so JSON becomes parseable.
        fixed = re.sub(r':\s*(?=[}\],])', ': null', text)
        return fixed if fixed != text else None

    def on_connect(self, client, userdata, flags, rc):
        self._awaiting_connack = False
        self._awaiting_connack_since = 0.0
        if rc == 0:
            self._set_runtime_connected(True, reason="connected")
            log_event(logger, logging.INFO, "mqtt", "session.connected", broker=self.broker_address)
            self.subscribe_to_topics()
            self.main_app.startup_sync_service.on_mqtt_connected()
        else:
            self._set_runtime_connected(False, reason=f"connect_rc_{rc}")
            log_event(logger, logging.ERROR, "mqtt", "session.connect_failed", rc=rc)

    def subscribe_to_topics(self):
        """Subscribes to all topics referenced by configured mqtt routes."""
        topic_candidates = [route.get("topic", "") for route in getattr(self.main_app, "mqtt_routes", [])]
        # Ignore disabled/empty topics and deduplicate while keeping order.
        topics = []
        for topic in topic_candidates:
            topic = str(topic).strip()
            if topic and topic not in topics:
                topics.append(topic)
        for topic in topics:
            log_event(logger, logging.DEBUG, "mqtt", "subscribe.requested", topic=topic)
            self.subscribe_to_topic(topic)

    def on_message(self, client, userdata, message):
        log_event(logger, logging.DEBUG, "mqtt", "message.received", topic=message.topic)
        self.handle_message(message.topic, message.payload)

    def on_disconnect(self, client, userdata, rc):
        self._awaiting_connack = False
        self._awaiting_connack_since = 0.0
        self._set_runtime_connected(False, reason=f"disconnect_rc_{rc}")
        if rc != 0:
            log_event(logger, logging.WARNING, "mqtt", "session.disconnected", rc=rc)
            self.nudge_reconnect(reason="disconnect")

    def on_publish(self, client, userdata, mid):
        log_event(logger, logging.DEBUG, "mqtt", "publish.ack", message_id=mid)

    def publish_action(self, action, value=None, topic=None):
        data = {"action": action}
        if value is not None:
            data["value"] = value
        payload = json.dumps(data)
        self.publish_message(payload=payload, topic=topic)

    def publish_message(self, payload=None, topic=None):
        """Publishes a message to a specified topic with retry logic if not connected."""
        try:
            if topic is None:
                if hasattr(self.main_app, "get_topic"):
                    topic = self.main_app.get_topic("actions_outgoing", "screen_commands/outgoing")
                else:
                    topic = "screen_commands/outgoing"
            if not self.client.is_connected():
                log_event(logger, logging.WARNING, "mqtt", "publish.skipped_not_connected", topic=topic)
                return
            self.client.publish(topic=topic, payload=payload, qos=self.main_app.settings.mqtt_qos)
        except Exception as e:
            log_event(logger, logging.ERROR, "mqtt", "publish.failed", topic=topic, error=e)
            self._set_runtime_connected(False, reason="publish_failed")

    def subscribe_to_topic(self, topic):
        """Subscribes to a topic with retry logic if disconnected."""
        try:
            if not self.client.is_connected():
                log_event(logger, logging.WARNING, "mqtt", "subscribe.skipped_not_connected", topic=topic)
                return
            result, mid = self.client.subscribe(topic)
            if result == 0:
                log_event(logger, logging.INFO, "mqtt", "subscribe.success", topic=topic, message_id=mid)
            else:
                log_event(logger, logging.ERROR, "mqtt", "subscribe.failed", topic=topic, result_code=result)
        except Exception as e:
            log_event(logger, logging.ERROR, "mqtt", "subscribe.exception", topic=topic, error=e)
            self._set_runtime_connected(False, reason="subscribe_exception")

    def start(self):
        self.client.loop_start()

    def stop(self):
        self.running = False
        self._reconnect_wakeup.set()
        self.client.loop_stop()
        self.client.disconnect()
        log_event(logger, logging.INFO, "mqtt", "client.stopped")
