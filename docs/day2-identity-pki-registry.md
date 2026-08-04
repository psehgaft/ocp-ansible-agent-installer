# Day-2 Identity, PKI, and Registry

This functional domain configures OpenShift identity, certificate, trust, and registry resources after the platform operators are available.

## Deployment modes

- `direct`: applies resources with `kubernetes.core.k8s`.
- `render`: writes desired state locally without cluster mutation.
- `gitops`: renders desired state for the GitOps reconciliation tree.

## Playbooks

- `playbooks/day2/certificates.yml`
- `playbooks/day2/cert-manager.yml`
- `playbooks/day2/oauth.yml`
- `playbooks/day2/ldap.yml`
- `playbooks/day2/ldap-group-sync.yml`
- `playbooks/day2/quay.yml`
- `playbooks/day2/external-registries.yml`
- `playbooks/day2/mirror-sets.yml`
- `playbooks/day2/registry-proxy.yml`
- `playbooks/day2/trusted-ca.yml`

## Secret policy

Direct mode can consume Ansible Vault values and creates Secrets with `no_log`. Render and GitOps modes reject or omit plaintext Kubernetes Secrets. Use External Secrets, Sealed Secrets, SOPS, or Vault references.

## LDAP synchronization

The LDAP synchronization role creates a ServiceAccount, least-privilege ClusterRole and ClusterRoleBinding, configuration ConfigMap, credential Secret, and CronJob. The default concurrency policy is `Forbid`; successful and failed job histories are limited. Test mode omits `--confirm`. Each execution writes command output into a report ConfigMap.

## Registry resources

Use `registry_resources` for `ImageDigestMirrorSet`, `ImageTagMirrorSet`, image configuration, and related resources. Use `registry_proxy_resource` for the cluster `Proxy`. Pull-secret updates must be supplied through Vault in direct mode or an approved secret-provider reference in rendered modes.
