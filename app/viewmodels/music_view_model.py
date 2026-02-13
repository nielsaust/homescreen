from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class MusicOverlayViewModel:
    top_text: str
    bottom_text: str
    show_top: bool
    show_bottom: bool


def sanitize_title(value: str) -> str:
    pattern_remaster = (
        r"\s*[-(].*?(\bremaster(ed)?\b|\bbonus\b|\blive\b|\bacoustic\b|\bremix\b|"
        r"\b(deluxe|extended|expanded|anniversary|single)\s+(version|edition)\b|\bfeat\..*\b).*\s*((\)|\]))?"
    )
    pattern_movie_score = r" \((Original Motion Picture Soundtrack|Soundtrack|OST|Score|Music from the Motion Picture)\)"

    cleaned = re.sub(pattern_remaster, "", value, flags=re.IGNORECASE)
    cleaned = re.sub(pattern_movie_score, "", cleaned, flags=re.IGNORECASE)
    return cleaned


def build_music_overlay_view_model(
    artist: str | None,
    title: str | None,
    album: str | None,
    channel: str | None,
    sanitize: bool,
) -> MusicOverlayViewModel:
    if sanitize:
        if title:
            title = sanitize_title(title)
        if album:
            album = sanitize_title(album)

    top_text = ""
    if artist:
        top_text = artist
    elif channel:
        top_text = channel

    bottom_text = ""
    if not channel and (title and album) and (title != album):
        bottom_text = f"{title} - {album}"
    elif title and title != channel:
        bottom_text = title

    return MusicOverlayViewModel(
        top_text=top_text,
        bottom_text=bottom_text,
        show_top=bool(top_text),
        show_bottom=bool(bottom_text),
    )
