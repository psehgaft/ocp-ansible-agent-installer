#!/usr/bin/env python3
from pathlib import Path
import sys
import yaml

EXCLUDED = {'.git', '.cache', 'www', 'reports/output'}
errors = []
for path in Path('.').rglob('*'):
    if path.suffix not in {'.yml', '.yaml'} or any(part in EXCLUDED for part in path.parts):
        continue
    try:
        list(yaml.safe_load_all(path.read_text(encoding='utf-8')))
    except Exception as exc:
        errors.append(f'{path}: {exc}')
if errors:
    print('\n'.join(errors), file=sys.stderr)
    raise SystemExit(1)
print('YAML parsing passed')
