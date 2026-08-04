from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARCH_PAGES = ROOT / "workshop/documentation/modules/ARCHITECTURE/pages"
CATALOG = ROOT / "framework/components.yml"


def _architecture_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(ARCH_PAGES.glob("*.adoc"))
    ).lower()


def test_workshop_covers_catalog_components_and_deployment_modes() -> None:
    catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))["components"]
    workshop = _architecture_text()

    required_component_terms = {
        "gitops": "gitops",
        "acm": "acm",
        "acs": "acs",
        "openshift_virtualization": "virtualization",
        "odf": "odf",
        "metallb": "metallb",
        "cert_manager": "cert-manager",
        "rhoso": "rhoso",
        "logging": "logging",
        "loki": "loki",
        "mtv": "mtv",
        "sriov": "sr-iov",
        "nmstate": "nmstate",
        "ptp": "ptp",
        "quay": "quay",
    }

    missing_catalog_entries = set(required_component_terms) - set(catalog)
    assert not missing_catalog_entries, (
        "Workshop acceptance map references components missing from catalog: "
        f"{sorted(missing_catalog_entries)}"
    )

    missing_workshop_terms = {
        component
        for component, term in required_component_terms.items()
        if term not in workshop
    }
    assert not missing_workshop_terms, (
        "Catalog components missing from architecture workshop: "
        f"{sorted(missing_workshop_terms)}"
    )

    for mode in ("direct", "render", "gitops"):
        assert mode in workshop, f"Deployment mode {mode!r} is not taught in workshop"


def test_workshop_references_implemented_validation_and_reporting_contracts() -> None:
    workshop = _architecture_text()
    required_terms = (
        "component_result",
        "markdown",
        "json",
        "html",
        "csv",
        "kustomize",
        "ansible-playbook",
        "health",
        "troubleshooting",
    )
    missing = [term for term in required_terms if term not in workshop]
    assert not missing, f"Workshop is missing implemented framework concepts: {missing}"


def test_assisted_installer_regression_contract_is_retained() -> None:
    required_paths = (
        "playbooks/00-preflight.yml",
        "playbooks/02-boot-discovery-iso.yml",
        "playbooks/03-test-virtual-media.yml",
        "playbooks/90-eject-media.yml",
        "playbooks/day0/discover-bmc.yml",
        "playbooks/day0/install.yml",
        "roles/bmc_discovery/tasks/main.yml",
        "roles/bmc_virtual_media/tasks/main.yml",
        "roles/assisted_cluster/tasks/main.yml",
        "roles/assisted_hosts/tasks/main.yml",
        "roles/assisted_install/tasks/main.yml",
        "docs/migration-from-idrac.md",
    )
    missing = [path for path in required_paths if not (ROOT / path).exists()]
    assert not missing, f"Assisted Installer regression contract missing: {missing}"


def test_assisted_installer_uses_generic_redfish_contract() -> None:
    discovery = (ROOT / "playbooks/day0/discover-bmc.yml").read_text(encoding="utf-8")
    preflight = (ROOT / "playbooks/00-preflight.yml").read_text(encoding="utf-8")
    install = (ROOT / "playbooks/day0/install.yml").read_text(encoding="utf-8")
    sample_inventory = (ROOT / "inventories/sample/hosts.yml").read_text(encoding="utf-8")

    combined = "\n".join((discovery, preflight, install, sample_inventory))
    assert "bmc_discovery" in combined
    assert "bmc_endpoint" in combined
    assert "role: idrac_discovery" not in combined


def test_assisted_installer_retains_safety_and_output_contracts() -> None:
    virtual_media = (ROOT / "playbooks/03-test-virtual-media.yml").read_text(
        encoding="utf-8"
    )
    install = (ROOT / "playbooks/day0/install.yml").read_text(encoding="utf-8")
    post_install = (ROOT / "roles/post_install/tasks/main.yml").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "--limit" in readme
    assert "test_iso_url" in virtual_media
    assert "role: post_install" in install
    assert "kubeconfig" in post_install.lower()
    assert "kubeadmin" in post_install.lower()
    assert "artifacts" in post_install.lower()
