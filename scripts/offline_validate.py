#!/usr/bin/env python3
"""Offline repository validation without requiring Ansible to be installed."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import jinja2
import yaml
from yaml.constructor import ConstructorError

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def error(message: str) -> None:
    ERRORS.append(message)


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key: {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_yaml(path: Path):
    try:
        return yaml.load(path.read_text(), Loader=UniqueKeyLoader)
    except Exception as exc:  # noqa: BLE001
        error(f"YAML parse failed: {path.relative_to(ROOT)}: {exc}")
        return None


for path in sorted(ROOT.rglob("*.yml")) + sorted(ROOT.rglob("*.yaml")):
    if "artifacts" not in path.parts:
        load_yaml(path)

for path in sorted(ROOT.rglob("*.j2")):
    try:
        jinja2.Environment().parse(path.read_text())
    except Exception as exc:  # noqa: BLE001
        error(f"Jinja parse failed: {path.relative_to(ROOT)}: {exc}")

for path in sorted((ROOT / "filter_plugins").glob("*.py")) + sorted((ROOT / "tests").glob("*.py")):
    try:
        ast.parse(path.read_text(), filename=str(path))
    except SyntaxError as exc:
        error(f"Python parse failed: {path.relative_to(ROOT)}: {exc}")

required_files = [
    "README.md",
    "WORKSHOP.md",
    "VALIDATION.md",
    "requirements.txt",
    "requirements.yml",
    "inventories/sample/hosts.yml",
    "inventories/sample/group_vars/all.yml",
    "inventories/sample/group_vars/vault.yml.example",
    "docs/architecture.md",
    "docs/variable-reference.md",
    "docs/migration-from-idrac.md",
    "docs/troubleshooting.md",
    "docs/references.md",
    "playbooks/site.yml",
    "playbooks/01-discover-bmc.yml",
    "playbooks/03-test-virtual-media.yml",
]
for relative in required_files:
    if not (ROOT / relative).is_file():
        error(f"Required file missing: {relative}")

role_pattern = re.compile(r"^\s*-\s+role:\s+([A-Za-z0-9_.-]+)\s*$", re.MULTILINE)
for playbook in sorted((ROOT / "playbooks").glob("*.yml")):
    for role in role_pattern.findall(playbook.read_text()):
        tasks = ROOT / "roles" / role / "tasks" / "main.yml"
        if not tasks.is_file():
            error(f"Playbook {playbook.name} references missing role tasks: {role}")

for tasks_file in sorted((ROOT / "roles").glob("*/tasks/main.yml")):
    data = load_yaml(tasks_file)
    if data is not None and not isinstance(data, list):
        error(f"Role task file must contain a YAML list: {tasks_file.relative_to(ROOT)}")

implementation_files = list((ROOT / "playbooks").rglob("*.yml")) + list((ROOT / "roles").rglob("*.yml"))
implementation_text = "\n".join(path.read_text(errors="ignore") for path in implementation_files)
for forbidden in ["dellemc.openmanage.idrac_", "role: idrac_discovery", "role: idrac_boot_discovery_iso"]:
    if forbidden in implementation_text:
        error(f"Dell-only implementation reference remains: {forbidden}")

requirements = load_yaml(ROOT / "requirements.yml") or {}
collection_names = {item.get("name") for item in requirements.get("collections", []) if isinstance(item, dict)}
if "community.general" not in collection_names:
    error("requirements.yml must include community.general")

inventory = load_yaml(ROOT / "inventories/sample/hosts.yml") or {}
try:
    baremetal = inventory["all"]["children"]["baremetal"]["children"]
    host_maps = [group.get("hosts", {}) for group in baremetal.values()]
    hosts = {name: values for mapping in host_maps for name, values in mapping.items()}
    declared_types = {values.get("bmc_type") for values in hosts.values()}
    if not {"ilo", "idrac"}.issubset(declared_types):
        error("Sample inventory must contain both ilo and idrac examples")
except Exception as exc:  # noqa: BLE001
    error(f"Sample inventory structure is invalid: {exc}")

if ERRORS:
    print("Offline validation failed:", file=sys.stderr)
    for item in ERRORS:
        print(f"- {item}", file=sys.stderr)
    raise SystemExit(1)

print("Offline repository validation passed.")
