# Changelog

## Unreleased

- Added the containerized GUI interface, dynamic repository-backed forms, encrypted
  profile generation, role-based access, confirmation gates, streamed and
  redacted execution logs, persistent audit/run history, and a complete runtime
  container.
- Added a GitOps-only Day-2 renderer with selectable profiles, dependency
  resolution, structured operands, Kustomize validation, explicit Git push
  controls, and minimal OpenShift GitOps bootstrap.
- Added a curated catalog of 52 Red Hat and requested ecosystem operators plus
  a generic contract for any additional OperatorHub or private catalog package.
- Added per-render oc-mirror v2 operator image sets for connected, partially
  disconnected, and fully air-gapped workflows.
- Added Vault-backed Git credentials, live PackageManifest validation, secret
  rejection, deterministic ownership boundaries, tests, and documentation.
- Recorded the graphical container runner as deferred GUI interface scope.

## 2.0.0 — 2026-07-30

- Replaced Dell-specific iDRAC discovery with standard Redfish discovery.
- Added HPE iLO, Dell iDRAC, generic Redfish, and automatic vendor-selection values.
- Added dynamic discovery of Redfish Systems, Managers, and Chassis resource IDs.
- Added cross-vendor NIC normalization, deterministic provisioning-MAC selection, and an explicit MAC-to-logical-NIC mapping override for production bonds.
- Replaced Dell virtual-media and power modules with `community.general.redfish_command`.
- Added inventory, group variables, Vault example, validation scripts, reports, migration guidance, and a Showroom-style workshop.
- Preserved backward-compatible `idrac_ip`, `idrac_user`, and `idrac_password` aliases for staged migrations.
