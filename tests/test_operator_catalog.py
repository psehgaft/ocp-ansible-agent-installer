from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: str):
    return yaml.safe_load((ROOT / path).read_text())


def test_required_platform_components_are_present():
    catalog = load_yaml("framework/components.yml")["components"]
    required = {
        "acm", "acs", "openshift_virtualization", "odf", "metallb",
        "baremetal_operator", "cert_manager", "rhoso", "gitops",
        "pipelines", "service_mesh", "logging", "loki", "observability",
        "openshift_ai", "mta", "mtv", "sriov", "nmstate", "ptp",
        "compliance", "external_secrets", "quay",
    }
    assert required <= set(catalog)


def test_catalog_entries_have_lifecycle_metadata():
    catalog = load_yaml("framework/components.yml")["components"]
    required_fields = {
        "display_name", "category", "enabled", "role", "namespace",
        "installation_type", "requires", "supported_openshift",
        "deployment_modes", "validation_hooks", "gitops",
    }
    for name, component in catalog.items():
        assert required_fields <= set(component), name
        assert {"path", "sync_wave"} <= set(component["gitops"]), name
        if component["installation_type"] == "olm":
            assert {"package", "channel", "source", "source_namespace"} <= set(component["olm"]), name


def test_operator_and_operand_catalogs_are_separate():
    components = load_yaml("framework/components.yml")["components"]
    operands = load_yaml("framework/operands.yml")["operands"]
    assert "acm_hub" not in components
    assert operands["acm_hub"]["operator"] == "acm"
    assert operands["acm_observability"]["role"] == "acm_observability"
    assert operands["acm_governance"]["role"] == "acm_governance"
