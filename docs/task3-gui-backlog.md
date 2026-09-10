# Task 3 Backlog: Graphical Playbook Runner

Task 3 is intentionally not implemented in Task 2.

The future deliverable will package the validated Ansible runtime, collections,
OpenShift clients, oc-mirror, Git, Kustomize, and this repository into a
container. A Java or Go web application will provide:

- schema-driven discovery of inventory and role variables;
- required-field validation and defaults for optional values;
- grouped forms for cluster, BMC, network, mirror, GitOps, operators, operands,
  and Vault-backed secrets;
- profile and individual operator selection based on
  `framework/day2-operator-catalog.yml`;
- render preview and diff before any Git push or cluster bootstrap;
- explicit confirmation gates for Git writes, BMC actions, installation, and
  GitOps bootstrap;
- streaming playbook output with secret redaction;
- task, host, and overall execution status;
- resumable execution and downloadable non-sensitive reports;
- role-based access, audit history, and concurrent-run protection;
- container health checks and persistent storage for approved artifacts.

The Task 2 YAML catalog and render summary are machine-readable contracts for
this interface. Task 3 should consume them instead of duplicating operator or
variable definitions in application code.
