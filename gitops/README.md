# GitOps Desired State

This tree is the GitOps-compatible source of desired state for OpenShift platform services.

## Layout

- `bootstrap/`: Argo CD bootstrap resources.
- `operators/`: operator installation resources.
- `platform/`: platform configuration created after operator installation.
- `day2/`: operational configuration such as identity, certificates, registry, monitoring, and backup.
- `applications/`: Argo CD Application and ApplicationSet definitions.
- `policies/`: ACM governance resources.
- `clusters/`: cluster-specific composition and references.
- `overlays/`: environment and cluster overlays.

Each component should use Kustomize-compatible manifests and avoid embedding credentials. Secrets must be supplied through an approved secret-management workflow.
