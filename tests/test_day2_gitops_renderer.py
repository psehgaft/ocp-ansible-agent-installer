import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts/render_day2_gitops.py"
CATALOG = ROOT / "framework/day2-operator-catalog.yml"


def render(tmp_path: Path, config: dict):
    tmp_path.mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "config.yml"
    output = tmp_path / "output"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(RENDERER), "--catalog", str(CATALOG), "--config", str(config_path), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result, output


def base_config(**overrides):
    config = {
        "cluster_name": "cluster-a",
        "openshift_minor_version": "4.19",
        "profile": "custom",
        "repository_url": "https://git.example.com/platform.git",
        "target_revision": "main",
        "repository_path": "clusters",
        "install_plan_approval": "Automatic",
        "enabled_operators": ["gitops"],
        "operator_overrides": {},
        "additional_operators": {},
        "catalog_source_images": {},
        "operands": {},
    }
    config.update(overrides)
    return config


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_renders_dependency_order_applications_and_mirror_config(tmp_path):
    result, output = render(tmp_path, base_config(enabled_operators=["mtv", "logging"]))
    assert result.returncode == 0, result.stderr
    summary = json.loads((output / "render-summary.json").read_text())
    assert summary["selected_operators"] == [
        "openshift_virtualization", "mtv", "loki", "logging"
    ]
    assert summary["selected_packages"][1]["package"] == "mtv-operator"
    app = load(output / "clusters/cluster-a/applications/operator-mtv.yaml")
    assert app["spec"]["source"]["path"] == "clusters/cluster-a/operators/mtv"
    mirror = load(output / "mirror/cluster-a-operators-imageset-config.yaml")
    assert mirror["mirror"]["operators"][0]["catalog"].endswith("v4.19")


def test_profile_and_explicit_selection_are_combined_without_duplicates(tmp_path):
    result, output = render(tmp_path, base_config(profile="minimal", enabled_operators=["gitops", "pipelines"]))
    assert result.returncode == 0, result.stderr
    summary = json.loads((output / "render-summary.json").read_text())
    assert summary["selected_operators"] == ["gitops", "pipelines"]


def test_operator_override_and_versioned_channel_are_rendered(tmp_path):
    result, output = render(tmp_path, base_config(
        enabled_operators=["lvms"], operator_overrides={"lvms": {"install_plan_approval": "Manual"}}
    ))
    assert result.returncode == 0, result.stderr
    subscription = load(output / "clusters/cluster-a/operators/lvms/subscription.yaml")
    assert subscription["spec"]["channel"] == "stable-4.19"
    assert subscription["spec"]["installPlanApproval"] == "Manual"


def test_additional_certified_operator_is_supported(tmp_path):
    custom = {
        "display_name": "Vendor CSI", "package": "vendor-csi", "channel": "stable",
        "source": "certified-operators", "namespace": "vendor-csi", "dependencies": [],
    }
    result, output = render(tmp_path, base_config(
        enabled_operators=["vendor_csi"], additional_operators={"vendor_csi": custom}
    ))
    assert result.returncode == 0, result.stderr
    subscription = load(output / "clusters/cluster-a/operators/vendor-csi/subscription.yaml")
    assert subscription["spec"]["source"] == "certified-operators"


def test_structured_operands_render_but_plain_secrets_are_rejected(tmp_path):
    operand = {"apiVersion": "operator.open-cluster-management.io/v1", "kind": "MultiClusterHub", "metadata": {"name": "multiclusterhub", "namespace": "open-cluster-management"}, "spec": {"availabilityConfig": "High"}}
    result, output = render(tmp_path, base_config(enabled_operators=["acm"], operands={"acm": [operand]}))
    assert result.returncode == 0, result.stderr
    assert load(output / "clusters/cluster-a/operands/acm/resource-001.yaml")["kind"] == "MultiClusterHub"

    secret = {"apiVersion": "v1", "kind": "Secret", "metadata": {"name": "bad"}, "stringData": {"password": "bad"}}
    result, _ = render(tmp_path / "secret", base_config(operands={"gitops": [secret]}))
    assert result.returncode != 0
    assert "Secret is forbidden" in result.stderr

    inline = {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "bad"}, "data": {"password": "bad"}}
    result, _ = render(tmp_path / "inline", base_config(operands={"gitops": [inline]}))
    assert result.returncode != 0
    assert "inline secret field" in result.stderr


def test_multiple_operators_in_one_namespace_create_one_operator_group(tmp_path):
    result, output = render(tmp_path, base_config(enabled_operators=["node_maintenance", "self_node_remediation"]))
    assert result.returncode == 0, result.stderr
    root = output / "clusters/cluster-a/operators"
    assert (root / "node-maintenance/operatorgroup.yaml").exists()
    assert not (root / "self-node-remediation/operatorgroup.yaml").exists()


def test_unknown_operator_and_dependency_cycle_fail_closed(tmp_path):
    result, _ = render(tmp_path, base_config(enabled_operators=["does_not_exist"]))
    assert result.returncode != 0
    assert "Unknown operator" in result.stderr

    cycle = {
        "display_name": "Cycle", "package": "cycle", "channel": "stable",
        "source": "redhat-operators", "namespace": "cycle", "dependencies": ["cycle"],
    }
    result, _ = render(tmp_path / "cycle", base_config(
        enabled_operators=["cycle"], additional_operators={"cycle": cycle}
    ))
    assert result.returncode != 0
    assert "Dependency cycle" in result.stderr


def test_renderer_does_not_delete_unmanaged_cluster_content(tmp_path):
    output = tmp_path / "output"
    unmanaged = output / "clusters/cluster-a/operators/custom"
    unmanaged.mkdir(parents=True)
    (unmanaged / "keep.yaml").write_text("keep: true\n")
    config_path = tmp_path / "config.yml"
    config_path.write_text(yaml.safe_dump(base_config()), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(RENDERER), "--catalog", str(CATALOG), "--config", str(config_path), "--output", str(output)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert (unmanaged / "keep.yaml").exists()


def test_curated_catalog_is_structurally_valid():
    catalog = load(CATALOG)
    assert len(catalog["operators"]) >= 50
    for name, operator in catalog["operators"].items():
        assert {"display_name", "package", "channel", "source", "namespace", "dependencies", "official"} <= set(operator), name
        assert operator["source"] in catalog["catalog_sources"], name
        for dependency in operator["dependencies"]:
            assert dependency in catalog["operators"], (name, dependency)
    requested = {"acm", "acs", "odf", "cluster_observability", "loki", "logging", "oadp", "compliance", "openshift_virtualization", "mtv", "mta", "sso", "cert_manager", "rhoso", "amq_streams", "sriov", "gitops", "pipelines", "openshift_ai", "dell_csm", "netapp_trident", "portworx"}
    assert requested <= set(catalog["operators"])


def test_every_curated_operator_can_be_rendered_together(tmp_path):
    catalog = load(CATALOG)
    selected = list(catalog["operators"])
    result, output = render(tmp_path, base_config(enabled_operators=selected))
    assert result.returncode == 0, result.stderr
    summary = json.loads((output / "render-summary.json").read_text())
    assert set(summary["selected_operators"]) == set(selected)
    assert summary["operator_count"] == len(selected)
