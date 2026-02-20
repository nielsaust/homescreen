#!/usr/bin/env python3
"""Fail when PEP604 union annotations are used without postponed evaluation.

Python 3.9 can parse ``a | b`` in annotations but evaluates them at import time
unless ``from __future__ import annotations`` is present, causing runtime errors.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", ".venv", "__pycache__"}


def _has_future_annotations(tree: ast.AST) -> bool:
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "__future__":
            continue
        if any(alias.name == "annotations" for alias in node.names):
            return True
    return False


def _contains_union_op(annotation: ast.AST | None) -> bool:
    if annotation is None:
        return False
    for node in ast.walk(annotation):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return True
    return False


def _iter_project_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*.py"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        files.append(path)
    return files


def main() -> int:
    violations: list[str] = []

    for path in _iter_project_files():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        if _has_future_annotations(tree):
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [
                    *node.args.posonlyargs,
                    *node.args.args,
                    *node.args.kwonlyargs,
                ]
                if node.args.vararg:
                    args.append(node.args.vararg)
                if node.args.kwarg:
                    args.append(node.args.kwarg)
                for arg in args:
                    if _contains_union_op(arg.annotation):
                        violations.append(f"{path.relative_to(ROOT)}:{arg.lineno} argument annotation uses '|'")
                if _contains_union_op(node.returns):
                    violations.append(f"{path.relative_to(ROOT)}:{node.lineno} return annotation uses '|'")
            elif isinstance(node, ast.AnnAssign):
                if _contains_union_op(node.annotation):
                    violations.append(f"{path.relative_to(ROOT)}:{node.lineno} variable annotation uses '|'")

    if violations:
        print("[py39-guard] FAILED")
        print("Add `from __future__ import annotations` or replace `|` unions with typing.Optional/Union.")
        for item in sorted(violations):
            print(f"- {item}")
        return 1

    print("[py39-guard] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
