#!/usr/bin/env sh
set -eu

umask 077
mkdir -p "${INSTALLER_UI_DATA_ROOT:-/data}" "${INSTALLER_UI_HOME:-/data/home}"

for binary in python3.12 ansible-playbook ansible-vault oc oc-mirror git kustomize helm; do
  if ! command -v "${binary}" >/dev/null 2>&1; then
    echo "Required runtime binary is unavailable: ${binary}" >&2
    exit 1
  fi
done

exec /usr/local/bin/installer-ui
