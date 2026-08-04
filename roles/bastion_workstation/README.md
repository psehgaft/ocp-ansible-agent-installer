# Bastion Workstation Role

Configures a RHEL-compatible bastion host for OpenShift installation, GitOps, Day-2 operations, troubleshooting, and CI validation.

## Installed tooling

- Python 3, pip, Jinja2, PyYAML and JSON Schema support
- Ansible Core and the repository collections
- `oc` and `kubectl`
- Optional `kubelet` installation; it remains stopped by default because a bastion is not an OpenShift node
- Kustomize and Helm
- Git, curl, jq, rsync, OpenSSL and DNS tools
- Podman, Buildah and Skopeo

## Inventory

```yaml
all:
  children:
    bastion:
      hosts:
        ocp-bastion.example.com:
          ansible_user: cloud-user
```

## Execution

```bash
ansible-playbook \
  -i inventories/<environment>/hosts.yml \
  playbooks/configure-bastion.yml
```

Override versions when required:

```bash
ansible-playbook \
  -i inventories/<environment>/hosts.yml \
  playbooks/configure-bastion.yml \
  -e bastion_openshift_version=4.18 \
  -e bastion_kubernetes_minor=v1.31 \
  -e bastion_helm_version=v3.17.3 \
  -e bastion_kustomize_version=v5.6.0
```

## Validation

The role validates all version inputs, installs the repository collections, runs version commands for the main tools, and writes the evidence report to:

```text
/var/tmp/ocp-bastion-toolchain.txt
```

## Security

Do not store registry credentials, pull secrets, kubeconfigs, Vault passwords, or SSH private keys in role defaults. Supply them through Ansible Vault, an external secret manager, or protected runtime environment variables.
