#!/usr/bin/env python3
from pathlib import Path
import os
import subprocess
import sys

EXCLUDED_DIRECTORIES = {
    ".git",
    ".collections",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "__pycache__",
}


def discover_charts(root: Path) -> list[Path]:
    """Return repository-owned Helm chart directories only."""
    charts: list[Path] = []

    for current_root, directory_names, file_names in os.walk(root):
        directory_names[:] = [
            name
            for name in directory_names
            if name not in EXCLUDED_DIRECTORIES and not name.startswith(".")
        ]

        if "Chart.yaml" in file_names:
            charts.append(Path(current_root))

    return sorted(charts)


def run_helm(command: list[str]) -> str | None:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return None

    output = result.stderr.strip() or result.stdout.strip()
    return f"{' '.join(command)}:\n{output}"


def main() -> int:
    charts = discover_charts(Path("."))
    failures: list[str] = []

    for chart in charts:
        commands = (
            ["helm", "lint", str(chart)],
            ["helm", "template", chart.name, str(chart)],
        )
        for command in commands:
            failure = run_helm(command)
            if failure:
                failures.append(failure)

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1

    print(f"Validated {len(charts)} repository-owned Helm charts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
