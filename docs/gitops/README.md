# Install and Discover RHOSO Using GitOps with ArgoCD

This guide covers installing and managing Red Hat OpenStack Services on OpenShift (RHOSO) using GitOps principles with ArgoCD.

## Overview

GitOps provides a declarative approach to managing RHOSO deployments:
- All configurations stored in Git
- ArgoCD continuously monitors and syncs state
- Automated deployment and updates
- Audit trail of all changes
- Easy rollback capabilities

## Prerequisites

### Infrastructure

- OpenShift 4.14 or later cluster
- Sufficient resources for RHOSO workloads
- Access to Red Hat registries

### Tools

- `oc` CLI
- `git` CLI
- ArgoCD CLI (optional)
- Access to Git repository

## Architecture

```
Git Repository (Source of Truth)
    ↓
ArgoCD (Continuous Reconciliation)
    ↓
OpenShift Cluster
    ↓
RHOSO Deployment
```

## Setup GitOps Infrastructure

### 1. Install Red Hat OpenShift GitOps Operator

#### Using OpenShift Console

1. Navigate to Operators → OperatorHub
2. Search for "Red Hat OpenShift GitOps"
3. Click Install
4. Select update channel and approval strategy
5. Click Install

#### Using CLI

```bash
# Create subscription for OpenShift GitOps
cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: openshift-gitops-operator
  namespace: openshift-operators
spec:
  channel: latest
  installPlanApproval: Automatic
  name: openshift-gitops-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF
```

#### Verify Installation

```bash
# Check operator status
oc get csv -n openshift-operators | grep gitops

# Check GitOps pods
oc get pods -n openshift-gitops

# Get ArgoCD URL
oc get route openshift-gitops-server -n openshift-gitops -o jsonpath='{.spec.host}'
```

### 2. Access ArgoCD

#### Get Admin Password

```bash
# Retrieve ArgoCD admin password
ARGOCD_PASSWORD=$(oc get secret openshift-gitops-cluster -n openshift-gitops \
  -o jsonpath='{.data.admin\.password}' | base64 -d)
echo "ArgoCD Admin Password: $ARGOCD_PASSWORD"
```

#### Login to ArgoCD UI

```bash
# Get ArgoCD URL
ARGOCD_URL=https://$(oc get route openshift-gitops-server -n openshift-gitops -o jsonpath='{.spec.host}')
echo "ArgoCD URL: $ARGOCD_URL"

# Open in browser and login with:
# Username: admin
# Password: $ARGOCD_PASSWORD
```

#### Login with ArgoCD CLI (Optional)

```bash
# Install ArgoCD CLI
curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x /usr/local/bin/argocd

# Login to ArgoCD
argocd login $ARGOCD_URL --username admin --password $ARGOCD_PASSWORD
```

## Prepare Git Repository

### 1. Create Repository Structure

```bash
# Clone your repository
git clone <your-repo-url>
cd <your-repo>

# Create directory structure for RHOSO
mkdir -p gitops/{operators,controlplane,dataplane,apps}
```

### 2. Add Operator Configurations

Create `gitops/operators/openstack-operator-subscription.yaml`:

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

### 3. Add Control Plane Configuration

Create `gitops/controlplane/openstackcontrolplane.yaml`:

```yaml
apiVersion: core.openstack.org/v1beta1
kind: OpenStackControlPlane
metadata:
  name: openstack
  namespace: openstack
spec:
  # Add your control plane configuration
  # See examples/manifests/ for templates
```

### 4. Add Data Plane Configuration

Create `gitops/dataplane/openstackdataplanenodeset.yaml`:

```yaml
apiVersion: dataplane.openstack.org/v1beta1
kind: OpenStackDataPlaneNodeSet
metadata:
  name: openstack-edpm
  namespace: openstack
spec:
  # Add your data plane configuration
  # See examples/manifests/ for templates
```

### 5. Commit and Push

```bash
git add gitops/
git commit -m "Add RHOSO GitOps configurations"
git push origin main
```

## Configure ArgoCD Applications

### 1. Create ArgoCD Project

```bash
cat <<EOF | oc apply -f -
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: rhoso
  namespace: openshift-gitops
spec:
  description: RHOSO GitOps Project
  sourceRepos:
    - '<your-repo-url>'
  destinations:
    - namespace: 'openstack*'
      server: https://kubernetes.default.svc
    - namespace: openshift-operators
      server: https://kubernetes.default.svc
  clusterResourceWhitelist:
    - group: '*'
      kind: '*'
EOF
```

### 2. Create Application for Operators

```bash
cat <<EOF | oc apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: rhoso-operators
  namespace: openshift-gitops
spec:
  project: rhoso
  source:
    repoURL: '<your-repo-url>'
    targetRevision: main
    path: gitops/operators
  destination:
    server: https://kubernetes.default.svc
    namespace: openstack-operators
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
EOF
```

### 3. Create Application for Control Plane

```bash
cat <<EOF | oc apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: rhoso-controlplane
  namespace: openshift-gitops
spec:
  project: rhoso
  source:
    repoURL: '<your-repo-url>'
    targetRevision: main
    path: gitops/controlplane
  destination:
    server: https://kubernetes.default.svc
    namespace: openstack
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
  # Wait for operators to be ready first
  sync:
    hooks:
      - name: wait-for-operators
EOF
```

### 4. Create Application for Data Plane

```bash
cat <<EOF | oc apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: rhoso-dataplane
  namespace: openshift-gitops
spec:
  project: rhoso
  source:
    repoURL: '<your-repo-url>'
    targetRevision: main
    path: gitops/dataplane
  destination:
    server: https://kubernetes.default.svc
    namespace: openstack
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
EOF
```

## Managing RHOSO with GitOps

### Making Configuration Changes

```bash
# 1. Update configuration in Git
cd <your-repo>
vim gitops/controlplane/openstackcontrolplane.yaml

# 2. Commit and push
git add gitops/controlplane/openstackcontrolplane.yaml
git commit -m "Update control plane configuration"
git push origin main

# 3. ArgoCD automatically syncs (if auto-sync enabled)
# Or manually sync:
argocd app sync rhoso-controlplane
```

### Monitoring Sync Status

#### Using ArgoCD UI

1. Navigate to ArgoCD URL
2. View application status
3. See sync history and details

#### Using ArgoCD CLI

```bash
# List applications
argocd app list

# Get application status
argocd app get rhoso-controlplane

# View sync history
argocd app history rhoso-controlplane
```

#### Using oc CLI

```bash
# Check application status
oc get application -n openshift-gitops

# Describe application
oc describe application rhoso-controlplane -n openshift-gitops
```

### Rolling Back Changes

```bash
# Using ArgoCD CLI
argocd app rollback rhoso-controlplane <revision-id>

# Or using Git
git revert <commit-hash>
git push origin main
# ArgoCD will automatically sync to previous state
```

## Advanced GitOps Patterns

### 1. Multi-Environment Setup

Create separate directories for different environments:

```
gitops/
├── base/              # Base configurations
├── overlays/
│   ├── dev/          # Development environment
│   ├── staging/      # Staging environment
│   └── production/   # Production environment
```

Use Kustomize for environment-specific configurations:

```yaml
# gitops/overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
bases:
  - ../../base
patchesStrategicMerge:
  - production-overrides.yaml
```

### 2. Sync Waves

Control deployment order using sync waves:

```yaml
apiVersion: core.openstack.org/v1beta1
kind: OpenStackControlPlane
metadata:
  name: openstack
  namespace: openstack
  annotations:
    argocd.argoproj.io/sync-wave: "2"  # Deploy after operators (wave 1)
spec:
  # ...
```

### 3. Health Checks

Define custom health checks:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: rhoso-controlplane
spec:
  # ...
  health:
    timeout: 600
    initialDelay: 30
```

### 4. Automated Pruning

Enable automatic cleanup of resources:

```yaml
syncPolicy:
  automated:
    prune: true      # Delete resources not in Git
    selfHeal: true   # Automatically sync if resources drift
```

## Discovering RHOSO Deployment

### Application Discovery

ArgoCD provides visibility into all RHOSO resources:

```bash
# View all resources managed by ArgoCD
argocd app resources rhoso-controlplane

# View resource tree
argocd app tree rhoso-controlplane
```

### Resource Visualization

In ArgoCD UI:
1. Navigate to application
2. View resource graph
3. See relationships between resources
4. Click resources for details

### Monitoring and Alerts

Integrate ArgoCD with monitoring:

```bash
# Configure Prometheus ServiceMonitor
cat <<EOF | oc apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: argocd-metrics
  namespace: openshift-gitops
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: argocd-metrics
  endpoints:
    - port: metrics
EOF
```

## Automation

Automated GitOps setup scripts are available in [automation/gitops/](../../automation/gitops/):

```bash
# Setup ArgoCD and initial applications
./automation/gitops/setup-gitops.sh

# Deploy RHOSO via GitOps
./automation/gitops/deploy-rhoso.sh
```

## Best Practices

1. **Single Source of Truth** - All configurations in Git
2. **Small, Atomic Commits** - Easy to understand and rollback
3. **Use Branches** - Test changes in feature branches
4. **Enable Auto-Sync** - Let ArgoCD maintain desired state
5. **Monitor Sync Status** - Watch for drift or failures
6. **Use Sync Waves** - Control deployment order
7. **Implement RBAC** - Control who can make changes
8. **Tag Releases** - Mark stable configurations
9. **Document Changes** - Good commit messages
10. **Test in Lower Environments** - Validate before production

## Troubleshooting

### Application Not Syncing

```bash
# Check application status
argocd app get rhoso-controlplane

# View sync errors
oc describe application rhoso-controlplane -n openshift-gitops

# Force sync
argocd app sync rhoso-controlplane --force
```

### Out of Sync Resources

```bash
# Identify out-of-sync resources
argocd app diff rhoso-controlplane

# View resource details
argocd app resources rhoso-controlplane
```

### ArgoCD Performance Issues

```bash
# Check ArgoCD pods
oc get pods -n openshift-gitops

# View logs
oc logs -n openshift-gitops -l app.kubernetes.io/name=argocd-server

# Scale ArgoCD
oc scale deployment argocd-server -n openshift-gitops --replicas=3
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Update RHOSO Config
on:
  push:
    branches: [main]
    paths: ['gitops/**']

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Sync ArgoCD
        run: |
          argocd app sync rhoso-controlplane --grpc-web
```

## References

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [OpenShift GitOps Documentation](https://docs.openshift.com/container-platform/4.14/cicd/gitops/understanding-openshift-gitops.html)
- [GitOps Best Practices](https://www.gitops.tech/)
