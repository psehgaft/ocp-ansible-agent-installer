#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

roots = sorted({path.parent for path in Path('gitops').rglob('kustomization.yaml')})
failures = []
for root in roots:
    build = subprocess.run(['kustomize', 'build', str(root)], capture_output=True, text=True, check=False)
    if build.returncode:
        failures.append(f'{root}: Kustomize build failed: {build.stderr.strip()}')
        continue
    validate = subprocess.run(
        ['kubeconform', '-strict', '-summary', '-ignore-missing-schemas', '-'],
        input=build.stdout,
        capture_output=True,
        text=True,
        check=False,
    )
    if validate.returncode:
        failures.append(f'{root}: {validate.stdout}\n{validate.stderr}')
if failures:
    print('\n'.join(failures), file=sys.stderr)
    raise SystemExit(1)
print(f'Validated Kubernetes resources from {len(roots)} Kustomize roots')
