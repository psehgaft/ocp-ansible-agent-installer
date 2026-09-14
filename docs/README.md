# OpenShift Automation Framework Documentation

This directory is the executive documentation index for the framework. Start
with the deployment map, choose one installation interface, and initialize
GitOps only after the new cluster is healthy.

## 1. Deployment with playbooks

| Procedure | Purpose | Canonical entry point |
|---|---|---|
| 1.1 Connected OpenShift | Install from Red Hat registries | `playbooks/day0/install.yml` |
| 1.2 Disconnected OpenShift | Mirror with `oc-mirror` v2, then install | `playbooks/day0/prepare-mirror.yml`, `playbooks/day0/install.yml` |
| 1.3 Day-2 activities | Validate and operate an installed cluster | `playbooks/day2/*.yml` |
| 1.4 GitOps initialization | Render, publish, and bootstrap OpenShift GitOps | `playbooks/day2/render-gitops.yml`, `playbooks/day2/bootstrap-gitops.yml` |

- [Executive deployment runbook](deployment-scenarios.md)
- [Day-0 bare-metal installation](day0-bare-metal-installation.md)
- [Complete variable reference](variable-reference.md)
- [Day-2 implementation catalog](day2-implementation-catalog.md)
- [Identity, PKI, and registry operations](day2-identity-pki-registry.md)
- [ACM BareMetalHost static networking](acm-bmh-static-networking.md)
- [GitOps foundation](gitops-foundation.md)

## 2. Deployment with the GUI interface

| Procedure | Purpose | GUI action |
|---|---|---|
| 2.1 Connected OpenShift | Configure and install a connected cluster | **Validate**, **Preflight**, **Discover**, **Boot**, **Install** |
| 2.2 Disconnected OpenShift | Render/mirror content and install offline | **Prepare release mirror**, then the installation actions |
| 2.3 Day-2 activities | Configure and preview desired state | **Render Day-2 GitOps** |
| 2.4 GitOps initialization | Publish approved state and initialize reconciliation | **Publish and bootstrap GitOps** |

- [GUI interface operations and security](gui-interface.md)
- [Executive deployment runbook](deployment-scenarios.md)

The GUI reads defaults from the same inventory YAML used by the playbooks. It
does not maintain an independent variable model.

## 3. Operators

Operator lifecycle is GitOps-first. Ansible resolves dependencies and renders
desired state; Argo CD installs operators and reconciles their operand custom
resources.

- [GitOps operator deployment and configuration](day2-gitops-operator-deployment.md)
- [Operator catalog](platform-operator-catalog.md)
- [Operator reference](platform-operators.md)

The older direct-deployment guide is retained only for controlled break-glass
or non-GitOps environments: [Direct operator deployment](operator-deployment-guide.md).

## Architecture, security, and operations

- [Architecture](architecture.md)
- [Secret handling](security/secret-handling.md)
- [Quality engineering](quality-engineering.md)
- [Reporting and validation hooks](reporting-validation-hooks.md)
- [Troubleshooting](troubleshooting.md)
- [Authoritative references](references.md)
- [Repository lifecycle and retired files](deprecated-files.md)

## Workshop

The [workshop entry point](../WORKSHOP.md) and its Antora navigation use the
same three-part structure and the same production commands as these runbooks.
See [workshop publication](workshop-deployment.md) for GitHub Pages and
OpenShift hosting procedures.
