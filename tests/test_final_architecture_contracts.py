from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/validate_architecture_contracts.py"
SPEC = importlib.util.spec_from_file_location("architecture_contracts", MODULE_PATH)
assert SPEC and SPEC.loader
architecture_contracts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(architecture_contracts)


def test_every_role_is_standardized_and_documentable() -> None:
    roles = architecture_contracts.discover_roles()
    assert roles
    assert all(role["task_count"] >= 0 for role in roles)
    assert all(role["documentation_source"] == "generated-from-role-structure" for role in roles)


def test_every_component_has_installation_and_functional_validation() -> None:
    components = architecture_contracts.validate_component_contracts()
    assert components
    assert all(component["installation_checks"] for component in components)
    assert all(component["functional_checks"] for component in components)


def test_direct_and_gitops_use_identical_canonical_bytes() -> None:
    equivalence = architecture_contracts.validate_desired_state_equivalence()
    assert equivalence
    assert all(item["sha256"] and item["byte_count"] > 0 for item in equivalence)


def test_legacy_workflows_are_retired() -> None:
    lifecycle = architecture_contracts.validate_workflow_lifecycle()
    assert lifecycle["supported"]
    assert lifecycle["retired"]
