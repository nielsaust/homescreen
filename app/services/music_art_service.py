from __future__ import annotations

import logging

import certifi
import requests

logger = logging.getLogger(__name__)


class MusicArtService:
    """Fetches album art bytes with retry/SSL handling."""

    def __init__(self, verify_ssl: bool = True):
        self.verify_ssl = verify_ssl

    def _resolve_ssl_verify(self):
        if not self.verify_ssl:
            return False
        try:
            return certifi.where()
        except Exception:
            return True

    def fetch_album_art_bytes(self, url: str, max_retries: int = 3) -> bytes | None:
        verify = self._resolve_ssl_verify()
        for retry in range(max_retries):
            try:
                response = requests.get(url, timeout=10, verify=verify)
                response.raise_for_status()
                return response.content
            except requests.RequestException as exc:
                logger.error(
                    "Error retrieving album art (attempt %s/%s): %s",
                    retry + 1,
                    max_retries,
                    exc,
                )
        return None
