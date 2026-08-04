# Day-2 Cluster Operations A

This change covers networking, MetalLB, SR-IOV, NMState, PTP, storage classes, volume snapshots, ODF Day-2, ingress, node configuration, MachineConfig, and Chrony/NTP.

All entry points use `day2_cluster_operations` and support `direct`, `render`, and `gitops` modes. Environment-specific manifests are supplied through inventory variables and are not hard-coded.

MachineConfig and node-level changes must be reviewed for disruption before direct application. Use render or GitOps mode for production change control.
