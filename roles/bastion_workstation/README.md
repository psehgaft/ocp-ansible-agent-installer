# Bastion Workstation Role

Configures a RHEL-compatible bastion host for OpenShift installation, GitOps, Day-2 operations, troubleshooting, and CI validation.

## Installed tooling

- Python 3, pip, Jinja2, PyYAML and JSON Schema support
- Ansible Core and repository collections
- `oc`, `kubectl`, optional `kubelet`
- Kustomize and Helm
- Git, curl, jq, rsync, OpenSSL and DNS tools
- Podman, Buildah and Skopeo

The kubelet package is installed only when `bastion_install_kubelet=true` and remains stopped by default because the bastion is not an OpenShift node.

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
ansible-playbook -i inventories/<environment>/hosts.yml playbooks/configure-bastion.yml
```

Override versions with `bastion_openshift_version`, `bastion_kubernetes_minor`, `bastion_helm_version`, and `bastion_kustomize_version`.

The validation report is written to `/var/tmp/ocp-bastion-toolchain.txt`.

Do not store pull secrets, kubeconfigs, registry credentials, Vault passwords, or SSH private keys in role defaults.
