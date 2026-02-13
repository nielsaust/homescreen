import logging
logger = logging.getLogger(__name__)

import logging
import asyncio
import json
import settings
from asyncio_mqtt import Client, MqttError

logger = logging.getLogger(__name__)

class MqttController:
    def __init__(self, main_app, broker_address, broker_port, username, password):
        self.main_app = main_app
        self.broker_address = broker_address
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.client = None

    async def connect(self):
        try:
            self.client = Client(self.broker_address,self.broker_port,username=self.username,password=self.username)
            await self.client.connect()
            await self.client.subscribe("music")
            await self.client.subscribe("screen_commands/incoming")
            await self.client.start_listening(self.on_message)
            self.main_app.on_mqtt_connected()
        except MqttError as e:
            logger.error(f"Connection to MQTT broker failed: {e}")

    async def handle_message(self, topic, payload):
        if payload:
            try:
                data = json.loads(payload)
            except Exception as e:
                logger.error(f"Error in MQTT payload ({payload if payload is not None else 'None'}): {e}")
                return

            await self.main_app.on_mqtt_message(topic, data)

    async def on_message(self, topic, payload, qos, properties):
        # Handle incoming MQTT messages here
        await self.handle_message(topic, payload)

    async def publish_message(self, payload, topic="screen_commands/outgoing"):
        # Publish a message to an MQTT topic
        await self.client.publish(topic, payload)

    async def start(self):
        await self.connect()

    async def stop(self):
        if self.client:
            await self.client.stop()
