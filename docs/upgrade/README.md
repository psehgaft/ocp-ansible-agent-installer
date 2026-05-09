# RHOSP 17.1 to RHOSO 18 Upgrade Using Adoption

This guide covers the process of upgrading/adopting Red Hat OpenStack Platform (RHOSP) 17.1 to Red Hat OpenStack Services on OpenShift (RHOSO) 18.

## Overview

The adoption process migrates an existing RHOSP 17.1 deployment to RHOSO 18 running on OpenShift. This is not an in-place upgrade but rather a migration that involves:

1. Deploying RHOSO 18 infrastructure on OpenShift
2. Migrating control plane services from RHOSP to RHOSO
3. Migrating data plane (compute nodes) to RHOSO management
4. Validating the migrated environment

## Prerequisites

### Existing Environment

- Working RHOSP 17.1 deployment
- All RHOSP services healthy and operational
- Complete backup of the RHOSP environment
- Database dumps of all OpenStack databases
- Configuration backups

### Target Environment

- OpenShift 4.14 or later cluster
- Sufficient resources to run both environments during migration
- Network connectivity between RHOSP and OpenShift environments
- Storage backend accessible from both environments

### Tools Required

- `openstack` CLI configured for RHOSP 17.1
- `oc` CLI for OpenShift
- Ansible 2.9 or later
- Migration tooling from Red Hat

## Pre-Adoption Preparation

### 1. Assess Current Environment

```bash
# Document current RHOSP environment
openstack --os-cloud rhosp17 service list
openstack --os-cloud rhosp17 compute service list
openstack --os-cloud rhosp17 network agent list

# Check workload inventory
openstack --os-cloud rhosp17 server list --all-projects
openstack --os-cloud rhosp17 volume list --all-projects
openstack --os-cloud rhosp17 network list --all-projects
```

### 2. Backup RHOSP Environment

```bash
# Backup databases
sudo podman exec -it galera-bundle-podman-0 \
  mysqldump --all-databases > rhosp17-databases-backup.sql

# Backup configurations
sudo tar -czf /root/rhosp17-configs-backup.tar.gz \
  /var/lib/config-data/puppet-generated/
```

### 3. Prepare OpenShift Cluster

```bash
# Create namespaces
oc create namespace openstack
oc create namespace openstack-operators

# Install RHOSO operators (see installation guide)
oc apply -f examples/manifests/operators/openstack-operator-subscription.yaml
```

## Adoption Process

### Phase 1: Deploy RHOSO Control Plane Infrastructure

#### 1.1 Install RHOSO Operators

```bash
# Install OpenStack operator
oc apply -f automation/upgrade/00-operators.yaml

# Wait for operators to be ready
oc wait --for=condition=Ready csv -l operators.coreos.com/openstack-operator.openstack-operators \
  -n openstack-operators --timeout=600s
```

#### 1.2 Prepare OpenStack Control Plane Configuration

```bash
# Extract RHOSP configuration
cd automation/upgrade
ansible-playbook extract-rhosp-config.yaml

# Review extracted configuration
cat /tmp/rhosp17-extracted-config.yaml
```

### Phase 2: Migrate Databases

#### 2.1 Stop RHOSP Control Plane Services

```bash
# Stop OpenStack services on RHOSP (maintain data plane)
sudo pcs resource disable openstack-cinder-api
sudo pcs resource disable openstack-nova-api
sudo pcs resource disable openstack-neutron-server
# ... stop other control plane services
```

#### 2.2 Migrate Database Data

```bash
# Create database secrets in OpenShift
oc create secret generic mariadb-root-password \
  --from-literal=password=<root-password> -n openstack

# Deploy MariaDB on OpenShift
oc apply -f examples/manifests/mariadb.yaml

# Import database data
oc exec -it mariadb-0 -n openstack -- mysql -u root -p < rhosp17-databases-backup.sql
```

### Phase 3: Deploy RHOSO Control Plane

#### 3.1 Create OpenStack Control Plane

```bash
# Apply customized control plane configuration
oc apply -f automation/upgrade/openstackcontrolplane-adopted.yaml

# Monitor deployment
oc get openstackcontrolplane -n openstack -w
```

#### 3.2 Verify Control Plane Services

```bash
# Check all services are running
oc get pods -n openstack

# Verify OpenStack services
export OS_AUTH_URL=$(oc get route keystone-public -n openstack -o jsonpath='{.spec.host}')
openstack service list
openstack compute service list
```

### Phase 4: Migrate Data Plane (Compute Nodes)

#### 4.1 Prepare Compute Nodes

```bash
# Update compute node configurations to point to RHOSO control plane
ansible-playbook -i inventory/compute automation/upgrade/prepare-compute-nodes.yaml
```

#### 4.2 Register Compute Nodes with RHOSO

```bash
# Create data plane node set for existing compute nodes
oc apply -f automation/upgrade/openstackdataplanenodeset-adopted.yaml

# Deploy to existing compute nodes
oc apply -f automation/upgrade/openstackdataplanedeployment-adopted.yaml
```

#### 4.3 Verify Compute Services

```bash
# Check compute services are registered with new control plane
openstack compute service list
openstack hypervisor list
```

### Phase 5: Migrate Workloads (Optional)

If you need to migrate existing instances:

```bash
# List all instances
openstack server list --all-projects

# For each instance, you may need to:
# 1. Create snapshot
# 2. Verify connectivity
# 3. Update metadata if needed
```

### Phase 6: Validation

#### 6.1 Functional Testing

```bash
# Test instance creation
openstack server create --flavor m1.small --image cirros \
  --network private test-instance

# Test volume creation
openstack volume create --size 10 test-volume

# Test network connectivity
openstack floating ip create public
```

#### 6.2 Workload Verification

```bash
# Verify existing workloads
openstack server list --all-projects
for server in $(openstack server list -f value -c ID); do
  openstack server show $server
  openstack console log show $server | tail -n 20
done
```

### Phase 7: Decommission RHOSP

Only after thorough validation:

```bash
# Stop RHOSP services completely
sudo pcs cluster stop --all

# Backup RHOSP environment one final time
sudo tar -czf /root/rhosp17-final-backup.tar.gz /var/lib/config-data/
```

## Rollback Procedures

### If Issues Occur During Migration

```bash
# Restore RHOSP control plane
sudo pcs cluster start --all

# Restore databases from backup
mysql -u root -p < rhosp17-databases-backup.sql

# Reconfigure compute nodes to use RHOSP
ansible-playbook -i inventory/compute automation/upgrade/rollback-compute-nodes.yaml
```

## Automation

For automated adoption process, use the playbooks in [automation/upgrade/](../../automation/upgrade/):

```bash
# Run complete adoption workflow
ansible-playbook -i inventory automation/upgrade/adopt-rhosp-to-rhoso.yaml
```

## Post-Adoption Tasks

### Update Documentation

- Update runbooks for RHOSO
- Update disaster recovery procedures
- Update monitoring and alerting

### Training

- Train operations team on RHOSO management
- Update operational procedures
- Document differences from RHOSP

## Troubleshooting

### Database Migration Issues

```bash
# Check database connectivity
oc exec -it mariadb-0 -n openstack -- mysql -u root -p -e "SHOW DATABASES;"

# Verify database users
oc exec -it mariadb-0 -n openstack -- mysql -u root -p -e "SELECT user, host FROM mysql.user;"
```

### Service Registration Issues

```bash
# Check service endpoints
openstack endpoint list

# Verify service catalog
openstack catalog list
```

### Compute Node Connection Issues

```bash
# Check compute service status
openstack compute service list

# View compute node logs
oc logs -n openstack -l app=nova-compute
```

## Best Practices

1. **Perform adoption during maintenance window** - Schedule downtime for critical steps
2. **Test in non-production first** - Practice the adoption process in a lab environment
3. **Maintain both environments** - Keep RHOSP running until RHOSO is fully validated
4. **Incremental migration** - Consider migrating workloads in phases
5. **Document everything** - Keep detailed logs of all steps and issues encountered

## References

- [RHOSO Adoption Guide](https://access.redhat.com/documentation/en-us/red_hat_openstack_services_on_openshift/18.0/html/adopting_red_hat_openstack_platform_to_red_hat_openstack_services_on_openshift/)
- [RHOSP 17.1 Documentation](https://access.redhat.com/documentation/en-us/red_hat_openstack_platform/17.1)
