#!/usr/bin/env python3
"""Validate every externally declared repository input contract."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "framework/input-contracts.yml"
ALLOWED_MODES = {"direct", "render", "gitops"}
ALLOWED_TYPES = (type(None), bool, int, float, str, list, dict)


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def fail(errors: list[str]) -> None:
    if errors:
        raise SystemExit("Input contract validation failed:\n- " + "\n- ".join(errors))


def is_secret_name(name: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(pattern.search(name) for pattern in patterns)


def secret_default_is_safe(value: Any) -> bool:
    if value in (None, ""):
        return True
    if isinstance(value, str):
        lowered = value.lower()
        return value.strip().startswith("{{") and any(
            marker in lowered for marker in ("vault", "lookup(", "env", "secret")
        )
    return False


def validate_role_defaults(errors: list[str], secret_patterns: list[re.Pattern[str]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for role_dir in sorted(path for path in (ROOT / "roles").iterdir() if path.is_dir()):
        defaults_path = role_dir / "defaults/main.yml"
        defaults = load_yaml(defaults_path) if defaults_path.exists() else {}
        if defaults is None:
            defaults = {}
        if not isinstance(defaults, dict):
            errors.append(f"{defaults_path.relative_to(ROOT)} must contain a mapping")
            continue

        for name, value in defaults.items():
            if not isinstance(name, str) or not name:
                errors.append(f"Role {role_dir.name} has an invalid default variable name: {name!r}")
                continue
            if not isinstance(value, ALLOWED_TYPES):
                errors.append(f"Role {role_dir.name} input {name} has unsupported type {type(value).__name__}")
            if is_secret_name(name, secret_patterns) and not secret_default_is_safe(value):
                errors.append(f"Role {role_dir.name} secret input {name} has a plaintext default")

        tasks_text = (role_dir / "tasks/main.yml").read_text(encoding="utf-8")
        has_runtime_validation = "ansible.builtin.assert" in tasks_text or "ansible.builtin.fail" in tasks_text
        evidence.append(
            {
                "role": role_dir.name,
                "declared_inputs": sorted(defaults),
                "runtime_assertions": has_runtime_validation,
                "contract": "defaults-type-and-secret-validation",
            }
        )
    return evidence


def walk_inventory_hosts(node: Any) -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    if not isinstance(node, dict):
        return found
    hosts = node.get("hosts", {})
    if isinstance(hosts, dict):
        for name, values in hosts.items():
            found.append((str(name), values if isinstance(values, dict) else {}))
    children = node.get("children", {})
    if isinstance(children, dict):
        for child in children.values():
            found.extend(walk_inventory_hosts(child))
    return found


def validate_inventories(errors: list[str], secret_patterns: list[re.Pattern[str]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for path in sorted((ROOT / "inventories").glob("*/hosts.yml")):
        data = load_yaml(path)
        if not isinstance(data, dict) or "all" not in data:
            errors.append(f"{path.relative_to(ROOT)} must contain an all inventory root")
            continue
        hosts = walk_inventory_hosts(data["all"])
        for hostname, values in hosts:
            if not hostname.strip():
                errors.append(f"{path.relative_to(ROOT)} contains an empty hostname")
            for name, value in values.items():
                if is_secret_name(str(name), secret_patterns) and not secret_default_is_safe(value):
                    errors.append(
                        f"{path.relative_to(ROOT)} host {hostname} contains plaintext secret input {name}"
                    )
        evidence.append({"inventory": str(path.relative_to(ROOT)), "host_count": len(hosts)})
    return evidence


def validate_components(errors: list[str], contract: dict[str, Any]) -> list[dict[str, Any]]:
    catalog = load_yaml(ROOT / "framework/components.yml") or {}
    components = catalog.get("components", {})
    required = contract["required_component_inputs"]
    version_pattern = re.compile(contract["validation"]["openshift_versions"]["pattern"])
    channel_pattern = re.compile(contract["validation"]["channels"]["pattern"])
    evidence: list[dict[str, Any]] = []

    for name, component in sorted(components.items()):
        missing = [key for key in required if key not in component]
        if missing:
            errors.append(f"Component {name} is missing inputs: {missing}")
            continue
        versions = component["supported_openshift"]
        if not isinstance(versions, list) or not versions:
            errors.append(f"Component {name} supported_openshift must be a non-empty list")
        else:
            for version in versions:
                if not version_pattern.fullmatch(str(version)):
                    errors.append(f"Component {name} has invalid OpenShift version {version!r}")
        modes = component["deployment_modes"]
        if not isinstance(modes, list) or not modes or not set(modes).issubset(ALLOWED_MODES):
            errors.append(f"Component {name} has invalid deployment modes: {modes!r}")
        if component["installation_type"] == "olm":
            olm = component.get("olm", {})
            for key in ("package", "channel", "source", "source_namespace"):
                if not str(olm.get(key, "")).strip():
                    errors.append(f"Component {name} OLM input {key} is required")
            if olm.get("channel") and not channel_pattern.fullmatch(str(olm["channel"])):
                errors.append(f"Component {name} has invalid OLM channel {olm['channel']!r}")
        evidence.append({"component": name, "modes": modes, "versions": versions})
    return evidence


def validate_profiles(errors: list[str]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    profiles_dir = ROOT / "profiles"
    if not profiles_dir.exists():
        return evidence
    for path in sorted(profiles_dir.glob("*.yml")):
        profile = load_yaml(path)
        if not isinstance(profile, dict) or not profile:
            errors.append(f"Profile {path.name} must contain a non-empty mapping")
            continue
        evidence.append({"profile": path.stem, "keys": sorted(profile)})
    return evidence


def validate_day2(errors: list[str], contract: dict[str, Any]) -> list[dict[str, Any]]:
    catalog = load_yaml(ROOT / "framework/day2-exercises.yml") or {}
    exercises = catalog.get("exercises", {})
    required = contract["required_day2_inputs"]
    evidence: list[dict[str, Any]] = []
    for name, exercise in sorted(exercises.items()):
        missing = [key for key in required if not exercise.get(key)]
        if missing:
            errors.append(f"Day-2 exercise {name} is missing inputs: {missing}")
            continue
        playbook_path = ROOT / exercise["playbook"]
        role_path = ROOT / "roles" / exercise["role"] / "tasks/main.yml"
        if not playbook_path.is_file():
            errors.append(f"Day-2 exercise {name} playbook does not exist: {exercise['playbook']}")
            continue
        if not role_path.is_file():
            errors.append(f"Day-2 exercise {name} role does not exist: {exercise['role']}")
            continue
        playbook_text = playbook_path.read_text(encoding="utf-8")
        if exercise["resources_variable"] not in playbook_text:
            errors.append(
                f"Day-2 exercise {name} does not bind resource input {exercise['resources_variable']}"
            )
        role_text = role_path.read_text(encoding="utf-8")
        for mode in ("direct", "gitops"):
            if mode not in role_text:
                errors.append(f"Day-2 role {exercise['role']} does not validate mode {mode}")
        evidence.append({"exercise": name, **exercise})
    return evidence


def main() -> int:
    contract = load_yaml(CONTRACT)
    if not isinstance(contract, dict) or contract.get("contract_version") != 1:
        raise SystemExit("framework/input-contracts.yml has an unsupported contract version")

    errors: list[str] = []
    secret_patterns = [
        re.compile(pattern) for pattern in contract["validation"]["secret_names"]["patterns"]
    ]
    evidence = {
        "roles": validate_role_defaults(errors, secret_patterns),
        "inventories": validate_inventories(errors, secret_patterns),
        "components": validate_components(errors, contract),
        "profiles": validate_profiles(errors),
        "day2": validate_day2(errors, contract),
    }
    fail(errors)

    output = ROOT / "reports/output"
    output.mkdir(parents=True, exist_ok=True)
    (output / "input-contracts.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("All externally declared inputs satisfy the repository contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
