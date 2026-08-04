"""Framework runtime filters for component selection and dependency ordering."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Set


class AnsibleFilterError(Exception):
    """Fallback error used when Ansible is not importable during unit tests."""


try:
    from ansible.errors import AnsibleFilterError as _AnsibleFilterError
except ImportError:  # pragma: no cover
    _AnsibleFilterError = AnsibleFilterError


def resolve_component_order(
    catalog: Mapping[str, Mapping[str, Any]], enabled_components: Iterable[str]
) -> List[str]:
    """Return enabled components and their required dependencies in topological order."""
    requested = list(dict.fromkeys(enabled_components))
    missing = sorted(component for component in requested if component not in catalog)
    if missing:
        raise _AnsibleFilterError(
            f"Unknown framework component(s): {', '.join(missing)}"
        )

    resolved: List[str] = []
    visiting: Set[str] = set()
    visited: Set[str] = set()

    def visit(component: str) -> None:
        if component in visited:
            return
        if component in visiting:
            raise _AnsibleFilterError(
                f"Circular framework dependency detected at component '{component}'"
            )
        if component not in catalog:
            raise _AnsibleFilterError(
                f"Component dependency '{component}' is not defined in the catalog"
            )

        visiting.add(component)
        metadata: Dict[str, Any] = dict(catalog[component] or {})
        dependencies = metadata.get("requires", metadata.get("dependencies", [])) or []
        for dependency in dependencies:
            visit(str(dependency))
        visiting.remove(component)
        visited.add(component)
        resolved.append(component)

    for item in requested:
        visit(item)
    return resolved


class FilterModule:
    """Expose framework runtime filters to Ansible."""

    def filters(self) -> Dict[str, Any]:
        return {"resolve_component_order": resolve_component_order}
