#!/usr/bin/env python3
"""Utilities to keep local_config/settings.json and settings.json.example in sync safely."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LOCAL_FILE = ROOT / "local_config" / "settings.json"
EXAMPLE_FILE = ROOT / "settings.json.example"

SENSITIVE_KEY_PARTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "dsn",
)

IGNORED_LOCAL_ONLY_PREFIXES = (
    "mqtt_topic_",
)


def is_sensitive_key(path: str) -> bool:
    lowered = path.lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path.name} at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=4) + "\n")


def flatten_paths(data: Any, prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            result.update(flatten_paths(value, path))
    else:
        result[prefix] = data
    return result


def infer_placeholder(path: str, value: Any) -> Any:
    key = path.split(".")[-1].lower()
    if is_sensitive_key(path):
        return "CHANGE_ME"
    if "url" in key:
        return "https://CHANGE_ME"
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return value
    if value is None:
        return None
    return value


def set_nested(data: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cur = data
    for part in parts[:-1]:
        if part not in cur or not isinstance(cur[part], dict):
            cur[part] = {}
        cur = cur[part]
    cur[parts[-1]] = value


def get_nested(data: dict[str, Any], path: str) -> Any:
    cur: Any = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(path)
        cur = cur[part]
    return cur


def delete_nested(data: dict[str, Any], path: str) -> bool:
    parts = path.split(".")
    cur: Any = data
    stack: list[tuple[dict[str, Any], str]] = []
    for part in parts[:-1]:
        if not isinstance(cur, dict) or part not in cur:
            return False
        stack.append((cur, part))
        cur = cur[part]

    if not isinstance(cur, dict) or parts[-1] not in cur:
        return False

    del cur[parts[-1]]

    # Cleanup empty parent dicts up the chain.
    while stack:
        parent, key = stack.pop()
        child = parent.get(key)
        if isinstance(child, dict) and len(child) == 0:
            del parent[key]
        else:
            break
    return True


def order_like_template(target: Any, template: Any) -> Any:
    """Recursively order target dict keys to match template key order first."""
    if not isinstance(target, dict):
        return target

    if not isinstance(template, dict):
        # No template shape: sort keys alphabetically for stable output.
        return {k: order_like_template(v, None) for k, v in sorted(target.items(), key=lambda x: x[0])}

    ordered: dict[str, Any] = {}

    # 1) Keys from template first, in template order.
    for key, template_value in template.items():
        if key in target:
            ordered[key] = order_like_template(target[key], template_value)

    # 2) Extra keys from target afterwards, stable alphabetic order.
    for key in sorted(k for k in target.keys() if k not in template):
        ordered[key] = order_like_template(target[key], None)

    return ordered


def command_check() -> int:
    try:
        local = load_json(LOCAL_FILE)
        example = load_json(EXAMPLE_FILE)
    except ValueError as exc:
        print(f"[settings-sync][error] {exc}")
        return 1

    local_paths = flatten_paths(local)
    example_paths = flatten_paths(example)

    raw_only_local = sorted(set(local_paths) - set(example_paths))
    only_local = sorted(
        path
        for path in raw_only_local
        if not any(path.startswith(prefix) for prefix in IGNORED_LOCAL_ONLY_PREFIXES)
    )
    only_example = sorted(set(example_paths) - set(local_paths))

    type_mismatches = []
    for path in sorted(set(local_paths) & set(example_paths)):
        a = local_paths[path]
        b = example_paths[path]
        if type(a) is not type(b):
            type_mismatches.append((path, type(a).__name__, type(b).__name__))

    print("[settings-sync] check")
    print(f"- only in local_config/settings.json: {len(only_local)}")
    print(f"- only in settings.json.example: {len(only_example)}")
    print(f"- type mismatches: {len(type_mismatches)}")

    if only_local:
        print("\n[only in local_config/settings.json]")
        for path in only_local:
            print(f"  - {path}")

    if only_example:
        print("\n[only in settings.json.example]")
        for path in only_example:
            print(f"  - {path}")

    if type_mismatches:
        print("\n[type mismatches]")
        for path, local_t, example_t in type_mismatches:
            print(f"  - {path}: local={local_t}, example={example_t}")

    return 0


def command_update_example() -> int:
    try:
        local = load_json(LOCAL_FILE)
        example = load_json(EXAMPLE_FILE)
    except ValueError as exc:
        print(f"[settings-sync][error] {exc}")
        return 1

    local_paths = flatten_paths(local)
    example_paths = flatten_paths(example)
    missing = sorted(set(local_paths) - set(example_paths))

    for path in missing:
        value = local_paths[path]
        placeholder = infer_placeholder(path, value)
        set_nested(example, path, placeholder)

    # Keep existing example order stable after additions.
    example = order_like_template(example, example)
    save_json(EXAMPLE_FILE, example)
    print(f"[settings-sync] updated {EXAMPLE_FILE.name} with {len(missing)} missing keys")
    return 0


def command_update_local() -> int:
    try:
        local = load_json(LOCAL_FILE)
        example = load_json(EXAMPLE_FILE)
    except ValueError as exc:
        print(f"[settings-sync][error] {exc}")
        return 1

    local_paths = flatten_paths(local)
    example_paths = flatten_paths(example)
    missing = sorted(set(example_paths) - set(local_paths))

    for path in missing:
        value = get_nested(example, path)
        set_nested(local, path, value)

    # Force local file ordering to follow example ordering.
    local = order_like_template(local, example)
    save_json(LOCAL_FILE, local)
    print(f"[settings-sync] updated {LOCAL_FILE.name} with {len(missing)} missing keys")
    return 0


def command_prune_local(apply: bool) -> int:
    try:
        local = load_json(LOCAL_FILE)
        example = load_json(EXAMPLE_FILE)
    except ValueError as exc:
        print(f"[settings-sync][error] {exc}")
        return 1

    local_paths = flatten_paths(local)
    example_paths = flatten_paths(example)
    raw_extra_paths = sorted(set(local_paths) - set(example_paths))
    extra_paths = sorted(
        path
        for path in raw_extra_paths
        if not any(path.startswith(prefix) for prefix in IGNORED_LOCAL_ONLY_PREFIXES)
    )

    print("[settings-sync] prune-local")
    print(f"- extra keys in local_config/settings.json: {len(extra_paths)}")
    if extra_paths:
        for path in extra_paths:
            print(f"  - {path}")

    if not apply:
        print("\n[settings-sync] dry-run only. Use '--apply' to remove these keys from local_config/settings.json.")
        return 0

    removed = 0
    for path in extra_paths:
        if delete_nested(local, path):
            removed += 1

    local = order_like_template(local, example)
    save_json(LOCAL_FILE, local)
    print(f"[settings-sync] removed {removed} keys from {LOCAL_FILE.name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync and check settings files")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="Show key/type differences")
    sub.add_parser("update-example", help="Add missing keys from local_config/settings.json to settings.json.example")
    sub.add_parser("update-local", help="Add missing keys from settings.json.example to local_config/settings.json")
    prune_local = sub.add_parser(
        "prune-local",
        help="Preview/remove keys in local_config/settings.json that do not exist in settings.json.example",
    )
    prune_local.add_argument(
        "--apply",
        action="store_true",
        help="Actually remove extra keys from local_config/settings.json (default is dry-run preview).",
    )

    args = parser.parse_args()
    if args.command == "check":
        return command_check()
    if args.command == "update-example":
        return command_update_example()
    if args.command == "update-local":
        return command_update_local()
    if args.command == "prune-local":
        return command_prune_local(apply=bool(args.apply))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
