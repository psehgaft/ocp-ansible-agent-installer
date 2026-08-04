from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path: Path):
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def test_legacy_site_wrapper_imports_canonical_playbook():
    data = _load_yaml(ROOT / "playbooks" / "site.yml")
    assert data == [{"import_playbook": "day0/install.yml"}]


def test_legacy_discovery_wrapper_imports_canonical_playbook():
    data = _load_yaml(ROOT / "playbooks" / "01-discover-bmc.yml")
    assert data == [{"import_playbook": "day0/discover-bmc.yml"}]


def test_obsolete_dell_backup_is_removed():
    assert not (
        ROOT / "roles" / "idrac_discovery_full" / "tasks" / "main-old.yml"
    ).exists()


def test_canonical_day0_playbooks_exist():
    assert (ROOT / "playbooks" / "day0" / "install.yml").is_file()
    assert (ROOT / "playbooks" / "day0" / "discover-bmc.yml").is_file()
