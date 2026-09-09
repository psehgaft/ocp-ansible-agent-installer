#!/usr/bin/env bash
set -Eeuo pipefail

INVENTORY="${1:-inventories/sample/hosts.yml}"

python3 - <<'PY_VALIDATE'
from pathlib import Path
import py_compile
yaml = __import__('yaml')

root = Path('.')
errors = []
excluded_parts = {
    '.git', '.collections', '.ansible', '.venv', 'venv', 'env',
    'node_modules', 'artifacts', 'www', '.cache', '__pycache__',
}

def is_repository_source(path: Path) -> bool:
    return not any(part in excluded_parts for part in path.parts)

for path in sorted(root.rglob('*.yml')) + sorted(root.rglob('*.yaml')):
    if not is_repository_source(path):
        continue
    try:
        yaml.safe_load(path.read_text())
    except Exception as exc:
        errors.append(f"{path}: {exc}")

try:
    py_compile.compile('filter_plugins/redfish_filters.py', doraise=True)
except Exception as exc:
    errors.append(f"filter_plugins/redfish_filters.py: {exc}")

if errors:
    raise SystemExit("Validation errors:\n" + "\n".join(errors))
print('YAML and Python parsing passed.')
PY_VALIDATE

python3 tests/test_redfish_filters.py
python3 scripts/offline_validate.py
python3 scripts/validate_input_contracts.py
python3 scripts/validate_repository_assets.py

if command -v ansible-inventory >/dev/null 2>&1; then
  ansible-inventory -i "$INVENTORY" --list >/dev/null
  echo "Ansible inventory parsing passed."
fi

if command -v ansible-playbook >/dev/null 2>&1; then
  while IFS= read -r playbook; do
    ansible-playbook -i "$INVENTORY" "$playbook" --syntax-check >/dev/null
    echo "Syntax check passed: $playbook"
  done < <(find playbooks -type f -name '*.yml' | sort)
fi
