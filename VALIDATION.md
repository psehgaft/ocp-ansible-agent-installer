# Validation Record

## Validation scope

This repository was validated offline before packaging. The validation covers repository structure, YAML and Jinja syntax, custom Python filter behavior, role references, mixed HPE iLO and Dell iDRAC sample inventory, and checks that executable playbooks no longer depend on Dell-only Ansible modules.

## Completed checks

The following command completed successfully in the build environment:

```bash
./scripts/validate.sh inventories/sample/hosts.yml
```

The successful checks included:

- YAML parsing with duplicate-key detection.
- Jinja template parsing.
- Python syntax checks.
- Unit tests for iLO-like and iDRAC-like Redfish payload normalization.
- IPv4, hostname, URL, and bracketed IPv6 BMC endpoint parsing.
- Required-file and role-reference validation.
- Verification that the sample inventory includes both `bmc_type: ilo` and `bmc_type: idrac`.
- Verification that executable playbooks and roles contain no `dellemc.openmanage.idrac_*` calls.
- Shell syntax validation for `scripts/preflight.sh` and `scripts/validate.sh`.

## Checks that require the target environment

The build environment did not have Ansible installed and had no access to a live HPE iLO or Dell iDRAC endpoint. Consequently, the following checks must be completed on the Ansible control node:

```bash
python3 -m pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
./scripts/preflight.sh inventories/mycluster/hosts.yml
./scripts/validate.sh inventories/mycluster/hosts.yml
```

When `ansible-playbook` is installed, `scripts/validate.sh` automatically runs `--syntax-check` against every playbook.

Before booting all cluster nodes, test one approved non-production host:

```bash
ansible-playbook \
  -i inventories/mycluster/hosts.yml \
  --ask-vault-pass \
  --limit master-0 \
  -e test_iso_url=https://images.example.com/test.iso \
  -e bmc_wait_for_node_ssh=false \
  playbooks/03-test-virtual-media.yml
```

Confirm that the ISO is mounted, one-time CD/DVD boot is accepted, and the server reaches the expected discovery environment. Firmware-specific virtual-media behavior must be validated separately for every server generation and BMC firmware baseline used in production.
