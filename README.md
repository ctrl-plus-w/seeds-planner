# Seeds Planner

CLI tools to scrape plant data from [permapeople.org](https://permapeople.org) and optimize companion plant placement across garden plots.

## Setup

Requires Python >= 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
# Install dependencies
uv sync
```

Create a `.env` file at the project root with your API credentials (required for the scraper):

```
PERMAPEOPLE_ID=your_api_id
PERMAPEOPLE_KEY=your_api_key
```

## Architecture

The project has two independent CLI tools that share data through JSON files:

```
scraper/          Fetches plant data and companion relationships from permapeople.org
    ↓ writes
.out/run_*/       Timestamped output directories with plants.json and companions.json
    ↓ reads
optimizer/        Assigns plants to garden plots using multi-objective optimization
```

### Directory layout

```
scraper/
  cli.py            CLI entry point (seeds-scraper)
  client.py         HTTP client for the permapeople.org API
  companions.py     HTML parser for companion/antagonist relationships
  storage.py        File I/O and run management
  config.py         API URLs, rate-limiting defaults

optimizer/
  cli.py            CLI entry point (seeds-optimizer)
  models/
    base.py         OptimizerModel abstract base class
    nsga2.py        NSGA-II implementation (default)
    __init__.py     Model registry
  classes/
    garden_data.py  In-memory representation of all plant data
    plant_info.py   Single plant metadata
  context.py        ProblemContext — optimization inputs derived from user args + garden data
  result.py         Solution and OptimizationResult dataclasses
  data.py           Loads and resolves plant data from JSON
  utils/            CLI parsing, pair utilities, width parsing, filesystem helpers
```

### Key abstractions

- **`GardenData`** — read-only container of all plants, companion pairs, and antagonist pairs loaded from a scraper run
- **`ProblemContext`** — everything an optimizer needs: plant indices, plot areas, companion/antagonist index pairs, preference weights
- **`OptimizerModel`** — abstract base class that all optimizers implement
- **`OptimizationResult`** / **`Solution`** — standardized output: each solution is an assignment of plants to plots plus objective values

## Scraper

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

## Optimizer

The optimizer assigns plants to garden plots while maximizing companion compatibility and space utilization. It uses multi-objective optimization to produce a set of Pareto-optimal solutions — trade-offs where improving one objective would worsen the other.

Plants listed earlier in `--plants` receive higher preference weights, so put your most important plants first.

### Usage

```bash
# Basic — uses the latest scraper run and default NSGA-II settings
uv run seeds-optimizer --plants "tomato,basil,carrot,pepper" --plots "6,8"

# Specify a data directory and model parameters
uv run seeds-optimizer \
  --plants "tomato,basil,carrot,pepper,lettuce,marigold" \
  --plots "6,8,10" \
  --data-dir .out/run_2026-03-23_15-52-37 \
  --model nsga2 \
  --pop-size 150 \
  --n-gen 300 \
  --seed 42 \
  --top 10
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `-p`, `--plants` | Comma-separated plant names or slugs, in preference order | *required* |
| `-k`, `--plots` | Comma-separated plot areas in m² | *required* |
| `-d`, `--data-dir` | Path to a scraper run directory | latest run in `.out/` |
| `--model` | Optimization model to use | `nsga2` |
| `--top` | Number of top solutions to display | `5` |

#### NSGA-II options

| Flag | Description | Default |
|------|-------------|---------|
| `--pop-size` | Population size | `100` |
| `--n-gen` | Number of generations | `200` |
| `--seed` | Random seed for reproducibility | *none* |

### Output

Solutions are ranked by a weighted score (60% compatibility + 40% space utilization). Each solution shows:

- Compatibility score and space utilization percentage
- Per-plot layout with plant names, areas, and companion relationships
- Unassigned plants (if any couldn't fit)

## Adding a new optimizer

1. Create a new file in `optimizer/models/` with a class that inherits `OptimizerModel`:

```python
# optimizer/models/my_model.py
import argparse

from optimizer.context import ProblemContext
from optimizer.models.base import OptimizerModel
from optimizer.result import OptimizationResult, Solution


class MyModel(OptimizerModel):
    name = "my-model"  # used as the --model flag value

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--my-param", type=int, default=50)

    def __init__(self, ctx: ProblemContext, args: argparse.Namespace) -> None:
        self.ctx = ctx
        self.my_param = args.my_param

    def optimize(self) -> OptimizationResult:
        # ctx.plant_slugs, ctx.plot_areas, ctx.plant_areas,
        # ctx.companion_index_pairs, ctx.antagonist_index_pairs,
        # ctx.pref_weights are all available
        ...
        return OptimizationResult(solutions=[...])
```

2. Register it in `optimizer/models/__init__.py`:

```python
from optimizer.models.my_model import MyModel

register_model(MyModel)
```

The model is now selectable via `--model my-model`. Model-specific arguments are added automatically through the two-phase CLI parsing in `optimizer/cli.py`.

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
