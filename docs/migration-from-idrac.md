# Migration from the iDRAC-Only Repository

## Summary

The original workflow used Dell-specific roles and `idrac_*` variables. The canonical implementation now retains the Assisted Installer sequence while replacing hardware discovery, virtual media, boot override, and power control with reusable Redfish roles.

## Canonical entry points

| Purpose | Canonical playbook | Compatibility wrapper |
|---|---|---|
| Full Day-0 installation | `playbooks/day0/install.yml` | `playbooks/site.yml` |
| BMC discovery and report | `playbooks/day0/discover-bmc.yml` | `playbooks/01-discover-bmc.yml` |

The compatibility wrappers remain supported during the migration period and import the canonical playbooks directly, preventing behavior drift.

## Role mapping

| Previous role or concept | Canonical role or concept |
|---|---|
| `idrac_discovery` / `idrac_discovery_full` | `bmc_discovery` |
| `idrac_boot_discovery_iso` | `iso_publish` + `bmc_virtual_media` |
| Dell-only report fields | Vendor-neutral `bmc_*` report fields |
| `dellemc.openmanage` collection | `community.general` Redfish modules |
| Hard-coded Dell resource assumptions | Dynamic Redfish collection/resource discovery |

## Variable migration

Previous:

```yaml
server-0:
  idrac_ip: 10.10.10.20
  idrac_user: root
  idrac_password: "{{ vault_idrac_password }}"
```

Recommended:

```yaml
server-0:
  bmc_type: idrac
  bmc_endpoint: https://10.10.10.20
  bmc_username: root
  bmc_password: "{{ vault_bmc_passwords[inventory_hostname] }}"
```

HPE example:

```yaml
server-1:
  bmc_type: ilo
  bmc_endpoint: https://10.10.10.21
  bmc_username: Administrator
  bmc_password: "{{ vault_bmc_passwords[inventory_hostname] }}"
```

The compatibility layer accepts `idrac_ip`, `idrac_user`, and `idrac_password`, but these aliases are intended only for controlled migration.

## Recommended migration sequence

1. Copy the old inventory to a new branch.
2. Rename `idrac_*` variables to `bmc_*` and add `bmc_type`.
3. Move passwords into `vault_bmc_passwords`.
4. Install the collections from `collections/requirements.yml`.
5. Run `playbooks/day0/discover-bmc.yml` without changing server power state.
6. Compare normalized NICs and selected provisioning MACs with switch and operating-system records.
7. Set a per-host MAC override where necessary.
8. Run `playbooks/03-test-virtual-media.yml --limit <one-host>` with a harmless bootable ISO on a non-production server.
9. Validate virtual-media ejection and one-time boot behavior.
10. Run `playbooks/02-boot-discovery-iso.yml` for a complete lab cluster.
11. Run `playbooks/day0/install.yml` only after all hosts pass discovery and virtual-media validation.

## Removal policy

Legacy files are removed only when all of the following are true:

- the canonical implementation exists;
- a compatibility entry point exists where users may still depend on the old path;
- static tests verify the wrapper imports the canonical playbook;
- repository search shows no active references to the obsolete implementation.

## Rollback

The Redfish roles do not alter BIOS settings, RAID configuration, or persistent boot order. To reverse a virtual-media test:

```bash
ansible-playbook \
  -i inventories/mycluster/hosts.yml \
  --ask-vault-pass \
  playbooks/90-eject-media.yml
```

Then confirm the server's normal boot device in iLO/iDRAC and power-cycle only if required by the platform state.
