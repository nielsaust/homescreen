from __future__ import annotations

import logging
import platform

import psutil

from app.observability.domain_logger import log_event

logger = logging.getLogger(__name__)


class SystemInfoService:
    """Platform detection and process memory observability helpers."""

    def detect_platform(self) -> dict:
        system_platform = platform.system()
        system_info = {
            "is_desktop": False,
            "system_platform": system_platform,
        }

        if system_platform == "Darwin":
            log_event(logger, logging.INFO, "system", "platform.detected", platform=system_platform, type="desktop_macos")
            system_info["is_desktop"] = True
            return system_info

        if system_platform == "Windows":
            log_event(logger, logging.INFO, "system", "platform.detected", platform=system_platform, type="desktop_windows")
            system_info["is_desktop"] = True
            return system_info

        if system_platform == "Linux":
            pi_detected = False
            try:
                with open("/proc/cpuinfo", "r") as cpuinfo:
                    for line in cpuinfo:
                        if line.startswith("Hardware") and ("BCM" in line or "Raspberry Pi" in line):
                            pi_detected = True
                            break
            except FileNotFoundError:
                pass

            if pi_detected:
                log_event(logger, logging.INFO, "system", "platform.detected", platform=system_platform, type="raspberry_pi")
            else:
                log_event(logger, logging.INFO, "system", "platform.detected", platform=system_platform, type="linux_non_pi")
            return system_info

        log_event(logger, logging.INFO, "system", "platform.detected", platform=system_platform, type="unknown")
        return system_info

    def get_process_memory_usage(self) -> int:
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss
        except Exception as exc:
            log_event(logger, logging.ERROR, "system", "memory.usage_failed", error=exc)
            return 0

    def log_memory_usage(self) -> None:
        memory = psutil.virtual_memory()
        memory_usage = self.get_process_memory_usage()
        available_memory_mb = memory.available / (1024 * 1024)
        used_memory_mb = memory_usage / (1024 * 1024)
        memory_percentage = used_memory_mb / available_memory_mb * 100 if available_memory_mb else 0
        log_event(
            logger,
            logging.DEBUG,
            "system",
            "memory.usage",
            used_mb=round(used_memory_mb, 2),
            available_mb=round(available_memory_mb, 2),
            pct=round(memory_percentage, 2),
        )
