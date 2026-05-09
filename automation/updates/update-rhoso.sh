#!/bin/bash
# RHOSO Update Automation Script
# This script helps automate updates to RHOSO deployments

set -e

echo "=== RHOSO Update Automation ==="

NAMESPACE_OPENSTACK="openstack"
NAMESPACE_OPERATORS="openstack-operators"
BACKUP_DIR="/tmp/rhoso-update-backup-$(date +%Y%m%d-%H%M%S)"

# Step 1: Pre-update backup
echo "Step 1: Creating backup..."
mkdir -p ${BACKUP_DIR}

echo "Backing up OpenStack control plane configuration..."
oc get openstackcontrolplane -n ${NAMESPACE_OPENSTACK} -o yaml > ${BACKUP_DIR}/controlplane-backup.yaml

echo "Backing up OpenStack data plane configuration..."
oc get openstackdataplanenodeset -n ${NAMESPACE_OPENSTACK} -o yaml > ${BACKUP_DIR}/dataplane-backup.yaml

# Step 2: Health check
echo "Step 2: Running health checks..."
echo "Checking operator health..."
oc get csv -n ${NAMESPACE_OPERATORS}

echo "Checking control plane health..."
oc get openstackcontrolplane -n ${NAMESPACE_OPENSTACK}

echo "Checking OpenStack services..."
# Add OpenStack service checks

# Step 3: Review available updates
echo "Step 3: Checking for available updates..."
oc get packagemanifest openstack-operator -n openshift-marketplace -o yaml

# Step 4: Approve updates (if manual approval)
echo "Step 4: Checking for pending install plans..."
PENDING_PLANS=$(oc get installplan -n ${NAMESPACE_OPERATORS} -o json | jq -r '.items[] | select(.spec.approved == false) | .metadata.name')

if [ -n "$PENDING_PLANS" ]; then
    echo "Found pending install plans:"
    echo "$PENDING_PLANS"
    echo "Approve with: oc patch installplan <name> -n ${NAMESPACE_OPERATORS} --type merge --patch '{\"spec\":{\"approved\":true}}'"
else
    echo "No pending install plans found"
fi

# Step 5: Monitor update
echo "Step 5: Monitoring update progress..."
echo "Watch operator: oc get csv -n ${NAMESPACE_OPERATORS} -w"
echo "Watch control plane: oc get openstackcontrolplane -n ${NAMESPACE_OPENSTACK} -w"

# Step 6: Validation
echo "Step 6: Update validation..."
echo "After update completes, run validation tests"

echo "=== Update automation completed ==="
echo "Backup location: ${BACKUP_DIR}"
echo "Please validate the update and test OpenStack services."
