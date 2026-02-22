from __future__ import annotations

import logging
import pathlib
import time

import ping3

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


class NetworkBootstrapService:
    """Startup/poll/reconnect bootstrap behavior for network and MQTT init."""

    def __init__(self, main_app):
        self.main_app = main_app
        self._mqtt_disabled_logged = False
        self._last_online_state = None
        self._mqtt_disconnected_poll_count = 0

    def is_internet_connected(self, host="8.8.8.8", timeout=3):
        try:
            return ping3.ping(host, timeout=timeout) is not None
        except Exception as e:
            log_event(logger, logging.INFO, "network", "connectivity_check_error", error=e)
            return False

    def network_sim_flag_path(self):
        return pathlib.Path(__file__).resolve().parents[2] / ".sim" / "network_down.flag"

    def is_network_simulated_down(self):
        if not _to_bool(getattr(self.main_app.settings, "enable_network_simulation", True), True):
            return False
        if _to_bool(getattr(self.main_app.settings, "simulate_outage_internet", False), False):
            return True
        return self.network_sim_flag_path().exists()

    def is_network_available(self, timeout=2):
        if self.is_network_simulated_down():
            return False
        return self.is_internet_connected(timeout=timeout)

    def wait_for_internet_connection(self):
        wait_on_boot = _to_bool(getattr(self.main_app.settings, "startup_block_on_internet", False), False)
        timeout_seconds = int(getattr(self.main_app.settings, "startup_wait_for_internet_seconds", 0) or 0)
        check_interval_seconds = int(getattr(self.main_app.settings, "startup_wait_check_interval_seconds", 5) or 5)

        if not wait_on_boot or timeout_seconds <= 0:
            online = self.is_network_available(timeout=2)
            self.main_app.publish_event("network.status", {"online": online})
            if online:
                log_event(logger, logging.INFO, "network", "startup.online")
            else:
                log_event(
                    logger,
                    logging.WARNING,
                    "network",
                    "startup.degraded_mode",
                    reason="offline_at_boot_non_blocking",
                )
            return

        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if self.is_network_available(timeout=2):
                self.main_app.publish_event("network.status", {"online": True})
                log_event(logger, logging.INFO, "network", "startup.online")
                return

            self.main_app.publish_event("network.status", {"online": False})
            remaining = max(0, int(deadline - time.time()))
            log_event(logger, logging.WARNING, "network", "startup.waiting_for_connection", remaining_seconds=remaining)
            time.sleep(check_interval_seconds)

        self.main_app.publish_event("network.status", {"online": False})
        log_event(
            logger,
            logging.WARNING,
            "network",
            "startup.degraded_mode",
            reason="startup_timeout",
            timeout_seconds=timeout_seconds,
        )

    def start_network_status_poll(self):
        self.main_app.root.after(self.main_app.network_status_poll_interval_ms, self._poll_network_status)

    def _poll_network_status(self):
        online = self.is_network_available(timeout=1)
        if self._last_online_state is None or bool(online) != bool(self._last_online_state):
            log_event(
                logger,
                logging.INFO,
                "network",
                "poll.online_state_changed",
                online=bool(online),
                sim_enabled=_to_bool(getattr(self.main_app.settings, "enable_network_simulation", True), True),
                sim_internet=_to_bool(getattr(self.main_app.settings, "simulate_outage_internet", False), False),
            )
        self.main_app.publish_event("network.status", {"online": online}, source="network_poll")
        self.maybe_init_mqtt_if_online(online)
        self._nudge_mqtt_reconnect_if_needed(online)
        self._log_mqtt_reconnect_stuck_state_if_needed(online)
        self._last_online_state = online
        self.main_app.root.after(self.main_app.network_status_poll_interval_ms, self._poll_network_status)

    def maybe_init_mqtt_if_online(self, online=None):
        if self.main_app.mqtt_initialized:
            return
        if not self.main_app.is_mqtt_enabled():
            if not self._mqtt_disabled_logged:
                log_event(logger, logging.INFO, "mqtt", "controller.init_skipped", reason="disabled_in_settings")
                self._mqtt_disabled_logged = True
            return
        self._mqtt_disabled_logged = False
        if online is None:
            online = self.is_network_available(timeout=1)
        if not online:
            return
        log_event(logger, logging.INFO, "mqtt", "controller.init_requested", reason="network_available")
        self.main_app.init_mqtt()

    def _nudge_mqtt_reconnect_if_needed(self, online: bool):
        if not bool(online):
            return
        if not self.main_app.is_mqtt_enabled():
            return
        if not bool(getattr(self.main_app, "mqtt_initialized", False)):
            return
        if bool(getattr(self.main_app, "mqtt_connected", False)):
            return

        mqtt_controller = getattr(self.main_app, "mqtt_controller", None)
        if mqtt_controller is None or not hasattr(mqtt_controller, "nudge_reconnect"):
            return

        reason = "network_online_poll"
        if self._last_online_state is False:
            reason = "network_restored"
        log_event(
            logger,
            logging.DEBUG,
            "mqtt",
            "reconnect.nudge_from_network_poll",
            reason=reason,
            online=bool(online),
            mqtt_connected=bool(getattr(self.main_app, "mqtt_connected", False)),
        )
        mqtt_controller.nudge_reconnect(reason=reason)

    def _log_mqtt_reconnect_stuck_state_if_needed(self, online: bool):
        if not bool(online):
            self._mqtt_disconnected_poll_count = 0
            return
        if not self.main_app.is_mqtt_enabled():
            self._mqtt_disconnected_poll_count = 0
            return
        if not bool(getattr(self.main_app, "mqtt_initialized", False)):
            self._mqtt_disconnected_poll_count = 0
            return
        if bool(getattr(self.main_app, "mqtt_connected", False)):
            self._mqtt_disconnected_poll_count = 0
            return

        self._mqtt_disconnected_poll_count += 1
        # With default 5s poll this logs every ~30s while internet is up but MQTT remains down.
        if self._mqtt_disconnected_poll_count % 6 != 0:
            return

        mqtt_controller = getattr(self.main_app, "mqtt_controller", None)
        controller_name = mqtt_controller.__class__.__name__ if mqtt_controller is not None else "None"
        thread_alive = None
        client_connected = None
        if mqtt_controller is not None:
            thread = getattr(mqtt_controller, "thread", None)
            thread_alive = bool(thread.is_alive()) if thread is not None else None
            client = getattr(mqtt_controller, "client", None)
            if client is not None and hasattr(client, "is_connected"):
                try:
                    client_connected = bool(client.is_connected())
                except Exception:
                    client_connected = None

        log_event(
            logger,
            logging.WARNING,
            "mqtt",
            "reconnect.still_disconnected",
            polls=self._mqtt_disconnected_poll_count,
            internet_online=True,
            mqtt_connected=bool(getattr(self.main_app, "mqtt_connected", False)),
            mqtt_unavailable_reason=str(getattr(self.main_app, "mqtt_unavailable_reason", "") or ""),
            controller=controller_name,
            controller_thread_alive=thread_alive,
            controller_client_connected=client_connected,
            sim_enabled=_to_bool(getattr(self.main_app.settings, "enable_network_simulation", True), True),
            sim_internet=_to_bool(getattr(self.main_app.settings, "simulate_outage_internet", False), False),
            sim_mqtt=_to_bool(getattr(self.main_app.settings, "simulate_outage_mqtt", False), False),
        )
