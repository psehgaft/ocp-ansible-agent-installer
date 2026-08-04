#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

charts = sorted({path.parent for path in Path('.').rglob('Chart.yaml') if '.git' not in path.parts})
failures = []
for chart in charts:
    for command in (['helm', 'lint', str(chart)], ['helm', 'template', chart.name, str(chart)]):
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode:
            failures.append(f"{' '.join(command)}:\n{result.stderr.strip()}")
if failures:
    print('\n'.join(failures), file=sys.stderr)
    raise SystemExit(1)
print(f'Validated {len(charts)} Helm charts')
