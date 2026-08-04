# Framework Core Architecture

## Purpose

The framework separates orchestration, implementation, and Kubernetes desired state while preserving the current installer during incremental migration.

## Responsibility boundaries

- `playbooks/` orchestrates workflows and contains minimal business logic.
- `roles/` contains idempotent Ansible implementation logic.
- `framework/` contains component metadata and dependency declarations.
- `gitops/` contains Kubernetes desired state compatible with Kustomize and OpenShift GitOps.
- `inventories/`, `group_vars/`, and `host_vars/` contain environment-specific inputs.
- `tests/` and `molecule/` contain automated validation.
- `reports/` is reserved for generated, non-source execution output.

## Migration policy

1. Existing working playbooks and roles remain operational until replaced.
2. Components are migrated individually in focused pull requests.
3. No secret values are committed to Git.
4. Kubernetes resources must be representable as declarative manifests.
5. Direct-apply mode and GitOps mode must consume the same documented variables.
6. Operator versions and channels must remain configurable and validated against the target OpenShift release.

## Standard role layout

```text
roles/<component>/
├── defaults/main.yml
├── handlers/main.yml
├── meta/main.yml
├── tasks/main.yml
├── templates/
├── files/
├── molecule/default/
└── README.md
```

Optional directories should only be added when used.

## GitOps layout

```text
gitops/
├── bootstrap/
├── operators/
├── platform/
├── day2/
├── applications/
├── policies/
├── clusters/
└── overlays/
```

Components should provide a Kustomize base and environment-specific overlays where appropriate. Argo CD Applications should reference immutable or controlled revisions in production.
