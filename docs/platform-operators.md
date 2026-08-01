# Optional OpenShift platform operators

Run the day-2 playbook after the Assisted Installer workflow has downloaded a working kubeconfig:

```bash
ansible-playbook \
  -i inventories/mycluster/hosts.yml \
  --ask-vault-pass \
  playbooks/install-platform-operators.yml
```

Enable the required components in `inventories/mycluster/group_vars/all.yml`:

```yaml
install_openshift_virtualization_operator: true
install_odf_operator: true
configure_cluster_baremetal_operator: true
```

## OpenShift Virtualization

The role installs package `kubevirt-hyperconverged` in `openshift-cnv` and can create `HyperConverged/kubevirt-hyperconverged`.

```bash
ansible-playbook -i inventories/mycluster/hosts.yml --ask-vault-pass \
  playbooks/install-platform-operators.yml --tags virtualization
```

## OpenShift Data Foundation

The role installs package `odf-operator` in `openshift-storage`. Operand creation is disabled by default because the `StorageSystem` and `StorageCluster` design depends on available devices, storage classes, capacity, encryption, and failure domains.

Set `odf_create_operand: true` only after supplying a reviewed `odf_operand_manifest`.

## Cluster Baremetal Operator

The Bare Metal Operator is part of the OpenShift release payload and is managed by the Cluster Version Operator. The role validates `clusteroperator/baremetal` and can optionally configure `Provisioning/provisioning-configuration`; it does not install a duplicate OperatorHub subscription.

```bash
oc --kubeconfig artifacts/<cluster>/auth/kubeconfig get clusteroperator baremetal
oc --kubeconfig artifacts/<cluster>/auth/kubeconfig get crd baremetalhosts.metal3.io
```
