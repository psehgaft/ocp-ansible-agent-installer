# Day-2 Implementation Catalog

This catalog maps the complete Day-2 scope to canonical repository playbooks. The list is additive: existing networking, storage, registry, virtualization, RHOSO, NTP, PTP, SR-IOV, NMState, MetalLB, MachineConfig, certificate audit, upgrade prechecks, reports, and other workflows remain supported.

## Health and evidence

| Capability | Canonical playbook | Notes |
|---|---|---|
| Cluster health | `playbooks/day2/cluster-health.yml` | Runs general health and focused etcd health workflows. |
| etcd backup | `playbooks/day2/etcd-backup.yml` | Requires `etcd_backup_confirm=true`; writes on one control-plane node and must be copied off-node. |
| must-gather | `playbooks/day2/must-gather.yml` | Supports standard and optional operator-specific images. |

## Certificates and identity

| Capability | Canonical playbook |
|---|---|
| API and Ingress certificates | `playbooks/day2/install_certs.yml` |
| Certificate audit | `playbooks/day2/certificate-audit.yml` |
| Trusted CA | `playbooks/day2/trusted-ca.yml` |
| cert-manager operands | `playbooks/day2/cert-manager.yml` |
| cluster-admin RBAC | `playbooks/day2/cluster-admin-rbac.yml` |
| LDAP / IDP | `playbooks/day2/ldap.yml` |
| HTPasswd | `playbooks/day2/htpasswd.yml` |
| OAuth reconciliation | `playbooks/day2/oauth.yml` |
| LDAP group/user sync | `playbooks/day2/ldap-group-sync.yml` |

Never grant `cluster-admin` through an implicit default. Define reviewed user or group subjects and retain a break-glass account until authentication changes are proven.

## Storage and backup

| Capability | Canonical playbook |
|---|---|
| ODF operator and operands | `playbooks/day2/storage.yml`, `playbooks/day2/odf-day2.yml` |
| Vendor CSI drivers | `playbooks/day2/platform-csi-drivers.yml` |
| StorageClasses | `playbooks/day2/storageclasses.yml` |
| Volume snapshots | `playbooks/day2/volume-snapshots.yml` |
| OADP operator and backups | `playbooks/day2/platform-oadp.yml`, `playbooks/day2/oadp.yml`, `playbooks/day2/backup-oadp.yml` |

## Nodes and capacity

| Capability | Canonical playbook |
|---|---|
| Node labels | `playbooks/day2/node-labels.yml` |
| Bare Metal Operator and BMH | `playbooks/day2/platform-baremetal.yml` |
| Static BMH and NNCP networking | `playbooks/day2/acm-bmh-static-networking.yml` |
| Node and MachineConfig changes | `playbooks/day2/node-configuration.yml`, `playbooks/day2/machineconfig.yml` |

## Monitoring and logging

`playbooks/day2/platform-observability-stack.yml` orchestrates the existing focused workflows:

- `monitoring.yml` for `cluster-monitoring-config`, Prometheus and Thanos PVC settings, retention, placement, rules, and monitors.
- `user-workload-monitoring.yml` for `enableUserWorkload: true` and user-workload configuration.
- `alertmanager.yml` for routing, receivers, inhibition, and protected credentials.
- `loki.yml` for LokiStack and object-storage integration.
- `logging.yml` for ClusterLogForwarder, inputs, outputs, pipelines, and collectors.

The operator lifecycle remains available through `platform-monitoring.yml` and `platform-logging.yml`.

## Security and compliance

| Capability | Canonical playbook | Required input |
|---|---|---|
| Compliance Operator | `playbooks/day2/compliance.yml` | `compliance_resources` containing reviewed OLM and ScanSettingBinding/TailoredProfile resources. |
| File Integrity Operator | `playbooks/day2/file-integrity.yml` | `file_integrity_resources` containing reviewed OLM and FileIntegrity resources. |
| ACS policies | `playbooks/day2/acs-policies.yml` | `acs_policy_resources`. |

Operator package channels vary by OpenShift release and mirrored catalog. The security playbooks intentionally require explicit resource lists instead of embedding a stale channel.

## Multicluster operations

| Capability | Canonical playbook | Notes |
|---|---|---|
| ACM hub | `playbooks/day2/acm-hub.yml` | Hub operands and policies. |
| Multicluster observability | `playbooks/day2/multicluster-observability.yml` | Provide storage Secret references and a `MultiClusterObservability` CR through `multicluster_observability_resources`. |
| GitOps operator and applications | `playbooks/day2/gitops-application-lifecycle.yml` | Installs OpenShift GitOps and applies AppProject/Application/ApplicationSet resources. |
| GitOps bootstrap | `playbooks/gitops-foundation.yml` | Renders or reconciles the repository structure. |
| Submariner | `playbooks/day2/submariner.yml` | Provide ManagedClusterAddOn, SubmarinerConfig, Broker and placement resources through `submariner_resources`. |

A remote Git repository must exist before push unless a provider-specific API workflow is supplied. The framework initializes and reconciles desired state but does not invent GitHub, GitLab, Bitbucket, or internal forge credentials.

For Submariner, open external firewalls before deployment: UDP 500 and 4500 for IPsec, or UDP 51820 for WireGuard, plus all product-required broker, API, and gateway traffic. These are network-infrastructure changes and are not silently modified by Kubernetes automation. Validate MTU, non-overlapping CIDRs, gateway labels, NAT, and routing before enabling the add-on.

## Recommended execution order

1. Run cluster health and create an etcd backup.
2. Capture a must-gather baseline.
3. Configure certificates, identity, group synchronization, and reviewed RBAC.
4. Establish storage, snapshots, and OADP recovery.
5. Apply node labels, capacity, BareMetalHost, and MachineConfig changes in controlled waves.
6. Configure monitoring, logging, Alertmanager, PVCs, and forwarding.
7. Install compliance, file-integrity, and ACS controls.
8. Configure ACM observability, GitOps application lifecycle, Submariner, placements, and policies.
9. Repeat health checks and capture evidence.
