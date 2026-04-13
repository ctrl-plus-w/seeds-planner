import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone

import httpx

from scraper.client import PermapeopleClient
from scraper.companions import scrape_plant_relationships
from scraper.config import REQUEST_DELAY, load_config
from scraper.storage import RunStorage

logger = logging.getLogger("scraper")


def cmd_scrape(args: argparse.Namespace) -> None:
    config = load_config()
    storage = RunStorage()
    run_dir = storage.create_run_dir()

    # Setup logging
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)-5s  %(message)s"))
    logger.addHandler(console)

    file_handler = storage.setup_run_logger(run_dir)
    logger.addHandler(file_handler)

    delay = (
        args.delay
        if hasattr(args, "delay") and args.delay is not None
        else REQUEST_DELAY
    )

    logger.info("Starting scrape run: %s", run_dir.name)
    logger.info("Output directory: %s", run_dir)

    plants: list[dict] = []
    errors: list[str] = []
    status = "success"
    started_at = datetime.now(timezone.utc)

    try:
        with PermapeopleClient(config["id"], config["key"], delay=delay) as client:
            for plant in client.iter_all_plants():
                plants.append(plant)
                if len(plants) % 500 == 0:
                    logger.info("Progress: %d plants collected so far", len(plants))
    except KeyboardInterrupt:
        logger.warning("Interrupted by user. Saving partial results...")
        status = "interrupted"
    except Exception as e:
        logger.error("Scrape failed: %s", e)
        errors.append(str(e))
        status = "error"

    finished_at = datetime.now(timezone.utc)
    duration = (finished_at - started_at).total_seconds()

    if plants:
        storage.save_plants(run_dir, plants)
        logger.info("Saved %d plants to %s", len(plants), run_dir / "plants.json")

    summary = {
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round(duration, 1),
        "total_plants": len(plants),
        "errors": errors,
        "status": status,
    }
    storage.save_summary(run_dir, summary)

    logger.info(
        "Scrape complete: %d plants in %.1fs [%s]", len(plants), duration, status
    )

    # Cleanup handlers
    logger.removeHandler(console)
    logger.removeHandler(file_handler)
    file_handler.close()


def cmd_companions(args: argparse.Namespace) -> None:
    storage = RunStorage()

    if args.run:
        runs = storage.list_runs()
        matching = [r for r in runs if r.name == args.run]
        if not matching:
            print(f"Run '{args.run}' not found.")
            sys.exit(1)
        run_dir = matching[0]
    else:
        run_dir = storage.select_run()
        if not run_dir:
            sys.exit(1)

    # Setup logging
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(levelname)-5s  %(message)s"))
    logger.addHandler(console)

    file_handler = logging.FileHandler(run_dir / "companions.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-5s %(message)s")
    )
    logger.addHandler(file_handler)

    delay = args.delay if args.delay is not None else REQUEST_DELAY

    plants = storage.load_plants(run_dir)
    logger.info("Loaded %d plants from %s", len(plants), run_dir.name)

    # Filter plants that have a link
    plants_with_link = [p for p in plants if p.get("link")]
    logger.info("%d plants have a link to scrape", len(plants_with_link))

    results: list[dict] = []
    errors: list[str] = []
    status = "success"
    started_at = datetime.now(timezone.utc)

    try:
        with httpx.Client() as client:
            for i, plant in enumerate(plants_with_link, 1):
                try:
                    rel = scrape_plant_relationships(client, plant, delay=delay)
                    if rel:
                        results.append(rel)
                        n_comp = len(rel["companions"])
                        n_ant = len(rel["antagonists"])
                        logger.debug(
                            "[%d/%d] %s: %d companions, %d antagonists",
                            i,
                            len(plants_with_link),
                            plant.get("name", "?"),
                            n_comp,
                            n_ant,
                        )
                except Exception as e:
                    logger.warning(
                        "[%d/%d] Failed for %s: %s",
                        i,
                        len(plants_with_link),
                        plant.get("name", "?"),
                        e,
                    )
                    errors.append(f"{plant.get('name', '?')}: {e}")

                if i % 100 == 0:
                    logger.info(
                        "Progress: %d/%d plants scraped (%d results so far)",
                        i,
                        len(plants_with_link),
                        len(results),
                    )

                if i < len(plants_with_link):
                    time.sleep(delay)
    except KeyboardInterrupt:
        logger.warning("Interrupted by user. Saving partial results...")
        status = "interrupted"

    finished_at = datetime.now(timezone.utc)
    duration = (finished_at - started_at).total_seconds()

    # Save results
    companions_path = run_dir / "companions.json"
    with open(companions_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info("Saved %d results to %s", len(results), companions_path)

    summary = {
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round(duration, 1),
        "total_plants_scraped": len(results),
        "total_plants_in_run": len(plants),
        "errors_count": len(errors),
        "errors": errors[:50],  # Cap stored errors
        "status": status,
    }
    summary_path = run_dir / "companions_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(
        "Companions scrape complete: %d/%d plants in %.1fs [%s]",
        len(results),
        len(plants_with_link),
        duration,
        status,
    )

    # Cleanup handlers
    logger.removeHandler(console)
    logger.removeHandler(file_handler)
    file_handler.close()


def cmd_clean(args: argparse.Namespace) -> None:
    storage = RunStorage()
    storage.clean(force=args.force)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="seeds-scraper",
        description="Scrape plant data from permapeople.org API",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape_parser = subparsers.add_parser(
        "scrape", help="Scrape all plants from the API"
    )
    scrape_parser.add_argument(
        "--delay",
        type=float,
        default=REQUEST_DELAY,
        help="Delay between API requests in seconds (default: %(default)s)",
    )

    companions_parser = subparsers.add_parser(
        "companions", help="Scrape companion/antagonist relationships from plant pages"
    )
    companions_parser.add_argument(
        "--delay",
        type=float,
        default=REQUEST_DELAY,
        help="Delay between requests in seconds (default: %(default)s)",
    )
    companions_parser.add_argument(
        "--run",
        type=str,
        default=None,
        help="Run directory name to use (skips interactive selection)",
    )

    clean_parser = subparsers.add_parser("clean", help="Remove all scrape output")
    clean_parser.add_argument(
        "-f", "--force", action="store_true", help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    if args.command == "scrape":
        cmd_scrape(args)
    elif args.command == "companions":
        cmd_companions(args)
    elif args.command == "clean":
        cmd_clean(args)


if __name__ == "__main__":
    main()
