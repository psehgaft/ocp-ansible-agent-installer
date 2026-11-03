# OpenShift vSphere Config + ACM/Hive CRDs Generator (Ansible)

This project generates:
- `install-config.yaml` for each cluster (IPI vSphere)
- `cluster.yaml` with ACM/Hive CRDs: Project, ClusterDeployment, ManagedCluster, MachinePool, Secrets, KlusterletAddonConfig

## Quick start
```bash
python3 -m pip install --user ansible
$EDITOR vars/clusters.yml                 # edit your variables
ansible-playbook site.yml                 # render files
ls -R output/
```

## What gets rendered
- `output/<cluster>/install-config.yaml`
- `output/<cluster>/cluster.yaml`

The `cluster.yaml` embeds the **base64** of `install-config.yaml` automatically.

## Security (recommended)
Move sensitive values to an encrypted file and include it via `vars_files`:
```yaml
vars_files:
  - vars/clusters.yml
  - vars/secure.yml  # encrypted with Ansible Vault
```
Encrypt with: `ansible-vault encrypt vars/secure.yml`

## References (APA)
- Red Hat. (2025). *Installing OpenShift on vSphere*. Red Hat Documentation.
- Red Hat. (2025). *Hive API: ClusterDeployment, MachinePool*. Red Hat/OpenShift Docs.
- Red Hat. (2025). *Red Hat Advanced Cluster Management for Kubernetes*. Red Hat Documentation.
- Ansible. (2025). *Templating (Jinja2)*. Ansible Documentation.
- Ansible. (2025). *Ansible Vault — Encrypting sensitive data*. Ansible Documentation.
