from __future__ import annotations

from dataclasses import replace

from core.events import AppEvent
from core.state import AppState


def reduce_state(state: AppState, event: AppEvent) -> AppState:
    """Pure reducer for app state transitions."""
    base = replace(state, updated_at=event.timestamp)
    event_type = event.event_type
    payload = event.payload

    if event_type == "app.started":
        return replace(
            base,
            system_platform=payload.get("system_platform", base.system_platform),
            is_desktop=payload.get("is_desktop", base.is_desktop),
            startup_queue_size=payload.get("startup_queue_size", base.startup_queue_size),
            data={**base.data, "version": payload.get("version")},
        )

    if event_type == "network.status":
        return replace(base, network_online=payload.get("online"))

    if event_type == "ui.screen.changed":
        return replace(
            base,
            screen_state=payload.get("screen", base.screen_state),
            is_display_on=payload.get("is_display_on", base.is_display_on),
        )

    if event_type == "interaction.received":
        return replace(base, last_interaction_type=payload.get("interaction_type"))

    if event_type == "action.triggered":
        return replace(base, last_action=payload.get("action"))

    if event_type == "mqtt.message.received":
        return replace(base, last_mqtt_topic=payload.get("topic"))

    if event_type == "music.updated":
        return replace(
            base,
            music_state=payload.get("state", base.music_state),
            music_title=payload.get("title", base.music_title),
            music_artist=payload.get("artist", base.music_artist),
        )

    if event_type == "device.state.updated":
        return replace(
            base,
            in_bed=payload.get("in_bed", base.in_bed),
            printer_progress=payload.get("printer_progress", base.printer_progress),
        )

    if event_type == "startup.queue.size":
        return replace(base, startup_queue_size=payload.get("size", base.startup_queue_size))

    return base
