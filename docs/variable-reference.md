# Variable reference

The sample inventory is the authoritative variable example. Values are grouped under `inventories/sample/group_vars/all/`; sensitive values belong only in encrypted `group_vars/vault.yml`.

## Required cluster variables

| Variable | Type | Purpose |
|---|---|---|
| `deployment_mode` | `connected` or `disconnected` | Selects the image source and optional `oc-mirror` stage. |
| `cluster_name` | String | Cluster identifier and artifact directory name. |
| `base_dns_domain` | String | DNS base domain. |
| `openshift_version` | String | Requested minor release identifier supported by the Assisted service, for example `4.18`. |
| `control_plane_count` | Integer | Must match the `control_plane` inventory group. |
| `compute_count` | Integer | Must match the `workers` inventory group. |
| `machine_networks` | List | Machine CIDRs in Assisted Installer API format. |
| `cluster_networks` | List | Pod CIDRs and per-node host prefixes. |
| `service_networks` | List | Service CIDRs. |
| `vip_allocation_mode` | `static` or `dhcp` | Determines whether VIP values are sent. |
| `api_vips` | List | Required when VIP allocation is static. |
| `ingress_vips` | List | Required when VIP allocation is static. |
| `pull_secret` | Vault expression | Pull secret JSON. |
| `ssh_public_key` | Vault expression | Authorized SSH public key. |

## Per-host variables

| Variable | Required | Default | Purpose |
|---|---:|---|---|
| `bmc_type` | Yes | `auto` | `ilo`, `idrac`, `generic`, or `auto`. |
| `bmc_endpoint` | Yes | None | BMC HTTPS endpoint without `/redfish/v1`. |
| `bmc_username` | Yes | Vault expression | Redfish username. |
| `bmc_password` | Yes | Vault expression | Redfish password. |
| `node_role` | Yes | None | `master` or `worker`. |
| `node_hostname` | Yes | None | Final OpenShift hostname. |
| `node_ipv4_address` | Static only | None | Installation-network IPv4 address. |
| `installation_disk_id` | No | Empty | Assisted Installer disk ID assigned the `install` role. |
| `disks_skip_formatting` | No | Empty list | Assisted Installer disk-preservation operations. |
| `provisioning_mac_override` | No | Empty | Explicit host-matching MAC. |
| `provisioning_nic_match` | No | Empty | Regex used to select the Redfish NIC. |
| `mac_interface_map_override` | No | Empty list | Explicit logical-NIC-to-MAC map. |
| `node_nmstate_config` | No | Undefined | Complete custom NMState mapping. |
| `assisted_host_api_overrides` | No | Empty mapping | Additional valid `host-update-params` fields. |

## Assisted Installer API mappings

`assisted_cluster_api` exposes stable `cluster-create-params` fields. `assisted_infra_env_api` exposes stable `infra-env-create-params` fields. The repository explicitly defines service defaults, and the payload filter omits empty values while retaining `false` and `0`.

| Cluster field | Repository default |
|---|---|
| `high_availability_mode` | `Full` |
| `cpu_architecture` | `x86_64` |
| `hyperthreading` | `all` |
| `network_type` | `OVNKubernetes` |
| `schedulable_masters` | `false` |
| `user_managed_networking` | `false` |
| `platform.type` | `baremetal` |
| `load_balancer.type` | `cluster-managed` |
| `disk_encryption.enable_on` | `none` |
| `disk_encryption.mode` | `tpmv2` |
| Proxy, NTP, release image, OS stream, tags, Tang servers, ignition endpoint | Empty and omitted |

| InfraEnv field | Repository default |
|---|---|
| `image_type` | `minimal-iso`; automatically `disconnected-iso` in disconnected mode |
| `cpu_architecture` | `x86_64` |
| `kernel_arguments` | Empty and omitted |
| `network_discovery_delay_seconds` | `0` |
| Proxy, NTP, rendezvous IP, ignition override, OS stream, CA | Empty and omitted |

Use `assisted_cluster_api_overrides`, `assisted_infra_env_api_overrides`, and per-host `assisted_host_api_overrides` for API fields not represented by the stable mappings. Unknown fields are rejected by Assisted Installer.

## Network variables

| Variable | Default | Purpose |
|---|---|---|
| `node_network_config_mode` | `static` | `static` renders InfraEnv NMState; `dhcp` omits it. |
| `install_network_mode` | `bond` | Generated `single` or `bond` configuration. |
| `install_network_interface` | `nic0` | Logical NIC for single-interface mode. |
| `install_network_bond_name` | `bond0` | Bond name. |
| `install_network_bond_ports` | `[nic0, nic1]` | Bond ports. |
| `install_network_bond_mode` | `802.3ad` | NMState bond mode. |
| `install_network_bond_options` | `{miimon: "100"}` | NMState bond options. |
| `install_network_mtu` | `1500` | Interface MTU. |
| `node_ipv4_prefix` | `24` | Static IPv4 prefix length. |
| `node_ipv4_gateway` | Example value | Static default gateway. |
| `node_dns_servers` | Example list | Static DNS resolvers. |

## Disconnected variables

| Variable | Default | Purpose |
|---|---|---|
| `disconnected_environment` | `partially_disconnected` | Partially disconnected or `air_gapped`. |
| `oc_mirror_workflow` | `render_only` | Render, mirror-to-mirror, mirror-to-disk, or disk-to-mirror. |
| `oc_mirror_run_during_install` | `false` | Executes mirroring inside the install playbook when explicitly enabled. |
| `oc_mirror_registry` | Example registry | Destination registry and namespace. |
| `disconnected_release_image` | Empty | Required digest-pinned mirror pullspec. |
| `mirror_ca_file` | Empty | CA bundle added to the discovery environment. |
| `oc_mirror_channel` | Derived stable channel | OpenShift release channel. |
| `oc_mirror_min_version` | `openshift_version` | Minimum mirrored release. |
| `oc_mirror_max_version` | `openshift_version` | Maximum mirrored release. |
| `oc_mirror_architectures` | `[amd64]` | Mirrored architectures. |

Task 1 intentionally does not send `olm_operators` or `operator_bundles` during cluster creation. Operator selection and configuration are Day-2 GitOps concerns. Every other newer top-level field can be supplied through the typed override mappings after confirming it in the service OpenAPI schema.

## Vault variables

```yaml
vault_pull_secret: '{"auths": {...}}'
vault_ssh_public_key: ssh-ed25519 ...
vault_assisted_offline_token: ...
vault_assisted_access_token: ...
vault_mirror_auth_json: '{"auths": {...}}'
vault_bmc_credentials:
  master-0:
    username: Administrator
    password: ...
```

Create the encrypted file with `playbooks/day0/create-vault.yml`; see [Day-0 bare-metal installation](day0-bare-metal-installation.md).
