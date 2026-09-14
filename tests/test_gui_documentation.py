import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "deployment-scenarios.md"
PROCEDURE_PAGES = [
    "15-connected-playbook.adoc",
    "16-disconnected-playbook.adoc",
    "17-connected-gui.adoc",
    "18-disconnected-gui.adoc",
    "19-day2-playbook.adoc",
    "20-day2-gui.adoc",
    "21-gitops-playbook.adoc",
    "22-gitops-gui.adoc",
    "23-operators-gitops.adoc",
]


def test_canonical_guide_covers_three_part_operating_model() -> None:
    content = GUIDE.read_text(encoding="utf-8")
    headings = [
        "1. Deployment with playbooks",
        "2. Deployment with the GUI interface",
        "3. Operators",
        "1.1 Install connected OpenShift",
        "1.2 Install disconnected OpenShift",
        "1.3 Perform Day-2 activities with playbooks",
        "1.4 Initialize GitOps with playbooks",
        "2.1 Install connected OpenShift",
        "2.2 Install disconnected OpenShift",
        "2.3 Perform Day-2 activities with the GUI interface",
        "2.4 Initialize GitOps with the GUI interface",
        "3.1 Deploy and configure operators with GitOps",
    ]
    for heading in headings:
        assert heading in content


def test_guide_references_every_authoritative_variable_group() -> None:
    content = GUIDE.read_text(encoding="utf-8")
    variable_root = ROOT / "inventories" / "sample" / "group_vars" / "all"
    for path in sorted(variable_root.glob("*.yml")):
        assert path.name in content
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert document, path
    assert "vault.yml" in content
    assert "hosts.yml" in content


def test_workshop_navigation_contains_every_procedure_page() -> None:
    pages = ROOT / "workshop" / "documentation" / "modules" / "ROOT" / "pages"
    navigation_files = [
        ROOT / "workshop" / "documentation" / "modules" / "ROOT" / "nav.adoc",
        ROOT / "workshop" / "documentation" / "modules" / "ARCHITECTURE" / "nav.adoc",
    ]
    for page in PROCEDURE_PAGES:
        assert (pages / page).is_file()
        for navigation in navigation_files:
            assert page in navigation.read_text(encoding="utf-8")


def test_documentation_uses_gui_interface_name_not_temporary_task_number() -> None:
    candidates = [ROOT / "README.md", ROOT / "WORKSHOP.md", ROOT / "CHANGELOG.md"]
    candidates.extend((ROOT / "docs").rglob("*.md"))
    candidates.extend((ROOT / "workshop").rglob("*.adoc"))
    pattern = re.compile(r"\btask[ -]?3\b", re.IGNORECASE)
    offending = [
        str(path.relative_to(ROOT))
        for path in candidates
        if pattern.search(path.read_text(encoding="utf-8"))
    ]
    assert not offending, f"Temporary GUI task name remains in: {offending}"


def test_retired_unreferenced_files_are_absent() -> None:
    retired = (
        "MANIFEST.sha256",
        "docs/gui-interface-roadmap.md",
        "hosts_lexample.yml",
        "playbooks/assited-test-network.yml",
        "playbooks/02-install-operators.yml",
        "playbooks/03-configure-rhoso.yml",
        "playbooks/04-configure-rhoso-network.yml",
        "roles/assisted_cluster/tasks/main-old.yml",
        "roles/assisted_hosts/tasks/main-old.yml",
        "roles/assisted_hosts/tasks/main-pooll-host.yml",
        "roles/rhoso_nmstate_nncp/tasks/main-old.yml",
    )
    unexpected = [path for path in retired if (ROOT / path).exists()]
    assert not unexpected, f"Retired files were restored: {unexpected}"

    retired_roles = (
        "openstack_operator",
        "rhoso_metallb_vips",
        "rhoso_multus_nad",
        "rhoso_nmstate_nncp",
        "rhoso_openstack_bootstrap",
        "rhoso_ovn_global_forwarding",
        "rhoso_preflight",
    )
    restored_roles = [
        name
        for name in retired_roles
        if any(path.is_file() for path in (ROOT / "roles" / name).rglob("*"))
    ]
    assert not restored_roles, f"Retired roles were restored: {restored_roles}"

    assisted_templates = ROOT / "roles" / "assisted_cluster" / "templates"
    assert {path.name for path in assisted_templates.iterdir()} == {
        "nmstate.yaml.j2",
        "static-network-config.json.j2",
    }


def test_gui_documentation_lists_every_allowlisted_action() -> None:
    actions = yaml.safe_load(
        (ROOT / "framework" / "gui-actions.yml").read_text(encoding="utf-8")
    )["actions"]
    content = (ROOT / "docs" / "gui-interface.md").read_text(encoding="utf-8")
    for action in actions.values():
        assert action["label"] in content
