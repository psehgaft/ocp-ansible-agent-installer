#!/usr/bin/env python3
"""Small dependency-free tests for cross-vendor Redfish NIC normalization."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from filter_plugins.redfish_filters import (
    redfish_endpoint_parts,
    redfish_nics,
    redfish_resource_id,
    redfish_select_provisioning_mac,
)

ILO_SAMPLE = {
    "redfish_facts": {
        "nic": {
            "entries": [
                {
                    "Name": "Embedded LOM 1",
                    "MACAddress": "AA-BB-CC-DD-EE-01",
                    "LinkStatus": "LinkUp",
                    "SpeedMbps": 25000,
                },
                {
                    "Name": "Embedded LOM 2",
                    "PermanentMACAddress": "AA:BB:CC:DD:EE:02",
                    "LinkStatus": "NoLink",
                },
            ]
        }
    }
}

IDRAC_SAMPLE = {
    "nic": {
        "entries": [
            [
                "System.Embedded.1",
                [
                    {
                        "Id": "NIC.Integrated.1-1-1",
                        "DeviceDescription": "Integrated NIC 1 Port 1",
                        "PermanentMACAddress": "00:11:22:33:44:55",
                        "Status": {"State": "Enabled"},
                    }
                ],
            ]
        ]
    }
}


def main() -> None:
    ilo_nics = redfish_nics(ILO_SAMPLE)
    assert len(ilo_nics) == 2
    assert ilo_nics[0]["mac_address"] == "aa:bb:cc:dd:ee:01"
    assert redfish_select_provisioning_mac(ILO_SAMPLE) == "aa:bb:cc:dd:ee:01"
    assert redfish_select_provisioning_mac(ILO_SAMPLE, "LOM 2") == "aa:bb:cc:dd:ee:02"

    idrac_nics = redfish_nics(IDRAC_SAMPLE)
    assert len(idrac_nics) == 1
    assert idrac_nics[0]["mac_address"] == "00:11:22:33:44:55"
    assert redfish_select_provisioning_mac(IDRAC_SAMPLE) == "00:11:22:33:44:55"
    assert redfish_resource_id("/redfish/v1/Managers/1/") == "1"
    assert redfish_endpoint_parts("10.0.0.1")["baseuri"] == "10.0.0.1"
    assert redfish_endpoint_parts("http://10.0.0.1:8080/")["port"] == 8080
    assert redfish_endpoint_parts("https://[2001:db8::1]:8443")["baseuri"] == "[2001:db8::1]:8443"
    print("Redfish normalization tests passed.")


if __name__ == "__main__":
    main()
