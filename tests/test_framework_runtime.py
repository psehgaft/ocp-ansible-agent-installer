from pathlib import Path
import importlib.util

import pytest


MODULE_PATH = Path(__file__).parents[1] / "filter_plugins" / "framework_runtime.py"
SPEC = importlib.util.spec_from_file_location("framework_runtime", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_resolves_dependencies_before_dependents():
    catalog = {
        "gitops": {"requires": []},
        "acm": {"requires": ["gitops"]},
    }

    assert MODULE.resolve_component_order(catalog, ["acm"]) == ["gitops", "acm"]


def test_rejects_unknown_components():
    with pytest.raises(Exception, match="Unknown framework component"):
        MODULE.resolve_component_order({}, ["missing"])


def test_rejects_circular_dependencies():
    catalog = {
        "a": {"requires": ["b"]},
        "b": {"requires": ["a"]},
    }

    with pytest.raises(Exception, match="Circular framework dependency"):
        MODULE.resolve_component_order(catalog, ["a"])
