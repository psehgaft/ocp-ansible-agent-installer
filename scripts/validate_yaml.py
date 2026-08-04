#!/usr/bin/env python3
from pathlib import Path
import sys

import yaml

EXCLUDED_PARTS = {
    ".git",
    ".cache",
    ".collections",
    ".ansible",
    ".venv",
    "venv",
    "node_modules",
    "artifacts",
    "www",
    "reports",
    "__pycache__",
}

errors = []
for path in Path(".").rglob("*"):
    if path.suffix not in {".yml", ".yaml"}:
        continue
    if any(part in EXCLUDED_PARTS for part in path.parts):
        continue
    try:
        list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{path}: {exc}")

if errors:
    print("\n".join(errors), file=sys.stderr)
    raise SystemExit(1)

print("YAML parsing passed")
