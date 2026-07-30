# Architecture

## Objective

The repository separates OpenShift Assisted Installer orchestration from server-vendor implementation details. HPE iLO and Dell iDRAC both expose Redfish resources, so the automation uses the same standards-based roles for inventory, virtual media, one-time boot, and power control.

## Control flow

```text
Inventory and Vault
        |
        v
Preflight and BMC endpoint normalization
        |
        v
Redfish service-root and resource discovery
        |
        +--> Systems resource --> NIC/CPU/memory/storage/boot/health
        +--> Manager resource --> controller/management NIC/virtual media
        +--> Chassis resource --> enclosure/fans/health
        +--> UpdateService --> firmware inventory
        |
        v
Normalize NICs and select provisioning MAC
        |
        v
Assisted Installer Cluster + InfraEnv + NMState mapping
        |
        v
Discovery ISO publication
        |
        v
Redfish VirtualMediaInsert + SetOneTimeBoot + restart
        |
        v
Host registration and MAC matching
        |
        v
OpenShift installation, credentials, and evidence
```

## Vendor selector

The inventory variable `bmc_type` accepts:

- `ilo`: explicitly identifies an HPE iLO controller.
- `idrac`: explicitly identifies a Dell iDRAC controller.
- `generic`: uses standards-based Redfish without a vendor assertion.
- `auto`: examines Redfish root, system, manager, and chassis identity fields.

The selector is intentionally not used to maintain duplicate vendor task trees. It records intent and allows future targeted workarounds while the default path remains portable Redfish.

## Resource discovery

The role queries `/redfish/v1/`, follows the advertised `Systems`, `Managers`, and `Chassis` collections, and selects the first member unless a per-host override is configured:

```yaml
bmc_system_id: "System.Embedded.1"
bmc_manager_id: "iDRAC.Embedded.1"
bmc_chassis_id: "System.Embedded.1"
```

HPE systems commonly expose IDs different from Dell systems. Dynamic discovery is therefore safer than embedding values such as `System.Embedded.1` or `iDRAC.Embedded.1` in shared automation.

## Compatibility layer

Legacy inventory variables are accepted during migration:

```yaml
idrac_ip: 10.10.10.20
idrac_user: root
idrac_password: "{{ vault_idrac_password }}"
```

They are normalized internally to:

```yaml
bmc_endpoint: https://10.10.10.20
bmc_username: root
bmc_password: "{{ vault_idrac_password }}"
bmc_type: idrac
```

New inventories should use only the `bmc_*` names.

## NIC normalization

Redfish responses vary by firmware and collection version. The custom filter plugin recursively searches nested objects for these common properties:

- `MACAddress`
- `MacAddress`
- `PermanentMACAddress`
- `FactoryMacAddress`

The provisioning MAC is selected in this order:

1. `provisioning_mac_override`.
2. A NIC whose name or ID matches `provisioning_nic_match`.
3. The first interface reporting an up/enabled link.
4. The first valid MAC discovered.

For production bonds, explicitly set `provisioning_nic_match` or `provisioning_mac_override` when the BMC enumeration order is not deterministic.

The InfraEnv normally assigns discovered NICs to `nic0`, `nic1`, and subsequent logical names in normalized discovery order. For hardware where physical-port intent must be fixed independently of Redfish enumeration, define a per-host map:

```yaml
mac_interface_map_override:
  - logical_nic_name: nic0
    mac_address: "aa:bb:cc:dd:ee:01"
  - logical_nic_name: nic1
    mac_address: "aa:bb:cc:dd:ee:02"
```

## Security boundaries

- BMC and Assisted Installer credentials are loaded from Ansible Vault.
- Raw evidence and credentials are written with restrictive permissions.
- TLS verification is configurable and should be enabled in production.
- Virtual-media and power operations are disruptive and should be constrained with inventory groups and `--limit` during testing.
- The control-node ISO server is intended for an isolated installation network, not for general-purpose exposure.
