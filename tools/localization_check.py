#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCALES = {
    "en": ROOT / "app" / "locales" / "en.json",
    "nl": ROOT / "app" / "locales" / "nl.json",
}


def _flatten_keys(obj: dict, prefix: str = "") -> set[str]:
    out: set[str] = set()
    for key, value in obj.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out |= _flatten_keys(value, full)
        else:
            out.add(full)
    return out


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    main_py = ROOT / "main.py"
    if main_py.exists():
        files.append(main_py)
    for path in (ROOT / "app").rglob("*.py"):
        if any(part in {".venv", "__pycache__", ".git"} for part in path.parts):
            continue
        files.append(path)
    return files


def _extract_used_and_dynamic_prefixes() -> tuple[set[str], set[str]]:
    used_keys: set[str] = set()
    dynamic_prefixes: set[str] = set()

    for path in _iter_python_files():
        source = path.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(source, filename=str(path))
        except Exception:
            continue

        t_aliases: set[str] = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "t"
            ):
                t_aliases.add(node.targets[0].id)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue

            func = node.func
            is_t_call = False
            if isinstance(func, ast.Attribute) and func.attr == "t":
                is_t_call = True
            elif isinstance(func, ast.Name) and func.id in t_aliases:
                is_t_call = True
            if not is_t_call:
                continue

            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                used_keys.add(first.value)
            elif isinstance(first, ast.JoinedStr):
                # Capture static prefix for dynamic keys, e.g. f"setup_name.{x}"
                prefix_parts: list[str] = []
                for part in first.values:
                    if isinstance(part, ast.Constant) and isinstance(part.value, str):
                        prefix_parts.append(part.value)
                    else:
                        break
                prefix = "".join(prefix_parts).strip()
                if prefix:
                    dynamic_prefixes.add(prefix)

    return used_keys, dynamic_prefixes


def main() -> int:
    locale_payloads = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in LOCALES.items()}
    locale_keys = {name: _flatten_keys(payload) for name, payload in locale_payloads.items()}

    used_keys, dynamic_prefixes = _extract_used_and_dynamic_prefixes()

    all_locale_names = sorted(locale_keys.keys())
    base_name = all_locale_names[0]
    base_keys = locale_keys[base_name]

    missing_by_locale: dict[str, list[str]] = {}
    mismatch_by_locale: dict[str, list[str]] = {}
    unused_by_locale: dict[str, list[str]] = {}

    for name in all_locale_names:
        keys = locale_keys[name]
        missing = sorted(k for k in used_keys if k not in keys and not any(k.startswith(prefix) for prefix in dynamic_prefixes))
        missing_by_locale[name] = missing

        if name != base_name:
            mismatch_by_locale[name] = sorted((base_keys - keys) | (keys - base_keys))

        unused = []
        for key in sorted(keys - used_keys):
            if any(key.startswith(prefix) for prefix in dynamic_prefixes):
                continue
            unused.append(key)
        unused_by_locale[name] = unused

    print("[localization-check]")
    print(f"- used keys: {len(used_keys)}")
    print(f"- dynamic prefixes: {', '.join(sorted(dynamic_prefixes)) if dynamic_prefixes else 'none'}")
    for name in all_locale_names:
        print(f"- locale {name}: keys={len(locale_keys[name])} missing={len(missing_by_locale[name])} unused={len(unused_by_locale[name])}")

    has_failures = False
    for name in all_locale_names:
        if missing_by_locale[name]:
            has_failures = True
            print(f"\n[missing in {name}]")
            for key in missing_by_locale[name]:
                print(f"  - {key}")

    for name in all_locale_names:
        if name == base_name:
            continue
        if mismatch_by_locale.get(name):
            has_failures = True
            print(f"\n[key mismatch vs {base_name} in {name}]")
            for key in mismatch_by_locale[name]:
                print(f"  - {key}")

    for name in all_locale_names:
        if unused_by_locale[name]:
            print(f"\n[unused in {name}]")
            for key in unused_by_locale[name]:
                print(f"  - {key}")

    if has_failures:
        print("\n[localization-check] FAILED")
        return 1
    print("\n[localization-check] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
