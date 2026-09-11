# Workshop: Deploy OpenShift with Playbooks or the GUI Interface

> **Canonical workflow notice:** Connected/disconnected inventory, Vault bootstrap,
> DHCP/static networking, disk selection, `oc-mirror` v2, the GUI interface, and
> Day-2 GitOps are documented in [`docs/deployment-scenarios.md`](docs/deployment-scenarios.md).
> Historical snippets below are retained as learning material; use the six
> canonical scenario pages for production execution.

## Canonical deployment paths

Choose one Day-0 installation path and one Day-2 path:

1. [Connected installation with playbooks](workshop/documentation/modules/ROOT/pages/15-connected-playbook.adoc)
2. [Disconnected installation with playbooks](workshop/documentation/modules/ROOT/pages/16-disconnected-playbook.adoc)
3. [Connected installation with the GUI interface](workshop/documentation/modules/ROOT/pages/17-connected-gui.adoc)
4. [Disconnected installation with the GUI interface](workshop/documentation/modules/ROOT/pages/18-disconnected-gui.adoc)
5. [Day-2 activities with playbooks](workshop/documentation/modules/ROOT/pages/19-day2-playbook.adoc)
6. [Day-2 activities with the GUI interface](workshop/documentation/modules/ROOT/pages/20-day2-gui.adoc)

Each path requires review of every variable group, encrypted credentials,
preflight validation, explicit confirmation before impactful operations, and a
retained evidence package. The detailed end-to-end runbook is
[`docs/deployment-scenarios.md`](docs/deployment-scenarios.md).

## Overview

This hands-on workshop teaches how to prepare, validate, and execute a vendor-neutral OpenShift bare-metal installation using Ansible, the Red Hat Assisted Installer API, and Redfish management controllers.

The labs intentionally use the same structure as the referenced Showroom workshop: prerequisites, estimated time, learning objectives, numbered procedures, verification, and conclusion.

## Audience

- OpenShift platform engineers.
- Bare-metal and data-center administrators.
- Ansible automation engineers.
- Architects migrating Dell-only workflows to mixed HPE and Dell infrastructure.

## Duration

Approximately 3.5–4.5 hours, excluding the OpenShift installation wait time.

## Learning outcomes

After completing the workshop, you will be able to:

- Explain how Redfish abstracts HPE iLO and Dell iDRAC.
- Configure a mixed-vendor Ansible inventory securely.
- Discover BMC topology, hardware inventory, and provisioning MACs.
- Create an Assisted Installer Cluster and InfraEnv through the API.
- Publish and mount a discovery ISO through Redfish virtual media.
- Validate one-time boot and power-control behavior safely.
- Complete an OpenShift installation and collect evidence.
- Troubleshoot BMC, NMState, ISO, and Assisted Installer failures.

---

# Module 1 Lab 1: Prepare the Environment

**Before you start:**

- Obtain a Linux control node with network access to the BMCs and Red Hat services.
- Obtain a non-production HPE or Dell server for the virtual-media lab.
- Confirm that DNS, VIP, load-balancer, and bare-metal network designs are approved.

**Prepares you for:** all remaining labs.

**Lab Type:** Foundational.

**Estimated Time:** 20–30 minutes.

> Validate tools, credentials, network paths, and repository content before issuing any Redfish power operation.

## Learning Objectives

After completing this lab, you will be able to:

- Install the required control-node packages.
- Install the Ansible collection.
- Verify Redfish and Assisted Installer connectivity.
- Run the repository validation tests.

## 1. Install control-node packages

On RHEL 9:

```bash
sudo dnf install -y python3 python3-pip git curl jq podman
python3 -m venv ~/venvs/ocp-redfish
source ~/venvs/ocp-redfish/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

## 2. Extract or clone the repository

From the delivered archive:

```bash
tar -xf ocp-ansible-agent-installer-redfish.tar
cd ocp-ansible-agent-installer-redfish
```

Or, after publishing it to Git:

```bash
git clone <YOUR_REPOSITORY_URL>
cd ocp-ansible-agent-installer-redfish
```

## 3. Install Ansible collections

```bash
ansible-galaxy collection install -r requirements.yml
ansible-galaxy collection list community.general
```

## 4. Verify CLI tools

```bash
python3 --version
ansible --version
ansible-playbook --version
curl --version
jq --version
podman --version
```

## 5. Test Redfish connectivity

Use an approved BMC account:

```bash
export BMC_ENDPOINT='https://10.10.10.11'
export BMC_USER='Administrator'
read -rsp 'BMC password: ' BMC_PASSWORD; echo

curl --fail --silent --show-error --insecure \
  --user "${BMC_USER}:${BMC_PASSWORD}" \
  "${BMC_ENDPOINT}/redfish/v1/" | jq .

unset BMC_PASSWORD
```

## 6. Run local tests

```bash
./tests/test_redfish_filters.py
./scripts/validate.sh inventories/sample/hosts.yml
```

The sample inventory intentionally contains placeholders, so full preflight will fail until Lab 2 is complete.

## Verification

```bash
ansible-galaxy collection list community.general
python3 tests/test_redfish_filters.py
find playbooks roles inventories -maxdepth 3 -type f | sort
```

Expected result:

- `community.general` is installed.
- Redfish normalization tests pass.
- The repository contains BMC, Assisted Installer, ISO, installation, and reporting roles.

## Conclusion

You prepared the control node, verified Redfish connectivity, installed the required collection, and validated the repository structure.

---

# Module 1 Lab 2: Configure Mixed-Vendor Inventory

**Before you start:** Complete Lab 1.

**Prepares you for:** Redfish discovery and Assisted Installer payload generation.

**Lab Type:** Configuration.

**Estimated Time:** 30–45 minutes.

> An inventory is an executable infrastructure contract. Record vendor intent explicitly and keep all credentials outside plaintext host definitions.

## Learning Objectives

- Create a cluster-specific inventory.
- Configure HPE iLO and Dell iDRAC hosts in the same group.
- Configure static network and ISO publication variables.
- Confirm host counts and logical NIC mappings.

## 1. Copy the sample inventory

```bash
cp -a inventories/sample inventories/lab
```

## 2. Configure HPE iLO hosts

Edit `inventories/lab/hosts.yml`:

```yaml
master-0:
  bmc_type: ilo
  bmc_endpoint: "https://10.10.10.11"
  bmc_username: "Administrator"
  bmc_password: "{{ vault_bmc_passwords[inventory_hostname] }}"
  node_role: master
  node_hostname: master-0
  node_ipv4_address: "192.168.50.21"
```

## 3. Configure Dell iDRAC hosts

```yaml
master-1:
  bmc_type: idrac
  bmc_endpoint: "https://10.10.10.12"
  bmc_username: "root"
  bmc_password: "{{ vault_bmc_passwords[inventory_hostname] }}"
  node_role: master
  node_hostname: master-1
  node_ipv4_address: "192.168.50.22"
```

Use `bmc_type: generic` for another conformant Redfish implementation. Use `auto` only when you accept runtime vendor detection.

## 4. Configure cluster variables

Edit `inventories/lab/group_vars/all.yml` and replace every `CHANGE_ME` value.

At minimum, verify:

```yaml
cluster_name: "ocp418-lab"
base_dns_domain: "example.com"
openshift_version: "4.18"
control_plane_count: 3
compute_count: 2
machine_network_cidr: "192.168.50.0/24"
api_vip: "192.168.50.10"
ingress_vip: "192.168.50.11"
```

## 5. Configure the installation network

Bond example:

```yaml
install_network_mode: bond
install_network_bond_name: bond0
install_network_bond_ports:
  - nic0
  - nic1
install_network_bond_mode: 802.3ad
install_network_mtu: 1500
```

Coordinate LACP and VLAN configuration with the switch team before booting the discovery ISO.

## 6. Configure ISO publication

For a local Podman web server:

```yaml
iso_delivery_mode: local_http
iso_http_advertise_address: "192.168.50.5"
iso_http_port: 8080
```

The advertised address must be reachable from every iLO/iDRAC management network.

## 7. Check inventory structure

```bash
ansible-inventory -i inventories/lab/hosts.yml --graph
ansible-inventory -i inventories/lab/hosts.yml --list | jq '.baremetal.hosts'
```

## Verification

Confirm:

- The `control_plane` and `workers` group sizes match configured counts.
- Every host has `bmc_type`, endpoint, username, node role, hostname, and node IP.
- No `CHANGE_ME` value remains in active inventory files.

```bash
grep -R --line-number 'CHANGE_ME' \
  inventories/lab/hosts.yml inventories/lab/group_vars/all.yml
```

## Conclusion

You created an auditable mixed-vendor inventory and defined the cluster, installation network, and ISO delivery model.

---

# Module 1 Lab 3: Protect Credentials with Ansible Vault

**Before you start:** Complete Lab 2.

**Prepares you for:** authenticated Redfish and Assisted Installer API operations.

**Lab Type:** Security.

**Estimated Time:** 15–20 minutes.

> Secrets should enter automation at runtime, not through Git history.

## Learning Objectives

- Create the active Vault file.
- Add per-host BMC passwords.
- Add the Assisted Installer token.
- Verify encryption and Git exclusions.

## 1. Create the Vault file

```bash
cp inventories/lab/group_vars/vault.yml.example \
   inventories/lab/group_vars/vault.yml
```

## 2. Add credentials

```yaml
assisted_offline_token: "REDACTED"

vault_bmc_passwords:
  master-0: "REDACTED"
  master-1: "REDACTED"
  master-2: "REDACTED"
  worker-0: "REDACTED"
  worker-1: "REDACTED"
```

## 3. Encrypt the file

```bash
ansible-vault encrypt inventories/lab/group_vars/vault.yml
```

## 4. Verify encryption

```bash
head -1 inventories/lab/group_vars/vault.yml
```

Expected prefix:

```text
$ANSIBLE_VAULT;
```

## 5. Create local secret files

```bash
install -d -m 0700 secrets
install -m 0600 /path/to/pull-secret.json secrets/pull-secret.json
install -m 0600 ~/.ssh/id_rsa.pub secrets/id_rsa.pub
```

## Verification

```bash
git check-ignore -v inventories/lab/group_vars/vault.yml
ansible-vault view inventories/lab/group_vars/vault.yml
```

## Conclusion

You removed BMC passwords and Assisted Installer tokens from plaintext inventory and prepared the required local secret files.

---

# Module 2 Lab 1: Discover iLO and iDRAC Inventory

**Before you start:** Complete Module 1.

**Prepares you for:** MAC mapping, virtual media, and Assisted Installer host matching.

**Lab Type:** Read-only hardware discovery.

**Estimated Time:** 20–30 minutes.

> Discovery is the safety gate. Do not proceed to virtual media until every host reports the expected model, serial number, NICs, and provisioning MAC.

## Learning Objectives

- Query Redfish service topology.
- Collect hardware and firmware evidence.
- Validate vendor detection.
- Override ambiguous NIC selection safely.

## 1. Run discovery

```bash
ansible-playbook \
  -i inventories/lab/hosts.yml \
  --ask-vault-pass \
  playbooks/01-discover-bmc.yml
```

## 2. Review the consolidated report

```bash
cat artifacts/ocp418-lab/reports/bmc-inventory.md
```

## 3. Inspect one raw record

```bash
jq '{
  bmc_type_effective,
  system_id,
  manager_id,
  model: .system.Model,
  serial: .system.SerialNumber,
  provisioning_mac,
  normalized_nics
}' artifacts/ocp418-lab/raw/bmc-master-0.json
```

## 4. Correct NIC selection when required

By regex:

```yaml
master-0:
  provisioning_nic_match: "Embedded LOM 1"
```

By exact MAC:

```yaml
master-0:
  provisioning_mac_override: "aa:bb:cc:dd:ee:ff"
```

When the NMState bond must use exact physical ports, pin the complete Assisted Installer mapping:

```yaml
master-0:
  mac_interface_map_override:
    - logical_nic_name: nic0
      mac_address: "aa:bb:cc:dd:ee:01"
    - logical_nic_name: nic1
      mac_address: "aa:bb:cc:dd:ee:02"
```

Rerun discovery after changing inventory.

## Verification

For every host, confirm:

- Requested and detected BMC type.
- Expected manufacturer/model/serial.
- Expected Systems, Managers, and Chassis IDs.
- All production NIC MAC addresses.
- Correct provisioning MAC.

## Conclusion

You collected vendor-neutral Redfish evidence and validated the MAC that will link physical inventory to Assisted Installer host registration.

---

# Module 2 Lab 2: Validate Virtual Media on One Host

**Before you start:** Complete Redfish discovery and obtain a BMC-reachable test ISO URL.

**Prepares you for:** discovery ISO boot across the cluster.

**Lab Type:** Disruptive, constrained test.

**Estimated Time:** 20–40 minutes.

> Use `--limit` and a non-production server. This lab changes one-time boot and restarts the selected server.

## Learning Objectives

- Insert ISO media through Manager or Systems Redfish resources.
- Set one-time CD/DVD boot.
- Restart one server.
- Eject media and confirm rollback.

## 1. Select an approved host

```bash
export TEST_HOST=master-0
export TEST_ISO_URL='https://web.example.com/images/test.iso'
```

## 2. Confirm the exact target

```bash
ansible-inventory -i inventories/lab/hosts.yml --host "${TEST_HOST}"
```

## 3. Run the virtual-media test

```bash
ansible-playbook \
  -i inventories/lab/hosts.yml \
  --ask-vault-pass \
  --limit "${TEST_HOST}" \
  -e "test_iso_url=${TEST_ISO_URL}" \
  -e bmc_wait_for_node_ssh=false \
  playbooks/03-test-virtual-media.yml
```

## 4. Observe the BMC

In iLO or iDRAC, verify:

- The ISO is connected.
- The next boot target is virtual CD/DVD.
- The server restarts.
- No persistent boot-order change was made.

## 5. Eject media

```bash
ansible-playbook \
  -i inventories/lab/hosts.yml \
  --ask-vault-pass \
  --limit "${TEST_HOST}" \
  -e "iso_existing_url=${TEST_ISO_URL}" \
  playbooks/90-eject-media.yml
```

## Verification

Confirm the virtual-media device is empty and the normal boot order remains intact.

## Conclusion

You validated the most disruptive hardware-management path on a controlled target before applying it to the cluster.

---

# Module 3 Lab 1: Create and Boot the Assisted Installer ISO

**Before you start:** Complete all previous labs and approve the maintenance window.

**Prepares you for:** host registration and installation.

**Lab Type:** Cluster deployment.

**Estimated Time:** 30–60 minutes plus host boot time.

> This lab creates Assisted Installer resources, publishes a discovery ISO, mounts it to every BMC, and restarts the servers.

## Learning Objectives

- Create Cluster and InfraEnv API objects.
- Render NMState and MAC mappings.
- Publish the discovery ISO.
- Boot all approved hosts.

## 1. Run full preflight

```bash
./scripts/preflight.sh inventories/lab/hosts.yml

ansible-playbook \
  -i inventories/lab/hosts.yml \
  --ask-vault-pass \
  playbooks/00-preflight.yml
```

## 2. Review the planned host set

```bash
ansible-inventory -i inventories/lab/hosts.yml --graph
```

## 3. Create and boot the discovery ISO

```bash
ansible-playbook \
  -i inventories/lab/hosts.yml \
  --ask-vault-pass \
  playbooks/02-boot-discovery-iso.yml
```

## 4. Verify the local ISO service

For `local_http` mode:

```bash
podman ps --filter name=ocp-assisted-iso-httpd
curl -I http://192.168.50.5:8080/discovery.iso
```

## 5. Review persisted API state

```bash
jq . artifacts/ocp418-lab/raw/cluster-create-response.json
jq . artifacts/ocp418-lab/raw/infraenv-create-response.json
```

## Verification

- All BMCs show the discovery ISO mounted.
- Hosts boot into the discovery environment.
- SSH port 22 becomes reachable when `bmc_wait_for_node_ssh=true`.
- The Assisted Installer begins displaying host inventory.

## Conclusion

You created the discovery environment and booted a mixed HPE/Dell bare-metal host set using one Redfish workflow.

---

# Module 3 Lab 2: Install and Verify OpenShift

**Before you start:** All hosts must register and pass Assisted Installer validations.

**Lab Type:** Installation.

**Estimated Time:** 60–120 minutes, environment-dependent.

> Treat failed Assisted Installer validations as actionable design feedback. Correct DNS, routing, NTP, storage, or hardware issues instead of bypassing them blindly.

## Learning Objectives

- Match hosts by provisioning MAC.
- Assign hostnames and roles.
- Start installation.
- Download and validate cluster credentials.

## 1. Run the complete workflow

The workflow is resumable through persisted API state:

```bash
ansible-playbook \
  -i inventories/lab/hosts.yml \
  --ask-vault-pass \
  playbooks/site.yml
```

If discovery and ISO boot were already completed, tags can constrain a rerun, but use tags only after reviewing dependencies.

## 2. Export the kubeconfig

```bash
export KUBECONFIG="$PWD/artifacts/ocp418-lab/auth/kubeconfig"
oc whoami
oc get clusterversion
oc get nodes -o wide
oc get clusteroperators
```

## 3. Review reports and events

```bash
cat artifacts/ocp418-lab/reports/install-report.md
jq '.[] | {event_time, severity, message}' \
  artifacts/ocp418-lab/raw/events.json | less
```

## 4. Eject installation media

```bash
ansible-playbook \
  -i inventories/lab/hosts.yml \
  --ask-vault-pass \
  playbooks/90-eject-media.yml
```

## Verification

```bash
oc get clusterversion
oc get nodes
oc get clusteroperators | grep -v ' True .*False .*False '
```

Expected result:

- ClusterVersion is Available.
- All intended nodes are Ready.
- Cluster Operators are Available and not Degraded.
- Discovery media is ejected.

## Conclusion

You completed a vendor-neutral bare-metal OpenShift installation and produced traceable BMC, API, and cluster evidence.

---

# Module 4: Troubleshooting and Final Challenge

**Estimated Time:** 30–45 minutes.

## Scenario

A mixed cluster has these symptoms:

- One iLO server reports no provisioning MAC.
- One iDRAC server cannot mount the ISO.
- Two hosts register but remain in insufficient status.

## Tasks

1. Inspect `bmc-<host>.json` and select the correct MAC with a regex or override.
2. Verify the ISO URL from the BMC management network.
3. Review virtual-media category and Redfish resource IDs.
4. Review `hosts-initial.json` and `events.json`.
5. Validate NMState, LACP, VLAN, MTU, DNS, gateway, and NTP values.
6. Rerun only read-only discovery first.
7. Repeat the one-host virtual-media test.
8. Resume the full installation only after all blocking conditions are resolved.

## Completion criteria

- Every host has a documented, deterministic provisioning MAC.
- Both iLO and iDRAC virtual-media tests succeed.
- All Assisted Installer validations are understood and resolved.
- The final report contains all intended hosts and output locations.
- Secrets and generated artifacts are excluded from Git.

## Cleanup

```bash
ansible-playbook \
  -i inventories/lab/hosts.yml \
  --ask-vault-pass \
  playbooks/90-eject-media.yml

podman rm -f ocp-assisted-iso-httpd || true
unset KUBECONFIG TEST_HOST TEST_ISO_URL BMC_ENDPOINT BMC_USER
```
