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

See [the Day-0 bare-metal installation guide](../docs/day0-bare-metal-installation.md) for connected, partially disconnected, and air-gapped examples.
