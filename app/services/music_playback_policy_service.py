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
            self.main_app.switch_to_idle()
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
        self.main_app.switch_to_idle()
