#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

roots = sorted({path.parent for path in Path('gitops').rglob('kustomization.yaml')})
failures = []
for root in roots:
    result = subprocess.run(['kustomize', 'build', str(root)], capture_output=True, text=True, check=False)
    if result.returncode:
        failures.append(f'{root}: {result.stderr.strip()}')
if failures:
    print('\n'.join(failures), file=sys.stderr)
    raise SystemExit(1)
print(f'Built {len(roots)} Kustomize roots')
