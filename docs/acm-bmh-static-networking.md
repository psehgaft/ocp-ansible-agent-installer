# ACM BareMetalHost Static Networking with LACP

This workflow generates separate manifests for two lifecycle phases:

- **Day 0 on the ACM hub:** one NMState `Secret` and, optionally, one `BareMetalHost` per physical node.
- **Day 2 on the managed cluster:** one hostname-scoped `NodeNetworkConfigurationPolicy` per node.

The design prevents a shared static IP policy from being applied to multiple nodes and keeps hub and managed-cluster credentials separate.

## Prerequisites

- ACM, Assisted Installer/Metal3, and the Bare Metal Operator are available on the hub.
- NMState is installed and healthy on the managed cluster.
- Each switch-side LAG is configured for IEEE 802.3ad/LACP before activating the bond.
- Interface names, boot MACs, BMC endpoints, IP addresses, gateways, DNS servers, and hostnames are verified.
- BMC credential Secrets already exist in each BMH namespace.

## Variables

Copy and edit:

```text
inventories/examples/group_vars/all/acm-bmh-static-networking.yml
```

Each item in `acm_bmh_nodes` must define:

- `name` and hub `namespace`
- managed-cluster `hostname`
- `boot_mac`, `bmc_address`, and `bmc_credentials_name`
- at least two `bond_interfaces`
- unique `ip_address`, `prefix_length`, `gateway`, and `dns_servers`

Optional per-node values include `network_data_secret_name`, `nncp_name`, `bond_name`, `bridge_name`, labels, online state, and BMC certificate verification behavior.

## Render manifests

```bash
ansible-playbook \
  -i inventories/examples/hosts.yml \
  playbooks/day2/acm-bmh-static-networking.yml \
  -e @inventories/examples/group_vars/all/acm-bmh-static-networking.yml
```

Generated files:

```text
rendered/acm-bmh-static-networking/hub/day0/resources.yml
rendered/acm-bmh-static-networking/managed/day2/resources.yml
```

Review both files before application.

## Apply to the correct clusters

```bash
export HUB_KUBECONFIG=$HOME/.kube/hub-config
export MANAGED_KUBECONFIG=$HOME/.kube/managed-config

ansible-playbook \
  playbooks/day2/acm-bmh-static-networking.yml \
  -e @inventories/examples/group_vars/all/acm-bmh-static-networking.yml \
  -e acm_bmh_networking_mode=apply \
  -e acm_bmh_apply_day0=true \
  -e acm_bmh_apply_day2=true
```

For initial provisioning, apply Day 0 first. Apply Day 2 only after the node has joined the managed cluster and its `kubernetes.io/hostname` label matches the configured hostname.

## Validation

Hub cluster:

```bash
oc --kubeconfig "$HUB_KUBECONFIG" -n my-cluster-namespace get secret,bmh
oc --kubeconfig "$HUB_KUBECONFIG" -n my-cluster-namespace describe bmh worker-1
```

Managed cluster:

```bash
oc --kubeconfig "$MANAGED_KUBECONFIG" get nncp
oc --kubeconfig "$MANAGED_KUBECONFIG" get nnce
oc --kubeconfig "$MANAGED_KUBECONFIG" get nodes -L kubernetes.io/hostname
oc --kubeconfig "$MANAGED_KUBECONFIG" debug node/worker-1.example.com -- chroot /host nmstatectl show
```

Do not activate an NNCP remotely until switch LACP configuration, console access, and rollback procedures are confirmed. A wrong interface name, VLAN assumption, gateway, or LACP configuration can disconnect the node.
