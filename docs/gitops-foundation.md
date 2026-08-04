# GitOps Foundation

## Source of truth

Kustomize is the default composition mechanism. Helm may be used only for components whose upstream lifecycle is materially easier to manage as a chart.

## Deployment modes

- `direct`: Ansible applies the selected environment overlay with `kubernetes.core.k8s`.
- `render`: Ansible copies the desired-state tree to the render directory and performs no cluster mutation.
- `gitops`: Ansible renders desired state and applies only the Argo CD project and root application required to begin reconciliation.

## Git write policy

Generated files are never committed or pushed automatically. A separate, explicit Git workflow must set both:

```yaml
gitops_git_write_enabled: true
gitops_git_write_workflow_confirmed: true
```

The foundation role itself does not execute `git commit` or `git push`.

## Secret policy

Plaintext secret values are prohibited in rendered output. Supported strategies are:

- External Secrets
- Sealed Secrets
- SOPS-encrypted manifests
- Vault references resolved outside Git

## Argo CD standards

- Every Application uses an AppProject.
- Sync waves are annotations containing quoted integers.
- Automated synchronization uses prune and self-heal only where explicitly configured.
- Server-side apply is the default sync option.
- Root applications point to environment overlays.
- ApplicationSets are used for repeated environment or cluster patterns.
- Health customization belongs in the Argo CD configuration layer and must be tested with the corresponding CRDs.
