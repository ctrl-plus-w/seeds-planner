# Seeds Planner - Scraper

CLI tool to scrape plant data and companion/antagonist relationships from [permapeople.org](https://permapeople.org).

## Setup

Requires Python >= 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
# Install dependencies
uv sync
```

Create a `.env` file at the project root with your API credentials:

```
PERMAPEOPLE_ID=your_api_id
PERMAPEOPLE_KEY=your_api_key
```

## Usage

### Scrape all plants

Fetches all plants from the API (paginated, 100/page) and saves them locally.

```bash
uv run seeds-scraper scrape
uv run seeds-scraper scrape --delay 1.0  # custom delay between requests (default: 0.5s)
```

### Scrape companion & antagonist relationships

Scrapes each plant's webpage to extract companion and antagonist links. Requires an existing scrape run.

```bash
uv run seeds-scraper companions              # interactive run selection
uv run seeds-scraper companions --run run_2026-03-23_15-52-37  # specify run directly
uv run seeds-scraper companions --delay 0.3  # faster requests
```

### Clean output

Removes all scrape output from `.out/`.

```bash
uv run seeds-scraper clean       # with confirmation prompt
uv run seeds-scraper clean -f    # skip confirmation
```

## Output structure

Each scrape run creates a timestamped directory:

```
.out/
  run_2026-03-23_15-52-37/
    plants.json              # all plants from the API
    summary.json             # run metadata (duration, count, status)
    scrape.log               # detailed log
    companions.json          # companion/antagonist data (after companions command)
    companions_summary.json  # companions run metadata
    companions.log           # companions detailed log
```
