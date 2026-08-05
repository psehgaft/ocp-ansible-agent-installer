#!/usr/bin/env bash
set -Eeuo pipefail

INVENTORY="${1:-inventories/sample/hosts.yml}"
FAIL=0

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'ERROR: required command not found: %s\n' "$1" >&2
    FAIL=1
  else
    printf 'OK: %s -> %s\n' "$1" "$(command -v "$1")"
  fi
}

for cmd in python3 ansible ansible-playbook ansible-galaxy curl jq oc podman; do
  need_cmd "$cmd"
done

if [[ ! -f "$INVENTORY" ]]; then
  echo "ERROR: inventory not found: $INVENTORY" >&2
  FAIL=1
else
  echo "OK: inventory exists: $INVENTORY"
fi

if grep -R --line-number --exclude='*.example' 'CHANGE_ME' \
  "$INVENTORY" "$(dirname "$INVENTORY")/group_vars/all.yml" 2>/dev/null; then
  echo "ERROR: unresolved CHANGE_ME placeholders were found." >&2
  FAIL=1
else
  echo "OK: no unresolved CHANGE_ME placeholders in active inventory files."
fi

if [[ -f "$(dirname "$INVENTORY")/group_vars/vault.yml" ]]; then
  if grep -q "^\$ANSIBLE_VAULT;" "$(dirname "$INVENTORY")/group_vars/vault.yml"; then
    echo "OK: vault.yml is encrypted."
  else
    echo "WARNING: vault.yml exists but does not appear to be encrypted." >&2
  fi
else
  echo "ERROR: create $(dirname "$INVENTORY")/group_vars/vault.yml from vault.yml.example." >&2
  FAIL=1
fi

if command -v ansible-galaxy >/dev/null 2>&1; then
  if ansible-galaxy collection list community.general 2>/dev/null | grep -q 'community.general'; then
    echo "OK: community.general is installed."
  else
    echo "ERROR: install collections with: ansible-galaxy collection install -r requirements.yml" >&2
    FAIL=1
  fi
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo "Preflight failed." >&2
  exit 1
fi

echo "Preflight passed."
