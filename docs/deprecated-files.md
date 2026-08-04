# Workflow Lifecycle and Retired Files

Workflow lifecycle is authoritative in `framework/workflows.yml` and enforced by `scripts/validate_architecture_contracts.py`.

## Retired compatibility entry points

The following compatibility wrappers have been removed. CI fails if any path is reintroduced.

| Retired path | Canonical replacement |
|---|---|
| `playbooks/01-discover-bmc.yml` | `playbooks/day0/discover-bmc.yml` |
| `playbooks/site.yml` | `playbooks/day0/install.yml` |
| `playbooks/test-preflight.yml` | `playbooks/00-preflight.yml` |

The root-level `audit_vmware_network.yml` was previously retired and replaced by `playbooks/audit_vmware_network.yml`.

## Supported operational workflows

These workflows are not legacy and must not be deleted merely because they are specialized:

| Workflow | Purpose |
|---|---|
| `playbooks/00-preflight.yml` | Canonical Day-0 prerequisite validation. |
| `playbooks/day0/discover-bmc.yml` | Canonical generic Redfish discovery. |
| `playbooks/day0/install.yml` | Canonical Assisted Installer orchestration. |
| `playbooks/02-boot-discovery-iso.yml` | Controlled discovery ISO creation and boot workflow. |
| `playbooks/03-test-virtual-media.yml` | Single-host non-production Redfish virtual-media validation. |
| `playbooks/90-eject-media.yml` | Explicit virtual-media cleanup and recovery. |

## Retained source material

The following content is retained as architecture and migration evidence, not as executable compatibility code:

- `workshop/documentation/modules/ROOT/`
- `workshop/WORKSHOP.md`
- `docs/migration-from-idrac.md`

## Enforcement

The workflow lifecycle validator requires that:

1. Every supported workflow exists.
2. Every supported workflow has a unique canonical path.
3. Every retired path is absent.
4. Each retired path declares its canonical replacement.
5. Assisted Installer regression tests reference only canonical Day-0 paths.

A pull request that reintroduces a retired wrapper or removes a supported recovery workflow fails static CI.
