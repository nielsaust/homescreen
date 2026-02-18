from __future__ import annotations

import copy

from app.ui.menu_button import MenuButton
from app.ui.menu_config_loader import (
    get_button_setting_requirements,
    get_menu_schema,
)


_BUTTON_SETTING_REQUIREMENTS = get_button_setting_requirements()


def _order_value(entry, fallback_idx):
    raw = entry.get("order")
    if isinstance(raw, int):
        return raw
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 10_000 + fallback_idx


def _sort_entries_by_order(entries):
    ordered = sorted(
        entries,
        key=lambda item_with_idx: _order_value(item_with_idx[1], item_with_idx[0]),
    )
    out = []
    for _, entry in ordered:
        cloned = copy.deepcopy(entry)
        children = cloned.get("screen") or []
        if children:
            cloned["screen"] = _sort_entries_by_order(list(enumerate(children)))
        out.append(cloned)
    return out


def _build_entry(schema_entry):
    button = MenuButton(
        schema_entry["id"],
        schema_entry["text"],
        schema_entry["image"],
        schema_entry["action"],
        cancel_close=bool(schema_entry.get("cancel_close", False)),
    )
    sub_schema = schema_entry.get("screen", [])
    return {
        "button": button,
        "screen": [_build_entry(child) for child in sub_schema],
    }


def _is_enabled_by_settings(button_id, settings):
    required_settings = _BUTTON_SETTING_REQUIREMENTS.get(button_id)
    if not required_settings:
        return True
    if settings is None:
        return True
    for key in required_settings:
        raw_value = getattr(settings, key, "")
        if isinstance(raw_value, bool):
            if not raw_value:
                return False
            continue
        value = str(raw_value).strip()
        if not value:
            return False
    return True


def _is_allowed_by_environment(schema_entry, settings):
    if not bool(schema_entry.get("dev_only", False)):
        return True
    env = str(getattr(settings, "app_environment", "production") or "production").strip().lower()
    return env not in {"production", "prod"}


def _filter_schema_by_settings(entries, settings):
    filtered = []
    for entry in entries:
        button_id = entry.get("id")
        if not _is_enabled_by_settings(button_id, settings):
            continue
        if not _is_allowed_by_environment(entry, settings):
            continue

        cloned = copy.deepcopy(entry)
        children = cloned.get("screen") or []
        if children:
            children = _filter_schema_by_settings(children, settings)
            cloned["screen"] = children
            if cloned.get("action") == "open_page":
                has_actionable_child = any(child.get("action") != "back" for child in children)
                if not has_actionable_child:
                    continue

        filtered.append(cloned)
    return filtered


def build_menu_buttons(settings=None):
    schema = _sort_entries_by_order(list(enumerate(get_menu_schema())))
    schema = _filter_schema_by_settings(schema, settings)
    return [_build_entry(entry) for entry in schema]
