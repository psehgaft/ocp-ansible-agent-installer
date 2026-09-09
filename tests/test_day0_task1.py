from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: str):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def test_sample_variables_are_grouped_by_responsibility() -> None:
    variable_dir = ROOT / "inventories/sample/group_vars/all"
    expected = {
        "00-required.yml",
        "10-assisted-installer.yml",
        "20-network.yml",
        "30-disconnected.yml",
        "40-bmc.yml",
        "50-runtime.yml",
    }
    assert {path.name for path in variable_dir.glob("*.yml")} == expected
    assert not (ROOT / "inventories/sample/group_vars/all.yml").exists()


def test_installer_supports_connected_and_disconnected_without_day2() -> None:
    playbook = load_yaml("playbooks/day0/install.yml")[0]
    roles = [item["role"] if isinstance(item, dict) else item for item in playbook["roles"]]
    assert "oc_mirror" in roles
    assert roles.index("oc_mirror") < roles.index("assisted_cluster")
    assert not any("day2" in role or "operator" in role for role in roles)

    text = (ROOT / "playbooks/day0/install.yml").read_text(encoding="utf-8")
    assert "deployment_mode == 'disconnected'" in text
    assert "oc_mirror_run_during_install" in text


def test_oc_mirror_v2_supports_all_transfer_workflows() -> None:
    tasks = (ROOT / "roles/oc_mirror/tasks/main.yml").read_text(encoding="utf-8")
    for workflow in (
        "render_only",
        "mirror_to_mirror",
        "mirror_to_disk",
        "disk_to_mirror",
    ):
        assert workflow in tasks
    assert "--v2" in tasks
    assert "operators:" not in (
        ROOT / "roles/oc_mirror/templates/imageset-config.yml.j2"
    ).read_text(encoding="utf-8")


def test_network_and_disk_controls_are_mapped_to_assisted_api() -> None:
    cluster_tasks = (ROOT / "roles/assisted_cluster/tasks/main.yml").read_text(encoding="utf-8")
    install_tasks = (ROOT / "roles/assisted_install/tasks/main.yml").read_text(encoding="utf-8")
    assert "node_network_config_mode == 'static'" in cluster_tasks
    assert "vip_allocation_mode == 'static'" in cluster_tasks
    assert "static_network_config" in cluster_tasks
    assert "disks_selected_config" in install_tasks
    assert "disks_skip_formatting" in install_tasks
    assert "assisted_host_api_overrides" in install_tasks


def test_payload_compaction_preserves_api_defaults() -> None:
    path = ROOT / "filter_plugins/payload_filters.py"
    spec = spec_from_file_location("payload_filters", path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.compact_dict(
        {
            "empty": "",
            "none": None,
            "list": [],
            "dict": {},
            "false": False,
            "zero": 0,
            "nested": {"keep": "value", "drop": ""},
        }
    ) == {"false": False, "zero": 0, "nested": {"keep": "value"}}


def test_vault_bootstrap_never_commits_plaintext_secret_inputs() -> None:
    assert not (ROOT / "secrets/pull-secret.json").exists()
    tasks = (ROOT / "roles/vault_bootstrap/tasks/main.yml").read_text(encoding="utf-8")
    assert "ansible-vault" in tasks
    assert "always:" in tasks
    assert "no_log: true" in tasks
    assert "state: absent" in tasks


def test_day0_guide_documents_all_supported_modes() -> None:
    guide = (ROOT / "docs/day0-bare-metal-installation.md").read_text(encoding="utf-8")
    for phrase in (
        "Connected installation",
        "Partially disconnected installation",
        "Fully air-gapped installation",
        "DHCP networking",
        "Static networking",
        "Assisted Installer API customization",
        "Scope boundary",
    ):
        assert phrase in guide
