from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def find_latest_run(project_root: Path | None = None) -> Path | None:
    out_dir = (project_root or PROJECT_ROOT) / ".out"
    if not out_dir.exists():
        return None
    runs = sorted(
        p for p in out_dir.iterdir() if p.is_dir() and p.name.startswith("run_")
    )
    return runs[-1] if runs else None
