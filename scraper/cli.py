import argparse
import logging
from datetime import datetime, timezone

from scraper.client import PermapeopleClient
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

    clean_parser = subparsers.add_parser("clean", help="Remove all scrape output")
    clean_parser.add_argument(
        "-f", "--force", action="store_true", help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    if args.command == "scrape":
        cmd_scrape(args)
    elif args.command == "clean":
        cmd_clean(args)


if __name__ == "__main__":
    main()
