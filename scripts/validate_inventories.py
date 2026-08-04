#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

inventories = sorted(Path('inventories').glob('*/hosts.y*ml'))
if not inventories:
    inventories = sorted(Path('inventories').glob('**/hosts.y*ml'))
failures = []
for inventory in inventories:
    result = subprocess.run(
        ['ansible-inventory', '-i', str(inventory), '--list'],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        failures.append(f'{inventory}: {result.stderr.strip()}')
if failures:
    print('\n'.join(failures), file=sys.stderr)
    raise SystemExit(1)
print(f'Validated {len(inventories)} inventories')
