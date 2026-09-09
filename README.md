# OpenShift Automation Framework

This repository provides a vendor-neutral OpenShift automation framework. Its canonical Day-0 path installs OpenShift on bare metal in connected, partially disconnected, or fully air-gapped environments. Day-2 content remains separate and must not be invoked by the installation playbook.

The Day-0 installation path uses the Red Hat Assisted Installer API, `oc-mirror` v2, Ansible Vault, and standards-based Redfish. HPE iLO, Dell iDRAC, and other standards-compliant BMCs use the same `bmc_*` contract. Dell-specific `idrac_*` variables remain compatibility aliases only.

For the complete installation procedure, variable catalog, network examples, and disconnected workflows, see [Day-0 bare-metal installation](docs/day0-bare-metal-installation.md).

## Architecture

The framework separates:

1. **Day-0 installation** — Redfish discovery, virtual media, Assisted Installer, host matching, and installation evidence.
2. **Platform operators** — catalog-driven installation and operator readiness.
3. **Operands and Day-2 configuration** — identity, PKI, registries, networking, storage, observability, backup, health, and platform services.
4. **GitOps desired state** — Kustomize-first Argo CD/OpenShift GitOps reconciliation.
5. **Validation and reporting** — normalized component results with Markdown, JSON, HTML, and CSV outputs.

Important directories:

```text
framework/                   Component, operand, profile, and result schemas
gitops/                      Argo CD bootstrap and Kustomize desired state
group_vars/                  Global defaults and examples
inventories/                 Environment-specific inventories and overrides
playbooks/day0/              Bare-metal discovery and Assisted Installer
playbooks/day2/              Day-2 cluster and platform configuration
playbooks/audit_vmware_network.yml
roles/                       Reusable Ansible roles
reports/                     Generated validation evidence
workshop/                    Antora workshop source
```

## Requirements

- Python 3.11 or later
- `ansible-core` 2.18 or later
- `oc`, `curl`, `jq`, Git, Kustomize, and Helm
- Access to the target BMCs and the selected Assisted Installer service
- `oc-mirror` v2 and a registry for disconnected installation
- Ansible Vault or an external secret manager

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
```

## Inventory model

The sample inventory separates required values, optional API defaults, networking, disconnected mirroring, BMC settings, runtime controls, and encrypted secrets:

```text
inventories/sample/group_vars/
├── all/
│   ├── 00-required.yml
│   ├── 10-assisted-installer.yml
│   ├── 20-network.yml
│   ├── 30-disconnected.yml
│   ├── 40-bmc.yml
│   └── 50-runtime.yml
└── vault.yml.example
```

Environment values override those defaults:

```text
inventories/
├── lab/
├── development/
├── testing/
├── production/
└── examples/
```

Recommended precedence is global defaults, environment group variables, environment host variables, and explicit command-line values. Secrets must be encrypted with Ansible Vault or resolved externally; plaintext passwords, pull secrets, tokens, private keys, and kubeconfigs must not be committed.

## Ansible execution

### 1. Prepare an inventory

```bash
cp -a inventories/sample inventories/lab-cluster
# Use playbooks/day0/create-vault.yml as documented in the Day-0 guide.
```

Use generic Redfish host variables:

```yaml
bmc_type: auto          # auto | ilo | idrac | generic
bmc_endpoint: https://10.10.10.11
bmc_username: "{{ vault_bmc_credentials[inventory_hostname].username }}"
bmc_password: "{{ vault_bmc_credentials[inventory_hostname].password }}"
```

### 2. Validate the repository and inventory

```bash
./scripts/validate.sh inventories/lab-cluster/hosts.yml
ansible-inventory -i inventories/lab-cluster/hosts.yml --list >/dev/null
```

### 3. Discover BMCs

```bash
ansible-playbook \
  -i inventories/lab-cluster/hosts.yml \
  --ask-vault-pass \
  playbooks/day0/discover-bmc.yml
```

### 4. Validate virtual media on one host

Always constrain destructive or boot-changing tests to an explicitly selected host:

```bash
ansible-playbook \
  -i inventories/lab-cluster/hosts.yml \
  --ask-vault-pass \
  playbooks/03-test-virtual-media.yml \
  --limit worker-0 \
  -e test_iso_url=https://mirror.example.com/agent.iso
```

### 5. Run Assisted Installer

```bash
ansible-playbook \
  -i inventories/lab-cluster/hosts.yml \
  --ask-vault-pass \
  playbooks/day0/install.yml
```

The same entry point is used for all connectivity models. Set `deployment_mode`, `disconnected_environment`, and `oc_mirror_workflow` in inventory. The playbook stops after installation credentials and evidence are downloaded; it does not perform Day-2 cluster mutations.

The canonical installation and discovery entry points are under `playbooks/day0/`. Retired wrapper paths are intentionally absent and are prohibited by repository validation.

### 6. Install a platform operator

```bash
ansible-playbook playbooks/install-platform-operator.yml \
  -e operator_lifecycle_component=acm \
  -e operator_lifecycle_deployment_mode=direct
```

### 7. Apply Day-2 configuration directly

```bash
ansible-playbook playbooks/day2/oauth.yml \
  -e day2_deployment_mode=direct
```

Direct mode applies validated resources with `kubernetes.core.k8s` and should be used for controlled administration, break-glass recovery, or environments not yet managed by GitOps.

### 8. Install custom API and Ingress certificates

The canonical playbook for replacing the OpenShift API named certificate and the default Ingress wildcard certificate is:

```text
playbooks/day2/install_certs.yml
```

The playbook accepts local PEM certificate and private-key paths through:

- `WILDCARD_CER`
- `WILDCARD_KEY`
- `API_CER`
- `API_KEY`
- `API_DOMAIN`
- `INGRESS_DOMAIN`

It supports three modes:

- `validate` — default; validates files, PEM parsing, remaining lifetime, hostname coverage, and certificate/private-key matching without changing the cluster.
- `render` — writes a protected manifest under `rendered/day2/certificates/` for local review.
- `apply` — creates the TLS Secrets, updates the default IngressController, reconciles the API named certificate, preserves unrelated API named certificates, and waits for operator recovery.

Validate first:

```bash
ansible-playbook playbooks/day2/install_certs.yml \
  -e WILDCARD_CER=/absolute/path/apps-wildcard.cer \
  -e WILDCARD_KEY=/absolute/path/apps-wildcard.key \
  -e API_CER=/absolute/path/api.cer \
  -e API_KEY=/absolute/path/api.key \
  -e API_DOMAIN=api.cluster.example.com \
  -e INGRESS_DOMAIN='*.apps.cluster.example.com'
```

Render for review:

```bash
ansible-playbook playbooks/day2/install_certs.yml \
  -e CERT_INSTALL_MODE=render \
  -e WILDCARD_CER=/absolute/path/apps-wildcard.cer \
  -e WILDCARD_KEY=/absolute/path/apps-wildcard.key \
  -e API_CER=/absolute/path/api.cer \
  -e API_KEY=/absolute/path/api.key \
  -e API_DOMAIN=api.cluster.example.com \
  -e INGRESS_DOMAIN='*.apps.cluster.example.com'
```

Back up the current configuration and apply:

```bash
mkdir -p evidence/certificates
oc get apiserver cluster -o yaml \
  > evidence/certificates/apiserver-before.yaml
oc get ingresscontroller default -n openshift-ingress-operator -o yaml \
  > evidence/certificates/ingresscontroller-before.yaml

ansible-playbook playbooks/day2/install_certs.yml \
  -e CERT_INSTALL_MODE=apply \
  -e WILDCARD_CER=/absolute/path/apps-wildcard.cer \
  -e WILDCARD_KEY=/absolute/path/apps-wildcard.key \
  -e API_CER=/absolute/path/api.cer \
  -e API_KEY=/absolute/path/api.key \
  -e API_DOMAIN=api.cluster.example.com \
  -e INGRESS_DOMAIN='*.apps.cluster.example.com'
```

Certificate changes trigger progressive reconciliation of Ingress router and kube-apiserver operands. Keep the original administrative session open until both ClusterOperators are Available and not Degraded, the API presents the expected certificate, a representative route presents the wildcard certificate, and a new login succeeds.

Rendered manifests contain private keys and must never be committed. Use SOPS, Sealed Secrets, External Secrets, Vault integration, or another approved encrypted-secret mechanism for GitOps delivery.

## GitOps execution

Kustomize is the default composition mechanism. Helm is used only when a chart provides meaningful lifecycle value.

### 1. Configure the Git source

Review the repository URL, target revision, cluster destination, project, and environment overlay under `gitops/bootstrap/` and `gitops/overlays/`.

### 2. Render desired state without cluster changes

```bash
ansible-playbook playbooks/gitops-foundation.yml \
  -e gitops_foundation_mode=render \
  -e gitops_foundation_environment=lab
```

### 3. Bootstrap OpenShift GitOps

```bash
ansible-playbook playbooks/gitops-foundation.yml \
  -e gitops_foundation_mode=gitops \
  -e gitops_foundation_environment=production
```

GitOps mode renders desired-state manifests and bootstraps standardized `AppProject`, `Application`, root application, and `ApplicationSet` resources. Generated files are never committed or pushed automatically unless the explicit Git-write workflow is enabled.

### 4. Validate desired state

```bash
kustomize build gitops/overlays/production >/tmp/production.yaml
kubeconform -strict -ignore-missing-schemas /tmp/production.yaml
```

Direct and GitOps modes must describe equivalent Kubernetes desired state. Direct mode applies that state immediately; GitOps mode publishes it for Argo CD reconciliation.

## Deployment modes

Components declare supported modes in `framework/components.yml`:

- `direct`: apply resources with Ansible.
- `render`: generate desired-state manifests without applying them.
- `gitops`: render manifests and reconcile through OpenShift GitOps.

The dependency resolver distinguishes mandatory dependencies, recommendations, conflicts, ordering-only constraints, and required external configuration.

## Validation and reports

Every component should emit the normalized `component_result` contract defined in `framework/component-result.schema.yml`.

Generate reports:

```bash
ansible-playbook playbooks/generate-component-report.yml \
  -e component_results=@reports/input/component-results.json
```

Outputs are written under `reports/output/` as Markdown, JSON, HTML, and CSV.

## VMware network audit

The read-only VMware network audit is located at:

```text
playbooks/audit_vmware_network.yml
```

Run it with encrypted or externally resolved credentials:

```bash
ansible-playbook playbooks/audit_vmware_network.yml \
  --ask-vault-pass \
  -e vcenter_hostname=vcenter.example.com \
  -e vcenter_username=auditor@vsphere.local
```

`vcenter_password` must come from Ansible Vault or an external secret lookup. The playbook does not contain a default password.

## Quality gates

Pull requests run YAML parsing, `yamllint`, `ansible-lint`, Python compilation, Ruff, pytest, inventory validation, Ansible syntax checks, Molecule when scenarios exist, ShellCheck, actionlint, Kustomize, Helm, kubeconform, secret scanning, Antora build, and documentation link validation.

Cluster integration tests, destructive tests, and scheduled compatibility tests are separate workflows with explicit credentials and approval boundaries.

## Workshop

The Antora workshop contains:

- the architecture-aligned framework learning path; and
- the retained Redfish and Assisted Installer source material.

The custom serving-certificate lesson is available at `4.4.8.1 Custom API and Ingress Certificates` and documents validation, rendering, application, endpoint verification, rollout impact, and rollback.

Build it with:

```bash
npm install -g @antora/cli @antora/site-generator
antora default-site.yml
```

## Migration and deprecation

See:

- [Repository compliance audit](docs/repository-compliance-audit.md)
- [Deprecation inventory](docs/deprecated-files.md)
- [Migration from iDRAC](docs/migration-from-idrac.md)
- [Architecture](docs/architecture.md)
- [Troubleshooting](docs/troubleshooting.md)

Do not restore retired compatibility wrappers. Canonical workflow paths and the migration conditions are enforced by `framework/workflows.yml` and CI.

## Security boundary

Never commit plaintext credentials, pull secrets, Assisted Installer tokens, kubeconfigs, private keys, vCenter passwords, or generated secret payloads. Use Ansible Vault, External Secrets, Sealed Secrets, SOPS, or Vault references.
