# Template System

The repository uses Jinja2 templates to convert validated inventory and component inputs into deterministic OpenShift, Kubernetes, Assisted Installer, Redfish, and RHOSO configuration artifacts.

## Template lifecycle

1. Inputs are declared in inventory, role defaults, the component catalog, or a profile.
2. `scripts/validate_input_contracts.py` validates data types, deployment modes, required values, versions, channels, and secret-safe defaults.
3. An Ansible role renders a `.j2` file with `ansible.builtin.template`.
4. The rendered output is either applied directly, stored under the render directory, or committed for GitOps reconciliation.
5. Static CI parses every Jinja template and the orphan audit verifies that each template is referenced by an active role or playbook.

## Common locations

```text
templates/                       Shared or historical top-level templates
roles/<role>/templates/          Role-owned templates
rendered/                        Generated output; not source-controlled desired state
gitops/                          Canonical GitOps manifests and Kustomize roots
```

Role-owned templates are preferred because ownership, inputs, tasks, and tests remain together.

## Basic example

Template:

```jinja2
apiVersion: v1
kind: Namespace
metadata:
  name: {{ target_namespace }}
  labels:
    app.kubernetes.io/managed-by: {{ management_system | default('ansible') }}
```

Task:

```yaml
- name: Render namespace manifest
  ansible.builtin.template:
    src: namespace.yml.j2
    dest: "{{ render_root }}/namespace.yml"
    mode: "0640"
```

Validated inputs:

```yaml
target_namespace: example-system
management_system: openshift-gitops
```

## Direct, render, and GitOps modes

A template must not create different desired state solely because the deployment mode changes. Mode changes only the delivery mechanism:

- `direct`: render and submit the resulting object with `kubernetes.core.k8s`.
- `render`: write the object to a deterministic local path for inspection.
- `gitops`: write the same desired state to the GitOps staging path for commit and reconciliation.

The architecture-contract validator records canonical hashes where direct and GitOps equivalence is declared.

## Secrets

Never place literal passwords, tokens, pull secrets, private keys, or BMC credentials in templates or defaults. Use Ansible Vault, protected environment variables, Kubernetes Secret references, or External Secrets. Mark tasks that process secret material with `no_log: true`.

## Template authoring rules

- Use YAML-safe quoting for values that may contain punctuation.
- Use `default()` only when the fallback is operationally safe.
- Validate required inputs before rendering.
- Keep conditionals small; move complex normalization into role tasks or filter plugins.
- Render deterministic ordering when byte-level equivalence matters.
- Add the template to a role task immediately; unreferenced templates fail the orphan audit.
- Validate rendered Kubernetes objects with kubeconform in CI.

## Validation

```bash
python scripts/offline_validate.py
python scripts/validate_input_contracts.py
python scripts/validate_repository_assets.py
pytest -q
```

To inspect a rendered GitOps tree:

```bash
kustomize build gitops/operators/<component>
```
