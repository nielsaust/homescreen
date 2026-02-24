from __future__ import annotations

import logging
import time

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

    def fetch_album_art_bytes(self, url: str, max_retries: int = 3, retry_delay_ms: int = 0) -> bytes | None:
        verify = self._resolve_ssl_verify()
        total_retries = max(1, int(max_retries or 1))
        delay_seconds = max(0.0, float(retry_delay_ms or 0) / 1000.0)
        for retry in range(total_retries):
            attempt = retry + 1
            try:
                response = requests.get(url, timeout=10, verify=verify)
                response.raise_for_status()
                if attempt > 1:
                    logger.info(
                        "Album art request succeeded on attempt %s/%s",
                        attempt,
                        total_retries,
                    )
                return response.content
            except requests.RequestException as exc:
                if attempt < total_retries:
                    logger.warning(
                        "Error retrieving album art (attempt %s/%s): %s",
                        attempt,
                        total_retries,
                        exc,
                    )
                else:
                    logger.error(
                        "Error retrieving album art (attempt %s/%s): %s",
                        attempt,
                        total_retries,
                        exc,
                    )
                if attempt < total_retries and delay_seconds > 0:
                    time.sleep(delay_seconds)
        return None
