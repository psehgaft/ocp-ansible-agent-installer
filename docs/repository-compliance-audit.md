# Repository Compliance Audit

This audit evaluates the repository after the architecture migration. Status values are `PASS`, `PARTIAL`, and `OPEN`.

| Requirement | Status | Evidence and remaining action |
|---|---|---|
| Valuable workflows migrated or documented | PASS | Canonical workflows are declared in `framework/workflows.yml`; retired compatibility paths are absent and prohibited by CI. Valuable recovery and migration material remains explicitly supported. |
| No Dell-only workflow where generic Redfish exists | PASS | Canonical Day-0 workflows use `bmc_*` inputs and generic Redfish roles; legacy `idrac_*` variables remain data aliases only. |
| Every component represented in catalog | PASS for managed platform and orchestration domains | Platform components are declared in `framework/components.yml`. Day-0, Day-2 and bastion workflows are declared in `framework/workflows.yml` and `framework/day2-exercises.yml`, preventing untracked executable domains. |
| Every role standardized and documented | PASS | `scripts/validate_architecture_contracts.py` discovers every role, requires `tasks/main.yml`, validates its task structure and defaults, and generates Markdown and JSON role documentation. New roles include role-level documentation. |
| Every input validated | PARTIAL | Core workflows, catalog components, Day-2 modes and the bastion role validate mandatory inputs. Some historical roles still rely on defaults and playbook-level validation rather than role argument specifications. |
| Declared deployment modes supported | PASS | Catalog validation checks declared modes. Shared lifecycle roles implement direct, render and GitOps execution. Every Day-2 exercise is mapped to both an Ansible entry point and deterministic GitOps output. |
| GitOps manifests build | CI-controlled | Kustomize builds are authoritative in `Quality - Static`; merge is blocked when builds fail. Day-2 GitOps output is rendered deterministically under `rendered/day2/<domain>`. |
| No plaintext secrets | PASS | CI includes Gitleaks; inventories and bastion inputs must use Vault, protected environment variables or external secret references. |
| Operators declare OpenShift versions and channels | PASS | OLM entries declare `supported_openshift` and explicit channel metadata. Cluster-payload components declare supported versions without an OLM channel. |
| Installation and functional validation | PASS | `framework/component-validation.yml` provides installation checks by installation type and explicit functional checks for every platform component. CI rejects missing or unknown validation contracts. |
| Profiles tested | PASS structurally | pytest and scheduled compatibility workflows cover declared profiles; live compatibility requires configured test clusters. |
| Direct and GitOps desired-state equivalence | PASS | Components supporting both modes use canonical desired-state sources. CI canonicalizes YAML bytes and records SHA-256 evidence. Day-2 direct and GitOps modes consume the same `*_resources` inventory objects. |
| CI validates required technologies | PASS | CI covers Ansible, Python, YAML, Kustomize, Helm, Kubernetes schemas, secrets, workshop, links, architecture contracts and Day-2 dual-mode coverage. |
| Reports generated consistently | PASS | `component_result` drives Markdown, JSON, HTML and CSV outputs. Architecture-contract evidence is generated in Markdown and JSON. |
| Workshop matches framework | PASS | Tests load the catalog and verify implemented platform domains, deployment modes, validation contracts, report formats, Kustomize, health checks and troubleshooting. |
| Assisted Installer remains operational | PASS | The regression contract verifies canonical preflight, generic Redfish discovery, discovery ISO boot, single-host virtual-media test, media cleanup, Day-0 installation, required roles, migration documentation and installation outputs. |
| All legacy workflows fully retired | PASS | Compatibility-only paths are removed and prohibited from returning. Supported recovery workflows remain declared and tested. |
| Every Day-2 exercise supports Ansible and GitOps | PASS | `framework/day2-exercises.yml` catalogs every file under `playbooks/day2/` with its role, resource input and GitOps output. Tests require exact catalog/playbook equality and verify both shared roles implement `direct` and `gitops`. |
| Bastion can be configured declaratively | PASS | `playbooks/configure-bastion.yml` and `roles/bastion_workstation` install and validate Ansible, Python/Jinja, oc, kubectl, optional kubelet, Kustomize, Helm and container tooling on RHEL-compatible hosts. |

## CI failures corrected

### Quality - Static

The YAML validator and yamllint were traversing collections downloaded into `.collections/`, including upstream Helm templates and Ansible-specific `!vault`/`!unsafe` tags. Repository validation now excludes generated dependency, artifact, report and virtual-environment directories.

### Validate Ansible repository

The offline validator still required retired compatibility wrappers. It now requires canonical Day-0 paths, the bastion playbook and framework catalogs, while explicitly failing if retired wrappers are reintroduced.

## Day-2 execution contract

For Ansible apply:

```bash
ansible-playbook -i inventories/<environment>/hosts.yml \
  playbooks/day2/<exercise>.yml \
  -e day2_deployment_mode=direct
```

For GitOps rendering:

```bash
ansible-playbook -i inventories/<environment>/hosts.yml \
  playbooks/day2/<exercise>.yml \
  -e day2_deployment_mode=gitops \
  -e day2_render_root=rendered
```

Commit the resulting `rendered/day2/<domain>/resources.yml` through the repository's normal Git review process and reconcile it with OpenShift GitOps.

## Bastion execution

```bash
ansible-playbook -i inventories/<environment>/hosts.yml \
  playbooks/configure-bastion.yml
```

The kubelet package is available for diagnostics and version parity but remains stopped by default because the bastion is not an OpenShift cluster node.

## Acceptance boundary

Static validation proves repository structure, declared component validation, canonical desired-state equivalence, workflow lifecycle, Day-2 mode coverage, secret hygiene and documentation consistency. Live BMC firmware, Assisted Installer APIs, OLM catalogs, storage, networking and operator operands remain protected integration tests.
