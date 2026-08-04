# Reporting and Validation Hooks

Every component should publish a normalized `component_result` through the `component_validation` role. The contract records requested and effective state, deployment mode, version, installation status, functional checks, warnings, errors, remediation guidance, and evidence.

## Example

```yaml
component_result:
  name: acm
  status: passed
  requested_state: enabled
  effective_state: installed
  deployment_mode: direct
  version: advanced-cluster-management.v2.15.0
  installation:
    subscription: ready
    csv: succeeded
    workloads: ready
  functional_checks:
    hub_available: true
  warnings: []
  errors: []
  remediation_recommendation: ""
  evidence:
    - resource: Subscription/acm
      namespace: open-cluster-management
```

## Report generation

```bash
ansible-playbook playbooks/generate-component-report.yml \
  -e component_results=@reports/input/component-results.json
```

The `component_report` role writes Markdown, JSON, HTML, and CSV files under `reports/output` by default. CSV is a summary; JSON preserves the complete normalized evidence model.

## Validation hook guidance

Operator roles should report Subscription, CSV, and workload readiness. Operand roles should append functional checks specific to the component, such as ACM Hub availability, ODF StorageCluster readiness, Quay route health, or MetalLB address-pool reconciliation.

Evidence entries should identify an exact command or Kubernetes resource. Do not include secret values, tokens, passwords, private keys, or unredacted configuration payloads.
