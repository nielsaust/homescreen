from __future__ import annotations

import logging
import os
import pathlib
import sys
from datetime import datetime, timedelta
from typing import Iterable

DEFAULT_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_MESSAGE_FORMAT = "%(asctime)s [%(name)s] %(levelname)s - %(message)s"
DEFAULT_NOISY_LOGGERS = (
    "PIL.PngImagePlugin",
    "urllib3.connectionpool",
)


def _parse_level(value, default=logging.INFO) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(getattr(logging, value.upper(), default))
    return int(default)


class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[38;5;159m",
        logging.INFO: "\033[38;5;113m",
        logging.WARNING: "\033[38;5;172m",
        logging.ERROR: "\033[38;5;1m",
        logging.CRITICAL: "\033[38;5;13m",
    }
    RESET = "\033[0m"

    def __init__(self, fmt: str, *, use_colors: bool = True):
        super().__init__(fmt)
        self.use_colors = bool(use_colors)

    def format(self, record):
        message = super().format(record)
        if not self.use_colors:
            return message
        color = self.COLORS.get(record.levelno, self.RESET)
        return f"{color}{message}{self.RESET}"


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

    project_root = pathlib.Path(__file__).parent
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = DateRotatingFileHandler(log_dir, retention_days=7)
    file_handler._homescreen_handler = "file"
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(DEFAULT_MESSAGE_FORMAT))
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler._homescreen_handler = "console"
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        ColoredFormatter(
            DEFAULT_MESSAGE_FORMAT,
            use_colors=bool(getattr(sys.stderr, "isatty", lambda: False)()),
        )
    )
    root_logger.addHandler(console_handler)

    root_logger.setLevel(logging.DEBUG)
    root_logger._homescreen_logging_configured = True


def apply_runtime_logging_policy(settings):
    root_logger = logging.getLogger()
    root_level = _parse_level(getattr(settings, "log_level", "INFO"), logging.INFO)
    console_level = _parse_level(getattr(settings, "console_log_level", "INFO"), logging.INFO)
    file_level = _parse_level(getattr(settings, "file_log_level", "DEBUG"), logging.DEBUG)

    root_logger.setLevel(root_level)
    for handler in root_logger.handlers:
        handler_name = getattr(handler, "_homescreen_handler", None)
        if handler_name == "console":
            handler.setLevel(console_level)
        elif handler_name == "file":
            handler.setLevel(file_level)
        else:
            handler.setLevel(root_level)

    noisy_debug_enabled = bool(getattr(settings, "log_noisy_third_party_debug", False))
    noisy_logger_names: Iterable[str] = tuple(getattr(settings, "log_noisy_loggers", DEFAULT_NOISY_LOGGERS))
    for logger_name in noisy_logger_names:
        target_logger = logging.getLogger(str(logger_name))
        if noisy_debug_enabled:
            target_logger.setLevel(logging.DEBUG)
        else:
            target_logger.setLevel(logging.WARNING)
