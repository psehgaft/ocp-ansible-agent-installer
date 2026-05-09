# RHOSO Installation - Connected Environment

This guide covers the installation of Red Hat OpenStack Services on OpenShift (RHOSO) 18 in a connected environment.

## Overview

RHOSO 18 is a cloud infrastructure platform that runs OpenStack control plane services as containers on OpenShift. This guide will walk you through deploying RHOSO on an existing OpenShift cluster with internet connectivity.

## Prerequisites

### Infrastructure Requirements

- OpenShift 4.14 or later cluster
- Minimum 3 control plane nodes
- Minimum 3 compute nodes for OpenStack workloads
- Internet connectivity (connected environment)
- Storage backend (e.g., Ceph, NFS, or local storage)

### Access Requirements

- OpenShift cluster-admin privileges
- Red Hat subscription with RHOSO entitlements
- Access to registry.redhat.io

### Tools Required

- `oc` CLI (matching your OpenShift version)
- `kubectl` CLI
- `git`

## Installation Steps

### 1. Prepare OpenShift Environment

#### Create Namespaces

```bash
oc create namespace openstack
oc create namespace openstack-operators
```

#### Label Nodes for OpenStack Workloads

```bash
# Label compute nodes for OpenStack services
oc label node <node-name> openstack.org/openstack-control-plane=enabled

# Label nodes for compute services (if using separate nodes)
oc label node <node-name> openstack.org/openstack-compute=enabled
```

### 2. Install Operators

#### Install RHOSO Operator

```bash
# Create operator subscription
cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: openstack-operator
  namespace: openstack-operators
spec:
  channel: stable-v1.0
  name: openstack-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF
```

#### Verify Operator Installation

```bash
oc get csv -n openstack-operators
oc get pods -n openstack-operators
```

### 3. Configure OpenStack Control Plane

#### Create OpenStack Control Plane CR

See [examples/manifests/openstackcontrolplane.yaml](../../examples/manifests/openstackcontrolplane.yaml) for a complete example.

```bash
oc apply -f examples/manifests/openstackcontrolplane.yaml
```

#### Monitor Deployment

```bash
# Watch the control plane deployment
oc get openstackcontrolplane -n openstack -w

# Check pod status
oc get pods -n openstack

# View logs
oc logs -n openstack -l app=openstack-controller
```

### 4. Configure Networking

#### Configure Network Isolation

```bash
# Create NetworkAttachmentDefinitions for isolated networks
oc apply -f examples/manifests/network-isolation.yaml
```

### 5. Deploy Data Plane

#### Create Data Plane Node Set

```bash
# Configure compute nodes
oc apply -f examples/manifests/openstackdataplanenodeset.yaml
```

#### Deploy Data Plane

```bash
# Trigger data plane deployment
oc apply -f examples/manifests/openstackdataplanedeployment.yaml
```

### 6. Verify Installation

#### Check Control Plane Status

```bash
oc get openstackcontrolplane -n openstack
oc describe openstackcontrolplane openstack -n openstack
```

#### Access OpenStack CLI

```bash
# Get OpenStack credentials
oc get secret openstack-admin-password -n openstack -o jsonpath='{.data.password}' | base64 -d

# Configure OpenStack CLI
export OS_AUTH_URL=$(oc get route keystone-public -n openstack -o jsonpath='{.spec.host}')
export OS_USERNAME=admin
export OS_PASSWORD=<password-from-above>
export OS_PROJECT_NAME=admin
export OS_USER_DOMAIN_NAME=Default
export OS_PROJECT_DOMAIN_NAME=Default
```

#### Test OpenStack Services

```bash
# List OpenStack services
openstack service list

# List endpoints
openstack endpoint list

# List compute services
openstack compute service list

# List network agents
openstack network agent list
```

## Post-Installation Tasks

### Create Networks and Flavors

```bash
# Create provider network
openstack network create --external --provider-network-type flat \
  --provider-physical-network datacentre provider-network

# Create subnet
openstack subnet create --network provider-network \
  --subnet-range 192.168.100.0/24 \
  --gateway 192.168.100.1 \
  provider-subnet

# Create flavors
openstack flavor create --ram 512 --disk 1 --vcpus 1 m1.tiny
openstack flavor create --ram 2048 --disk 20 --vcpus 1 m1.small
openstack flavor create --ram 4096 --disk 40 --vcpus 2 m1.medium
```

### Configure Security Groups

```bash
# Allow ICMP
openstack security group rule create --proto icmp default

# Allow SSH
openstack security group rule create --proto tcp --dst-port 22 default
```

## Automation

For automated installation, see the automation scripts in [automation/installation/](../../automation/installation/).

## Troubleshooting

### Common Issues

#### Operator Not Installing

```bash
# Check operator pod logs
oc logs -n openstack-operators -l name=openstack-operator

# Check operator subscription
oc get subscription openstack-operator -n openstack-operators -o yaml
```

#### Control Plane Not Ready

```bash
# Check control plane status
oc describe openstackcontrolplane openstack -n openstack

# Check individual service pods
oc get pods -n openstack
oc logs -n openstack <pod-name>
```

#### Network Issues

```bash
# Verify NetworkAttachmentDefinitions
oc get network-attachment-definitions -n openstack

# Check pod network configuration
oc describe pod <pod-name> -n openstack
```

## Next Steps

- [Configure RHOSO Updates](../updates/README.md)
- [Set up GitOps with ArgoCD](../gitops/README.md)
- [Plan RHOSP 17.1 Upgrade](../upgrade/README.md)

## References

- [RHOSO 18 Documentation](https://access.redhat.com/documentation/en-us/red_hat_openstack_services_on_openshift/18.0)
- [OpenStack Operator Documentation](https://github.com/openstack-k8s-operators)
