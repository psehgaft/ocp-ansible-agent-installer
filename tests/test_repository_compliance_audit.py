from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_collection_requirements_are_resolvable_from_galaxy() -> None:
    for path in (ROOT / "requirements.yml", ROOT / "collections/requirements.yml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        names = {item["name"] for item in data["collections"]}
        assert "redhat.openshift" not in names
        assert "kubernetes.core" in names
        assert "community.vmware" in names


def test_example_group_vars_have_unique_keys() -> None:
    class UniqueKeyLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):  # type: ignore[no-untyped-def]
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            assert key not in mapping, f"duplicate key: {key}"
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    UniqueKeyLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping,
    )
    yaml.load(
        (ROOT / "group_vars/example/main.yml").read_text(encoding="utf-8"),
        Loader=UniqueKeyLoader,
    )


def test_preflight_uses_generic_redfish() -> None:
    text = (ROOT / "playbooks/test-preflight.yml").read_text(encoding="utf-8")
    assert "role: bmc_discovery" in text
    assert "role: idrac_discovery" not in text
    assert "bmc_endpoint" in text


def test_vmware_audit_moved_and_has_no_default_password() -> None:
    assert not (ROOT / "audit_vmware_network.yml").exists()
    playbook = ROOT / "playbooks/audit_vmware_network.yml"
    text = playbook.read_text(encoding="utf-8")
    assert playbook.exists()
    assert "YourPasswordHere" not in text
    assert "vcenter_password is defined" in text
    assert "no_log: true" in text


def test_readme_documents_ansible_gitops_and_reports() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for required in (
        "## Ansible execution",
        "## GitOps execution",
        "## Validation and reports",
        "playbooks/audit_vmware_network.yml",
        "docs/deprecated-files.md",
    ):
        assert required in text


def test_assisted_installer_regression_paths_remain() -> None:
    required = (
        "playbooks/day0/discover-bmc.yml",
        "playbooks/day0/install.yml",
        "playbooks/03-test-virtual-media.yml",
        "workshop/documentation/modules/ROOT/pages/04-discovery.adoc",
        "workshop/documentation/modules/ROOT/pages/07-install.adoc",
    )
    for relative in required:
        assert (ROOT / relative).exists(), relative
