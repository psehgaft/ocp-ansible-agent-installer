# Repository Compliance Audit

This audit evaluates the repository after the architecture migration. Status values are `PASS`, `PARTIAL`, and `OPEN`.

| Requirement | Status | Evidence and remaining action |
|---|---|---|
| Valuable workflows migrated or documented | PARTIAL | Day-0 Redfish and Assisted Installer remain operational and the workshop maps legacy procedures. Compatibility wrappers remain documented in `docs/deprecated-files.md`. |
| No Dell-only workflow where generic Redfish exists | PASS | `playbooks/test-preflight.yml` now uses `bmc_*` inputs and `bmc_discovery`; legacy `idrac_*` variables are aliases only. |
| Every component represented in catalog | PARTIAL | The platform operator catalog covers the declared platform operators. Day-0 Assisted Installer/Redfish and generic Day-2 workflows are orchestration domains rather than OLM components and must remain documented separately. |
| Every role standardized and documented | PARTIAL | New framework roles follow defaults/tasks/templates structure. Several legacy roles still lack a role-level README and should be normalized incrementally. |
| Every input validated | PARTIAL | Core entry points and new roles assert mandatory inputs. Legacy roles require continued conversion to explicit argument specifications or assertions. |
| Declared deployment modes supported | PASS for catalog components | Catalog validation checks declared modes; direct, render, and GitOps are implemented by shared lifecycle roles. |
| GitOps manifests build | CI-controlled | Kustomize builds are authoritative in `Quality - Static`; merge is blocked when builds fail. |
| No plaintext secrets | PASS after this PR | The VMware audit default password was removed. CI includes Gitleaks; inventories must use Vault or external references. |
| Operators declare OpenShift versions and channels | PASS | OLM entries declare `supported_openshift` and explicit channel metadata. Cluster-payload components declare supported versions without an OLM channel. |
| Installation and functional validation | PARTIAL | Installation validation is standardized. Component-specific functional hooks exist but not every operand has a complete live-cluster test yet. |
| Profiles tested | PASS structurally | pytest and scheduled compatibility workflows cover declared profiles; live compatibility requires configured test clusters. |
| Direct and GitOps desired-state equivalence | PARTIAL | Both modes consume shared desired-state inputs. A canonical rendered-manifest diff test should be added for every component. |
| CI validates required technologies | PASS | CI covers Ansible, Python, YAML, Kustomize, Helm, Kubernetes schemas, secrets, workshop, and links. |
| Reports generated consistently | PASS | `component_result` drives Markdown, JSON, HTML, and CSV outputs. |
| Workshop matches framework | PASS structurally | The architecture workshop references the implemented catalog, modes, Day-2 domains, reporting, and retained Day-0 workflow. |
| Assisted Installer remains operational | PASS structurally | Generic Redfish discovery, virtual media, Assisted Installer entry points, compatibility wrappers, and regression tests remain present. Live BMC validation is environment-dependent. |

## CI root causes corrected

1. `redhat.openshift` could not be resolved from Galaxy. It was removed; supported Kubernetes/OpenShift automation uses `kubernetes.core`.
2. `group_vars/example/main.yml` contained duplicate `rhoso_project_name` keys. The example was normalized.
3. `openstack-nncp-new.yaml.j2` had an unclosed Jinja `if` block and invalid interface nesting. The template was replaced with a generic data-driven NMState template.
4. `playbooks/test-preflight.yml` referenced the removed `idrac_discovery` role. It now uses `bmc_discovery` and generic Redfish variables.

## Acceptance boundary

Static validation can prove syntax, schemas, composition, catalog completeness, secret hygiene, and documentation consistency. Live functional equivalence for BMC firmware, Assisted Installer, OLM catalogs, storage, networking, and operator operands requires integration environments and cannot be claimed from static CI alone.
