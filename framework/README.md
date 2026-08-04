# Framework Core

This directory contains the declarative metadata and orchestration conventions for the OpenShift automation framework.

## Responsibilities

- Define the supported component catalog.
- Describe component dependencies and execution order.
- Keep feature flags separate from implementation logic.
- Provide metadata consumed by Ansible and GitOps workflows.

Runtime logic remains in standard Ansible roles under `roles/`. Kubernetes desired state remains under `gitops/`.
