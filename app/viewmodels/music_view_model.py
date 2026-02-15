from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class MusicOverlayViewModel:
    top_text: str
    bottom_text: str
    show_top: bool
    show_bottom: bool


_BRACKET_META_PATTERN = re.compile(
    r"\s*[\(\[][^)\]]*"
    r"(?:"
    r"remaster(?:ed)?|remix|live|acoustic|mono|stereo|instrumental|karaoke|"
    r"bonus|radio\s*edit|edit|version|deluxe|extended|expanded|anniversary|single|"
    r"ost|soundtrack|score|motion\s+picture|from\s+the\s+motion\s+picture"
    r")"
    r"[^)\]]*[\)\]]",
    flags=re.IGNORECASE,
)
_FEAT_PATTERN = re.compile(
    r"\s*[\(\[]?\s*(?:feat\.?|ft\.?|featuring)\s+[^)\]-]+[\)\]]?\s*",
    flags=re.IGNORECASE,
)
_TRAILING_META_PATTERN = re.compile(
    r"\s*[-–—]\s*"
    r"(?:"
    r"(?:20\d{2}\s+)?remaster(?:ed)?(?:\s+\d{4})?|remix|live.*|acoustic.*|"
    r"radio\s*edit|edit|version|deluxe.*|extended.*|expanded.*|anniversary.*|single.*|"
    r"(?:from\s+.+\s+)?(?:ost|soundtrack|score|motion\s+picture.*)"
    r")\s*$",
    flags=re.IGNORECASE,
)
_WHITESPACE_PATTERN = re.compile(r"\s+")


def sanitize_title(value: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        return ""

    # Remove noisy feature tags and bracketed metadata blocks.
    cleaned = _FEAT_PATTERN.sub(" ", cleaned)
    previous = None
    while previous != cleaned:
        previous = cleaned
        cleaned = _BRACKET_META_PATTERN.sub("", cleaned)

    # Remove trailing dash metadata suffixes.
    cleaned = _TRAILING_META_PATTERN.sub("", cleaned)

    # Normalize spacing and trailing separators.
    cleaned = _WHITESPACE_PATTERN.sub(" ", cleaned).strip(" -–—:;,.")
    if not cleaned:
        return str(value).strip()
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
