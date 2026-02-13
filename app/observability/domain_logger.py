from __future__ import annotations

import logging


def _format_fields(fields: dict) -> str:
    if not fields:
        return ""
    parts = []
    for key, value in fields.items():
        parts.append(f"{key}={value!r}")
    return " " + " ".join(parts)


def log_event(logger: logging.Logger, level: int, domain: str, event: str, **fields):
    logger.log(level, "[%s] %s%s", domain, event, _format_fields(fields))
