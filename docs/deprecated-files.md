# Workflow Lifecycle and Retired Files

Workflow lifecycle is authoritative in `framework/workflows.yml` and enforced by `scripts/validate_architecture_contracts.py`.

## Retired compatibility entry points

The following compatibility wrappers have been removed. CI fails if any path is reintroduced.

| Retired path | Canonical replacement |
|---|---|
| `playbooks/01-discover-bmc.yml` | `playbooks/day0/discover-bmc.yml` |
| `playbooks/site.yml` | `playbooks/day0/install.yml` |
| `playbooks/test-preflight.yml` | `playbooks/00-preflight.yml` |
| `hosts_lexample.yml` | `inventories/sample/hosts.yml` |
| `roles/assisted_cluster/tasks/main-old.yml` | `roles/assisted_cluster/tasks/main.yml` |
| `roles/assisted_hosts/tasks/main-old.yml` | `roles/assisted_hosts/tasks/main.yml` |
| `roles/assisted_hosts/tasks/main-pooll-host.yml` | `roles/assisted_hosts/tasks/main.yml` |
| `roles/rhoso_nmstate_nncp/tasks/main-old.yml` | `roles/rhoso_nmstate_nncp/tasks/main.yml` |
| `playbooks/assited-test-network.yml` | `playbooks/00-preflight.yml` plus offline payload validation |
| `playbooks/02-install-operators.yml` | `playbooks/day2/render-gitops.yml` and `playbooks/day2/bootstrap-gitops.yml` |
| `playbooks/03-configure-rhoso.yml` | `playbooks/day2/platform-rhoso.yml` |
| `playbooks/04-configure-rhoso-network.yml` | `playbooks/day2/rhoso-day2.yml` with structured GitOps resources |
| `MANIFEST.sha256` | Release-generated checksums; source-tree manifests are not maintained manually |

The dedicated `openstack_operator` and `rhoso_*` roles used only by the retired
wrappers were also removed. RHOSO operator lifecycle now uses the shared
catalog renderer; control-plane, data-plane, networking, and secret references
are supplied as reviewed structured resources rather than repository-specific
templates containing environment assumptions.

Experimental Assisted Installer Cluster/InfraEnv payload templates and NMState
variants with no callers were removed as well. The canonical role constructs
the API payloads from validated dictionaries and renders static networking only
through `static-network-config.json.j2` and `nmstate.yaml.j2`.

The two seven-line milestone summaries `day2-cluster-operations-a.md` and
`day2-cluster-operations-b.md` were removed after their content was superseded
by `day2-implementation-catalog.md` and the executive deployment runbook.

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

- `workshop/documentation/modules/ROOT/pages/01-environment.adoc` through the
  foundational Redfish and Assisted Installer lessons
- `docs/migration-from-idrac.md`

## Enforcement

The workflow lifecycle validator requires that:

1. Every supported workflow exists.
2. Every supported workflow has a unique canonical path.
3. Every retired path is absent.
4. Each retired path declares its canonical replacement.
5. Assisted Installer regression tests reference only canonical Day-0 paths.

A pull request that reintroduces a retired wrapper or removes a supported recovery workflow fails static CI.
