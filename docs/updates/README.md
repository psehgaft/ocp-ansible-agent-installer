# RHOSO Updates Lab

This guide covers managing and applying updates to Red Hat OpenStack Services on OpenShift (RHOSO) 18 deployments.

## Overview

RHOSO updates include:
- Operator updates (OLM-managed)
- Control plane updates
- Data plane updates
- Container image updates
- Configuration updates

Updates in RHOSO leverage OpenShift's operator lifecycle management and GitOps practices for controlled, automated updates.

## Prerequisites

- Running RHOSO 18 deployment
- OpenShift cluster-admin privileges
- Backup of current environment
- Access to Red Hat registries
- Maintenance window scheduled

## Update Types

### 1. Operator Updates (Z-stream)

Minor updates to the OpenStack operator managed by Operator Lifecycle Manager (OLM).

### 2. Minor Version Updates (Y-stream)

Updates within the same major version (e.g., 18.0 to 18.1).

### 3. Configuration Updates

Changes to OpenStack service configurations without version changes.

## Update Process

### Phase 1: Pre-Update Preparation

#### 1.1 Backup Current Environment

```bash
# Backup etcd
oc login -u system:admin
/usr/local/bin/cluster-backup.sh /home/core/backup

# Backup OpenStack databases
oc exec -it mariadb-0 -n openstack -- mysqldump --all-databases > openstack-db-backup.sql

# Backup OpenStack configurations
oc get openstackcontrolplane openstack -n openstack -o yaml > openstack-controlplane-backup.yaml
oc get openstackdataplanenodeset -n openstack -o yaml > openstack-dataplane-backup.yaml
```

#### 1.2 Health Check

```bash
# Check operator health
oc get csv -n openstack-operators
oc get pods -n openstack-operators

# Check control plane health
oc get openstackcontrolplane -n openstack
oc get pods -n openstack

# Verify OpenStack services
openstack service list
openstack compute service list
openstack network agent list
```

#### 1.3 Review Update Notes

```bash
# Check available updates
oc get packagemanifest openstack-operator -n openshift-marketplace -o yaml

# Review update documentation
# Check errata and known issues
```

### Phase 2: Update Operators

#### 2.1 Update OpenStack Operator

Operators can be updated automatically or manually based on approval strategy.

**Automatic Updates:**
```bash
# Check subscription approval strategy
oc get subscription openstack-operator -n openstack-operators -o yaml

# If installPlanApproval is "Automatic", updates happen automatically
```

**Manual Updates:**
```bash
# List available install plans
oc get installplan -n openstack-operators

# Approve pending install plan
oc patch installplan <install-plan-name> -n openstack-operators \
  --type merge --patch '{"spec":{"approved":true}}'
```

#### 2.2 Verify Operator Update

```bash
# Check CSV status
oc get csv -n openstack-operators

# Verify operator pods
oc get pods -n openstack-operators

# Check operator logs
oc logs -n openstack-operators -l name=openstack-operator
```

### Phase 3: Update Control Plane

#### 3.1 Update Control Plane Services

The operator automatically updates control plane services based on the operator version.

```bash
# Monitor control plane update
oc get openstackcontrolplane -n openstack -w

# Check individual service updates
oc get pods -n openstack

# View update progress
oc describe openstackcontrolplane openstack -n openstack
```

#### 3.2 Rolling Update of Services

Services update in a controlled rolling fashion:

```bash
# Monitor service-by-service updates
watch "oc get pods -n openstack | grep -E 'keystone|nova|neutron|cinder|glance|placement'"
```

#### 3.3 Verify Control Plane

```bash
# Check all services are running
oc get pods -n openstack

# Verify OpenStack API access
openstack service list
openstack endpoint list

# Test basic operations
openstack flavor list
openstack image list
openstack network list
```

### Phase 4: Update Data Plane

#### 4.1 Update Data Plane Node Set

```bash
# Update data plane node set definition if needed
oc edit openstackdataplanenodeset openstack-edpm -n openstack

# Trigger data plane update deployment
cat <<EOF | oc apply -f -
apiVersion: dataplane.openstack.org/v1beta1
kind: OpenStackDataPlaneDeployment
metadata:
  name: openstack-edpm-update
  namespace: openstack
spec:
  nodeSets:
    - openstack-edpm
  servicesOverride:
    - update
EOF
```

#### 4.2 Monitor Data Plane Update

```bash
# Watch deployment progress
oc get openstackdataplanedeployment -n openstack -w

# Check ansible execution
oc logs -n openstack -l app=openstackansibleee

# Verify compute services
openstack compute service list
```

#### 4.3 Rolling Update of Compute Nodes

For minimal downtime, update compute nodes one at a time:

```bash
# Disable compute node
openstack compute service set <hostname> nova-compute --disable

# Migrate instances (optional)
openstack server migrate <server-id>

# Update node
# (Ansible playbooks handle this automatically)

# Enable compute node
openstack compute service set <hostname> nova-compute --enable
```

### Phase 5: Configuration Updates

#### 5.1 Update Control Plane Configuration

```bash
# Edit control plane configuration
oc edit openstackcontrolplane openstack -n openstack

# Or apply updated manifest
oc apply -f examples/manifests/openstackcontrolplane-updated.yaml
```

#### 5.2 Update Data Plane Configuration

```bash
# Update data plane configuration
oc edit openstackdataplanenodeset openstack-edpm -n openstack

# Deploy configuration changes
oc apply -f automation/updates/deploy-config-update.yaml
```

### Phase 6: Post-Update Validation

#### 6.1 Verify All Services

```bash
# Check operator status
oc get csv -n openstack-operators

# Check control plane
oc get openstackcontrolplane -n openstack
oc get pods -n openstack

# Check data plane
oc get openstackdataplanenodeset -n openstack
openstack compute service list
openstack network agent list
```

#### 6.2 Functional Testing

```bash
# Test instance operations
openstack server create --flavor m1.small --image cirros \
  --network private test-update-instance
  
# Wait for instance to be active
openstack server show test-update-instance

# Test volume operations
openstack volume create --size 1 test-update-volume
openstack volume list

# Test network operations
openstack router list
openstack floating ip list

# Cleanup test resources
openstack server delete test-update-instance
openstack volume delete test-update-volume
```

#### 6.3 Workload Validation

```bash
# Verify existing workloads are healthy
openstack server list --all-projects

# Check instance console logs
for server in $(openstack server list -f value -c ID); do
  echo "Checking server: $server"
  openstack console log show $server | tail -n 10
done
```

## Update Strategies

### Strategy 1: Automatic Updates

Configure automatic approval for updates:

```yaml
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: openstack-operator
  namespace: openstack-operators
spec:
  channel: stable-v1.0
  installPlanApproval: Automatic
  name: openstack-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
```

### Strategy 2: Manual Approval

Maintain control over when updates are applied:

```yaml
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: openstack-operator
  namespace: openstack-operators
spec:
  channel: stable-v1.0
  installPlanApproval: Manual
  name: openstack-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
```

### Strategy 3: GitOps-Based Updates

Use ArgoCD for declarative update management (see [GitOps guide](../gitops/README.md)).

## Rollback Procedures

### Rollback Operator Update

```bash
# List previous CSVs
oc get csv -n openstack-operators

# Delete current CSV (will revert to previous)
oc delete csv <current-csv> -n openstack-operators

# Alternatively, restore from backup
oc apply -f openstack-operator-backup.yaml
```

### Rollback Control Plane

```bash
# Restore control plane from backup
oc apply -f openstack-controlplane-backup.yaml

# Monitor rollback
oc get openstackcontrolplane -n openstack -w
```

### Rollback Data Plane

```bash
# Restore data plane configuration
oc apply -f openstack-dataplane-backup.yaml

# Redeploy data plane
oc apply -f automation/updates/rollback-dataplane.yaml
```

## Automation

Automated update workflows are available in [automation/updates/](../../automation/updates/):

```bash
# Run automated update
ansible-playbook automation/updates/update-rhoso.yaml

# Run update with checks
ansible-playbook automation/updates/update-rhoso-with-validation.yaml
```

## Monitoring Updates

### Using OpenShift Console

1. Navigate to Operators → Installed Operators
2. Select openstack-operator
3. View update status and history

### Using CLI

```bash
# Watch operator updates
oc get csv -n openstack-operators -w

# Monitor control plane updates
oc get openstackcontrolplane -n openstack -w

# View events
oc get events -n openstack --sort-by='.lastTimestamp'
```

## Best Practices

1. **Always backup before updates** - Ensure you can rollback
2. **Test updates in non-production** - Validate in lab environment first
3. **Schedule maintenance windows** - Plan for potential downtime
4. **Update during low-traffic periods** - Minimize impact on users
5. **Monitor throughout the process** - Watch for issues in real-time
6. **Validate after updates** - Ensure all services work correctly
7. **Document the process** - Keep records of updates performed
8. **Use GitOps for consistency** - Track changes in version control

## Troubleshooting

### Update Stuck or Failed

```bash
# Check operator logs
oc logs -n openstack-operators -l name=openstack-operator

# Check install plan status
oc get installplan -n openstack-operators
oc describe installplan <plan-name> -n openstack-operators

# Check control plane status
oc describe openstackcontrolplane openstack -n openstack
```

### Service Not Starting After Update

```bash
# Check pod status
oc get pods -n openstack
oc describe pod <pod-name> -n openstack

# View pod logs
oc logs <pod-name> -n openstack

# Check for configuration issues
oc get openstackcontrolplane openstack -n openstack -o yaml
```

### Data Plane Update Issues

```bash
# Check deployment status
oc describe openstackdataplanedeployment -n openstack

# View ansible logs
oc logs -n openstack -l app=openstackansibleee

# Check compute services
openstack compute service list
```

## References

- [RHOSO Update Documentation](https://access.redhat.com/documentation/en-us/red_hat_openstack_services_on_openshift/18.0)
- [Operator Lifecycle Manager](https://docs.openshift.com/container-platform/4.14/operators/understanding/olm/olm-understanding-olm.html)
