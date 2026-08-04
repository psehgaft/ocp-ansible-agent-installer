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

Each environment may contain `hosts.yml`, `group_vars/`, and `host_vars/`. Global defaults remain in repository-level `group_vars/`; environment values override them. Secrets belong in encrypted Vault files or external credential systems.
