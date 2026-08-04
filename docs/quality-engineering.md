# Quality Engineering

The repository uses four CI classes:

1. **Static validation** runs on every pull request and push to `main`.
2. **Cluster integration** runs only through `workflow_dispatch` with protected cluster credentials.
3. **Destructive testing** requires a protected GitHub environment and the exact approval phrase `APPROVE-DESTRUCTIVE`.
4. **Compatibility validation** runs weekly and validates supported OpenShift/profile combinations.

## Static quality gates

- YAML parsing and `yamllint`
- `ansible-lint`
- Python compilation and Ruff
- pytest
- inventory parsing
- Ansible syntax checks
- Molecule scenarios when present
- Shellcheck and actionlint
- Kustomize builds
- Helm lint/template
- kubeconform validation, including Argo CD resources with missing external CRD schemas allowed
- Gitleaks secret scanning
- Antora workshop build
- documentation link validation

## Cluster credentials

Cluster credentials must be stored as the protected `KUBECONFIG_B64` GitHub environment secret. They must never be committed to the repository or printed in workflow logs.

## Merge policy

The static workflow is intended to become a required branch protection check. Integration and destructive workflows are operational qualification gates rather than default pull-request checks.
