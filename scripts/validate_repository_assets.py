#!/usr/bin/env python3
"""Validate repository documentation coverage and detect orphan implementation assets."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "output"
ERRORS: list[str] = []


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def repository_text(paths: list[Path]) -> str:
    chunks: list[str] = []
    for path in paths:
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


components = (load_yaml(ROOT / "framework" / "components.yml") or {}).get("components", {})
workflows = load_yaml(ROOT / "framework" / "workflows.yml") or {}
day2 = (load_yaml(ROOT / "framework" / "day2-exercises.yml") or {}).get("exercises", {})

playbooks = sorted((ROOT / "playbooks").rglob("*.yml"))
framework_files = sorted((ROOT / "framework").glob("*.yml"))
documentation_files = sorted((ROOT / "docs").glob("*.md"))
workshop_files = sorted((ROOT / "workshop").rglob("*.adoc"))
implementation_text = repository_text(playbooks + framework_files)
documentation_text = repository_text(documentation_files + workshop_files + [ROOT / "README.md"])

catalog_roles = {
    value.get("role")
    for value in components.values()
    if isinstance(value, dict) and value.get("role")
}
workflow_roles = set()
for section in ("supported", "workflows"):
    data = workflows.get(section, {})
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, dict) and value.get("role"):
                workflow_roles.add(value["role"])
day2_roles = {
    value.get("role")
    for value in day2.values()
    if isinstance(value, dict) and value.get("role")
}

role_records = []
orphan_roles = []
orphan_templates = []
for role_dir in sorted(path for path in (ROOT / "roles").iterdir() if path.is_dir()):
    role = role_dir.name
    tasks = role_dir / "tasks" / "main.yml"
    role_tasks_text = repository_text(sorted((role_dir / "tasks").glob("*.yml"))) if (role_dir / "tasks").is_dir() else ""
    referenced = bool(
        role in catalog_roles
        or role in workflow_roles
        or role in day2_roles
        or re.search(rf"(?:role:|include_role:|import_role:)[^\n]*\b{re.escape(role)}\b", implementation_text)
        or re.search(rf"\b{re.escape(role)}\b", implementation_text)
    )
    documented = (role_dir / "README.md").is_file() or bool(re.search(rf"\b{re.escape(role)}\b", documentation_text))
    usable = tasks.is_file() and referenced
    if not usable:
        orphan_roles.append(role)

    templates = sorted((role_dir / "templates").rglob("*")) if (role_dir / "templates").is_dir() else []
    template_module_used = "ansible.builtin.template" in role_tasks_text or " template:" in role_tasks_text
    for template in [item for item in templates if item.is_file()]:
        explicitly_referenced = template.name in role_tasks_text or str(template.relative_to(role_dir / "templates")) in role_tasks_text
        if not usable or not (template_module_used or explicitly_referenced):
            orphan_templates.append(str(template.relative_to(ROOT)))

    role_records.append(
        {
            "role": role,
            "tasks": tasks.is_file(),
            "referenced": referenced,
            "documented": documented,
            "templates": [str(item.relative_to(ROOT)) for item in templates if item.is_file()],
        }
    )

# Shared top-level templates must be referenced by file name in active sources.
for template in sorted((ROOT / "templates").rglob("*")) if (ROOT / "templates").is_dir() else []:
    if template.is_file() and template.name not in implementation_text:
        orphan_templates.append(str(template.relative_to(ROOT)))

operator_guide = ROOT / "docs" / "operator-deployment-guide.md"
if not operator_guide.is_file():
    ERRORS.append("Missing docs/operator-deployment-guide.md")
    missing_operator_docs = sorted(components)
else:
    operator_text = operator_guide.read_text(encoding="utf-8")
    missing_operator_docs = [name for name in components if f"`{name}`" not in operator_text]
    if missing_operator_docs:
        ERRORS.append("Operator guide is missing components: " + ", ".join(missing_operator_docs))

nav = ROOT / "workshop" / "documentation" / "modules" / "ARCHITECTURE" / "nav.adoc"
template_page = ROOT / "workshop" / "documentation" / "modules" / "ARCHITECTURE" / "pages" / "12-template-system.adoc"
if not template_page.is_file():
    ERRORS.append("Missing workshop template-system module")
if not nav.is_file() or "12-template-system.adoc" not in nav.read_text(encoding="utf-8"):
    ERRORS.append("Workshop template-system module is not linked from nav.adoc")

if orphan_roles:
    ERRORS.append("Orphan roles: " + ", ".join(orphan_roles))
if orphan_templates:
    ERRORS.append("Orphan templates: " + ", ".join(orphan_templates))

report = {
    "status": "PASS" if not ERRORS else "FAIL",
    "components_documented": len(components) - len(missing_operator_docs),
    "components_total": len(components),
    "playbook_entrypoints": [str(path.relative_to(ROOT)) for path in playbooks],
    "roles": role_records,
    "orphan_roles": orphan_roles,
    "orphan_templates": orphan_templates,
    "errors": ERRORS,
}
REPORT_DIR.mkdir(parents=True, exist_ok=True)
(REPORT_DIR / "repository-assets.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

markdown = [
    "# Repository Asset Audit",
    "",
    f"Status: **{report['status']}**",
    "",
    f"Catalog components documented: {report['components_documented']}/{report['components_total']}",
    f"Playbook entry points: {len(playbooks)}",
    f"Roles: {len(role_records)}",
    f"Orphan roles: {len(orphan_roles)}",
    f"Orphan templates: {len(orphan_templates)}",
    "",
]
if ERRORS:
    markdown.extend(["## Findings", ""] + [f"- {item}" for item in ERRORS])
(REPORT_DIR / "repository-assets.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")

if ERRORS:
    print("Repository asset validation failed:")
    for item in ERRORS:
        print(f"- {item}")
    raise SystemExit(1)

print("Repository assets and documentation validation passed.")
