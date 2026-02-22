from __future__ import annotations

import logging
import os
import pathlib
import re
import sys
from datetime import datetime, timedelta
from typing import Iterable

DEFAULT_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_FILE_MESSAGE_FORMAT = "timestamp=%(asctime)s level=%(levelname)s logger=%(name)s msg=%(message)s"
DEFAULT_NOISY_LOGGERS = (
    "PIL.PngImagePlugin",
    "urllib3.connectionpool",
)
DEFAULT_LOG_PROFILE = "default"
DEFAULT_LOG_PROFILES = {
    "default": {
        "console_level": "INFO",
        "file_level": "DEBUG",
        "log_noisy_third_party_debug": False,
    },
    "dev": {
        "console_level": "DEBUG",
        "file_level": "DEBUG",
        "log_noisy_third_party_debug": False,
    },
    "pi": {
        "console_level": "INFO",
        "file_level": "INFO",
        "log_noisy_third_party_debug": False,
    },
    "quiet": {
        "console_level": "WARNING",
        "file_level": "INFO",
        "log_noisy_third_party_debug": False,
    },
}


def _parse_level(value, default=logging.INFO) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(getattr(logging, value.upper(), default))
    return int(default)


def _parse_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "enabled"}:
            return True
        if normalized in {"0", "false", "no", "off", "disabled", ""}:
            return False
    return default


def _resolve_profile(settings):
    profile_name = str(getattr(settings, "log_profile", DEFAULT_LOG_PROFILE) or DEFAULT_LOG_PROFILE).strip().lower()
    profile = DEFAULT_LOG_PROFILES.get(profile_name, DEFAULT_LOG_PROFILES[DEFAULT_LOG_PROFILE])
    return profile_name, profile


class StructuredConsoleFormatter(logging.Formatter):
    RESET = "\033[0m"
    TS_COLOR = "\033[38;5;255m"
    MSG_COLOR = "\033[38;5;252m"
    VALUE_COLOR = "\033[38;5;117m"
    BOOL_COLOR = "\033[38;5;141m"
    NUMBER_COLOR = "\033[38;5;222m"
    LOGGER_COLOR = "\033[38;5;245m"
    BADGES = {
        logging.DEBUG: "\033[38;5;16;48;5;68m[DEBUG]\033[0m",
        logging.INFO: "\033[38;5;16;48;5;42m[INFO ]\033[0m",
        logging.WARNING: "\033[38;5;16;48;5;220m[WARN ]\033[0m",
        logging.ERROR: "\033[38;5;15;48;5;160m[ERROR]\033[0m",
        logging.CRITICAL: "\033[38;5;15;48;5;88m[FATAL]\033[0m",
    }

    def __init__(self, *, use_colors: bool = True):
        super().__init__()
        self.use_colors = bool(use_colors)

    def _wrap_color(self, text: str, color: str) -> str:
        return f"{color}{text}{self.MSG_COLOR}"

    def _colorize_values(self, message: str) -> str:
        message = re.sub(
            r"\b(True|False|None|true|false|null)\b",
            lambda m: self._wrap_color(m.group(0), self.BOOL_COLOR),
            message,
        )
        message = re.sub(r"'([^']*)'", lambda m: self._wrap_color(m.group(0), self.VALUE_COLOR), message)
        message = re.sub(r'"([^"]*)"', lambda m: self._wrap_color(m.group(0), self.VALUE_COLOR), message)
        return message

    def format(self, record):
        ts = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        level_name = record.levelname
        message = record.getMessage()
        logger_name = record.name

        if not self.use_colors:
            base = f"{ts} [{level_name:<5}] logger={logger_name} {message}"
        else:
            badge = self.BADGES.get(record.levelno, f"[{level_name:<5}]")
            colored_message = self._colorize_values(message)
            base = (
                f"{self.TS_COLOR}{ts}{self.RESET} "
                f"{badge} "
                f"{self.LOGGER_COLOR}{logger_name}{self.RESET} "
                f"{self.MSG_COLOR}{colored_message}{self.RESET}"
            )

        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            return f"{base}\n{exc_text}"
        return base


class DateRotatingFileHandler(logging.FileHandler):
    def __init__(
        self,
        log_dir: pathlib.Path,
        *,
        retention_days: int = 7,
        mode: str = "a",
        encoding: str | None = "utf-8",
        delay: bool = False,
    ):
        self.log_dir = pathlib.Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = max(1, int(retention_days))
        self.current_date = datetime.now().strftime(DEFAULT_DATE_FORMAT)
        self.fallback_log_path = self.log_dir / "rollover_logs.txt"
        self._in_rollover = False
        super().__init__(self._build_log_filename(self.current_date), mode, encoding, delay)

    def emit(self, record):
        try:
            today = datetime.now().strftime(DEFAULT_DATE_FORMAT)
            if today != self.current_date:
                self._rollover(today)
            super().emit(record)
        except Exception as exc:
            self._fallback_write("[ERROR] Error during emit", exc)

    def _rollover(self, today: str):
        if self._in_rollover:
            self._fallback_write("[WARN] Ignoring re-entrant rollover")
            return
        self._in_rollover = True
        try:
            if self.stream:
                self.stream.close()
                self.stream = None
            self.baseFilename = self._build_log_filename(today)
            self.current_date = today
            self.stream = self._open()
            self._delete_old_logs()
        except Exception as exc:
            self._fallback_write("[ERROR] Error during rollover", exc)
        finally:
            self._in_rollover = False

    def _delete_old_logs(self):
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        for log_file in self.log_dir.glob("*.log"):
            try:
                if datetime.strptime(log_file.stem, DEFAULT_DATE_FORMAT) < cutoff:
                    log_file.unlink()
            except ValueError:
                # Ignore files that are not date-based logs.
                continue
            except Exception as exc:
                self._fallback_write(f"[ERROR] Error deleting log file {log_file}", exc)

    def _build_log_filename(self, date_str: str) -> str:
        return os.fspath(self.log_dir / f"{date_str}.log")

    def _fallback_write(self, message: str, exc: Exception | None = None):
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            with open(self.fallback_log_path, "a", encoding="utf-8") as fh:
                fh.write(f"{datetime.now().isoformat()} {message}\n")
                if exc is not None:
                    fh.write(f"Exception: {exc}\n")
        except Exception:
            # Last resort: avoid recursive logger usage in logger setup path.
            print(message, file=sys.stderr)
            if exc is not None:
                print(exc, file=sys.stderr)


def setup_logging():
    root_logger = logging.getLogger()
    if getattr(root_logger, "_homescreen_logging_configured", False):
        return

    project_root = pathlib.Path(__file__).resolve().parents[2]
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = DateRotatingFileHandler(log_dir, retention_days=7)
    file_handler._homescreen_handler = "file"
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(DEFAULT_FILE_MESSAGE_FORMAT))
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler._homescreen_handler = "console"
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(StructuredConsoleFormatter(use_colors=bool(getattr(sys.stderr, "isatty", lambda: False)())))
    root_logger.addHandler(console_handler)

    root_logger.setLevel(logging.DEBUG)
    root_logger._homescreen_logging_configured = True


def apply_runtime_logging_policy(settings):
    root_logger = logging.getLogger()
    profile_name, profile = _resolve_profile(settings)

    debug_enabled = _parse_bool(
        getattr(settings, "log_debug_enabled", getattr(settings, "debug_logging", False)),
        False,
    )
    if debug_enabled:
        # Unified debug mode: one switch enables debug everywhere.
        console_level = logging.DEBUG
        file_level = logging.DEBUG
        root_level = logging.DEBUG
    else:
        console_level = _parse_level(
            getattr(settings, "log_console_level", getattr(settings, "console_log_level", profile["console_level"])),
            logging.INFO,
        )
        file_level = _parse_level(
            getattr(settings, "log_file_level", getattr(settings, "file_log_level", profile["file_level"])),
            logging.DEBUG,
        )
        root_default = min(console_level, file_level)
        root_level = _parse_level(getattr(settings, "log_level", root_default), root_default)

    root_logger.setLevel(root_level)
    for handler in root_logger.handlers:
        handler_name = getattr(handler, "_homescreen_handler", None)
        if handler_name == "console":
            handler.setLevel(console_level)
        elif handler_name == "file":
            handler.setLevel(file_level)
        else:
            handler.setLevel(root_level)

    noisy_debug_enabled = bool(
        getattr(settings, "log_noisy_third_party_debug", profile["log_noisy_third_party_debug"])
    )
    noisy_logger_names: Iterable[str] = tuple(getattr(settings, "log_noisy_loggers", DEFAULT_NOISY_LOGGERS))
    for logger_name in noisy_logger_names:
        target_logger = logging.getLogger(str(logger_name))
        if noisy_debug_enabled:
            target_logger.setLevel(logging.DEBUG)
        else:
            target_logger.setLevel(logging.WARNING)

    domain_override_enabled = _parse_bool(
        getattr(settings, "log_enable_domain_levels", getattr(settings, "enable_domain_log_levels", False)),
        False,
    )
    logger_levels = getattr(settings, "log_domain_levels", getattr(settings, "logger_levels", {})) or {}
    if domain_override_enabled and isinstance(logger_levels, dict):
        for logger_name, configured_level in logger_levels.items():
            logging.getLogger(str(logger_name)).setLevel(_parse_level(configured_level, logging.INFO))

    logging.getLogger(__name__).info(
        "Logging policy profile='%s' applied (debug=%s, root=%s, console=%s, file=%s, noisy_debug=%s, domain_overrides=%s).",
        profile_name,
        debug_enabled,
        logging.getLevelName(root_level),
        logging.getLevelName(console_level),
        logging.getLevelName(file_level),
        noisy_debug_enabled,
        domain_override_enabled,
    )
