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
import paho.mqtt.client as mqtt

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
                logger.warning("Network unavailable; delaying MQTT connect attempt.")
                if hasattr(self.main_app, "publish_event"):
                    self.main_app.publish_event("network.status", {"online": False}, source="mqtt")
                time.sleep(retry_delay)
                retry_delay = min(self.reconnect_max_interval, retry_delay * 2)
                continue
            try:
                self.client.connect(self.broker_address, self.broker_port, 60)
                logger.info("Successfully connected to the MQTT broker.")
                if hasattr(self.main_app, "publish_event"):
                    self.main_app.publish_event("network.status", {"online": True}, source="mqtt")
                break
            except socket.error as e:
                logger.error(f"Socket error. Broker: {self.broker_address}, error: {e}")
            except Exception as e:
                logger.error(f"Unexpected exception during MQTT connection: {e}")
            time.sleep(retry_delay)
            retry_delay = min(self.reconnect_max_interval, retry_delay * 2)
            logger.warning("Could not connect to the MQTT broker. Retrying in %ss...", retry_delay)

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
                logger.warning(f"MQTT connection issue detected: {e}. Attempting to reconnect...")
                self.reconnect()

    def reconnect(self):
        """Attempts to reconnect to the MQTT broker with retries."""
        retry_delay = self.reconnect_interval
        while self.running:
            if hasattr(self.main_app, "is_network_available") and not self.main_app.is_network_available(timeout=1):
                logger.warning("Network unavailable; delaying MQTT reconnect attempt.")
                if hasattr(self.main_app, "publish_event"):
                    self.main_app.publish_event("network.status", {"online": False}, source="mqtt")
                time.sleep(retry_delay)
                retry_delay = min(self.reconnect_max_interval, retry_delay * 2)
                continue
            try:
                self.client.reconnect()
                logger.info("Reconnected to the MQTT broker.")
                if hasattr(self.main_app, "publish_event"):
                    self.main_app.publish_event("network.status", {"online": True}, source="mqtt")
                break
            except Exception as e:
                logger.error(f"MQTT reconnect failed: {e}")
                time.sleep(retry_delay)
                retry_delay = min(self.reconnect_max_interval, retry_delay * 2)

    def handle_message(self, topic, payload):
        """Processes incoming MQTT messages and logs any deserialization issues."""
        if payload:
            try:
                data = json.loads(payload)
                if hasattr(self.main_app, "enqueue_mqtt_message"):
                    self.main_app.enqueue_mqtt_message(topic, data)
                else:
                    self.main_app.on_mqtt_message(topic, data)
            except json.JSONDecodeError as e:
                logger.error(f"Error in MQTT payload ({payload if payload is not None else 'None'}): {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"MQTT connected to broker @ {self.broker_address}")
            self.subscribe_to_topics()
            self.main_app.on_mqtt_connected()
        else:
            logger.error("Connection to MQTT broker failed with result code %d", rc)

    def subscribe_to_topics(self):
        """Subscribes to predefined topics."""
        topics = [
            self.main_app.settings.mqtt_topic_music,
            self.main_app.settings.mqtt_topic_doorbell,
            self.main_app.settings.mqtt_topic_printer_progress,
            self.main_app.settings.mqtt_topic_calendar,
            self.main_app.settings.mqtt_topic_devices,
            self.main_app.settings.mqtt_topic_alert,
            # Additional topics can be added here
            #self.main_app.settings.mqtt_topic_print_start
            #self.main_app.settings.mqtt_topic_print_done
            #self.main_app.settings.mqtt_topic_print_cancelled
            #self.main_app.settings.mqtt_topic_print_change_filament
        ]
        for topic in topics:
            logger.debug("Subscribing to topic: " + topic)
            self.subscribe_to_topic(topic)

    def on_message(self, client, userdata, message):
        logger.debug(f"Received message from MQTT broker: {message.topic}, {message.payload}")
        self.handle_message(message.topic, message.payload)

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning("Unexpected disconnection from MQTT broker. Reconnecting...")
            self.reconnect()

    def on_publish(self, client, userdata, mid):
        logger.debug(f"MQTT published (message ID: {mid})")

    def publish_action(self, action, value=None):
        data = {"action": action}
        if value:
            data["value"] = value
        payload = json.dumps(data)
        self.publish_message(payload)

    def publish_message(self, payload=None, topic="screen_commands/outgoing"):
        """Publishes a message to a specified topic with retry logic if not connected."""
        try:
            if not self.client.is_connected():
                logger.warning("MQTT client is disconnected. Attempting to reconnect before publishing.")
                self.reconnect()
            self.client.publish(topic=topic, payload=payload, qos=self.main_app.settings.mqtt_qos)
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            self.reconnect()

    def subscribe_to_topic(self, topic):
        """Subscribes to a topic with retry logic if disconnected."""
        try:
            if not self.client.is_connected():
                logger.warning(f"MQTT client is disconnected. Attempting to reconnect before subscribing to {topic}.")
                self.reconnect()
            result, mid = self.client.subscribe(topic)
            if result == 0:
                logger.info(f"Successfully subscribed to {topic}")
            else:
                logger.error(f"Failed to subscribe to {topic} with result code {result}")
        except Exception as e:
            logger.error(f"Failed to subscribe to {topic}: {e}")
            self.reconnect()

    def start(self):
        self.client.loop_start()

    def stop(self):
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        logger.warning("MQTT client stopped.")
