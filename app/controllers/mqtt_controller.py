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

        # Attempt initial connection
        self.connect_to_broker()
        self.custom_loop_start()

    def connect_to_broker(self):
        """Attempts to connect to the broker."""
        retry_delay = self.reconnect_interval
        while self.running:
            if hasattr(self.main_app, "is_network_available") and not self.main_app.is_network_available(timeout=1):
                log_event(logger, logging.WARNING, "mqtt", "connect.delayed.network_unavailable")
                if hasattr(self.main_app, "publish_event"):
                    self.main_app.publish_event("network.status", {"online": False}, source="mqtt")
                time.sleep(retry_delay)
                retry_delay = min(self.reconnect_max_interval, retry_delay * 2)
                continue
            try:
                self.client.connect(self.broker_address, self.broker_port, 60)
                log_event(
                    logger,
                    logging.INFO,
                    "mqtt",
                    "connect.success",
                    broker=self.broker_address,
                    port=self.broker_port,
                )
                if hasattr(self.main_app, "publish_event"):
                    self.main_app.publish_event("network.status", {"online": True}, source="mqtt")
                break
            except socket.error as e:
                log_event(logger, logging.ERROR, "mqtt", "connect.socket_error", broker=self.broker_address, error=e)
            except Exception as e:
                log_event(logger, logging.ERROR, "mqtt", "connect.exception", error=e)
            time.sleep(retry_delay)
            retry_delay = min(self.reconnect_max_interval, retry_delay * 2)
            log_event(logger, logging.WARNING, "mqtt", "connect.retry_scheduled", retry_delay_seconds=retry_delay)

    def custom_loop_start(self):
        self.thread = threading.Thread(target=self.custom_loop)
        self.thread.daemon = True
        self.thread.start()

    def custom_loop(self):
        """Custom loop to keep MQTT connection alive and reconnect if needed."""
        while self.running:
            try:
                self.client.loop(timeout=1.0)
            except (TimeoutError, Exception) as e:
                log_event(logger, logging.WARNING, "mqtt", "loop.error_reconnect", error=e)
                self.reconnect()

    def reconnect(self):
        """Attempts to reconnect to the MQTT broker with retries."""
        retry_delay = self.reconnect_interval
        while self.running:
            if hasattr(self.main_app, "is_network_available") and not self.main_app.is_network_available(timeout=1):
                log_event(logger, logging.WARNING, "mqtt", "reconnect.delayed.network_unavailable")
                if hasattr(self.main_app, "publish_event"):
                    self.main_app.publish_event("network.status", {"online": False}, source="mqtt")
                time.sleep(retry_delay)
                retry_delay = min(self.reconnect_max_interval, retry_delay * 2)
                continue
            try:
                self.client.reconnect()
                log_event(
                    logger,
                    logging.INFO,
                    "mqtt",
                    "reconnect.success",
                    broker=self.broker_address,
                    port=self.broker_port,
                )
                if hasattr(self.main_app, "publish_event"):
                    self.main_app.publish_event("network.status", {"online": True}, source="mqtt")
                break
            except Exception as e:
                log_event(logger, logging.ERROR, "mqtt", "reconnect.failed", error=e)
                time.sleep(retry_delay)
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
        if rc == 0:
            log_event(logger, logging.INFO, "mqtt", "session.connected", broker=self.broker_address)
            self.subscribe_to_topics()
            self.main_app.startup_sync_service.on_mqtt_connected()
        else:
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
        if rc != 0:
            log_event(logger, logging.WARNING, "mqtt", "session.disconnected", rc=rc)
            self.reconnect()

    def on_publish(self, client, userdata, mid):
        log_event(logger, logging.DEBUG, "mqtt", "publish.ack", message_id=mid)

    def publish_action(self, action, value=None):
        data = {"action": action}
        if value:
            data["value"] = value
        payload = json.dumps(data)
        self.publish_message(payload)

    def publish_message(self, payload=None, topic=None):
        """Publishes a message to a specified topic with retry logic if not connected."""
        try:
            if topic is None:
                if hasattr(self.main_app, "get_topic"):
                    topic = self.main_app.get_topic("actions_outgoing", "screen_commands/outgoing")
                else:
                    topic = "screen_commands/outgoing"
            if not self.client.is_connected():
                log_event(logger, logging.WARNING, "mqtt", "publish.reconnect_before_send")
                self.reconnect()
            self.client.publish(topic=topic, payload=payload, qos=self.main_app.settings.mqtt_qos)
        except Exception as e:
            log_event(logger, logging.ERROR, "mqtt", "publish.failed", topic=topic, error=e)
            self.reconnect()

    def subscribe_to_topic(self, topic):
        """Subscribes to a topic with retry logic if disconnected."""
        try:
            if not self.client.is_connected():
                log_event(logger, logging.WARNING, "mqtt", "subscribe.reconnect_before_subscribe", topic=topic)
                self.reconnect()
            result, mid = self.client.subscribe(topic)
            if result == 0:
                log_event(logger, logging.INFO, "mqtt", "subscribe.success", topic=topic, message_id=mid)
            else:
                log_event(logger, logging.ERROR, "mqtt", "subscribe.failed", topic=topic, result_code=result)
        except Exception as e:
            log_event(logger, logging.ERROR, "mqtt", "subscribe.exception", topic=topic, error=e)
            self.reconnect()

    def start(self):
        self.client.loop_start()

    def stop(self):
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        log_event(logger, logging.INFO, "mqtt", "client.stopped")
