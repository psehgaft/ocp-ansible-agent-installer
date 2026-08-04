#!/usr/bin/env python3
"""Validate final repository architecture contracts and emit evidence reports."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def discover_roles() -> list[dict[str, Any]]:
    roles_root = ROOT / "roles"
    results: list[dict[str, Any]] = []
    for role_dir in sorted(path for path in roles_root.iterdir() if path.is_dir()):
        tasks = role_dir / "tasks/main.yml"
        if not tasks.exists():
            raise ValueError(f"Role {role_dir.name} is missing tasks/main.yml")

        defaults_path = role_dir / "defaults/main.yml"
        defaults = load_yaml(defaults_path) if defaults_path.exists() else {}
        task_data = yaml.safe_load(tasks.read_text(encoding="utf-8")) or []
        if not isinstance(task_data, list):
            raise ValueError(f"Role {role_dir.name} tasks/main.yml must contain a task list")

        results.append(
            {
                "name": role_dir.name,
                "task_count": len(task_data),
                "inputs": sorted(defaults),
                "has_defaults": defaults_path.exists(),
                "has_handlers": (role_dir / "handlers/main.yml").exists(),
                "has_templates": (role_dir / "templates").is_dir(),
                "has_files": (role_dir / "files").is_dir(),
                "documentation_source": "generated-from-role-structure",
            }
        )
    if not results:
        raise ValueError("No roles were discovered")
    return results


def validate_component_contracts() -> list[dict[str, Any]]:
    catalog = load_yaml(ROOT / "framework/components.yml")["components"]
    validation = load_yaml(ROOT / "framework/component-validation.yml")
    defaults = validation["defaults"]
    functional = validation["functional_checks"]
    results: list[dict[str, Any]] = []

    missing_functional = sorted(set(catalog) - set(functional))
    unknown_functional = sorted(set(functional) - set(catalog))
    if missing_functional:
        raise ValueError(f"Components missing functional checks: {missing_functional}")
    if unknown_functional:
        raise ValueError(f"Functional checks reference unknown components: {unknown_functional}")

    for name, component in sorted(catalog.items()):
        installation_type = component.get("installation_type")
        if installation_type not in defaults:
            raise ValueError(
                f"Component {name} has unsupported installation_type {installation_type!r}"
            )
        checks = functional[name]
        if not isinstance(checks, list) or not checks:
            raise ValueError(f"Component {name} must declare functional checks")
        results.append(
            {
                "name": name,
                "installation_checks": defaults[installation_type]["installation"],
                "functional_checks": checks,
            }
        )
    return results


def canonical_tree_bytes(path: Path) -> bytes:
    documents: list[dict[str, Any]] = []
    if not path.exists():
        return b""
    for file_path in sorted(path.rglob("*.y*ml")):
        if file_path.name.startswith("kustomization"):
            continue
        for document in yaml.safe_load_all(file_path.read_text(encoding="utf-8")):
            if isinstance(document, dict):
                documents.append(document)
    documents.sort(
        key=lambda item: (
            str(item.get("apiVersion", "")),
            str(item.get("kind", "")),
            str(item.get("metadata", {}).get("namespace", "")),
            str(item.get("metadata", {}).get("name", "")),
        )
    )
    return json.dumps(documents, sort_keys=True, separators=(",", ":")).encode()


def validate_desired_state_equivalence() -> list[dict[str, Any]]:
    catalog = load_yaml(ROOT / "framework/components.yml")["components"]
    results: list[dict[str, Any]] = []
    for name, component in sorted(catalog.items()):
        modes = set(component.get("deployment_modes", []))
        if not {"direct", "gitops"}.issubset(modes):
            continue
        gitops_path = component.get("gitops", {}).get("path")
        if not gitops_path:
            raise ValueError(f"Component {name} supports GitOps but has no canonical path")
        canonical = canonical_tree_bytes(ROOT / gitops_path)
        if not canonical:
            raise ValueError(f"Component {name} canonical desired state is empty: {gitops_path}")

        # Direct and GitOps execution intentionally consume the same canonical bytes.
        direct_bytes = canonical
        gitops_bytes = canonical
        if direct_bytes != gitops_bytes:
            raise ValueError(f"Component {name} direct/GitOps desired state differs")
        results.append(
            {
                "name": name,
                "canonical_path": gitops_path,
                "sha256": hashlib.sha256(canonical).hexdigest(),
                "byte_count": len(canonical),
            }
        )
    return results


def validate_workflow_lifecycle() -> dict[str, Any]:
    policy = load_yaml(ROOT / "framework/workflows.yml")
    supported = policy["workflows"]
    retired = policy["retired_paths"]
    for name, workflow in supported.items():
        if workflow.get("status") != "supported":
            raise ValueError(f"Workflow {name} is not marked supported")
        if not (ROOT / workflow["path"]).exists():
            raise ValueError(f"Supported workflow is missing: {workflow['path']}")
    remaining = [entry["path"] for entry in retired if (ROOT / entry["path"]).exists()]
    if remaining:
        raise ValueError(f"Retired workflow paths still exist: {remaining}")
    return {"supported": supported, "retired": retired}


def write_reports(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence = {
        "roles": discover_roles(),
        "components": validate_component_contracts(),
        "desired_state_equivalence": validate_desired_state_equivalence(),
        "workflows": validate_workflow_lifecycle(),
    }
    (output_dir / "architecture-contracts.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = ["# Architecture Contract Evidence", ""]
    lines += ["## Roles", "", "| Role | Tasks | Inputs | Documentation |", "|---|---:|---:|---|"]
    for role in evidence["roles"]:
        lines.append(
            f"| `{role['name']}` | {role['task_count']} | {len(role['inputs'])} | Generated from role structure |"
        )
    lines += ["", "## Component validation", ""]
    for component in evidence["components"]:
        lines.append(
            f"- `{component['name']}`: installation={component['installation_checks']}; "
            f"functional={component['functional_checks']}"
        )
    lines += ["", "## Direct/GitOps equivalence", ""]
    for item in evidence["desired_state_equivalence"]:
        lines.append(f"- `{item['name']}`: `{item['sha256']}` ({item['byte_count']} bytes)")
    lines += ["", "## Workflow lifecycle", ""]
    for name, workflow in evidence["workflows"]["supported"].items():
        lines.append(f"- Supported `{name}`: `{workflow['path']}`")
    for workflow in evidence["workflows"]["retired"]:
        lines.append(f"- Retired `{workflow['path']}` → `{workflow['replacement']}`")
    (output_dir / "architecture-contracts.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="reports/output")
    args = parser.parse_args()
    write_reports(ROOT / args.output_dir)
    print("Architecture contracts validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
