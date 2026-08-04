# Platform Operator Catalog

The platform operator catalog is the source of lifecycle metadata for supported OpenShift operators.

## Separation of concerns

Operator roles install or validate the operator only. Operand roles configure custom resources after the operator is ready.

Examples:

- `acm_operator` installs Advanced Cluster Management.
- `acm_hub` creates `MultiClusterHub`.
- `acm_observability` creates `MultiClusterObservability`.
- `acm_governance` manages policies and policy sets.

## Deployment modes

- `direct`: apply OLM resources with `kubernetes.core.k8s` and wait for the installed CSV.
- `render`: render manifests without applying them.
- `gitops`: render manifests into the GitOps working tree for Argo CD reconciliation.

## Usage

```bash
ansible-playbook playbooks/install-platform-operator.yml \
  -e operator_lifecycle_component=acm \
  -e operator_lifecycle_deployment_mode=direct
```

Render-only example:

```bash
ansible-playbook playbooks/install-platform-operator.yml \
  -e operator_lifecycle_component=cert_manager \
  -e operator_lifecycle_deployment_mode=render
```

## Catalog rules

Every operator entry declares its display name, category, role, namespace, installation type, dependencies, supported OpenShift versions, deployment modes, validation hooks, and GitOps path/sync wave. OLM-based entries additionally declare package, channel, catalog source, and catalog namespace.

Channels are explicit defaults and must be reviewed against the target OpenShift release and mirrored catalog before production deployment.
