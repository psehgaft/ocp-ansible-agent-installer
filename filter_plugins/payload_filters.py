"""Filters used to construct Assisted Installer API payloads."""


def compact_dict(value):
    """Recursively remove null and empty values while preserving false and zero."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            compacted = compact_dict(item)
            if compacted not in (None, "", [], {}):
                result[key] = compacted
        return result
    if isinstance(value, list):
        return [compacted for item in value if (compacted := compact_dict(item)) not in (None, "", [], {})]
    return value


class FilterModule:
    """Expose payload filters to Ansible."""

    def filters(self):
        return {"compact_dict": compact_dict}

