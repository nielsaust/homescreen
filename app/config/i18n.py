from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
APP_LOCALES_DIR = ROOT / "app" / "locales"
LOCAL_I18N_DIR = ROOT / "local_config" / "i18n"


class _SafeFormatDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


class I18n:
    def __init__(self, settings):
        self.settings = settings
        self.locale = str(getattr(settings, "language", "en") or "en").strip().lower()
        self.catalog = self._load_catalog()

    def _load_json_dict(self, path: Path) -> dict:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        except Exception as exc:
            logger.warning("Could not load i18n catalog from %s: %s", path, exc)
        return {}

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        out = dict(base)
        for key, value in override.items():
            if key in out and isinstance(out[key], dict) and isinstance(value, dict):
                out[key] = I18n._deep_merge(out[key], value)
            else:
                out[key] = value
        return out

    def _candidate_local_override_paths(self) -> list[Path]:
        base = self.locale.split("-")[0].split("_")[0]
        candidates: list[Path] = []
        if self.locale:
            candidates.append(LOCAL_I18N_DIR / f"{self.locale}.json")
        if base and base != self.locale:
            candidates.append(LOCAL_I18N_DIR / f"{base}.json")
        return candidates

    def _builtin_base_path(self) -> Path:
        base = self.locale.split("-")[0].split("_")[0]
        if self.locale:
            p = APP_LOCALES_DIR / f"{self.locale}.json"
            if p.exists():
                return p
        if base:
            p = APP_LOCALES_DIR / f"{base}.json"
            if p.exists():
                return p
        return APP_LOCALES_DIR / "en.json"

    def _load_catalog(self) -> dict:
        builtin_path = self._builtin_base_path()
        base_catalog = self._load_json_dict(builtin_path) if builtin_path.exists() else {}
        if not base_catalog:
            logger.warning("No built-in i18n catalog found for locale '%s'", self.locale)
            return {}

        merged = base_catalog
        for path in self._candidate_local_override_paths():
            if not path.exists():
                continue
            override = self._load_json_dict(path)
            if not override:
                continue
            merged = self._deep_merge(merged, override)
            logger.info("Applied i18n local override locale='%s' from %s", self.locale, path)
        logger.info("Loaded i18n catalog locale='%s' from %s", self.locale, builtin_path)
        return merged

    def _get_nested(self, key: str):
        node = self.catalog
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node

    def t(self, key: str, default: str | None = None, **kwargs) -> str:
        raw = self._get_nested(key)
        if not isinstance(raw, str):
            raw = default if default is not None else key
        if not kwargs:
            return raw
        try:
            return raw.format_map(_SafeFormatDict(**kwargs))
        except Exception:
            return raw
