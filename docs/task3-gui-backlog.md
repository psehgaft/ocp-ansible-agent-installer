# Task 3 Backlog: Graphical Playbook Runner

Task 3 was intentionally excluded from Task 2 and is implemented by the
containerized Go runner described in [Task 3: Containerized Graphical Playbook
Runner](task3-gui-runner.md).

The delivered baseline packages the validated Ansible runtime, collections,
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

The Task 2 YAML catalog and inventory variable files are the machine-readable
contracts consumed by this interface. Future backlog items are external OIDC,
multi-replica coordination, a Kubernetes Operator deployment, and pluggable
secret-manager backends.
