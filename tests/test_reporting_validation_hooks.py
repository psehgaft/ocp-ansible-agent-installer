from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_component_result_schema_has_required_fields() -> None:
    schema = yaml.safe_load((ROOT / "framework/component-result.schema.yml").read_text())
    required = set(schema["required"])
    expected = {
        "name", "status", "requested_state", "effective_state",
        "deployment_mode", "version", "installation", "functional_checks",
        "warnings", "errors", "remediation_recommendation", "evidence",
    }
    assert expected <= required


def test_all_report_formats_are_present() -> None:
    templates = ROOT / "roles/component_report/templates"
    assert (templates / "report.md.j2").exists()
    assert (templates / "report.html.j2").exists()
    assert (templates / "summary.csv.j2").exists()
    tasks = (ROOT / "roles/component_report/tasks/main.yml").read_text()
    assert ".json" in tasks


def test_operator_lifecycle_publishes_component_result() -> None:
    tasks = (ROOT / "roles/operator_lifecycle/tasks/main.yml").read_text()
    assert "name: component_validation" in tasks
    assert "component_validation_installation" in tasks
    assert "component_validation_evidence" in tasks
    assert "component_validation_remediation_recommendation" in tasks


def test_evidence_contract_supports_command_or_resource() -> None:
    schema = yaml.safe_load((ROOT / "framework/component-result.schema.yml").read_text())
    evidence = schema["properties"]["evidence"]["items"]
    assert {"command", "resource"} <= set(evidence["properties"])
