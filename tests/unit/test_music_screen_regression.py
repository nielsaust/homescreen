from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.ui.screens.music_screen import MusicScreen


class TestMusicScreenRegression(unittest.TestCase):
    def _make_screen(self, music_object):
        screen = MusicScreen.__new__(MusicScreen)
        screen.main_app = SimpleNamespace(
            music_object=music_object,
            settings=SimpleNamespace(media_show_titles=True),
            music_debug_logging=False,
        )
        calls = {
            "clear": 0,
            "art": 0,
            "overlays": 0,
            "remove_overlays": 0,
        }

        def _clear_current():
            calls["clear"] += 1

        def _maybe_load_album_art(_url):
            calls["art"] += 1

        def _show_overlays(_artist, _title, _album, _channel):
            calls["overlays"] += 1

        def _remove_overlays():
            calls["remove_overlays"] += 1

        screen.clear_current = _clear_current
        screen._maybe_load_album_art = _maybe_load_album_art
        screen.show_overlays = _show_overlays
        screen.remove_overlays = _remove_overlays
        return screen, calls

    def test_show_does_not_fail_when_artist_missing(self):
        music_object = SimpleNamespace(
            state="playing",
            title="Song",
            artist=None,
            channel=None,
            album="Album",
            album_art_api_url="/api/media_player_proxy/x",
        )
        screen, calls = self._make_screen(music_object)

        result = screen.show()

        self.assertTrue(result)
        self.assertEqual(calls["clear"], 1)
        self.assertEqual(calls["art"], 1)
        # Partial metadata should still render (no hard fail).
        self.assertEqual(calls["overlays"], 1)
        self.assertEqual(calls["remove_overlays"], 0)

    def test_show_still_renders_overlays_with_full_metadata(self):
        music_object = SimpleNamespace(
            state="playing",
            title="Song",
            artist="Artist",
            channel=None,
            album="Album",
            album_art_api_url="/api/media_player_proxy/x",
        )
        screen, calls = self._make_screen(music_object)

        result = screen.show()

        self.assertTrue(result)
        self.assertEqual(calls["clear"], 1)
        self.assertEqual(calls["art"], 1)
        self.assertEqual(calls["overlays"], 1)
        self.assertEqual(calls["remove_overlays"], 0)


if __name__ == "__main__":
    unittest.main()
