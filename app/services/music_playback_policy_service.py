from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import MainApp


class MusicPlaybackPolicyService:
    """Owns delayed idle fallback behavior for paused music playback."""

    def __init__(self, main_app: MainApp):
        self.main_app = main_app
        self._music_pause_timeout = None

    def cancel_pause_idle_timeout(self) -> None:
        if self._music_pause_timeout is None:
            return
        self.main_app.root.after_cancel(self._music_pause_timeout)
        self._music_pause_timeout = None

    def schedule_pause_idle(self) -> None:
        self.cancel_pause_idle_timeout()
        if self.main_app.music_pause_grace_ms <= 0:
            self.main_app.screen_state_controller.switch_to_idle()
            return

        self._music_pause_timeout = self.main_app.root.after(
            self.main_app.music_pause_grace_ms,
            self._apply_music_pause_idle,
        )

    def _apply_music_pause_idle(self) -> None:
        self._music_pause_timeout = None
        if self.main_app.display_controller.get_screen_state() == "menu":
            return
        state = getattr(self.main_app.music_object, "state", None)
        if state == "playing":
            return
        self._clear_music_before_idle_transition()
        self.main_app.screen_state_controller.switch_to_idle()

    def _clear_music_before_idle_transition(self) -> None:
        clear_art = bool(getattr(self.main_app.settings, "clear_album_art_when_idle", False))
        clear_info = bool(getattr(self.main_app.settings, "clear_music_info", False))
        if clear_art:
            self.main_app.display_controller.cancel_pending_album_art_load()
            self.main_app.display_controller.clear_album_art()
        if clear_info:
            self.main_app.display_controller.clear_music_info()
