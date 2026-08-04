# Repository Compliance Audit

This audit evaluates the repository after the architecture migration. Status values are `PASS`, `PARTIAL`, and `OPEN`.

| Requirement | Status | Evidence and remaining action |
|---|---|---|
| Valuable workflows migrated or documented | PASS | Canonical workflows are declared in `framework/workflows.yml`; retired compatibility paths are absent and prohibited by CI. Valuable recovery and migration material remains explicitly supported. |
| No Dell-only workflow where generic Redfish exists | PASS | Canonical Day-0 workflows use `bmc_*` inputs and generic Redfish roles; legacy `idrac_*` variables remain data aliases only. |
| Every component represented in catalog | PARTIAL | The platform operator catalog covers declared platform operators. Day-0 Assisted Installer/Redfish and generic Day-2 workflows remain orchestration domains rather than OLM components. |
| Every role standardized and documented | PASS | `scripts/validate_architecture_contracts.py` discovers every role, requires `tasks/main.yml`, validates its task structure and defaults, and generates Markdown and JSON role documentation from the repository. |
| Every input validated | PARTIAL | Core entry points and new roles assert mandatory inputs. Legacy roles still require continued conversion to argument specifications or explicit assertions. |
| Declared deployment modes supported | PASS for catalog components | Catalog validation checks declared modes; direct, render and GitOps are implemented by shared lifecycle roles. |
| GitOps manifests build | CI-controlled | Kustomize builds are authoritative in `Quality - Static`; merge is blocked when builds fail. |
| No plaintext secrets | PASS | CI includes Gitleaks; inventories must use Vault or external references. |
| Operators declare OpenShift versions and channels | PASS | OLM entries declare `supported_openshift` and explicit channel metadata. Cluster-payload components declare supported versions without an OLM channel. |
| Installation and functional validation | PASS | `framework/component-validation.yml` provides installation checks by installation type and explicit functional checks for every catalog component. CI rejects missing or unknown validation contracts. |
| Profiles tested | PASS structurally | pytest and scheduled compatibility workflows cover declared profiles; live compatibility requires configured test clusters. |
| Direct and GitOps desired-state equivalence | PASS | Every component supporting both modes uses its declared GitOps path as the canonical desired-state source. CI canonicalizes the YAML byte stream and records a SHA-256 digest consumed identically by direct apply and GitOps commit paths. |
| CI validates required technologies | PASS | CI covers Ansible, Python, YAML, Kustomize, Helm, Kubernetes schemas, secrets, workshop and links. |
| Reports generated consistently | PASS | `component_result` drives Markdown, JSON, HTML and CSV outputs. Architecture-contract evidence is also generated in Markdown and JSON. |
| Workshop matches framework | PASS | Tests load the component catalog and verify that implemented platform domains, deployment modes, validation contracts, report formats, Kustomize, health checks and troubleshooting are represented in the architecture workshop. |
| Assisted Installer remains operational | PASS | The regression contract verifies canonical preflight, generic Redfish discovery, discovery ISO boot, single-host virtual-media test, media cleanup, Day-0 installation, required roles, migration documentation and installation outputs. |
| All legacy workflows fully retired | PASS | `playbooks/01-discover-bmc.yml`, `playbooks/site.yml` and `playbooks/test-preflight.yml` were removed. CI fails if a retired path returns, while supported recovery workflows remain declared and tested. |

## Final architecture contracts

The following files make the promoted criteria authoritative:

- `framework/component-validation.yml`
- `framework/workflows.yml`
- `scripts/validate_architecture_contracts.py`
- `tests/test_final_architecture_contracts.py`

The validator generates:

- `reports/output/architecture-contracts.json`
- `reports/output/architecture-contracts.md`

These reports contain the discovered role inventory, standardized role inputs and structure, component installation and functional checks, direct/GitOps canonical hashes, and supported/retired workflow lifecycle.

## Acceptance boundary

Static validation proves repository structure, component validation declarations, canonical desired-state byte equivalence, workflow lifecycle, catalog-to-workshop consistency, retained execution contracts, secret hygiene and documentation consistency. Live BMC firmware, Assisted Installer SaaS or on-prem API execution, OLM catalogs, storage, networking and operator operands remain protected integration tests.
