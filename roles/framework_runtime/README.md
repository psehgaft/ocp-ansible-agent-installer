# Framework Runtime Role

Builds and validates the effective OpenShift platform deployment plan.

## Responsibilities

- Load framework defaults, the selected deployment profile, the component catalog, and compatibility metadata.
- Merge profile features with explicit feature overrides.
- Resolve required component dependencies in deterministic order.
- Reject unknown components, circular dependencies, unsupported deployment modes, and unsupported OpenShift versions.
- Publish `platform_runtime_plan` for downstream orchestration.

## Primary variables

| Variable | Default | Description |
|---|---:|---|
| `platform_profile` | `minimal` | Deployment profile name. |
| `platform_deployment_mode` | `direct` | One of `direct`, `render`, or `gitops`. |
| `platform_openshift_version` | `4.18` | OpenShift minor version used for compatibility validation. |
| `platform_features` | `{}` | Explicit feature overrides applied after profile defaults. |

## Example

```bash
ansible-playbook playbooks/framework-runtime.yml \
  -e platform_profile=enterprise \
  -e platform_deployment_mode=gitops \
  -e platform_openshift_version=4.18 \
  -e '{"platform_features":{"openshift_virtualization":true}}'
```

This role plans execution only. Component implementation and cluster mutation remain the responsibility of component-specific roles and later orchestration pull requests.
