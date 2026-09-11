#!/usr/bin/env python3
"""Schema discovery, validation, and safe inventory/Vault generation for the GUI."""

from __future__ import annotations

import argparse
import copy
import ipaddress
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def value_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def humanize(name: str) -> str:
    return name.replace("_", " ").strip().title()


def inventory_hosts(document: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    baremetal = document.get("all", {}).get("children", {}).get("baremetal", {})
    for group in baremetal.get("children", {}).values():
        for name, variables in group.get("hosts", {}).items():
            item = {"name": name}
            item.update(copy.deepcopy(variables or {}))
            item.pop("bmc_username", None)
            item.pop("bmc_password", None)
            result.append(item)
    return result


def discover(root: Path) -> dict[str, Any]:
    sample = root / "inventories" / "sample"
    metadata = load_yaml(root / "framework" / "gui-variable-metadata.yml")
    catalog = load_yaml(root / "framework" / "day2-operator-catalog.yml")
    action_document = load_yaml(root / "framework" / "gui-actions.yml")
    variables: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []

    for path in sorted((sample / "group_vars" / "all").glob("*.yml")):
        group_name = path.stem
        group_metadata = metadata.get("groups", {}).get(group_name, {})
        groups.append({
            "id": group_name,
            "label": group_metadata.get("label", humanize(group_name)),
            "order": group_metadata.get("order", 999),
            "icon": group_metadata.get("icon", "settings"),
        })
        for name, default in load_yaml(path).items():
            hints = copy.deepcopy(metadata.get("variables", {}).get(name, {}))
            variables.append({
                "name": name,
                "group": group_name,
                "label": hints.pop("label", humanize(name)),
                "default": default,
                "type": value_type(default),
                "source": str(path.relative_to(root)),
                **hints,
            })

    secret_group = metadata.get("groups", {}).get("secrets", {})
    groups.append({
        "id": "secrets",
        "label": secret_group.get("label", "Secrets"),
        "order": secret_group.get("order", 999),
        "icon": secret_group.get("icon", "lock"),
    })
    vault_example = load_yaml(sample / "group_vars" / "vault.yml.example")
    secret_names = set(vault_example) | set(metadata.get("secrets", {}))
    for name in sorted(secret_names):
        if name == "vault_bmc_credentials":
            continue
        hints = copy.deepcopy(metadata.get("secrets", {}).get(name, {}))
        variables.append({
            "name": name,
            "group": "secrets",
            "label": hints.pop("label", humanize(name)),
            "default": "",
            "type": "string",
            "sensitive": True,
            "source": "inventories/sample/group_vars/vault.yml.example",
            **hints,
        })

    operators = []
    for name, item in catalog.get("operators", {}).items():
        operators.append({"id": name, **item})

    return {
        "version": 1,
        "groups": sorted(groups, key=lambda item: (item["order"], item["id"])),
        "variables": variables,
        "host_fields": [
            {"name": name, "label": hints.get("label", humanize(name)), **hints}
            for name, hints in metadata.get("host_fields", {}).items()
        ],
        "host_defaults": inventory_hosts(load_yaml(sample / "hosts.yml")),
        "profiles": catalog.get("profiles", {}),
        "operators": operators,
        "platform_features": catalog.get("platform_features", {}),
        "actions": action_document.get("actions", {}),
    }


def is_blank(value: Any) -> bool:
    return value is None or value == "" or (isinstance(value, str) and "CHANGE_ME" in value)


def visible(hints: dict[str, Any], values: dict[str, Any]) -> bool:
    condition = hints.get("visible_when", {})
    return all(
        values.get(name) in expected if isinstance(expected, list) else values.get(name) == expected
        for name, expected in condition.items()
    )


def validate_payload(root: Path, payload: dict[str, Any]) -> list[dict[str, str]]:
    schema = discover(root)
    values = {
        field["name"]: copy.deepcopy(field.get("default"))
        for field in schema["variables"]
        if field["group"] != "secrets"
    }
    values.update(payload.get("values", {}))
    secrets = payload.get("secrets", {})
    hosts = payload.get("hosts", [])
    errors: list[dict[str, str]] = []

    for field in schema["variables"]:
        source = secrets if field["group"] == "secrets" else values
        value = source.get(field["name"], field.get("default"))
        if field.get("required") and visible(field, values) and is_blank(value):
            errors.append({"field": field["name"], "message": "This value is required"})
        pattern = field.get("pattern")
        if pattern and value and not re.fullmatch(pattern, str(value)):
            errors.append({"field": field["name"], "message": "Value does not match the required format"})
        minimum = field.get("minimum")
        if minimum is not None and isinstance(value, (int, float)) and value < minimum:
            errors.append({"field": field["name"], "message": f"Value must be at least {minimum}"})

    mode = values.get("node_network_config_mode", "static")
    host_names: set[str] = set()
    for index, host in enumerate(hosts):
        prefix = f"hosts[{index}]"
        name = host.get("name", "")
        if not name or name in host_names:
            errors.append({"field": f"{prefix}.name", "message": "Host name must be present and unique"})
        host_names.add(name)
        for required in ("node_hostname", "node_role", "bmc_type", "bmc_endpoint", "bmc_username", "bmc_password"):
            if is_blank(host.get(required)):
                errors.append({"field": f"{prefix}.{required}", "message": "This value is required"})
        endpoint = str(host.get("bmc_endpoint", ""))
        if endpoint and not endpoint.startswith("https://"):
            errors.append({"field": f"{prefix}.bmc_endpoint", "message": "BMC endpoint must use HTTPS"})
        if mode == "static" and is_blank(host.get("node_ipv4_address")):
            errors.append({"field": f"{prefix}.node_ipv4_address", "message": "Static mode requires an address"})
        if host.get("node_ipv4_address"):
            try:
                ipaddress.ip_address(host["node_ipv4_address"])
            except ValueError:
                errors.append({"field": f"{prefix}.node_ipv4_address", "message": "Invalid IP address"})

    expected_masters = values.get("control_plane_count")
    expected_workers = values.get("compute_count")
    masters = sum(host.get("node_role") == "master" for host in hosts)
    workers = sum(host.get("node_role") == "worker" for host in hosts)
    if isinstance(expected_masters, int) and masters != expected_masters:
        errors.append({"field": "control_plane_count", "message": f"Expected {expected_masters} master host definitions, found {masters}"})
    if isinstance(expected_workers, int) and workers != expected_workers:
        errors.append({"field": "compute_count", "message": f"Expected {expected_workers} worker host definitions, found {workers}"})

    selected = payload.get("operators", values.get("day2_gitops_enabled_operators", []))
    known = {item["id"] for item in schema["operators"]}
    for operator in selected:
        if operator not in known:
            errors.append({"field": "operators", "message": f"Unknown operator: {operator}"})
    return errors


def safe_profile(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", value):
        raise ValueError("Profile name must contain only letters, numbers, underscore, or hyphen")
    return value


def render_inventory(hosts: list[dict[str, Any]]) -> dict[str, Any]:
    groups = {"control_plane": {"hosts": {}}, "workers": {"hosts": {}}}
    for host in hosts:
        name = host["name"]
        variables = {key: copy.deepcopy(value) for key, value in host.items() if key not in {"name", "bmc_username", "bmc_password"}}
        variables["bmc_username"] = "{{ vault_bmc_credentials[inventory_hostname].username }}"
        variables["bmc_password"] = "{{ vault_bmc_credentials[inventory_hostname].password }}"
        target = "control_plane" if variables.get("node_role") == "master" else "workers"
        groups[target]["hosts"][name] = variables
    return {"all": {"children": {"baremetal": {"children": groups}}}}


def write_private_yaml(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    path.chmod(0o600)


def write_private_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def save(root: Path, data_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    errors = validate_payload(root, payload)
    if errors:
        return {"valid": False, "errors": errors}
    profile = safe_profile(str(payload.get("profile", "default")))
    destination = data_root / "inventories" / profile
    destination.mkdir(parents=True, exist_ok=True)
    destination.chmod(0o700)
    values = {}
    for field in discover(root)["variables"]:
        if field["group"] != "secrets":
            values[field["name"]] = copy.deepcopy(field.get("default"))
    values.update(copy.deepcopy(payload.get("values", {})))
    values["artifacts_dir"] = str(data_root / "artifacts" / profile)
    values["day2_gitops_enabled_operators"] = copy.deepcopy(payload.get("operators", values.get("day2_gitops_enabled_operators", [])))
    values["pull_secret"] = "{{ vault_pull_secret }}"
    values["ssh_public_key"] = "{{ vault_ssh_public_key }}"

    write_private_yaml(destination / "hosts.yml", render_inventory(payload.get("hosts", [])))
    write_private_yaml(destination / "group_vars" / "all" / "gui-values.yml", values)

    secrets = copy.deepcopy(payload.get("secrets", {}))
    secrets["vault_bmc_credentials"] = {
        host["name"]: {"username": host["bmc_username"], "password": host["bmc_password"]}
        for host in payload.get("hosts", [])
    }
    vault_path = destination / "group_vars" / "vault.yml"
    write_private_yaml(vault_path, secrets)

    password = str(payload.get("vault_password", ""))
    password_file_setting = os.environ.get("INSTALLER_UI_VAULT_PASSWORD_FILE", "")
    managed_password_path = data_root / "secrets" / f"{profile}.vault-password"
    if password_file_setting:
        password_path = Path(password_file_setting)
        if not password_path.is_file():
            raise ValueError("INSTALLER_UI_VAULT_PASSWORD_FILE does not exist")
    elif password:
        managed_password_path.parent.mkdir(parents=True, exist_ok=True)
        managed_password_path.write_text(password + "\n", encoding="utf-8")
        managed_password_path.chmod(0o600)
        password_path = managed_password_path
    else:
        vault_path.unlink(missing_ok=True)
        return {"valid": False, "errors": [{"field": "vault_password", "message": "A Vault password or mounted password file is required"}]}

    result = subprocess.run(
        ["ansible-vault", "encrypt", "--vault-password-file", str(password_path), str(vault_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        vault_path.unlink(missing_ok=True)
        if not password_file_setting:
            managed_password_path.unlink(missing_ok=True)
        raise RuntimeError(result.stderr.strip() or "ansible-vault encryption failed")

    state = {
        "profile": profile,
        "inventory": str(destination / "hosts.yml"),
        "vault_password_file": str(password_path),
    }
    write_private_json(destination / ".gui-state.json", state)
    return {"valid": True, "profile": profile, "inventory": state["inventory"]}


def read_payload() -> dict[str, Any]:
    value = json.load(sys.stdin)
    if not isinstance(value, dict):
        raise ValueError("Request body must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("schema", "validate", "save"))
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--data-root", type=Path, default=Path("artifacts/gui"))
    args = parser.parse_args()
    try:
        if args.command == "schema":
            result = discover(args.root.resolve())
        elif args.command == "validate":
            errors = validate_payload(args.root.resolve(), read_payload())
            result = {"valid": not errors, "errors": errors}
        else:
            result = save(args.root.resolve(), args.data_root.resolve(), read_payload())
        print(json.dumps(result, indent=2))
        return 0 if result.get("valid", True) else 2
    except (OSError, ValueError, RuntimeError, yaml.YAMLError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
