"""Normalization filters for heterogeneous Redfish payloads.

The community.general Redfish modules return nested structures that can vary by
vendor, firmware, and collection version. These filters recursively inspect the
payload instead of depending on a fixed Dell or HPE response shape.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit
from typing import Any, Dict, Iterable, List

_MAC_RE = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")


def _walk(value: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            yield from _walk(nested)


def _normalise_mac(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower().replace("-", ":")
    if re.fullmatch(r"[0-9a-f]{12}", text):
        text = ":".join(text[i : i + 2] for i in range(0, 12, 2))
    return text if _MAC_RE.fullmatch(text) else ""


def redfish_nics(value: Any) -> List[Dict[str, Any]]:
    """Return a de-duplicated normalized NIC list from any Redfish payload."""
    result: List[Dict[str, Any]] = []
    seen = set()
    mac_keys = ("MACAddress", "MacAddress", "PermanentMACAddress", "FactoryMacAddress")

    for item in _walk(value):
        mac = ""
        for key in mac_keys:
            mac = _normalise_mac(item.get(key))
            if mac:
                break
        if not mac or mac in seen:
            continue
        seen.add(mac)
        status = item.get("Status")
        status_state = status.get("State") if isinstance(status, dict) else status
        result.append(
            {
                "name": item.get("Name") or item.get("DeviceDescription") or item.get("Id") or "",
                "id": item.get("Id") or item.get("DeviceId") or item.get("@odata.id") or "",
                "mac_address": mac,
                "permanent_mac_address": _normalise_mac(item.get("PermanentMACAddress")),
                "link_status": item.get("LinkStatus") or status_state or "Unknown",
                "speed_mbps": item.get("SpeedMbps") or item.get("CurrentLinkSpeedMbps") or item.get("BitRate") or 0,
                "interface_enabled": item.get("InterfaceEnabled"),
            }
        )
    return result


def redfish_select_provisioning_mac(
    value: Any, name_pattern: str = "", override: str = ""
) -> str:
    """Select a provisioning MAC using override, regex, LinkUp, then first NIC."""
    override_mac = _normalise_mac(override)
    if override:
        if not override_mac:
            raise ValueError(f"Invalid provisioning MAC override: {override}")
        return override_mac

    nics = redfish_nics(value)
    if not nics:
        return ""

    if name_pattern:
        regex = re.compile(name_pattern, re.IGNORECASE)
        for nic in nics:
            searchable = f"{nic['name']} {nic['id']}"
            if regex.search(searchable):
                return nic["mac_address"]

    for nic in nics:
        if str(nic.get("link_status", "")).lower() in {"linkup", "up", "enabled"}:
            return nic["mac_address"]

    return nics[0]["mac_address"]



def redfish_endpoint_parts(value: Any) -> Dict[str, Any]:
    """Normalize a BMC URL and return endpoint, baseuri, host, port, and scheme."""
    text = str(value or "").strip().rstrip("/")
    if not re.match(r"^https?://", text, re.IGNORECASE):
        text = "https://" + text
    parsed = urlsplit(text)
    if not parsed.hostname:
        raise ValueError(f"Invalid BMC endpoint: {value}")
    scheme = parsed.scheme.lower()
    port = parsed.port or (443 if scheme == "https" else 80)
    host_for_uri = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    default_port = 443 if scheme == "https" else 80
    baseuri = host_for_uri if port == default_port else f"{host_for_uri}:{port}"
    endpoint = f"{scheme}://{baseuri}"
    return {
        "endpoint": endpoint,
        "baseuri": baseuri,
        "host": parsed.hostname,
        "port": port,
        "scheme": scheme,
    }

def redfish_resource_id(uri: Any) -> str:
    """Extract the final resource ID from a Redfish @odata.id URI."""
    if not uri:
        return ""
    return str(uri).rstrip("/").split("/")[-1]


class FilterModule:
    def filters(self):
        return {
            "redfish_nics": redfish_nics,
            "redfish_select_provisioning_mac": redfish_select_provisioning_mac,
            "redfish_resource_id": redfish_resource_id,
            "redfish_endpoint_parts": redfish_endpoint_parts,
        }
