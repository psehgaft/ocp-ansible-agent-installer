# Environment inventories

Use one directory per environment:

```text
inventories/
├── lab/
├── development/
├── testing/
├── production/
└── examples/
```

Each environment may contain `hosts.yml`, `group_vars/`, and `host_vars/`. Copy `inventories/sample` to obtain the categorized Day-0 layout. Secrets belong in encrypted Vault files or external credential systems; create the inventory vault with `playbooks/day0/create-vault.yml`.

Task 2 selection and repository controls belong in
`group_vars/all/60-day2-gitops.yml`. Git credentials belong only in the
encrypted `group_vars/vault.yml`.

See [the Day-0 bare-metal installation guide](../docs/day0-bare-metal-installation.md) for connected, partially disconnected, and air-gapped examples.
See [the Day-2 GitOps operator guide](../docs/day2-gitops-operator-deployment.md) for render, publish, bootstrap, and operator mirroring.
