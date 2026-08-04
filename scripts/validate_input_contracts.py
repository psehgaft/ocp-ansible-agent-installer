#!/usr/bin/env python3
"""Validate every externally declared repository input contract."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_MODES = {"direct", "render", "gitops"}
ALLOWED_TYPES = (type(None), bool, int, float, str, list, dict)


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def secret_default_is_safe(value: Any) -> bool:
    if value in (None, ""):
        return True
    if isinstance(value, str):
        lowered = value.lower()
        return value.strip().startswith("{{") and any(
            marker in lowered for marker in ("vault", "lookup(", "env", "secret")
        )
    return False


def walk_hosts(node: Any) -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    if not isinstance(node, dict):
        return found
    for name, values in (node.get("hosts") or {}).items():
        found.append((str(name), values if isinstance(values, dict) else {}))
    for child in (node.get("children") or {}).values():
        found.extend(walk_hosts(child))
    return found


def main() -> int:
    contract = load_yaml(ROOT / "framework/input-contracts.yml")
    if not isinstance(contract, dict) or contract.get("contract_version") != 1:
        raise SystemExit("Unsupported input contract version")

    errors: list[str] = []
    secret_patterns = [
        re.compile(pattern)
        for pattern in contract["validation"]["secret_names"]["patterns"]
    ]
    version_pattern = re.compile(contract["validation"]["openshift_versions"]["pattern"])
    channel_pattern = re.compile(contract["validation"]["channels"]["pattern"])
    evidence: dict[str, list[dict[str, Any]]] = {
        "roles": [],
        "inventories": [],
        "components": [],
        "profiles": [],
        "day2": [],
    }

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
                errors.append(f"Role {role_dir.name} has invalid input name {name!r}")
                continue
            if not isinstance(value, ALLOWED_TYPES):
                errors.append(f"Role {role_dir.name} input {name} has unsupported type")
            if any(pattern.search(name) for pattern in secret_patterns) and not secret_default_is_safe(value):
                errors.append(f"Role {role_dir.name} secret input {name} has a plaintext default")
        evidence["roles"].append(
            {"role": role_dir.name, "declared_inputs": sorted(defaults)}
        )

    for path in sorted((ROOT / "inventories").glob("*/hosts.yml")):
        data = load_yaml(path)
        if not isinstance(data, dict) or "all" not in data:
            errors.append(f"{path.relative_to(ROOT)} must contain an all inventory root")
            continue
        hosts = walk_hosts(data["all"])
        for hostname, values in hosts:
            if not hostname.strip():
                errors.append(f"{path.relative_to(ROOT)} contains an empty hostname")
            for name, value in values.items():
                if any(pattern.search(str(name)) for pattern in secret_patterns) and not secret_default_is_safe(value):
                    errors.append(
                        f"{path.relative_to(ROOT)} host {hostname} contains plaintext secret input {name}"
                    )
        evidence["inventories"].append(
            {"inventory": str(path.relative_to(ROOT)), "host_count": len(hosts)}
        )

    catalog = load_yaml(ROOT / "framework/components.yml") or {}
    required_component = contract["required_component_inputs"]
    for name, component in sorted((catalog.get("components") or {}).items()):
        missing = [key for key in required_component if key not in component]
        if missing:
            errors.append(f"Component {name} is missing inputs: {missing}")
            continue
        versions = component["supported_openshift"]
        if not isinstance(versions, list) or not versions:
            errors.append(f"Component {name} supported_openshift must be non-empty")
        else:
            for version in versions:
                if not version_pattern.fullmatch(str(version)):
                    errors.append(f"Component {name} has invalid OpenShift version {version!r}")
        modes = component["deployment_modes"]
        if not isinstance(modes, list) or not modes or not set(modes).issubset(ALLOWED_MODES):
            errors.append(f"Component {name} has invalid deployment modes {modes!r}")
        if component["installation_type"] == "olm":
            olm = component.get("olm", {})
            for key in ("package", "channel", "source", "source_namespace"):
                if not str(olm.get(key, "")).strip():
                    errors.append(f"Component {name} OLM input {key} is required")
            if olm.get("channel") and not channel_pattern.fullmatch(str(olm["channel"])):
                errors.append(f"Component {name} has invalid channel {olm['channel']!r}")
        evidence["components"].append(
            {"component": name, "versions": versions, "modes": modes}
        )

    profiles_dir = ROOT / "profiles"
    if profiles_dir.exists():
        for path in sorted(profiles_dir.glob("*.yml")):
            profile = load_yaml(path)
            if not isinstance(profile, dict) or not profile:
                errors.append(f"Profile {path.name} must contain a non-empty mapping")
            else:
                evidence["profiles"].append(
                    {"profile": path.stem, "keys": sorted(profile)}
                )

    day2 = load_yaml(ROOT / "framework/day2-exercises.yml") or {}
    required_day2 = contract["required_day2_inputs"]
    for name, exercise in sorted((day2.get("exercises") or {}).items()):
        missing = [key for key in required_day2 if not exercise.get(key)]
        if missing:
            errors.append(f"Day-2 exercise {name} is missing inputs: {missing}")
            continue
        playbook = ROOT / exercise["playbook"]
        role_tasks = ROOT / "roles" / exercise["role"] / "tasks/main.yml"
        if not playbook.is_file():
            errors.append(f"Day-2 exercise {name} playbook is missing")
            continue
        if not role_tasks.is_file():
            errors.append(f"Day-2 exercise {name} role is missing")
            continue
        if exercise["resources_variable"] not in playbook.read_text(encoding="utf-8"):
            errors.append(f"Day-2 exercise {name} does not bind {exercise['resources_variable']}")
        role_text = role_tasks.read_text(encoding="utf-8")
        for mode in ("direct", "gitops"):
            if mode not in role_text:
                errors.append(f"Day-2 role {exercise['role']} does not support {mode}")
        evidence["day2"].append({"exercise": name, **exercise})

    if errors:
        raise SystemExit("Input contract validation failed:\n- " + "\n- ".join(errors))

    output = ROOT / "reports/output"
    output.mkdir(parents=True, exist_ok=True)
    (output / "input-contracts.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("All externally declared inputs satisfy the repository contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
