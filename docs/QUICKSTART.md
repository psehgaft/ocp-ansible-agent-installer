# Quick Start Guide

This guide helps you get started quickly with RHOSO installation or upgrade.

## Choose Your Path

### Path 1: Fresh RHOSO Installation

For installing RHOSO 18 on a new OpenShift cluster.

**Time Required**: 2-4 hours

1. **Prerequisites** (30 minutes)
   ```bash
   # Verify you have OpenShift 4.14+ cluster
   oc version
   
   # Verify you have cluster-admin access
   oc whoami
   oc auth can-i create namespaces
   ```

2. **Quick Install** (1-2 hours)
   ```bash
   # Clone this repository
   git clone https://github.com/gutseb/rhoso-demo-lab-playground.git
   cd rhoso-demo-lab-playground
   
   # Run installation script
   ./automation/installation/install-rhoso.sh
   ```

3. **Configure and Deploy** (1-2 hours)
   ```bash
   # Customize control plane configuration
   vi examples/manifests/openstackcontrolplane.yaml
   
   # Apply configuration
   oc apply -f examples/manifests/openstackcontrolplane.yaml
   
   # Monitor deployment
   oc get openstackcontrolplane -n openstack -w
   ```

**Full Guide**: [Installation Documentation](docs/installation/README.md)

---

### Path 2: RHOSP 17.1 to RHOSO 18 Upgrade

For upgrading/adopting an existing RHOSP 17.1 environment.

**Time Required**: 4-8 hours (plus testing)

1. **Backup RHOSP** (1 hour)
   ```bash
   # Backup databases
   podman exec -it galera-bundle-podman-0 \
     mysqldump --all-databases > /root/rhosp17-db-backup.sql
   
   # Backup configurations
   sudo tar -czf /root/rhosp17-configs.tar.gz /var/lib/config-data/
   ```

2. **Prepare OpenShift** (1-2 hours)
   ```bash
   # Install RHOSO operators
   ./automation/installation/install-rhoso.sh
   ```

3. **Run Adoption** (2-4 hours)
   ```bash
   # Start adoption process
   ./automation/upgrade/adopt-rhosp-to-rhoso.sh
   ```

4. **Validate** (1 hour)
   ```bash
   # Verify OpenStack services
   openstack service list
   openstack compute service list
   openstack server list --all-projects
   ```

**Full Guide**: [Upgrade/Adoption Documentation](docs/upgrade/README.md)

---

### Path 3: GitOps with ArgoCD

For managing RHOSO using GitOps principles.

**Time Required**: 1-2 hours

1. **Install ArgoCD** (30 minutes)
   ```bash
   # Run GitOps setup
   ./automation/gitops/setup-gitops.sh
   ```

2. **Configure Git Repository** (30 minutes)
   ```bash
   # Create GitOps directory structure
   mkdir -p gitops/{operators,controlplane,dataplane}
   
   # Copy example configurations
   cp examples/manifests/*.yaml gitops/
   
   # Commit to Git
   git add gitops/
   git commit -m "Add RHOSO GitOps configurations"
   git push
   ```

3. **Create ArgoCD Applications** (30 minutes)
   - Follow instructions in [GitOps Documentation](docs/gitops/README.md)
   - Configure ArgoCD to watch your Git repository
   - Deploy RHOSO via GitOps

**Full Guide**: [GitOps Documentation](docs/gitops/README.md)

---

## Common First Steps

Regardless of your path, you'll need:

### 1. Verify Prerequisites

```bash
# Check OpenShift cluster
oc get nodes
oc get clusterversion

# Check storage
oc get sc

# Check network
oc get network.config cluster -o yaml
```

### 2. Create Namespaces

```bash
oc create namespace openstack
oc create namespace openstack-operators
```

### 3. Set Up Credentials

```bash
# Create service secrets (customize passwords)
oc create secret generic osp-secret \
  --from-literal=AdminPassword=<admin-password> \
  --from-literal=DatabasePassword=<db-password> \
  -n openstack
```

## Validation

After deployment, validate your RHOSO installation:

```bash
# Check control plane
oc get openstackcontrolplane -n openstack

# Check pods
oc get pods -n openstack

# Get OpenStack credentials
oc get secret openstack-admin-password -n openstack \
  -o jsonpath='{.data.password}' | base64 -d

# Test OpenStack CLI
export OS_AUTH_URL=https://$(oc get route keystone-public -n openstack -o jsonpath='{.spec.host}')
export OS_USERNAME=admin
export OS_PASSWORD=<password-from-above>
export OS_PROJECT_NAME=admin

openstack service list
```

## Next Steps

### Create Test Resources

```bash
# Create network
openstack network create test-network
openstack subnet create --network test-network \
  --subnet-range 192.168.1.0/24 test-subnet

# Create flavor
openstack flavor create --ram 512 --disk 1 --vcpus 1 m1.tiny

# Launch instance (requires image)
openstack server create --flavor m1.tiny \
  --network test-network test-instance
```

### Enable Additional Services

- Configure Cinder backends for block storage
- Set up network isolation
- Configure external networks for floating IPs
- Enable additional services (Heat, Octavia, etc.)

### Set Up Monitoring

- Configure OpenStack metrics collection
- Set up alerting
- Enable logging aggregation

## Troubleshooting

### Operator Not Installing

```bash
oc get csv -n openstack-operators
oc logs -n openstack-operators -l name=openstack-operator
```

### Control Plane Not Ready

```bash
oc describe openstackcontrolplane openstack -n openstack
oc get pods -n openstack
oc logs -n openstack <pod-name>
```

### OpenStack Services Not Accessible

```bash
# Check routes
oc get routes -n openstack

# Check service endpoints
openstack endpoint list
```

## Getting Help

- **Documentation**: See [docs/](docs/) directory
- **Examples**: See [examples/](examples/) directory  
- **Automation**: See [automation/](automation/) directory
- **Issues**: Open an issue on GitHub
- **Red Hat Support**: Use Red Hat Customer Portal

## Useful Commands

```bash
# Watch deployment progress
watch oc get pods -n openstack

# View all OpenStack resources
oc get all -n openstack

# Check operator logs
oc logs -n openstack-operators deployment/openstack-operator

# View events
oc get events -n openstack --sort-by='.lastTimestamp'

# Get resource details
oc describe openstackcontrolplane openstack -n openstack
```

## Learning Resources

- [RHOSO Documentation](https://access.redhat.com/documentation/en-us/red_hat_openstack_services_on_openshift/)
- [OpenStack Documentation](https://docs.openstack.org/)
- [OpenShift Documentation](https://docs.openshift.com/)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
