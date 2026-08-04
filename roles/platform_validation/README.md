# platform_validation

Common preflight validation for framework playbooks.

## Validates

- Supported deployment mode.
- Supported OpenShift minor version.
- Runtime feature-map type.
- Optional kubeconfig existence before cluster-changing tasks.

This role must run before component roles mutate the cluster.
