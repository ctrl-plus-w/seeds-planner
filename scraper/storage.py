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

    def load_plants(self, run_dir: Path) -> list[dict]:
        path = run_dir / "plants.json"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def select_run(self) -> Path | None:
        runs = self.list_runs()
        if not runs:
            print("No scrape runs found. Run 'seeds-scraper scrape' first.")
            return None
        print("Available runs:")
        for i, run in enumerate(runs, 1):
            summary_path = run / "summary.json"
            extra = ""
            if summary_path.exists():
                with open(summary_path, encoding="utf-8") as f:
                    summary = json.load(f)
                extra = f" — {summary.get('total_plants', '?')} plants, {summary.get('status', '?')}"
            print(f"  [{i}] {run.name}{extra}")
        choice = input(f"\nSelect a run [1-{len(runs)}]: ")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(runs):
                return runs[idx]
        except ValueError:
            pass
        print("Invalid selection.")
        return None

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
