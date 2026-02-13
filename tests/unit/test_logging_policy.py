from __future__ import annotations

import logging
import unittest
from types import SimpleNamespace

from app.observability.logger import apply_runtime_logging_policy


class TestLoggingPolicy(unittest.TestCase):
    def setUp(self):
        self.root = logging.getLogger()
        self.original_handlers = list(self.root.handlers)
        self.original_level = self.root.level

        for handler in list(self.root.handlers):
            self.root.removeHandler(handler)

        self.console_handler = logging.StreamHandler()
        self.console_handler._homescreen_handler = "console"
        self.console_handler.setLevel(logging.INFO)

        self.file_handler = logging.StreamHandler()
        self.file_handler._homescreen_handler = "file"
        self.file_handler.setLevel(logging.DEBUG)

        self.root.addHandler(self.console_handler)
        self.root.addHandler(self.file_handler)

    def tearDown(self):
        for handler in list(self.root.handlers):
            self.root.removeHandler(handler)
        for handler in self.original_handlers:
            self.root.addHandler(handler)
        self.root.setLevel(self.original_level)

    def test_profile_pi_applies_expected_levels(self):
        settings = SimpleNamespace(
            log_profile="pi",
            log_noisy_loggers=["urllib3.connectionpool"],
            logger_levels={},
        )

        apply_runtime_logging_policy(settings)

        self.assertEqual(self.root.level, logging.INFO)
        self.assertEqual(self.console_handler.level, logging.INFO)
        self.assertEqual(self.file_handler.level, logging.INFO)
        self.assertEqual(logging.getLogger("urllib3.connectionpool").level, logging.WARNING)

    def test_explicit_settings_override_profile(self):
        settings = SimpleNamespace(
            log_profile="quiet",
            log_level="DEBUG",
            console_log_level="WARNING",
            file_log_level="ERROR",
            log_noisy_third_party_debug=True,
            log_noisy_loggers=["PIL.PngImagePlugin"],
            logger_levels={"app.controllers.mqtt_controller": "WARNING"},
        )

        apply_runtime_logging_policy(settings)

        self.assertEqual(self.root.level, logging.DEBUG)
        self.assertEqual(self.console_handler.level, logging.WARNING)
        self.assertEqual(self.file_handler.level, logging.ERROR)
        self.assertEqual(logging.getLogger("PIL.PngImagePlugin").level, logging.DEBUG)
        self.assertEqual(logging.getLogger("app.controllers.mqtt_controller").level, logging.WARNING)


if __name__ == "__main__":
    unittest.main()
