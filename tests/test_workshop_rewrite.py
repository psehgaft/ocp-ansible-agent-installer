from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "workshop/documentation/modules/ARCHITECTURE"
LEGACY = ROOT / "workshop/documentation/modules/ROOT"


def test_architecture_module_contains_required_pages() -> None:
    required = {
        "index.adoc",
        "01-framework-inventory.adoc",
        "02-redfish-assisted-installer.adoc",
        "03-deployment-modes.adoc",
        "04-platform-operators.adoc",
        "05-acm-acs.adoc",
        "06-storage-virtualization.adoc",
        "07-pki-identity.adoc",
        "08-quay-registries.adoc",
        "09-day2-operations.adoc",
        "10-health-troubleshooting.adoc",
        "11-new-component.adoc",
        "appendix-dependencies.adoc",
        "legacy-workshop.adoc",
    }
    assert required <= {path.name for path in (ARCH / "pages").glob("*.adoc")}


def test_legacy_workshop_is_preserved() -> None:
    assert (LEGACY / "nav.adoc").exists()
    assert (LEGACY / "pages/04-discovery.adoc").exists()
    assert (LEGACY / "pages/07-install.adoc").exists()


def test_antora_registers_both_tracks() -> None:
    content = (ROOT / "workshop/documentation/antora.yml").read_text()
    assert "modules/ARCHITECTURE/nav.adoc" in content
    assert "modules/ROOT/nav.adoc" in content


def test_dependency_model_is_taught() -> None:
    content = (ARCH / "pages/appendix-dependencies.adoc").read_text()
    for key in ("requires", "recommends", "conflicts", "after", "requires_configuration"):
        assert key in content
