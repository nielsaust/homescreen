from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

SENSITIVE_KEY_PARTS = (
    "password",
    "token",
    "secret",
    "authorization",
    "api_key",
    "dsn",
)


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def _sanitize_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in mapping.items():
        if _is_sensitive_key(str(key)):
            sanitized[key] = "[redacted]"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_mapping(value)
        else:
            sanitized[key] = value
    return sanitized


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    extra = event.get("extra")
    if isinstance(extra, dict):
        event["extra"] = _sanitize_mapping(extra)

    contexts = event.get("contexts")
    if isinstance(contexts, dict):
        event["contexts"] = _sanitize_mapping(contexts)

    tags = event.get("tags")
    if isinstance(tags, dict):
        event["tags"] = _sanitize_mapping(tags)

    request = event.get("request")
    if isinstance(request, dict):
        headers = request.get("headers")
        if isinstance(headers, dict):
            request["headers"] = _sanitize_mapping(headers)
        data = request.get("data")
        if isinstance(data, dict):
            request["data"] = _sanitize_mapping(data)

    return event


def _level_from_settings(value: Any, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(getattr(logging, value.upper(), default))
    return int(default)


def init_sentry(settings: Any) -> bool:
    enabled = bool(getattr(settings, "do_sentry_logging", False))
    dsn = str(getattr(settings, "sentry_dsn", "") or "").strip()
    if not enabled:
        logger.info("Sentry disabled (do_sentry_logging=false).")
        return False
    if not dsn:
        logger.warning("Sentry enabled but sentry_dsn is empty; skipping Sentry init.")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.threading import ThreadingIntegration
        from sentry_sdk.integrations.tkinter import TkinterIntegration
    except Exception as exc:
        logger.error("Could not import sentry_sdk: %s", exc)
        return False

    environment = str(getattr(settings, "sentry_environment", "development"))
    release = str(getattr(settings, "version", "dev"))
    traces_sample_rate = float(getattr(settings, "sentry_traces_sample_rate", 0.0))
    send_default_pii = bool(getattr(settings, "sentry_send_default_pii", False))

    breadcrumbs_level = _level_from_settings(getattr(settings, "sentry_breadcrumb_level", "INFO"), logging.INFO)
    event_level = _level_from_settings(getattr(settings, "sentry_event_level", "ERROR"), logging.ERROR)

    logging_integration = LoggingIntegration(
        level=breadcrumbs_level,
        event_level=event_level,
    )

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        send_default_pii=send_default_pii,
        integrations=[
            logging_integration,
            ThreadingIntegration(propagate_hub=True),
            TkinterIntegration(),
        ],
        before_send=_before_send,
        traces_sample_rate=traces_sample_rate,
    )

    sentry_sdk.set_tag("platform", "homescreen")
    logger.info(
        "Sentry initialized (env=%s, release=%s, breadcrumbs=%s, event=%s).",
        environment,
        release,
        logging.getLevelName(breadcrumbs_level),
        logging.getLevelName(event_level),
    )
    return True
