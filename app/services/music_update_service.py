from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp


class MusicUpdateService:
    """Owns music MQTT update queueing, coalescing and debounce flush behavior."""

    def __init__(self, main_app: MainApp):
        self.main_app = main_app
        self._pending_payload = None
        self._update_after_id = None
        self._update_seq = 0

    def queue_update(self, data):
        self.main_app.record_music_metric("received")
        self._update_seq += 1
        update_seq = self._update_seq
        self.main_app.log_music_debug(
            f"[music] queue start seq={update_seq} raw_keys={sorted((data or {}).keys())}",
            data,
        )
        normalized = self.main_app.music_service.normalize_payload(data or {})
        self.main_app.log_music_debug(f"[music] normalized seq={update_seq}", normalized)
        has_transport = self.main_app.music_service.has_transport_update(normalized)
        if has_transport and self.main_app.music_apply_transport_immediately:
            self.main_app.log_music_debug(f"[music] transport-priority seq={update_seq}")
            self._pending_payload = normalized
            if self._update_after_id:
                self.main_app.root.after_cancel(self._update_after_id)
                self._update_after_id = None
            self.flush(reason="transport")
            return

        if self._pending_payload is None:
            self._pending_payload = normalized
        else:
            # Merge partial updates so fast event bursts don't drop fields.
            self.main_app.record_music_metric("coalesced")
            self._pending_payload.update(normalized)
        self.main_app.log_music_debug(f"[music] pending merged seq={update_seq}", self._pending_payload)
        if self._update_after_id:
            self.main_app.root.after_cancel(self._update_after_id)
            self.main_app.log_music_debug(f"[music] debounce reset seq={update_seq}")
        self._update_after_id = self.main_app.root.after(self.main_app.music_update_debounce_ms, self.flush)

    def flush(self, reason="debounced"):
        self._update_after_id = None
        payload = self._pending_payload
        self._pending_payload = None
        if payload is None:
            self.main_app.log_music_debug("[music] flush skipped: no pending payload")
            return
        self.main_app.log_music_debug(f"[music] flush pending payload reason={reason}", payload)
        resolved_payload = self.main_app.music_service.resolve_payload(self.main_app.music_object, payload)
        self.main_app.log_music_debug("[music] resolved payload", resolved_payload)
        if not self.main_app.music_service.should_process(
            resolved_payload,
            drop_duplicates=self.main_app.music_drop_duplicate_payloads,
        ):
            self.main_app.log_music_debug("[music] duplicate payload dropped", resolved_payload)
            self.main_app.record_music_metric("dropped")
            return
        self.main_app.log_music_debug("[music] applying payload", resolved_payload)
        self.main_app.record_music_metric("applied")
        self.main_app.update_music_object(resolved_payload)
        self.main_app.publish_event(
            "menu.refresh.requested",
            {"reason": "music.update.applied"},
            source="main",
        )
