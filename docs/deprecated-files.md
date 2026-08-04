# Deprecated and Compatibility Files

Do not delete compatibility files solely because a newer path exists. Removal requires a repository-wide reference check, successful static CI, and an Assisted Installer regression run.

## Safe to remove after this PR merges

| File | Replacement | Reason |
|---|---|---|
| `audit_vmware_network.yml` | `playbooks/audit_vmware_network.yml` | The root copy has been moved, secured, documented, and removed in this PR. |

## Deprecated compatibility entry points

These files should remain temporarily because external automation or the retained workshop may still call them.

| Deprecated path | Preferred path | Removal condition |
|---|---|---|
| `playbooks/01-discover-bmc.yml` | `playbooks/day0/discover-bmc.yml` | Remove only after all documentation, CI, and consumers use the Day-0 path. |
| `playbooks/site.yml` | `playbooks/day0/install.yml` | Remove only after an end-to-end Assisted Installer regression test confirms functional equivalence. |
| `playbooks/test-preflight.yml` | Day-0 preflight through shared roles | Keep as a generic compatibility diagnostic until the workshop and external automation stop referencing it. |
| `playbooks/02-boot-discovery-iso.yml` | Day-0 installation orchestration | Keep while it remains a supported standalone recovery/test operation. |
| `playbooks/03-test-virtual-media.yml` | Day-0 test workflow | Do not remove; it is a valuable non-production BMC validation workflow. Consider relocating later, not deleting. |
| `playbooks/90-eject-media.yml` | Day-0 media cleanup | Do not remove until an equivalent Day-0 cleanup entry point exists and is tested. |

## Legacy source material that is not deprecated for deletion

- `workshop/documentation/modules/ROOT/`
- `workshop/WORKSHOP.md`
- `docs/migration-from-idrac.md`

These files preserve the proven Assisted Installer migration history and operational procedures. They may be reorganized later, but must not be deleted blindly.

## Role-level candidates for future normalization

Legacy roles without a role-level README, argument specification, or standardized validation hook are candidates for refactoring, not immediate deletion. Generate the list mechanically during a later cleanup PR and migrate one functional domain at a time.

## Required deletion procedure

1. Search all YAML, Python, shell, Markdown, AsciiDoc, and workflow files for references.
2. Replace references with the preferred path.
3. Run `./scripts/validate.sh inventories/sample/hosts.yml`.
4. Run the complete static CI workflow.
5. Execute Redfish discovery and virtual-media tests against an approved non-production host.
6. Execute an Assisted Installer dry run or controlled installation regression.
7. Remove the file in a dedicated PR with rollback instructions.
