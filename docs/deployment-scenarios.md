# OpenShift deployment scenarios

This is the canonical operator runbook for the repository. It covers the same
validated variable model through Ansible CLI or the containerized GUI
interface. Choose one Day-0 path and, only after the cluster is installed,
choose one Day-2 GitOps path.

## Supported paths

| Path | Day | Entry point | Infrastructure changes |
|---|---:|---|---|
| Connected installation with playbooks | 0 | `playbooks/day0/install.yml` | Bare-metal installation |
| Disconnected installation with playbooks | 0 | `prepare-mirror.yml`, then `install.yml` | Mirror and bare-metal installation |
| Connected installation with GUI | 0 | GUI actions | Bare-metal installation after confirmation |
| Disconnected installation with GUI | 0 | GUI actions | Mirror and installation after separate confirmations |
| Day-2 with playbooks | 2 | `render-gitops.yml`, then `bootstrap-gitops.yml` | Git push and minimal GitOps bootstrap when enabled |
| Day-2 with GUI | 2 | **Render Day-2 GitOps**, then **Publish and bootstrap GitOps** | Same GitOps boundary after confirmation |

The Day-0 installer stops after downloading installation credentials and
evidence. It does not install operators. Day-2 renders desired state to Git;
after the minimal OpenShift GitOps bootstrap, Argo CD performs reconciliation.

## Common preparation

### 1. Prepare the execution host

Use RHEL 9 or another supported Linux host with Python 3.11+, Ansible,
`oc`, `oc-mirror` v2, Git, Podman, Kustomize, Helm, DNS access, and routes to
the BMC network. The GUI image packages these dependencies.

For CLI execution:

```bash
git clone https://github.com/psehgaft/ocp-ansible-agent-installer.git
cd ocp-ansible-agent-installer
python3 -m pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
```

### 2. Create an environment inventory

```bash
cp -a inventories/sample inventories/production-a
export INVENTORY="$PWD/inventories/production-a/hosts.yml"
export VAULT_PASSWORD_FILE=/secure/production-a-vault-password
chmod 600 "$VAULT_PASSWORD_FILE"
```

### 3. Configure every variable group

Review every key in every file. Keep a documented default only when it is
correct for the target environment. Replace all `CHANGE_ME` values. Empty
optional values are omitted from Assisted Installer requests, while Boolean
`false` and integer `0` remain explicit.

| File / GUI section | Variables to review |
|---|---|
| `00-required.yml` / **Cluster** | `deployment_mode`, `cluster_name`, `base_dns_domain`, `openshift_version`, node counts, machine/cluster/service networks, VIP allocation, API VIPs, Ingress VIPs, pull-secret and SSH-key references |
| `10-assisted-installer.yml` / **Assisted Installer API** | service and SSO URLs, auth mode, cluster API fields, InfraEnv API fields, proxies, NTP, architecture, HA, network type, encryption, ignition, release image, kernel arguments, trust bundle, and forward-compatible overrides |
| `20-network.yml` / **Network** | DHCP/static mode, prefix, gateway, DNS, single NIC/bond, ports, bond mode/options, MTU, IPv6, and optional complete per-host NMState |
| `30-disconnected.yml` / **Disconnected** | environment type, `oc-mirror` workflow, workspace/archive, registry, TLS, parallelism, retries, archive size, channel, version range, architectures, graph, mirrored release, CA, additional images, and Helm content |
| `40-bmc.yml` / **BMC and Redfish** | TLS validation/CA, timeout, Redfish resource IDs, boot device, virtual-media category/fallback, power command, SSH wait, delays, and provisioning NIC matching |
| `50-runtime.yml` / **Runtime** | ISO delivery mode/address/port/image/URL, artifacts, kubeconfig/password paths, state reuse, and registration/readiness/install retry policy |
| `60-day2-gitops.yml` / **Day-2 GitOps** | profile, operators, overrides, additional packages, operands, approval, channel adaptation, catalog images, Git coordinates, render/checkout paths, push confirmation, and bootstrap controls |
| `vault.yml` / **Credentials and secrets** | pull secret, SSH public key, Assisted Installer token, per-host BMC credentials, optional registry auth, and optional Git credentials |
| `hosts.yml` / **Hosts** | inventory name, hostname, role, BMC type/endpoint, credentials, static IP, installation disk, disks to preserve, NIC map, complete NMState, and Assisted Host API overrides |

The exhaustive defaults and descriptions remain in the files themselves and in
[Variable reference](variable-reference.md). The GUI reads them directly; it
does not maintain a second set of defaults.

Generate a review checklist directly from the same schema used by the GUI. This
lists every current variable, its group, whether it is conditionally required,
its type, source file, and default value:

```bash
python3 scripts/gui_config.py schema --root . |
  jq -r '.variables[] | [.group, .name, (.required // false), .type, .source, (.default | tojson)] | @tsv' \
  > variable-review-checklist.tsv
```

Do not mark a group complete until every row has either an environment-specific
value or an explicitly accepted documented default.

### 4. Create the encrypted Vault for CLI execution

Prepare the source files outside Git and run:

```bash
export OCP_VAULT_PASSWORD_FILE="$VAULT_PASSWORD_FILE"
export OCP_VAULT_OUTPUT_FILE="$PWD/inventories/production-a/group_vars/vault.yml"
export OCP_PULL_SECRET_FILE=/secure/pull-secret.json
export OCP_SSH_PUBLIC_KEY_FILE=/secure/id_ed25519.pub
export OCP_BMC_CREDENTIALS_FILE=/secure/production-a-bmc.yml
export OCP_ASSISTED_OFFLINE_TOKEN='REDACTED'
ansible-playbook playbooks/day0/create-vault.yml
ansible-vault view --vault-password-file "$VAULT_PASSWORD_FILE" \
  inventories/production-a/group_vars/vault.yml >/dev/null
```

For an on-premises Assisted Service, set `OCP_ASSISTED_ACCESS_TOKEN` instead of
the SaaS offline token. For dedicated mirror credentials, also set
`OCP_MIRROR_AUTH_FILE`.

### 5. Validate before any change

```bash
./scripts/validate.sh "$INVENTORY"
ansible-inventory -i "$INVENTORY" \
  --vault-password-file "$VAULT_PASSWORD_FILE" --graph
ansible-playbook -i "$INVENTORY" \
  --vault-password-file "$VAULT_PASSWORD_FILE" \
  playbooks/00-preflight.yml
```

Resolve every blocking validation before continuing.

## Scenario 1: connected installation with playbooks

### Configure connected mode

In `00-required.yml`:

```yaml
deployment_mode: connected
cluster_name: production-a
base_dns_domain: example.com
openshift_version: "4.18"
```

In `10-assisted-installer.yml` select `saas` or `onprem`. For SaaS:

```yaml
assisted_auth_mode: saas
assisted_api_url: https://api.openshift.com/api/assisted-install/v2
```

Choose DHCP or static addressing in `20-network.yml`.

DHCP nodes and DHCP VIPs:

```yaml
node_network_config_mode: dhcp
vip_allocation_mode: dhcp
```

Static nodes and static VIPs:

```yaml
node_network_config_mode: static
vip_allocation_mode: static
node_ipv4_prefix: 24
node_ipv4_gateway: 192.168.50.1
node_dns_servers: [192.168.50.5, 192.168.50.6]
api_vips: [{ip: 192.168.50.10}]
ingress_vips: [{ip: 192.168.50.11}]
```

Set every host BMC, role, hostname, address when static, and stable
`installation_disk_id` in `hosts.yml`.

### Discover, review, and install

```bash
ansible-playbook -i "$INVENTORY" \
  --vault-password-file "$VAULT_PASSWORD_FILE" \
  playbooks/day0/discover-bmc.yml

ansible-playbook -i "$INVENTORY" \
  --vault-password-file "$VAULT_PASSWORD_FILE" \
  playbooks/day0/install.yml
```

Review `artifacts/production-a/`, then verify the downloaded credentials:

```bash
export KUBECONFIG="$PWD/artifacts/production-a/auth/kubeconfig"
oc get clusterversion
oc get nodes -o wide
oc get clusteroperators
```

## Scenario 2: disconnected installation with playbooks

Complete the common inventory first, then set:

```yaml
deployment_mode: disconnected
disconnected_environment: partially_disconnected
oc_mirror_workflow: render_only
oc_mirror_registry: registry.example.com:8443/ocp4
oc_mirror_dest_tls_verify: true
oc_mirror_src_tls_verify: true
mirror_ca_file: /etc/pki/ca-trust/source/anchors/registry-ca.pem
disconnected_release_image: registry.example.com:8443/ocp4/openshift-release-dev/ocp-release@sha256:REPLACE
```

### Partially disconnected: mirror to mirror

First render and inspect the generated ImageSetConfiguration:

```bash
ansible-playbook -i "$INVENTORY" \
  --vault-password-file "$VAULT_PASSWORD_FILE" \
  playbooks/day0/prepare-mirror.yml
```

After approval, set `oc_mirror_workflow: mirror_to_mirror`, rerun the playbook,
record the digest-pinned release pullspec, and place it in
`disconnected_release_image`. Keep `oc_mirror_run_during_install: false` to
avoid repeating a completed mirror.

### Fully air-gapped: disk transfer

On the connected transfer host use:

```yaml
disconnected_environment: air_gapped
oc_mirror_workflow: mirror_to_disk
```

Run `prepare-mirror.yml`, transfer the complete archive, repository checkout,
Vault, and trusted CA through the approved media process. On the disconnected
control host use:

```yaml
assisted_auth_mode: onprem
assisted_api_url: https://assisted-service.example.com/api/assisted-install/v2
oc_mirror_workflow: disk_to_mirror
```

Run `prepare-mirror.yml` again to populate the disconnected registry. Set the
exact release digest produced by `oc-mirror`.

### Install from the mirror

```bash
./scripts/validate.sh "$INVENTORY"
ansible-playbook -i "$INVENTORY" \
  --vault-password-file "$VAULT_PASSWORD_FILE" \
  playbooks/day0/install.yml
```

Verify that nodes use the mirrored release and retain the mirror workspace,
mapping resources, logs, and installation evidence.

## Scenario 3: connected installation with the GUI interface

### Start the GUI

```bash
export INSTALLER_UI_AUTH_TOKENS="$(openssl rand -hex 24)=admin"
podman compose up --build
```

Open `http://127.0.0.1:8080` through an SSH tunnel or approved TLS reverse
proxy and enter the token value before `=admin`.

### Create the profile

1. Create a uniquely named profile such as `production-a`.
2. In **Cluster**, set connected mode, identity, version, topology, networks,
   VIP allocation, and VIPs when static.
3. In **Assisted Installer API**, review every default and configure SaaS or
   on-premises authentication, proxies, NTP, encryption, and API overrides.
4. In **Network**, select DHCP or static, then configure the interface/bond,
   gateway, DNS, MTU, IPv6, and custom NMState when required.
5. In **BMC and Redfish**, review certificate, virtual-media, boot, power, and
   timeout settings.
6. In **Runtime**, select ISO delivery and all retry/artifact settings.
7. In **Hosts**, add exactly the declared master and worker counts. Configure
   iLO/iDRAC/generic/auto, HTTPS endpoint, credentials, role, hostname, static
   IP when used, disk ID, disks to preserve, NIC map, and host API overrides.
8. In **Credentials and secrets**, enter pull secret, SSH key, Assisted
   Installer token, and Vault password. These are encrypted before saving.
9. Review **Day-2 GitOps** but leave push and bootstrap disabled during Day-0.
10. Select **Validate configuration**, correct all errors, and save the profile.

### Execute the connected workflow

Run these allowlisted actions in order:

1. **Run preflight**.
2. **Discover BMC inventory**; inspect discovered NICs and disk identifiers.
3. Update `installation_disk_id` where necessary and validate again.
4. **Boot discovery ISO**, entering `BOOT`.
5. **Install OpenShift**, entering `INSTALL`.
6. Follow the live redacted log until the run succeeds.
7. Download the non-sensitive report and retrieve kubeconfig/password from the
   protected `/data/artifacts/<profile>/` volume.
8. Optionally **Eject virtual media**, entering `EJECT`.

## Scenario 4: disconnected installation with the GUI interface

Create the profile as in Scenario 3, but configure **Disconnected** completely:

1. Select `deployment_mode=disconnected`.
2. Select partially disconnected or air-gapped.
3. Configure workspace/archive paths, registry, TLS verification, CA,
   parallelism, retries, archive size, channel, minimum/maximum release,
   architecture, graph, and optional images/Helm content.
4. Supply mirror authentication JSON when it differs from the pull secret.
5. Supply the digest-pinned `disconnected_release_image` before installation.
6. For on-premises Assisted Service, supply its URL and access token.

Execute each phase separately:

1. Select `oc_mirror_workflow=render_only`, save, validate, and run
   **Prepare release mirror** with confirmation `MIRROR`.
2. Inspect the rendered ImageSetConfiguration and report.
3. Change to `mirror_to_mirror`, `mirror_to_disk`, or `disk_to_mirror` for the
   approved transfer phase; save, validate, and confirm `MIRROR` again.
4. Update the mirrored release digest, set
   `oc_mirror_run_during_install=false`, and validate.
5. Run preflight and BMC discovery.
6. Boot the ISO with `BOOT` and install with `INSTALL`.
7. Retain `/data` evidence and mirror artifacts outside the container lifecycle.

Air-gapped environments require separate GUI instances on the connected and
disconnected hosts, with the `/data` content and mirror archive transferred by
the approved offline process. The GUI does not bypass an air gap.

## Scenario 5: Day-2 activities with playbooks

Do not begin until the target cluster is healthy and its kubeconfig is active.

### Configure desired state

In `60-day2-gitops.yml`, review every variable and set at least:

```yaml
day2_gitops_cluster_name: production-a
day2_gitops_openshift_minor_version: "4.18"
day2_gitops_profile: enterprise
day2_gitops_enabled_operators:
  - gitops
  - acm
  - acs
  - odf
  - openshift_virtualization
day2_gitops_operator_overrides: {}
day2_gitops_additional_operators: {}
day2_gitops_operands: {}
day2_gitops_repository_url: git@github.com:example/openshift-desired-state.git
day2_gitops_repository_branch: main
day2_gitops_repository_path: clusters
day2_gitops_git_push_enabled: false
day2_gitops_git_push_confirmed: false
day2_gitops_bootstrap_enabled: false
```

Replace `day2_gitops_operands` with complete Custom Resources for the selected
operators. Plain Kubernetes Secrets and common inline credential fields are
rejected. Store Git credentials only in the encrypted Vault.

### Render and validate without changes

```bash
ansible-playbook -i "$INVENTORY" \
  --vault-password-file "$VAULT_PASSWORD_FILE" \
  playbooks/day2/render-gitops.yml
kustomize build artifacts/day2-gitops-rendered/clusters/production-a
```

Review operator channels, dependencies, namespaces, install-plan approval,
sync waves, operands, and the Day-2 `oc-mirror` configuration.

### Publish and bootstrap

After approval set:

```yaml
day2_gitops_git_push_enabled: true
day2_gitops_git_push_confirmed: true
day2_gitops_bootstrap_enabled: true
```

Then run:

```bash
ansible-playbook -i "$INVENTORY" \
  --vault-password-file "$VAULT_PASSWORD_FILE" \
  playbooks/day2/bootstrap-gitops.yml
oc get applications.argoproj.io -n openshift-gitops
oc get subscriptions.operators.coreos.com -A
oc get csv -A
```

For disconnected Day-2, mirror the generated operator ImageSetConfiguration
and apply the `oc-mirror` IDMS, ITMS, and CatalogSource outputs before GitOps
bootstrap.

## Scenario 6: Day-2 activities with the GUI interface

1. Open the saved cluster profile.
2. In **Day-2 GitOps**, select a built-in profile or `custom`.
3. Select only required operators. Dependencies are resolved automatically.
4. Review the OpenShift minor version, approval mode, channel adaptation,
   operator overrides, extra packages, catalog images, Git URL/branch/path,
   project, render root, and checkout directory.
5. Enter complete operand resources in the structured editor.
6. Enter Git username/token or SSH key in **Credentials and secrets** only when
   the selected authentication mode requires it.
7. Leave push and bootstrap disabled, save, validate, and select
   **Render Day-2 GitOps**.
8. Download and review the render report and desired-state tree.
9. For disconnected clusters, execute the generated operator mirror workflow
   outside or through the approved mirror action and apply its mapping/catalog
   resources before bootstrap.
10. Enable both Git push switches and bootstrap only after approval.
11. Save and validate again.
12. Select **Publish and bootstrap GitOps**, enter `GITOPS`, and monitor the
    redacted execution stream.
13. Verify root and child Applications, Subscriptions, InstallPlans, CSVs, and
    operand health from OpenShift. Subsequent changes are Git commits reconciled
    by Argo CD, not ad-hoc GUI or Ansible mutations.

## Completion evidence

For every scenario retain:

- the validated non-secret configuration preview;
- the encrypted Vault and its separately protected password mechanism;
- BMC discovery, mirror, Assisted Installer, and Ansible execution logs;
- rendered GitOps content and commit SHA where applicable;
- kubeconfig and kubeadmin password in protected storage;
- cluster, node, ClusterOperator, Argo CD Application, Subscription, InstallPlan,
  and CSV status relevant to the selected path.

See [Day-0 bare-metal installation](day0-bare-metal-installation.md),
[Day-2 GitOps operator deployment](day2-gitops-operator-deployment.md), and
[Containerized GUI Interface](gui-interface.md) for detailed contracts and
troubleshooting boundaries.
