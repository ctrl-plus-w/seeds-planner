import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from scraper.config import PROJECT_ROOT


class RunStorage:
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or (PROJECT_ROOT / ".out")

    def create_run_dir(self) -> Path:
        timestamp = datetime.now().strftime("run_%Y-%m-%d_%H-%M-%S")
        run_dir = self.base_dir / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def save_plants(self, run_dir: Path, plants: list[dict]) -> Path:
        path = run_dir / "plants.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(plants, f, indent=2, ensure_ascii=False)
        return path

    def save_summary(self, run_dir: Path, summary: dict) -> Path:
        path = run_dir / "summary.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        return path

    def setup_run_logger(self, run_dir: Path) -> logging.FileHandler:
        handler = logging.FileHandler(run_dir / "scrape.log", encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-5s %(message)s")
        )
        return handler

    def list_runs(self) -> list[Path]:
        if not self.base_dir.exists():
            return []
        return sorted(
            [
                p
                for p in self.base_dir.iterdir()
                if p.is_dir() and p.name.startswith("run_")
            ]
        )

    def clean(self, force: bool = False) -> bool:
        if not self.base_dir.exists():
            print("Nothing to clean. .out/ directory does not exist.")
            return False

        runs = self.list_runs()
        if not runs:
            print("Nothing to clean. .out/ directory is empty.")
            return False

        if not force:
            print("The following runs will be deleted:")
            for run in runs:
                files = list(run.rglob("*"))
                size = sum(f.stat().st_size for f in files if f.is_file())
                size_mb = size / (1024 * 1024)
                print(f"  - {run.name} ({len(files)} files, {size_mb:.1f} MB)")
            answer = input("\nAre you sure? [y/N] ")
            if answer.lower() not in ("y", "yes"):
                print("Aborted.")
                return False

        shutil.rmtree(self.base_dir)
        print(f"Cleaned {len(runs)} run(s).")
        return True
