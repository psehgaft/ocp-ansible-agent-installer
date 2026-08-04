# Repository Compliance Audit

This audit evaluates the repository after the architecture migration. Status values are `PASS`, `PARTIAL`, and `OPEN`.

| Requirement | Status | Evidence and remaining action |
|---|---|---|
| Valuable workflows migrated or documented | PASS | Canonical workflows are declared in `framework/workflows.yml`; retired compatibility paths are absent and prohibited by CI. Valuable recovery and migration material remains explicitly supported. |
| No Dell-only workflow where generic Redfish exists | PASS | Canonical Day-0 workflows use `bmc_*` inputs and generic Redfish roles; legacy `idrac_*` variables remain data aliases only. |
| Every component represented in the catalog | PASS | Platform components are declared in `framework/components.yml`; Day-0 and supported workflow domains are declared in `framework/workflows.yml`; all Day-2 exercises are declared in `framework/day2-exercises.yml`. |
| Every role has standardized structure and documentation | PASS | `scripts/validate_architecture_contracts.py` discovers every role, requires `tasks/main.yml`, validates role structure/defaults, and emits Markdown/JSON evidence. The bastion role includes a dedicated README. |
| Every input is validated | PARTIAL | Core workflow inputs, component metadata, deployment modes, Day-2 resource contracts, and bastion version/platform inputs are validated. Some historical roles still rely on playbook-level assertions or defaults instead of role argument specifications. |
| Every component supports declared deployment modes | PASS | Catalog validation enforces declared modes. Shared lifecycle roles implement direct, render, and GitOps. Every Day-2 exercise is mapped to both Ansible and GitOps execution. |
| GitOps manifests build successfully | CI-controlled | `Quality - Static` runs Kustomize builds and Kubernetes/Argo CD schema validation. Day-2 GitOps output is rendered deterministically under `rendered/day2/<domain>`. |
| No plaintext secrets exist | PASS | Gitleaks is part of CI. Inventories and bastion configuration must use Vault, protected environment variables, or external secret references. |
| Every operator declares supported OpenShift versions and channels | PASS | OLM components declare `supported_openshift` and explicit channels; cluster-payload components declare supported versions without an OLM channel. |
| Every component has installation and functional validation | PASS | `framework/component-validation.yml` defines installation checks by installation type and functional checks for every catalog component. |
| Profiles are tested | PASS structurally | pytest and scheduled compatibility workflows cover declared profiles. Live profile certification still requires configured test clusters. |
| Direct and GitOps modes produce equivalent desired state | PASS | Canonical YAML byte streams and SHA-256 evidence are generated for components supporting both modes. Day-2 direct and GitOps modes consume the same `*_resources` inventory objects. |
| CI validates Ansible, Python, YAML, Kustomize, Helm and Kubernetes schemas | PASS | `Quality - Static` covers all required technologies plus secrets, workshop, links, and architecture contracts. |
| Reports are generated consistently | PASS | Component results produce Markdown, JSON, HTML, and CSV; architecture-contract evidence produces Markdown and JSON. |
| Workshop content matches the implemented framework | PASS | Tests compare workshop content with the component catalog, deployment modes, reporting, Kustomize, health checks, and troubleshooting contracts. |
| Existing Assisted Installer functionality remains operational | PASS | Regression tests retain canonical preflight, generic Redfish discovery, ISO boot, single-host virtual-media test, media cleanup, Day-0 install, migration docs, and installation outputs. |
| Every Day-2 exercise is executable with Ansible and GitOps | PASS | `framework/day2-exercises.yml` must exactly match every file under `playbooks/day2/`; tests verify the shared roles implement `direct` and `gitops`. |
| Bastion can be configured declaratively | PASS | `playbooks/configure-bastion.yml` and `roles/bastion_workstation` install Ansible, Python/Jinja, oc, kubectl, optional kubelet, Kustomize, Helm, and container tooling. |

## CI failures corrected

### Quality - Static

The YAML validator and yamllint were traversing collections downloaded into `.collections/`, including upstream Helm templates and Ansible-specific `!vault` and `!unsafe` tags. `scripts/validate_yaml.py` and `.yamllint` now exclude generated dependencies, artifacts, reports, virtual environments, and Node modules.

### Validate Ansible repository

`scripts/offline_validate.py` still required retired compatibility wrappers. It now requires canonical Day-0 paths, the bastion playbook, and the framework catalogs, while failing if retired wrappers are reintroduced.

## Day-2 execution

Apply directly with Ansible:

```bash
ansible-playbook -i inventories/<environment>/hosts.yml \
  playbooks/day2/<exercise>.yml \
  -e day2_deployment_mode=direct
```

Render for GitOps:

```bash
ansible-playbook -i inventories/<environment>/hosts.yml \
  playbooks/day2/<exercise>.yml \
  -e day2_deployment_mode=gitops \
  -e day2_render_root=rendered
```

Commit `rendered/day2/<domain>/resources.yml` and reconcile it with OpenShift GitOps.

## Bastion execution

```bash
ansible-playbook -i inventories/<environment>/hosts.yml \
  playbooks/configure-bastion.yml
```

The kubelet package is optional and remains stopped by default because the bastion is not an OpenShift cluster node.

## Acceptance boundary

Static validation proves repository structure, declared component validation, canonical desired-state equivalence, workflow lifecycle, Day-2 mode coverage, secret hygiene, and documentation consistency. Live BMC firmware, Assisted Installer APIs, OLM catalogs, storage, networking, and operator operands remain protected integration tests.
