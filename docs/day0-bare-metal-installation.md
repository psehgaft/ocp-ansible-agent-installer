# Day-0 bare-metal installation

This guide covers only the installation of OpenShift Container Platform on bare metal. It deliberately stops after the cluster is installed and the Assisted Installer credentials are downloaded. Operators and all other Day-2 configuration belong in GitOps.

Use this guide for the variable and API contract. For ordered CLI and GUI
procedures, start with the [six deployment scenarios](deployment-scenarios.md).

## Supported paths

| Content access | Assisted Installer | Image workflow | Supported |
|---|---|---|---|
| Connected | Red Hat SaaS or on-premises | Pull from Red Hat registries | Yes |
| Partially disconnected | Red Hat SaaS or on-premises | `oc-mirror` mirror-to-mirror | Yes |
| Air-gapped | On-premises Assisted Installer | `oc-mirror` mirror-to-disk, then disk-to-mirror | Yes |

Host provisioning uses standards-based Redfish and supports HPE iLO, Dell iDRAC, and other compatible BMCs. The control node must be able to reach each BMC and the discovery ISO must be reachable by each BMC virtual-media implementation.

## Variable layout

Copy the sample inventory before editing it:

```bash
cp -a inventories/sample inventories/my-cluster
```

The variables are intentionally split by responsibility:

| File | Classification | Purpose |
|---|---|---|
| `group_vars/all/00-required.yml` | Required | Cluster identity, release, topology, networks, VIPs, and secret references |
| `group_vars/all/10-assisted-installer.yml` | Optional defaults | Assisted Installer endpoint, auth mode, cluster API, InfraEnv API, and forward-compatible overrides |
| `group_vars/all/20-network.yml` | Optional defaults | DHCP/static addressing, single NIC/bond, DNS, routes, MTU, and custom NMState |
| `group_vars/all/30-disconnected.yml` | Conditional | `oc-mirror` v2, registry, archive, and mirrored release settings |
| `group_vars/all/40-bmc.yml` | Optional defaults | Redfish, virtual media, TLS, power, and timeout settings |
| `group_vars/all/50-runtime.yml` | Optional defaults | ISO publication, artifacts, polling, and state reuse |
| `group_vars/vault.yml` | Required encrypted | Pull secret, SSH public key, Assisted Installer token, BMC credentials, and optional mirror auth |
| `hosts.yml` | Required per host | BMC endpoint/type, node role/name, static address, disk ID, NIC map, and host API overrides |

Values named `CHANGE_ME` are never usable defaults. The preflight role rejects them before contacting the Assisted Installer API.

## Create the encrypted secrets vault

Create a YAML file outside the repository containing BMC credentials keyed by inventory hostname:

```yaml
master-0:
  username: Administrator
  password: REDACTED
master-1:
  username: root
  password: REDACTED
master-2:
  username: Administrator
  password: REDACTED
worker-0:
  username: Administrator
  password: REDACTED
worker-1:
  username: root
  password: REDACTED
```

Prepare the inputs and run the non-interactive vault playbook:

```bash
export OCP_VAULT_PASSWORD_FILE=/secure/path/vault-password.txt
export OCP_VAULT_OUTPUT_FILE="$PWD/inventories/my-cluster/group_vars/vault.yml"
export OCP_PULL_SECRET_FILE=/secure/path/pull-secret.json
export OCP_SSH_PUBLIC_KEY_FILE=/secure/path/id_ed25519.pub
export OCP_BMC_CREDENTIALS_FILE=/secure/path/bmc-credentials.yml
export OCP_ASSISTED_OFFLINE_TOKEN='REDACTED'

# Optional for on-premises Assisted Installer authentication:
# export OCP_ASSISTED_ACCESS_TOKEN='REDACTED'

# Optional when oc-mirror uses a dedicated registry auth file:
# export OCP_MIRROR_AUTH_FILE=/secure/path/mirror-auth.json

make vault
```

The playbook writes plaintext only to a mode `0600` temporary file, encrypts the destination with `ansible-vault`, and deletes the temporary file in an `always` block. Do not commit the password file or source secret files.

## Configure hosts and disk selection

Every host requires a BMC endpoint, node name, and role. Static mode also requires `node_ipv4_address`.

```yaml
master-0:
  bmc_type: ilo                 # ilo | idrac | generic | auto
  bmc_endpoint: https://10.0.0.11
  bmc_username: "{{ vault_bmc_credentials[inventory_hostname].username }}"
  bmc_password: "{{ vault_bmc_credentials[inventory_hostname].password }}"
  node_role: master
  node_hostname: master-0
  node_ipv4_address: 192.168.50.21
  installation_disk_id: /dev/disk/by-id/wwn-0x5000c50000000001
```

`installation_disk_id` is sent as `disks_selected_config` with the `install` role. Use the disk ID reported by Assisted Installer host inventory. Leave it empty only when Assisted Installer can select the disk unambiguously.

Optional host controls are:

```yaml
disks_skip_formatting:
  - disk_id: /dev/disk/by-id/wwn-0x5000c50000000002
    skip_formatting: true
assisted_host_api_overrides:
  machine_config_pool_name: worker-special
  node_labels:
    - key: node-role.kubernetes.io/special
      value: ""
```

## DHCP networking

Set the following values:

```yaml
node_network_config_mode: dhcp
vip_allocation_mode: dhcp
```

In DHCP mode, `static_network_config`, `api_vips`, and `ingress_vips` are omitted from the API request. DHCP must provide DNS, default routes, NTP reachability, and stable addressing appropriate for the selected Assisted Installer features.

You can also use DHCP for hosts with statically assigned VIPs:

```yaml
node_network_config_mode: dhcp
vip_allocation_mode: static
api_vips: [{ip: 192.168.50.10}]
ingress_vips: [{ip: 192.168.50.11}]
```

## Static networking

The default static generator supports a single Ethernet interface or an `802.3ad` bond. Logical NIC names map to MAC addresses discovered from Redfish. Use `mac_interface_map_override` on a host when BMC NIC ordering is ambiguous.

For VLANs, bridges, routes beyond the default route, IPv6 addresses, or other advanced NMState features, provide a complete per-host mapping:

```yaml
node_nmstate_config:
  interfaces:
    - name: nic0
      type: ethernet
      state: up
      ipv4:
        enabled: true
        dhcp: false
        address:
          - ip: 192.168.50.21
            prefix-length: 24
  dns-resolver:
    config:
      server: [192.168.50.5]
  routes:
    config:
      - destination: 0.0.0.0/0
        next-hop-address: 192.168.50.1
        next-hop-interface: nic0
```

## Connected installation

Set:

```yaml
deployment_mode: connected
assisted_auth_mode: saas
```

Then validate and install:

```bash
export ANSIBLE_VAULT_PASSWORD_FILE=/secure/path/vault-password.txt
make validate INVENTORY=inventories/my-cluster/hosts.yml
make install INVENTORY=inventories/my-cluster/hosts.yml \
  VAULT_ARGS="--vault-password-file $ANSIBLE_VAULT_PASSWORD_FILE"
```

## Partially disconnected installation

The control node must reach the source registries and the destination registry.

```yaml
deployment_mode: disconnected
disconnected_environment: partially_disconnected
oc_mirror_workflow: mirror_to_mirror
oc_mirror_run_during_install: false
oc_mirror_registry: registry.example.com:8443/ocp4
disconnected_release_image: registry.example.com:8443/ocp4/openshift-release-dev/ocp-release@sha256:REPLACE
mirror_ca_file: /etc/pki/ca-trust/source/anchors/registry-ca.pem
```

Render and review the image set, execute mirroring, then install:

```bash
make mirror INVENTORY=inventories/my-cluster/hosts.yml \
  VAULT_ARGS="--vault-password-file $ANSIBLE_VAULT_PASSWORD_FILE"
make install INVENTORY=inventories/my-cluster/hosts.yml \
  VAULT_ARGS="--vault-password-file $ANSIBLE_VAULT_PASSWORD_FILE"
```

`oc_mirror_run_during_install` defaults to `false`, preventing a completed mirror operation from running again during installation. Set it to `true` only when deliberately using `make install` as a single combined mirror-and-install operation.

## Fully air-gapped installation

On the connected transfer host:

```yaml
deployment_mode: disconnected
disconnected_environment: air_gapped
assisted_auth_mode: onprem
oc_mirror_workflow: mirror_to_disk
```

Run `make mirror`, transfer the complete archive and repository checkout to the disconnected control node, then set:

```yaml
oc_mirror_workflow: disk_to_mirror
assisted_api_url: https://assisted-service.example.com/api/assisted-install/v2
```

Run `make mirror` again to populate the registry. Set the exact digest-pinned `disconnected_release_image` produced in the mirror mapping before running `make install`.

## Assisted Installer API customization

The structured `assisted_cluster_api` and `assisted_infra_env_api` mappings expose stable options and their service defaults. Empty strings, empty lists, and empty mappings are removed from the JSON request; Boolean `false` and integer `0` are retained.

Use the override mappings for fields added by a newer Assisted Installer service:

```yaml
assisted_cluster_api_overrides:
  tags: cost-center=network
assisted_infra_env_api_overrides:
  network_discovery_delay_seconds: 120
```

Per-host fields use `assisted_host_api_overrides`. The Assisted Installer rejects unknown fields, so confirm keys against the OpenAPI document exposed by the exact service version.

## Scope boundary

The installation playbook performs only these actions:

1. Preflight validation.
2. Redfish discovery and evidence collection.
3. Optional OpenShift release mirroring.
4. Assisted Installer cluster and InfraEnv creation.
5. Discovery ISO publication and Redfish virtual-media boot.
6. Host matching, role assignment, optional disk selection, and installation.
7. Download of the kubeconfig and kubeadmin password plus installation evidence.

It does not install operators, configure identity providers, apply mirror resources to the installed cluster, or perform any other Day-2 mutation.

## References

- [Red Hat Assisted Installer documentation](https://docs.redhat.com/en/documentation/assisted_installer_for_openshift_container_platform/2026/)
- [Assisted Installer REST API source and OpenAPI specification](https://github.com/openshift/assisted-service/blob/master/swagger.yaml)
- [OpenShift oc-mirror documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/disconnected_environments/about-installing-oc-mirror-v2)
- [OpenShift oc-mirror v2 source and workflow reference](https://github.com/openshift/oc-mirror)
- [Ansible Vault guide](https://docs.ansible.com/projects/ansible/latest/vault_guide/index.html)
- [DMTF Redfish standard](https://www.dmtf.org/standards/redfish)
