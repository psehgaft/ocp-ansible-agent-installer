# OpenShift Bare Metal Install via Assisted Installer + Dell iDRAC (Ansible)

> Canonical guides: [Day-0 bare-metal installation](day0-bare-metal-installation.md),
> [Day-2 GitOps operator deployment](day2-gitops-operator-deployment.md), and
> [Task 3 graphical runner backlog](task3-gui-backlog.md).

## What this does
This project provisions an OpenShift cluster on Dell bare-metal servers by:
1. Discovering server MAC/disk inventory via iDRAC (Redfish).
2. Creating an Assisted Installer cluster + InfraEnv via the Assisted Installer API.
3. Generating a Discovery ISO and attaching it as iDRAC virtual media.
4. Waiting for hosts to register, assigning roles/hostnames, and triggering installation.
5. Downloading `kubeconfig` and `kubeadmin-password` locally.
6. Writing a structured installation report and exporting raw API data.

## Prerequisites (external)
You must provide the typical Bare Metal prerequisites: DNS, VIP reachability, and an external load balancer for API/Ingress (or an equivalent design). See the OCP bare metal IPI overview for the networking assumptions. 

## Prerequisites (control node)
- Ansible >= 2.15
- Python >= 3.9
- Collections:
  - `community.general`
  - `dellemc.openmanage`

Install collections:
```bash
ansible-galaxy collection install -r requirements.yml
```

### The Assisted Installer is supported on the following CPU architectures:

- x86_64
- arm64
- ppc64le (IBM Power®)
- s390x (IBM Z®)

### Example DNS configuration

```bash
$TTL 1W
@	IN	SOA	ns1.example.com.	root (
			2019070700	; serial
			3H		; refresh (3 hours)
			30M		; retry (30 minutes)
			2W		; expiry (2 weeks)
			1W )		; minimum (1 week)
	IN	NS	ns1.example.com.
	IN	MX 10	smtp.example.com.
;
;
ns1.example.com.		IN	A	192.168.1.1
smtp.example.com.		IN	A	192.168.1.5
;
helper.example.com.		IN	A	192.168.1.5
;
api.ocp4.example.com.		IN	A	192.168.1.5
api-int.ocp4.example.com.	IN	A	192.168.1.5
;
*.apps.ocp4.example.com.	IN	A	192.168.1.5
;
control-plane0.ocp4.example.com.	IN	A	192.168.1.97
control-plane1.ocp4.example.com.	IN	A	192.168.1.98
control-plane2.ocp4.example.com.	IN	A	192.168.1.99
;
worker0.ocp4.example.com.	IN	A	192.168.1.11
worker1.ocp4.example.com.	IN	A	192.168.1.7

```

## Secrets
Store secrets with Ansible Vault:
- `idrac_password`
- `assisted_offline_token` (SaaS) or `assisted_access_token` (on-prem)
- `pull-secret.json`

## Inventory layout
- `inventories/sample/hosts.yml` contains:
  - iDRAC IPs (required)
  - cluster variables
  - file paths for pull-secret and SSH key
- `inventories/sample/host_vars/*` contain per-node static networking (IP/gw/DNS) and role.

> The inventory avoids including MAC addresses because those are pulled from iDRAC at runtime.


## Configure inventory
1. Copy the sample:
```bash
cp -a inventories/sample inventories/mycluster
```
2. Edit `inventories/mycluster/hosts.yml` and `host_vars/*.yml`.
3. Place your pull-secret and SSH key files under `./secrets/`.

## Run
```bash
ANSIBLE_CONFIG=ansible.cfg \
ansible-playbook -i inventories/mycluster/hosts.yml playbooks/install.yml
```

## Outputs
Artifacts are written under `./artifacts` by default:
- `./artifacts/auth/kubeconfig`
- `./artifacts/auth/kubeadmin-password`
- `./artifacts/reports/install-report.md`
- raw iDRAC and API responses under `./artifacts/raw/`

## Troubleshooting
- If hosts do not appear: confirm iDRAC virtual media works and the Discovery ISO is reachable from the server network.
- If installation fails: inspect `./artifacts/raw/events.json` and `cluster-final.json`.
- If using SaaS tokens: access tokens are short-lived; the playbook refreshes using the offline token.


# OpenShift 4.18 — Operator Installation Automation (Ansible Roles)

## What this is
A role-based Ansible project to install, via OLM:
- **Kubernetes NMState Operator**
- **MetalLB Operator**
- **cert-manager Operator for Red Hat OpenShift**
- **OpenStack Operator (RHOSO)**

Each operator is a separate role under `roles/<operator>/` and invoked from:
- `playbooks/install-operators.yml`

The automation follows the standard Operator Lifecycle Manager pattern:
**Namespace → OperatorGroup → Subscription → wait for CSV Succeeded → (optional) create operand CR**.

## Prerequisites
- `oc` CLI installed on the Ansible control node.
- A `kubeconfig` with `cluster-admin` privileges (kubeadmin is fine).
- The OperatorHub catalog source configured:
  - Connected: `redhat-operators` in `openshift-marketplace`
  - Disconnected: your mirrored `CatalogSource` (set `operator_source`/`operator_source_namespace`)

## Quick start
1) Install optional collections:
```bash
ansible-galaxy collection install -r requirements.yml
```
2) Put your kubeconfig at `./artifacts/auth/kubeconfig` (or set `kubeconfig_path` in `inventories/sample/hosts.yml`).

3) Run:
```bash
ansible-playbook -i inventories/sample/hosts.yml playbooks/install-operators.yml
```

## What each role does
### `roles/nmstate_operator`
- Installs `kubernetes-nmstate-operator` into `openshift-nmstate`
- Optionally creates `NMState/nmstate`

### `roles/metallb_operator`
- Installs `metallb-operator` into `metallb-system`
- Optionally creates `MetalLB/metallb`
- You still must create `IPAddressPool` + `L2Advertisement` (or BGP) after operator install.

### `roles/cert_manager_operator`
- Installs `openshift-cert-manager-operator` into `cert-manager-operator`
- Uses an **AllNamespaces** OperatorGroup (`targetNamespaces: []`)
- Optionally creates `CertManager/cluster` (operand components appear in `cert-manager` namespace)

### `roles/openstack_operator`
- Installs `openstack-operator` into `openstack-operators`
- Optional creation of `OpenStack/openstack` is disabled by default (`create_openstack_cr: false`) because RHOSO typically needs additional prerequisites.

## Variables (inventory)
See `inventories/sample/hosts.yml` for:
- `kubeconfig_path`, `oc_bin`
- `operator_source`, `operator_source_namespace`
- `*_channel` and `create_*_cr` toggles

# RHOSO Ansible – Bootstrap (openstack project + labels + osp-secret)

This repository provides an **idempotent** Ansible workflow to bootstrap the RHOSO namespace and create the
required `osp-secret` Secret for RHOSO service pods.

What it does:
- Creates the `openstack` project (`oc new-project openstack`) if it does not exist.
- Applies mandatory namespace labels for privileged pod creation by OpenStack Operators:
  - `pod-security.kubernetes.io/enforce=privileged`
  - `security.openshift.io/scc.podSecurityLabelSync=false`
- Renders and applies `osp-secret` as a Kubernetes `Secret` (type `Opaque`) using values provided in inventory.

## Prerequisites

On the machine where you run Ansible:
- `ansible` installed.
- `oc` CLI installed and able to reach the cluster.
- A valid kubeconfig (set `rhoso_kubeconfig` in inventory or export `KUBECONFIG`).

If you set `rhoso_generate_missing_secrets: true` **and** omit `BarbicanSimpleCryptoKEK`,
install `python3-cryptography` because the role generates a Fernet key using Python.

> **Operational warning:** RHOSO docs indicate service passwords in `osp-secret` should not be changed after the control plane is deployed because it can cause outages (keystone mismatch). Plan your secret values up-front and treat them as immutable post-deploy.

## Project layout

```text
rhoso-ansible/
├─ ansible.cfg
├─ inventory/
│  └─ hosts.yml
├─ group_vars/
│  └─ all.yml               # example variables (store real values in Vault)
├─ playbooks/
│  └─ configure-rhoso.yml
└─ roles/
   └─ rhoso_openstack_bootstrap/
      ├─ tasks/main.yml
      └─ templates/osp-secret.yaml.j2
```

## Configure inventory

1) Edit `inventory/hosts.yml`:
- Set `rhoso_kubeconfig` to the correct path.

2) Edit `group_vars/all.yml`:
- Replace all `CHANGE_ME_*` placeholders with **real values**.
- Recommended: store `group_vars/all.yml` in **Ansible Vault**.

Password requirements (as implemented by default):
- `HeatAuthEncryptionKey` is enforced to be **exactly 32 characters**.
- All other `*Password` and `OctaviaHeartbeatKey` are enforced to be **32 characters** when
  `rhoso_enforce_32char_passwords: true`.

## Run

```bash
cd rhoso-ansible
ansible-playbook -i inventory/hosts.yml playbooks/configure-rhoso-bootstrap.yml
```

## Outputs

- Rendered manifests are written to `./rendered/` (mode `0700` directory, `0600` files).
- `osp-secret` is applied to the `openstack` namespace.


## Base64 handling

By default, provide **plaintext** values in `rhoso_osp_secret` and the template will base64-encode them into `Secret.data`.

If your inventory already contains base64-encoded values, set:

```yaml
rhoso_osp_secret_values_are_base64: true

## Step-by-step: Bootstrap RHOSO namespace and osp-secret with Ansible

### Prepare access

1. Copy kubeconfig for the target OpenShift cluster (admin or delegated user with permissions).
2. Verify `oc` access:

```bash
export KUBECONFIG=/path/to/kubeconfig
oc whoami
oc get nodes
```

### Configure secrets (recommended: Ansible Vault)

Edit `group_vars/all.yml` and set the values under `rhoso_osp_secret`.
For production, encrypt it:

```bash
ansible-vault encrypt group_vars/all.yml
```

### Run the playbook

```bash
ansible-playbook -i inventory/hosts.yml playbooks/configure-rhoso.yml
```

### Verify results

```bash
oc get project openstack
oc get namespace openstack -o jsonpath='{.metadata.labels}'; echo
oc get secret osp-secret -n openstack
```

Expected labels include:
- `pod-security.kubernetes.io/enforce=privileged`
- `security.openshift.io/scc.podSecurityLabelSync=false`

### Notes

- If you need to use `oc project openstack` interactively to avoid specifying `-n openstack`, do it in your shell.
- Treat `osp-secret` values as immutable after control plane deployment to avoid service outages due to keystone mismatch.

# RHOSO Ansible – Networking (NMState NNCP + Multus NAD + MetalLB VIPs)

This project configures RHOSO networking using the documented approach:

1. Prepare OpenShift worker nodes with isolated network interfaces using **Kubernetes NMState**
   (`NodeNetworkConfigurationPolicy`).
2. Attach RHOSO service pods to isolated networks using **Multus**
   (`NetworkAttachmentDefinition`) with **Whereabouts** IPAM.
3. Prepare VIPs on isolated networks using **MetalLB** (`IPAddressPool`, `L2Advertisement`).
4. If the cluster uses **OVN-Kubernetes**, optionally enable
   `gatewayConfig.ipForwarding=Global` so MetalLB can operate on a secondary interface.

## Guardrails: `TBD!`

Per your requirement, any missing IP/network value is set to `TBD!` in `group_vars/all.yml`.
By default, `rhoso_fail_on_tbd: true` will stop execution until you replace all `TBD!`.

Typical items you must set:
- `ocp_worker_node_ips.<node>.<network>` (host IP addresses for VLAN interfaces)
- `metallb_pool_start` / `metallb_pool_end` for each VIP-enabled network (must not overlap with Whereabouts or NetConfig allocation ranges)
- Optional networks (octavia/designate/designateext) if you enable them

## Run

```bash
cd rhoso-ansible-network
ansible-playbook -i inventory/hosts.yml playbooks/configure-rhoso-network.yml
```

### Run only one phase (tags)

```bash
ansible-playbook -i inventory/hosts.yml playbooks/configure-rhoso-network.yml --tags nmstate
ansible-playbook -i inventory/hosts.yml playbooks/configure-rhoso-network.yml --tags nad
ansible-playbook -i inventory/hosts.yml playbooks/configure-rhoso-network.yml --tags metallb
ansible-playbook -i inventory/hosts.yml playbooks/configure-rhoso-network.yml --tags ovn

## Step-by-step: Configure RHOSO networking with Ansible

### Prerequisites

- You can run `oc` against the target cluster (admin or delegated permissions).
- Operators/CRDs already installed:
  - Kubernetes NMState (NNCP)
  - Multus + Whereabouts (NAD + IPAM)
  - MetalLB (IPAddressPool/L2Advertisement) if you plan to use VIPs

### Fill inventory variables

Edit:
- `inventory/hosts.yml` (kubeconfig path)
- `group_vars/all.yml` (network definition + per-node IPs)

Replace every `TBD!` value. The playbook fails by default if any `TBD!` remains.

### Run

```bash
ansible-playbook -i inventory/hosts.yml playbooks/configure-rhoso-network.yml
```

### Validate

#### NNCP

```bash
oc get nncp
oc get nnce
```

#### NADs

```bash
oc get net-attach-def -n openstack
```

#### MetalLB

```bash
oc get -n metallb-system ipaddresspool
oc get -n metallb-system l2advertisement
```

#### OVN forwarding (if used)

```bash
oc get network.operator cluster -o jsonpath='{.spec.defaultNetwork.type}'; echo
oc get network.operator cluster -o jsonpath='{.spec.defaultNetwork.ovnKubernetesConfig.gatewayConfig.ipForwarding}'; echo

# Troubleshoting


oc adm must-gather --dir=/tmp/mg-all
oc adm must-gather -- /usr/bin/gather_network_logs --dir=/tmp/mg-net
oc adm must-gather -- /usr/bin/gather_network_logs

oc get network.config.openshift.io cluster -o yaml > network-cluster.yaml
oc get co network -o yaml > co-network.yaml
oc get ingresscontroller -n openshift-ingress-operator -o yaml > ingress.yaml

oc get network.config.openshift.io cluster -o yaml > 01-network-cluster.yaml
oc get scheduler.config.openshift.io cluster -o yaml > 02-scheduler.yaml
oc get ingresscontroller -n openshift-ingress-operator -o yaml > 03-ingress.yaml
oc get dns.config.openshift.io cluster -o yaml > 04-dns.yaml
oc get infrastructures.config.openshift.io cluster -o yaml > 05-infrastructure.yaml
oc get featuregate.config.openshift.io cluster -o yaml > 06-featuregate.yaml
oc get proxy.config.openshift.io cluster -o yaml > 07-proxy.yaml

oc get co -o yaml > clusteroperators-all.yaml
oc get subscription -A -o yaml > subscriptions-all.yaml
oc get installplan -A -o yaml > installplans-all.yaml
oc get clusterserviceversion -A -o yaml > csvs-all.yaml

oc get networkpolicy -A -o yaml > networkpolicies-all.yaml
oc get egressnetworkpolicy -A -o yaml > egressnetworkpolicies.yaml
oc get egressfirewall -A -o yaml > egressfirewalls.yaml
oc get egressip -A -o yaml > egressips.yaml
oc get networkattachmentdefinitions -A -o yaml > multus-nad.yaml

oc get nodes -o yaml > nodes.yaml
oc get machine -A -o yaml > machines.yaml
oc get machineconfigpool -o yaml > mcp.yaml
oc get machineconfig -o yaml > machineconfigs.yaml

oc adm must-gather --dest-dir=/tmp/captures-net --source-dir='/tmp/tcpdump/' --image=registry.redhat.io/openshift4/network-tools-rhel8:latest --node-selector='node-role.kubernetes.io/worker' --host-network=true --timeout=60s -- tcpdump -i any -c 5000 -w /tmp/tcpdump/capture.pcap

ovs from node: 
oc get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | while read node; do
  echo "===== NODO: $node ====="
  oc debug node/"$node" -- chroot /host bash -c "ip a && ip r && ovs-vsctl show && ovs-ofctl dump-flows br-int" 2>&1
  echo ""
done

# References

- [Openshift Istaller SWAGER](https://api.openshift.com/?urls.primaryName=assisted-service%20service&extIdCarryOver=true&sc_cid=RHCTG0180000371695#/installer)
- [Installing OpenShift Container Platform with the Assisted Installer](https://docs.redhat.com/en/documentation/assisted_installer_for_openshift_container_platform/2026/html-single/installing_openshift_container_platform_with_the_assisted_installer/index#getting-cluster-validations-by-using-rest-api_preinstallation-validations)
