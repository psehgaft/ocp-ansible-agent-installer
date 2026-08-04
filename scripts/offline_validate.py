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
EXCLUDED_PARTS = {
    ".git", ".collections", ".ansible", ".venv", "venv", "env",
    "node_modules", "artifacts", "www", ".cache", "__pycache__", "reports",
}


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


def is_repository_source(path: Path) -> bool:
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        relative = path
    return not any(part in EXCLUDED_PARTS for part in relative.parts)


def load_yaml(path: Path):
    try:
        return yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except Exception as exc:  # noqa: BLE001
        error(f"YAML parse failed: {path.relative_to(ROOT)}: {exc}")
        return None


for path in sorted(ROOT.rglob("*.yml")) + sorted(ROOT.rglob("*.yaml")):
    if is_repository_source(path):
        load_yaml(path)

for path in sorted(ROOT.rglob("*.j2")):
    if not is_repository_source(path):
        continue
    try:
        jinja2.Environment().parse(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        error(f"Jinja parse failed: {path.relative_to(ROOT)}: {exc}")

for path in sorted((ROOT / "filter_plugins").glob("*.py")) + sorted((ROOT / "tests").glob("*.py")):
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
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
    "playbooks/00-preflight.yml",
    "playbooks/day0/discover-bmc.yml",
    "playbooks/day0/install.yml",
    "playbooks/03-test-virtual-media.yml",
    "playbooks/90-eject-media.yml",
    "playbooks/configure-bastion.yml",
    "framework/components.yml",
    "framework/component-validation.yml",
    "framework/day2-exercises.yml",
    "framework/workflows.yml",
]
for relative in required_files:
    if not (ROOT / relative).is_file():
        error(f"Required file missing: {relative}")

retired_files = [
    "playbooks/site.yml",
    "playbooks/01-discover-bmc.yml",
    "playbooks/test-preflight.yml",
]
for relative in retired_files:
    if (ROOT / relative).exists():
        error(f"Retired workflow path was reintroduced: {relative}")

role_pattern = re.compile(r"^\s*-\s+role:\s+([A-Za-z0-9_.-]+)\s*$", re.MULTILINE)
for playbook in sorted((ROOT / "playbooks").rglob("*.yml")):
    for role in role_pattern.findall(playbook.read_text(encoding="utf-8")):
        tasks = ROOT / "roles" / role / "tasks" / "main.yml"
        if not tasks.is_file():
            error(f"Playbook {playbook.relative_to(ROOT)} references missing role tasks: {role}")

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
if "kubernetes.core" not in collection_names:
    error("requirements.yml must include kubernetes.core")

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
