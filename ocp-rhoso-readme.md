# Plan prerequisites

 - Confirm OCP 4.18 is installed and stable; oc access with cluster-admin.
 - Define your required networks (typical: ctlplane, internalapi, storage, tenant) and IP pools/VIPs.

# Prepare OpenShift for RHOSO

 - Install prerequisite Operators: cert-manager, MetalLB, NMState.
 - Ensure a working StorageClass for RHOSO stateful components (DB/MQ/etc.).

# Configure node networking (NMState)

- Create the required VLANs/bonds/bridges on RHOSO worker nodes (MTU end-to-end).

# Configure service VIPs (MetalLB)

- Create IPAddressPool and advertisements for internal endpoints (e.g., internalapi).
- Annotate RHOSO services to request specific VIPs.

# Install the OpenStack Operator (openstack-operator)

- Install from OperatorHub or CLI (subscription channel example: stable-v1.0).
- Create the OpenStack initialization CR to start the operator.

# Create the RHOSO project

- Create namespace openstack for RHOSO workloads.

# Create osp-secret (credentials)

- Define all required passwords/keys before deploying the control plane (changing later is not supported).

# Create Multus NetworkAttachmentDefinitions

- Define NADs for your networks (docs show macvlan + whereabouts patterns).

# Deploy RHOSO control plane

- Apply OpenStackControlPlane CR: set secret, storageClass, network attachments, and MetalLB LB VIP annotations.
- Validate via pods and the OpenStackClient pod.

# Deploy RHOSO data plane

Prepare RHEL 9.4 nodes and define one/more OpenStackDataPlaneNodeSet objects, then the DataPlane CR

---

# RHOSO 18 on OpenShift (OCP 4.18) — Step-by-step Runbook

> Goal: Deploy **Red Hat OpenStack Services on OpenShift (RHOSO) 18** control plane on OCP, then deploy the RHOSO data plane on RHEL nodes (NodeSets).
> Assumption: You already have a working **OpenShift 4.18** cluster.

---

## Day 1 — Inputs (before you touch the cluster)

- **FQDNs**: OCP API + Ingress configured and reachable.
- **Storage**: At least one StorageClass for RHOSO stateful pods (RWO; RWX if your design needs it).
- **Network design**: VLAN/Subnet/MTU/GW/IP pools for (typical) `ctlplane`, `internalapi`, `storage`, `tenant` (+ optional `external`).
- **VIP strategy**: Which endpoints should be `LoadBalancer` (MetalLB) vs cluster-internal.
- **RHEL dataplane nodes**: RHEL 9.4, routable to required networks, SSH reachable, time sync.

---

## Day 2 — Prepare OpenShift prerequisites

1) Validate OCP health:
```bash
oc get clusterversion
oc get nodes
oc get co
```

2) Install Operators (minimum set commonly required):
- **cert-manager**
- **NMState**
- **MetalLB**

3) Configure MetalLB (L2 example):
- Create `IPAddressPool` (e.g., `internalapi`)
- Create `L2Advertisement`

4) Configure node NIC/VLAN/MTU with NMState:
- Ensure each RHOSO worker has the interfaces that will be referenced by Multus NADs.

---

## Day 3 — Install the OpenStack Operator (openstack-operator)

### CLI path (example)
```bash
oc create ns openstack-operators

cat << 'EOF' | oc apply -f -
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: openstack-operators
  namespace: openstack-operators
spec:
  targetNamespaces:
  - openstack-operators
EOF

cat << 'EOF' | oc apply -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: openstack-operator
  namespace: openstack-operators
spec:
  name: openstack-operator
  channel: stable-v1.0
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF
```

Initialize the operator:
```bash
cat << 'EOF' | oc apply -f -
apiVersion: osp-director.openstack.org/v1beta1
kind: OpenStack
metadata:
  name: openstack
  namespace: openstack-operators
spec: {}
EOF
```

---

## Day 4 — Create the RHOSO namespace and credentials

1) Namespace:
```bash
oc create ns openstack
oc project openstack
```

2) Create `osp-secret` **(passwords are effectively immutable once deployed)**:
```bash
cat << 'EOF' | oc apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: osp-secret
  namespace: openstack
type: Opaque
stringData:
  AdminPassword: "<strong-password>"
  DatabasePassword: "<strong-password>"
  # Add all required keys per RHOSO documentation for your deployment.
EOF
```

---

## Day 5 — Create Multus NetworkAttachmentDefinitions (NADs)

Pattern (macvlan + whereabouts). Adjust `master` + ranges per your design:
```yaml
apiVersion: k8s.cni.cncf.io/v1
kind: NetworkAttachmentDefinition
metadata:
  name: tenant
  namespace: openstack
spec:
  config: |
    {
      "cniVersion": "0.3.1",
      "name": "tenant",
      "type": "macvlan",
      "master": "tenant",
      "ipam": {
        "type": "whereabouts",
        "range": "172.19.0.0/24",
        "range_start": "172.19.0.30",
        "range_end": "172.19.0.70"
      }
    }
```

Create NADs for: `ctlplane`, `internalapi`, `storage`, `tenant` (at minimum).

---

## Day 6 — Deploy the RHOSO control plane (OpenStackControlPlane)

1) Create `OpenStackControlPlane` (skeleton):
```yaml
apiVersion: core.openstack.org/v1beta1
kind: OpenStackControlPlane
metadata:
  name: openstack
  namespace: openstack
spec:
  secret: osp-secret
  storageClass: <your-storageclass>
  # Add service templates, networkAttachments per service, and MetalLB overrides as needed.
```

2) Apply it:
```bash
oc apply -f openstackcontrolplane.yaml
```

3) Monitor reconciliation:
```bash
oc get pods -n openstack -w
oc get openstackcontrolplane -n openstack -o yaml | less
```

4) Use the OpenStackClient pod when available:
```bash
oc get pods -n openstack | grep -i openstackclient
oc rsh -n openstack <openstackclient-pod>
openstack service list
openstack endpoint list
```

---

## Day 7 — Deploy the RHOSO data plane (NodeSets)

1) Prepare RHEL nodes (RHEL 9.4):
- Subscriptions/repos configured
- NICs/VLANs/MTU aligned with `ctlplane/internalapi/storage/tenant`
- SSH connectivity for automation

2) Create one/more `OpenStackDataPlaneNodeSet` objects (compute/networker/etc), then the DataPlane CR.

3) Monitor:
```bash
oc get openstackdataplane -n openstack
oc get openstackdataplanenodeset -n openstack
```

---

## Day 8 — Validation checklist

- Pods: all RHOSO control plane pods Running/Ready
- Keystone: services/endpoints exist
- Compute: `openstack hypervisor list`
- Networking: reachability across `internalapi/storage/tenant`; MetalLB VIPs reachable within L2/L3 boundary
- Launch: image + flavor + network test instance

---

## Day 9 — Recommended automation (GitOps)

- Put **MetalLB**, **NMState**, **NADs**, **OpenStackControlPlane**, **DataPlane NodeSets** in Git.
- Use **OpenShift GitOps (Argo CD)** to apply + drift-correct.

---

