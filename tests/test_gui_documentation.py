import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "deployment-scenarios.md"
SCENARIO_PAGES = [
    "15-connected-playbook.adoc",
    "16-disconnected-playbook.adoc",
    "17-connected-gui.adoc",
    "18-disconnected-gui.adoc",
    "19-day2-playbook.adoc",
    "20-day2-gui.adoc",
]


def test_canonical_guide_covers_all_six_execution_paths() -> None:
    content = GUIDE.read_text(encoding="utf-8")
    headings = [
        "Scenario 1: connected installation with playbooks",
        "Scenario 2: disconnected installation with playbooks",
        "Scenario 3: connected installation with the GUI interface",
        "Scenario 4: disconnected installation with the GUI interface",
        "Scenario 5: Day-2 activities with playbooks",
        "Scenario 6: Day-2 activities with the GUI interface",
    ]
    for heading in headings:
        assert f"## {heading}" in content


def test_guide_references_every_authoritative_variable_group() -> None:
    content = GUIDE.read_text(encoding="utf-8")
    variable_root = ROOT / "inventories" / "sample" / "group_vars" / "all"
    for path in sorted(variable_root.glob("*.yml")):
        assert path.name in content
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert document, path
    assert "vault.yml" in content
    assert "hosts.yml" in content


def test_workshop_navigation_contains_six_scenario_pages() -> None:
    pages = ROOT / "workshop" / "documentation" / "modules" / "ROOT" / "pages"
    navigation_files = [
        ROOT / "workshop" / "documentation" / "modules" / "ROOT" / "nav.adoc",
        ROOT / "workshop" / "documentation" / "modules" / "ARCHITECTURE" / "nav.adoc",
    ]
    for page in SCENARIO_PAGES:
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


def test_gui_documentation_lists_every_allowlisted_action() -> None:
    actions = yaml.safe_load(
        (ROOT / "framework" / "gui-actions.yml").read_text(encoding="utf-8")
    )["actions"]
    content = (ROOT / "docs" / "gui-interface.md").read_text(encoding="utf-8")
    for action in actions.values():
        assert action["label"] in content
