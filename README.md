# OpenShift Assisted Installer Automation with Vendor-Neutral Redfish

This repository automates an OpenShift bare-metal deployment through the Red Hat Assisted Installer API and a standards-based Redfish management workflow.

It is based on the architecture of `psehgaft/ocp-ansible-agent-installer`, but replaces the Dell-only iDRAC discovery and virtual-media implementation with a reusable BMC abstraction that supports:

- HPE iLO 5/6 as the primary target; iLO 4 is best-effort when its firmware exposes the required Redfish resources and actions.
- Dell iDRAC 8/9 with Redfish support.
- Other standards-compliant Redfish BMCs through the `generic` driver.
- Automatic vendor detection with `bmc_type: auto`.

The primary selector is the per-host variable:

```yaml
bmc_type: ilo       # ilo | idrac | generic | auto
```

The implementation uses `community.general.redfish_info` for inventory and `community.general.redfish_command` for virtual media, one-time boot, and power operations. Vendor-specific resource IDs are discovered dynamically from `/redfish/v1/`.

## Capabilities

1. Validate the Ansible control node and required variables.
2. Connect to each BMC and discover its Redfish topology.
3. Collect system, manager, chassis, NIC, CPU, memory, storage-volume, firmware, health, boot, and virtual-media data.
4. Normalize NIC information across iLO and iDRAC responses.
5. Select or validate the provisioning MAC address.
6. Create the Assisted Installer cluster and InfraEnv resources.
7. Generate static NMState configuration for single-NIC or bonded installation networks.
8. Download or reference the Assisted Installer discovery ISO.
9. Insert the ISO through Redfish virtual media.
10. Set a one-time CD/DVD boot override and restart the server.
11. Match discovered hosts by MAC address, assign roles and hostnames, and start installation.
12. Download the kubeconfig and kubeadmin password.
13. Generate raw JSON evidence and a Markdown installation report.

## Repository layout

```text
.
├── ansible.cfg
├── inventories/sample/
│   ├── hosts.yml
│   └── group_vars/
│       ├── all.yml
│       └── vault.yml.example
├── filter_plugins/redfish_filters.py
├── playbooks/
├── roles/
├── scripts/
├── docs/
├── WORKSHOP.md
└── workshop/                 # Antora/Showroom-style workshop source
```

## Requirements

- RHEL 9, Fedora, or another supported Linux control node.
- Python 3.11 or later.
- `ansible-core` 2.18 or later.
- `community.general` collection.
- `oc`, `curl`, and `jq`.
- Network access from the control node to each BMC HTTPS endpoint.
- Network access from each BMC to the discovery ISO URL.
- DNS, API/Ingress VIPs, load balancing, and the other bare-metal prerequisites required by OpenShift.
- A Red Hat pull secret and SSH public key.
- A Red Hat Assisted Installer offline token for SaaS, or an access token for an on-premises Assisted Service.

Install the Python and collection dependencies:

```bash
python3 -m pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
```

## Quick start

### 1. Copy the sample inventory

```bash
cp -a inventories/sample inventories/mycluster
```

### 2. Configure hosts

Edit `inventories/mycluster/hosts.yml`.

For HPE iLO:

```yaml
master-0:
  bmc_type: ilo
  bmc_endpoint: "https://10.10.10.11"
  bmc_username: "Administrator"
  node_role: master
  node_hostname: master-0
  node_ipv4_address: "192.168.50.21"
```

For Dell iDRAC:

```yaml
worker-0:
  bmc_type: idrac
  bmc_endpoint: "https://10.10.10.21"
  bmc_username: "root"
  node_role: worker
  node_hostname: worker-0
  node_ipv4_address: "192.168.50.31"
```

`bmc_type: auto` can be used when the BMC exposes recognizable manufacturer information at the Redfish service root or manager resource. Explicit `ilo` or `idrac` values are recommended for production because they make inventory intent auditable.

### 3. Configure cluster variables

Edit `inventories/mycluster/group_vars/all.yml`. Every `CHANGE_ME` value is commented in English and must be reviewed.

### 4. Configure secrets

```bash
cp inventories/mycluster/group_vars/vault.yml.example \
   inventories/mycluster/group_vars/vault.yml
ansible-vault encrypt inventories/mycluster/group_vars/vault.yml
```

The sample inventory references `vault_bmc_passwords`, which allows different BMC credentials per host.

### 5. Validate

```bash
./scripts/preflight.sh inventories/mycluster/hosts.yml
./scripts/validate.sh inventories/mycluster/hosts.yml
```

### 6. Discover BMC inventory only

```bash
ansible-playbook \
  -i inventories/mycluster/hosts.yml \
  --ask-vault-pass \
  playbooks/01-discover-bmc.yml
```

Review:

```text
artifacts/<cluster-name>/raw/bmc-<hostname>.json
artifacts/<cluster-name>/reports/bmc-inventory.md
```

### 7. Test virtual media on one approved non-production host

```bash
ansible-playbook \
  -i inventories/mycluster/hosts.yml \
  --ask-vault-pass \
  --limit master-0 \
  -e test_iso_url=https://images.example.com/test.iso \
  -e bmc_wait_for_node_ssh=false \
  playbooks/03-test-virtual-media.yml
```

### 8. Run the complete installation

```bash
ansible-playbook \
  -i inventories/mycluster/hosts.yml \
  --ask-vault-pass \
  playbooks/site.yml
```

### 9. Eject discovery media after installation

```bash
ansible-playbook \
  -i inventories/mycluster/hosts.yml \
  --ask-vault-pass \
  playbooks/90-eject-media.yml
```

## ISO delivery modes

### `local_http` — recommended for controlled bare-metal networks

The control node downloads the discovery ISO and serves it with a local Podman HTTP container. Configure:

```yaml
iso_delivery_mode: local_http
iso_http_advertise_address: "192.168.50.10"
iso_http_port: 8080
```

The BMC management network must be able to reach that address and port.

### `existing_http`

Use an existing HTTP/HTTPS server:

```yaml
iso_delivery_mode: existing_http
iso_existing_url: "https://images.example.com/ocp/discovery.iso"
```

### `direct_url`

Pass the Assisted Installer image URL directly to the BMC:

```yaml
iso_delivery_mode: direct_url
```

This mode only works when the BMC can resolve, route to, and download from the generated URL.

## BMC compatibility controls

The following variables handle implementation differences without duplicating the playbooks:

```yaml
bmc_type: ilo
bmc_system_id: "1"                  # Optional override; normally auto-discovered
bmc_manager_id: "1"                 # Optional override; normally auto-discovered
bmc_virtual_media_category: Manager  # Manager or Systems
bmc_boot_device: Cd
bmc_validate_certs: true
bmc_ca_path: "/etc/pki/ca-trust/source/anchors/bmc-ca.pem"
```

Set `bmc_validate_certs: false` only for initial lab validation. Production environments should install the BMC issuing CA and enable validation.

## Backward compatibility

The BMC discovery role accepts these legacy Dell variables when the new variables are not defined:

| Legacy variable | New variable |
|---|---|
| `idrac_ip` | `bmc_endpoint` |
| `idrac_user` | `bmc_username` |
| `idrac_password` | `bmc_password` |

New inventories should use the `bmc_*` names. See [docs/migration-from-idrac.md](docs/migration-from-idrac.md).

## Security notes

- Store passwords and Assisted Installer tokens with Ansible Vault or an external secret manager.
- Do not commit pull secrets, kubeconfigs, tokens, or generated artifacts.
- Enable TLS validation and use `bmc_ca_path` in production.
- Restrict the local ISO web server to the installation network.
- Rotate temporary BMC credentials after the installation window.
- Review the generated `artifacts/` directory because it contains sensitive installation state.

## Documentation

- [Workshop guide](WORKSHOP.md)
- [Validation record](VALIDATION.md)
- [Architecture](docs/architecture.md)
- [Variable reference](docs/variable-reference.md)
- [Migration from the iDRAC-only repository](docs/migration-from-idrac.md)
- [Troubleshooting](docs/troubleshooting.md)
- [References](docs/references.md)

## Important validation boundary

The repository includes syntax, structure, and data-normalization tests. Live virtual-media behavior still depends on BMC firmware, licensing, Redfish implementation, network reachability, and ISO protocol support. Validate first with `playbooks/01-discover-bmc.yml`, then use `playbooks/03-test-virtual-media.yml` with `--limit` on one non-production server before running the cluster-wide discovery ISO or installation playbooks.
