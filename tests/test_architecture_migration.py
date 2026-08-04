from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_retired_site_wrapper_remains_absent():
    assert not (ROOT / "playbooks" / "site.yml").exists()
    assert (ROOT / "playbooks" / "day0" / "install.yml").is_file()


def test_retired_discovery_wrapper_remains_absent():
    assert not (ROOT / "playbooks" / "01-discover-bmc.yml").exists()
    assert (ROOT / "playbooks" / "day0" / "discover-bmc.yml").is_file()


def test_obsolete_dell_backup_is_removed():
    assert not (
        ROOT / "roles" / "idrac_discovery_full" / "tasks" / "main-old.yml"
    ).exists()


def test_canonical_day0_playbooks_exist():
    assert (ROOT / "playbooks" / "day0" / "install.yml").is_file()
    assert (ROOT / "playbooks" / "day0" / "discover-bmc.yml").is_file()
