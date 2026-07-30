# Variable Reference

## Per-host variables

| Variable | Required | Values / example | Purpose |
|---|---:|---|---|
| `bmc_type` | Yes | `ilo`, `idrac`, `generic`, `auto` | Declares or detects the management-controller technology. |
| `bmc_endpoint` | Yes | `https://10.10.10.11` | BMC HTTPS endpoint without `/redfish/v1`. |
| `bmc_username` | Yes | `Administrator` or `root` | Redfish account. |
| `bmc_password` | Yes | Vault expression | Redfish password. |
| `node_role` | Yes | `master`, `worker` | Assisted Installer host role. |
| `node_hostname` | Yes | `master-0` | Final node hostname. |
| `node_ipv4_address` | Yes | `192.168.50.21` | Static installation-network address. |
| `provisioning_mac_override` | No | `aa:bb:cc:dd:ee:ff` | Forces the MAC used to match Assisted Installer registration. |
| `provisioning_nic_match` | No | `LOM 1|Integrated.1-1` | Regex for selecting a NIC by name or Redfish ID. |
| `mac_interface_map_override` | No | List of `logical_nic_name` and `mac_address` entries | Replaces discovery order with an explicit Assisted Installer MAC-to-logical-NIC map. |
| `bmc_system_id` | No | `System.Embedded.1` | Overrides dynamic Systems resource selection. |
| `bmc_manager_id` | No | `iDRAC.Embedded.1` | Overrides dynamic Managers resource selection. |
| `bmc_chassis_id` | No | `System.Embedded.1` | Overrides dynamic Chassis resource selection. |
| `bmc_virtual_media_category` | No | `Manager`, `Systems` | Redfish location used for virtual media. Default: `Manager`. |

## Cluster variables

| Variable | Required | Purpose |
|---|---:|---|
| `assisted_api_url` | Yes | Assisted Installer v2 API endpoint. |
| `assisted_auth_mode` | Yes | `saas` or `onprem`. |
| `cluster_name` | Yes | Cluster identifier and artifact directory name. |
| `base_dns_domain` | Yes | Base DNS domain. |
| `openshift_version` | Yes | Requested release stream/version supported by the selected Assisted service. |
| `control_plane_count` | Yes | Must match the `control_plane` inventory group. |
| `compute_count` | Yes | Must match the `workers` inventory group. |
| `machine_network_cidr` | Yes | Bare-metal machine network. |
| `api_vip` | Yes | API virtual IP. |
| `ingress_vip` | Yes | Ingress virtual IP. |
| `pull_secret_file` | Yes | Local pull-secret path. |
| `ssh_public_key_file` | Yes | Local SSH public-key path. |

## Static network variables

| Variable | Purpose |
|---|---|
| `install_network_mode` | `single` or `bond`. |
| `install_network_interface` | Logical NIC name used for single-interface mode. |
| `install_network_bond_name` | Bond name. |
| `install_network_bond_ports` | Logical NICs included in the bond. |
| `install_network_bond_mode` | NMState bond mode, for example `802.3ad`. |
| `install_network_mtu` | Installation network MTU. |
| `node_ipv4_prefix` | IPv4 prefix length. |
| `node_ipv4_gateway` | Default gateway. |
| `node_dns_servers` | DNS resolver list. |
| `ntp_servers` | NTP sources included in the Assisted Installer resources. |

## Redfish behavior variables

| Variable | Default | Purpose |
|---|---|---|
| `bmc_validate_certs` | `false` | Enables BMC certificate validation. Set `true` in production. |
| `bmc_ca_path` | empty | PEM CA bundle used when validation is enabled. |
| `bmc_timeout` | `120` | Redfish request timeout in seconds. |
| `bmc_boot_device` | `Cd` | One-time boot target. |
| `bmc_virtual_media_category` | `Manager` | Preferred virtual-media resource category. |
| `bmc_virtual_media_fallback_to_systems` | `true` | Retries insertion through the Systems resource. |
| `bmc_power_command` | `PowerForceRestart` | Power action after boot override. |
| `bmc_wait_for_node_ssh` | `true` | Waits for port 22 on the discovery environment. |

## ISO delivery variables

| Variable | Purpose |
|---|---|
| `iso_delivery_mode` | `local_http`, `existing_http`, or `direct_url`. |
| `iso_http_advertise_address` | Control-node address reachable from every BMC. |
| `iso_http_bind_address` | Local bind address for the Podman HTTP container. |
| `iso_http_port` | Published TCP port. |
| `iso_existing_url` | Existing BMC-reachable ISO URL. |
| `assisted_image_type` | `minimal-iso` or `full-iso`. |

## Vault variables

```yaml
assisted_offline_token: "..."       # SaaS
# assisted_access_token: "..."      # On-premises service

vault_bmc_passwords:
  master-0: "..."
  master-1: "..."
```

Encrypt the active file:

```bash
ansible-vault encrypt inventories/mycluster/group_vars/vault.yml
```
