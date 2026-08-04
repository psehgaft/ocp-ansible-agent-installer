# Day-2 Cluster Operations B

This change covers monitoring, Alertmanager, user workload monitoring, logging and forwarding, Loki, OADP backup, upgrade prechecks, certificate audit, etcd health, ACM Hub, RHACS policies, RHOSO, OpenShift Virtualization, consolidated health checks, and JSON/Markdown reports.

Resource-oriented playbooks support `direct`, `render`, and `gitops` modes. Audit playbooks run read-only command arrays with `changed_when: false` and tolerate individual collection failures so evidence can still be reported.

Production environments should supply reviewed resource definitions and command overrides through inventory. No credentials, endpoints, or environment-specific storage configuration are hard-coded.
