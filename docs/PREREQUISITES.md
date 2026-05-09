# Installation Prerequisites

This document outlines the prerequisites for deploying RHOSO using the automation in this repository.

## Hardware Requirements

### OpenShift Cluster

- **Control Plane Nodes**: Minimum 3 nodes
  - 8 vCPUs per node
  - 32 GB RAM per node
  - 120 GB storage per node

- **Worker Nodes**: Minimum 3 nodes for OpenStack services
  - 16 vCPUs per node
  - 64 GB RAM per node
  - 200 GB storage per node

- **Compute Nodes** (for OpenStack workloads): As needed
  - Depends on workload requirements
  - Recommended: 32+ vCPUs, 128+ GB RAM per node

### Storage

- Persistent storage provider (e.g., Ceph, NFS, local storage)
- Minimum 500 GB for OpenStack services
- Additional storage for OpenStack workloads (volumes, images)

## Software Requirements

### OpenShift

- OpenShift Container Platform 4.14 or later
- OpenShift CLI (`oc`) matching cluster version

### RHOSO

- RHOSO 18.0 or later
- Access to Red Hat registries (registry.redhat.io)
- Valid Red Hat subscriptions with RHOSO entitlements

### For RHOSP Adoption

- Existing RHOSP 17.1 deployment
- Network connectivity between RHOSP and OpenShift environments

### Tools

- `git` CLI
- `kubectl` CLI (optional, `oc` can be used instead)
- `openstack` CLI (for validation and testing)
- Ansible 2.9 or later (for automation playbooks)
- `jq` (for JSON parsing in scripts)
- `yq` (for YAML manipulation)

### For GitOps

- ArgoCD CLI (optional, UI can be used)
- Git repository for storing configurations

## Access Requirements

### Red Hat Subscriptions

- Red Hat OpenStack Platform subscription
- OpenShift Container Platform subscription
- Access to Red Hat Container Registry

### Network Access

- Internet connectivity (for connected installation)
- Access to:
  - registry.redhat.io
  - quay.io
  - github.com (for cloning this repository)

### Credentials

- OpenShift cluster-admin access
- SSH access to compute nodes (for data plane deployment)
- Git repository access (if using private repository)

## Network Requirements

### OpenShift Cluster Networks

- Control plane network
- Pod network (default OpenShift SDN or OVN-Kubernetes)
- Service network

### OpenStack Networks

- Management network (control plane)
- Storage network
- Tenant network (for VM traffic)
- External/provider network (for floating IPs)

### Firewall Rules

Ensure the following ports are accessible:

- OpenShift API: 6443
- OpenShift Console: 443
- OpenStack APIs: 443 (via OpenShift routes)
- SSH to compute nodes: 22
- VXLAN/Geneve for tenant networks: 4789/6081

## Pre-Installation Steps

### 1. Verify OpenShift Cluster

```bash
# Check cluster version
oc version

# Check node status
oc get nodes

# Check cluster operators
oc get clusteroperators
```

### 2. Verify Subscriptions

```bash
# Check Red Hat subscriptions on OpenShift
# This varies based on your subscription method
```

### 3. Verify Storage

```bash
# Check available storage classes
oc get storageclass

# Verify PVs can be provisioned
```

### 4. Verify Network Connectivity

```bash
# Test connectivity to Red Hat registries
oc run test-registry --image=registry.redhat.io/ubi9/ubi-minimal:latest --restart=Never
oc logs test-registry
oc delete pod test-registry
```

### 5. Set Up Local Environment

```bash
# Clone this repository
git clone https://github.com/gutseb/rhoso-demo-lab-playground.git
cd rhoso-demo-lab-playground

# Install required tools (example for RHEL/Fedora)
sudo dnf install -y git ansible jq

# Install oc CLI
# Download from https://mirror.openshift.com/pub/openshift-v4/clients/ocp/
```

### 6. Configure Authentication

```bash
# Login to OpenShift
oc login <cluster-url> -u <username>

# Verify cluster access
oc whoami
oc auth can-i create namespaces
```

## Next Steps

After verifying all prerequisites:

1. Review the [Installation Guide](docs/installation/README.md)
2. Or review the [Upgrade Guide](docs/upgrade/README.md) if adopting from RHOSP 17.1
3. Follow the step-by-step instructions for your scenario

## Troubleshooting Prerequisites

### Insufficient Permissions

```bash
# Verify you have cluster-admin role
oc get clusterrolebinding | grep cluster-admin
```

### Storage Issues

```bash
# List storage classes
oc get sc

# Check if default storage class is set
oc get sc -o jsonpath='{.items[?(@.metadata.annotations.storageclass\.kubernetes\.io/is-default-class=="true")].metadata.name}'
```

### Registry Access Issues

```bash
# Check registry authentication
oc get secret pull-secret -n openshift-config -o json | \
  jq -r '.data.".dockerconfigjson"' | base64 -d | jq

# Test pulling an image
podman pull registry.redhat.io/ubi9/ubi-minimal:latest
```

## Support

For issues with prerequisites, refer to:
- [Red Hat OpenShift Documentation](https://docs.openshift.com/)
- [Red Hat Customer Portal](https://access.redhat.com/)
