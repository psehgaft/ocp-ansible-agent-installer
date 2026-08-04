# Platform Operator Deployment Guide

This guide documents the supported Ansible and GitOps deployment paths for every component declared in `framework/components.yml`.

## Prerequisites

```bash
ansible-galaxy collection install -r requirements.yml
oc whoami
oc get clusterversion version
```

Use an inventory such as `inventories/sample/hosts.yml`, provide secrets through Ansible Vault or protected environment variables, and validate inputs before deployment:

```bash
python scripts/validate_input_contracts.py
python scripts/validate_architecture_contracts.py
```

## Generic deployment commands

Deploy one component directly:

```bash
ansible-playbook -i inventories/sample/hosts.yml \
  playbooks/install-platform-operator.yml \
  -e component_name=<component> \
  -e deployment_mode=direct
```

Render the same desired state:

```bash
ansible-playbook -i inventories/sample/hosts.yml \
  playbooks/install-platform-operator.yml \
  -e component_name=<component> \
  -e deployment_mode=render \
  -e render_root=rendered
```

Prepare the component for GitOps reconciliation:

```bash
ansible-playbook -i inventories/sample/hosts.yml \
  playbooks/install-platform-operator.yml \
  -e component_name=<component> \
  -e deployment_mode=gitops \
  -e render_root=rendered
```

Deploy all components enabled in the catalog or selected profile:

```bash
ansible-playbook -i inventories/sample/hosts.yml \
  playbooks/install-platform-operators.yml \
  -e deployment_mode=direct
```

## Supported components

| Component key | Product or function | Installation path | Example |
|---|---|---|---|
| `gitops` | Red Hat OpenShift GitOps | OLM | `-e component_name=gitops` |
| `acm` | Advanced Cluster Management | OLM | `-e component_name=acm` |
| `acs` | Advanced Cluster Security | OLM | `-e component_name=acs` |
| `openshift_virtualization` | OpenShift Virtualization | OLM | `-e component_name=openshift_virtualization` |
| `odf` | OpenShift Data Foundation | OLM | `-e component_name=odf` |
| `metallb` | MetalLB Operator | OLM | `-e component_name=metallb` |
| `baremetal_operator` | Cluster Bare Metal configuration | Cluster payload | `-e component_name=baremetal_operator` |
| `cert_manager` | cert-manager Operator | OLM | `-e component_name=cert_manager` |
| `rhoso` | Red Hat OpenStack Services on OpenShift | OLM | `-e component_name=rhoso` |
| `pipelines` | OpenShift Pipelines | OLM | `-e component_name=pipelines` |
| `service_mesh` | OpenShift Service Mesh | OLM | `-e component_name=service_mesh` |
| `logging` | OpenShift Logging | OLM | `-e component_name=logging` |
| `loki` | Loki Operator | OLM | `-e component_name=loki` |
| `observability` | Cluster Observability Operator | OLM | `-e component_name=observability` |
| `openshift_ai` | Red Hat OpenShift AI | OLM | `-e component_name=openshift_ai` |
| `mta` | Migration Toolkit for Applications | OLM | `-e component_name=mta` |
| `mtv` | Migration Toolkit for Virtualization | OLM | `-e component_name=mtv` |
| `sriov` | SR-IOV Network Operator | OLM | `-e component_name=sriov` |
| `nmstate` | Kubernetes NMState Operator | OLM | `-e component_name=nmstate` |
| `ptp` | PTP Operator | OLM | `-e component_name=ptp` |
| `compliance` | Compliance Operator | OLM | `-e component_name=compliance` |
| `external_secrets` | External Secrets Operator | OLM | `-e component_name=external_secrets` |
| `quay` | Red Hat Quay | OLM | `-e component_name=quay` |

The catalog is authoritative. Run the following to print the exact current keys:

```bash
python - <<'PY'
import yaml
for name in yaml.safe_load(open('framework/components.yml'))['components']:
    print(name)
PY
```

## Examples

### OpenShift GitOps

```bash
ansible-playbook -i inventories/sample/hosts.yml \
  playbooks/install-platform-operator.yml \
  -e component_name=gitops \
  -e deployment_mode=direct

oc get subscription,csv -n openshift-gitops-operator
oc get pods -n openshift-gitops
```

### ACM with dependencies

ACM declares GitOps as a dependency. Deploy the selected dependency graph with the multi-component playbook or enable both components in a profile.

```bash
ansible-playbook -i inventories/sample/hosts.yml \
  playbooks/install-platform-operators.yml \
  -e deployment_mode=direct \
  -e selected_components='["gitops", "acm"]'

oc get multiclusterhub -A
```

### ODF through GitOps

```bash
ansible-playbook -i inventories/sample/hosts.yml \
  playbooks/install-platform-operator.yml \
  -e component_name=odf \
  -e deployment_mode=gitops \
  -e render_root=rendered

kustomize build gitops/operators/odf
```

Commit the generated or canonical manifests to the configured Git repository and allow Argo CD to reconcile them.

### RHOSO

```bash
ansible-playbook -i inventories/sample/hosts.yml \
  playbooks/install-platform-operators.yml \
  -e deployment_mode=direct \
  -e selected_components='["cert_manager", "nmstate", "rhoso"]'
```

After the operator is ready, run the RHOSO operand and network playbooks documented in the repository.

## Validation and rollback

Before deployment:

```bash
python scripts/validate_input_contracts.py
python scripts/validate_kustomize.py
ansible-playbook -i inventories/sample/hosts.yml playbooks/install-platform-operator.yml --syntax-check
```

After deployment, use the component validation hooks and generated reports under `reports/output/`. For GitOps rollback, revert the Git commit. For direct mode, change the declared catalog/profile state and rerun the playbook; do not manually edit OLM resources unless performing documented break-glass recovery.
