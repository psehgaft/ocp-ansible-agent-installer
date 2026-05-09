# OpenShift Assisted Installer (Dell iDRAC) — Installation Report

## Cluster
- Name: `openshift-llas1`
- Base domain: `ulti.io`
- Version: `4.18`
- Cluster ID: `dedb899c-215a-4d74-9b67-ec6df5968d23`
- InfraEnv ID: `377e3cec-6326-474e-a956-b4a6218f9797`
- API VIP: `10.150.18.254`
- Ingress VIP: `10.150.18.253`

## Outputs
- kubeconfig: `./artifacts/openshift-llas1/auth/kubeconfig`
- kubeadmin password: `./artifacts/openshift-llas1/auth/kubeadmin-password`
- Raw API payloads/responses: `./artifacts/raw`
- Events: `./artifacts/raw/events.json`
- Logs bundle (if available): `./artifacts/reports/assisted-logs.tar.gz`

## Hosts
- llas1ocs1000 (role=master, ip=10.150.18.241, idrac=10.144.1.148, prov_mac=00:4e:01:4f:03:91)
- llas1ocs2000 (role=master, ip=10.150.18.242, idrac=10.144.2.148, prov_mac=00:4e:01:50:a4:11)
- llas1ocs3000 (role=master, ip=10.150.18.243, idrac=10.144.3.148, prov_mac=00:4e:01:48:b2:94)
- llas1ocs1001 (role=worker, ip=10.150.18.244, idrac=10.144.1.188, prov_mac=00:4e:01:4f:03:9e)
- llas1ocs2001 (role=worker, ip=10.150.18.245, idrac=10.144.2.188, prov_mac=00:4e:01:50:a4:1e)
- llas1ocs3001 (role=worker, ip=10.150.18.246, idrac=10.144.3.188, prov_mac=00:4e:01:48:b2:9e)
- llas1ocs1002 (role=worker, ip=10.150.18.247, idrac=10.144.1.147, prov_mac=00:4e:01:4f:03:ab)
- llas1ocs2002 (role=worker, ip=10.150.18.248, idrac=10.144.2.147, prov_mac=00:4e:01:50:a4:2e)
- llas1ocs3002 (role=worker, ip=10.150.18.249, idrac=10.144.3.147, prov_mac=00:4e:01:48:b2:ab)

## Notes
- If the install fails, review:
  1) `events.json`
  2) `cluster-final.json`
  3) iDRAC raw files under `raw/idrac-*.json`
