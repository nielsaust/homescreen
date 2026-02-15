from __future__ import annotations

import unittest

from app.viewmodels.music_view_model import build_music_overlay_view_model, sanitize_title


class TestMusicViewModel(unittest.TestCase):
    def test_sanitize_title_removes_common_metadata(self):
        cases = [
            ("Sexy For Me - Remastered 2011", "Sexy For Me"),
            ("Love Song (feat. Artist Name)", "Love Song"),
            ("Track Name (Live at Wembley 1990)", "Track Name"),
            ("Movie Theme (Original Motion Picture Soundtrack)", "Movie Theme"),
            ("Hit Single - From The Motion Picture Soundtrack", "Hit Single"),
            ("Dance Track [Radio Edit]", "Dance Track"),
        ]
        for original, expected in cases:
            with self.subTest(original=original):
                self.assertEqual(sanitize_title(original), expected)

    def test_overlay_view_model_respects_sanitize_toggle(self):
        title = "Song Name - Remastered 2011"
        album = "Album Name (Deluxe Edition)"

        vm_off = build_music_overlay_view_model(
            artist="Artist",
            title=title,
            album=album,
            channel=None,
            sanitize=False,
        )
        vm_on = build_music_overlay_view_model(
            artist="Artist",
            title=title,
            album=album,
            channel=None,
            sanitize=True,
        )

        self.assertIn("Remastered", vm_off.bottom_text)
        self.assertIn("Deluxe", vm_off.bottom_text)
        self.assertEqual(vm_on.bottom_text, "Song Name - Album Name")


if __name__ == "__main__":
    unittest.main()
