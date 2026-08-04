#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

playbooks = sorted(Path('playbooks').rglob('*.yml'))
failures = []
for playbook in playbooks:
    result = subprocess.run(
        ['ansible-playbook', str(playbook), '--syntax-check'],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        failures.append(f'{playbook}:\n{result.stdout}\n{result.stderr}')
if failures:
    print('\n'.join(failures), file=sys.stderr)
    raise SystemExit(1)
print(f'Syntax checked {len(playbooks)} playbooks')
