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

    def is_internet_connected(self, host="8.8.8.8", timeout=3):
        try:
            return ping3.ping(host, timeout=timeout) is not None
        except Exception as e:
            log_event(logger, logging.INFO, "network", "connectivity_check_error", error=e)
            return False

    def network_sim_flag_path(self):
        return pathlib.Path(__file__).resolve().parents[2] / ".sim" / "network_down.flag"

    def is_network_simulated_down(self):
        if not bool(getattr(self.main_app.settings, "enable_network_simulation", True)):
            return False
        if bool(getattr(self.main_app.settings, "simulate_outage_internet", False)):
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
        self.main_app.publish_event("network.status", {"online": online}, source="network_poll")
        self.maybe_init_mqtt_if_online(online)
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
