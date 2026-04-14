# Seeds Planner

Scrape plant data from [permapeople.org](https://permapeople.org) and optimize companion plant placement across garden plots. Ships as three pieces:

- **CLI tools** (`seeds-scraper`, `seeds-optimizer`) for data and terminal-based optimization
- **HTTP API** (`seeds-api`) — FastAPI backend exposing `/plants` and `/optimize`
- **Web app** (`web/`) — React + Vite frontend to build plots, pick plants, and explore the Pareto front interactively

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

Components communicate through JSON files on disk and HTTP:

```
scraper/          Fetches plant data and companion relationships from permapeople.org
    ↓ writes
.out/run_*/       Timestamped output directories with plants.json and companions.json
    ↓ reads
optimizer/        Assigns plants to garden plots using multi-objective optimization
    ↑ used by
api/              FastAPI service exposing /plants and /optimize
    ↑ called by
web/              React + Vite frontend (plot builder, plant picker, Pareto explorer)
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
    base.py            OptimizerModel abstract base class
    problem.py         Shared pymoo Problem (compatibility + space utilization)
    nsga2_initial.py   First-generation NSGA-II (one variable per plant)
    nsga2_quantity.py  NSGA-II on a quantity-expanded instance (one variable per plant unit)
    __init__.py        Model registry
  classes/
    garden_data.py  In-memory representation of all plant data
    plant_info.py   Single plant metadata
  context.py        ProblemContext — optimization inputs derived from user args + garden data
  result.py         Solution and OptimizationResult dataclasses
  data.py           Loads and resolves plant data from JSON
  utils/            CLI parsing, pair utilities, width parsing, filesystem helpers

api/
  main.py           FastAPI app + CORS, entry point (seeds-api)
  schemas.py        Pydantic request/response models
  service.py        Glue between HTTP payloads and the optimizer

web/
  src/pages/Optimizer.tsx        Main page: plots + plants + results
  src/components/PlotBuilder.tsx Plot size editor
  src/components/PlantPicker.tsx Plant search and quantity picker
  src/components/ResultsView.tsx Pareto front, compatibility/space slider, detailed layout
  src/components/GardenSvg.tsx   SVG rendering of a solution
  src/api/                       Typed client for the FastAPI backend
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
  --model nsga2-initial \
  --pop-size 150 \
  --n-gen 300 \
  --seed 42 \
  --top 10
```

### Available models

| Name | Description |
|------|-------------|
| `nsga2-initial` | One decision variable per plant slug — the original formulation |
| `nsga2-quantity` | One decision variable per plant unit (quantities are expanded up-front). Duplicate solutions (identical assignment tuples) are filtered out in post-processing to avoid returning the same layout multiple times |

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `-p`, `--plants` | Comma-separated plant names or slugs, in preference order | *required* |
| `-k`, `--plots` | Comma-separated plot areas in m² | *required* |
| `-d`, `--data-dir` | Path to a scraper run directory | latest run in `.out/` |
| `--model` | Optimization model to use (`nsga2-initial`, `nsga2-quantity`) | `nsga2-initial` |
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

## HTTP API

Start the FastAPI backend (auto-reloads on changes):

```bash
uv run seeds-api
```

The service binds to `http://127.0.0.1:8000` and exposes:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/plants` | List of plants available from the latest scraper run |
| `POST` | `/optimize` | Run the optimizer for a given plots + plants payload |

CORS is pre-configured for the Vite dev server (`http://localhost:5273`).

## Web app

The React + Vite frontend lives in `web/` and calls the API above.

```bash
cd web
npm install
npm run dev       # Vite dev server on http://localhost:5273
npm run build     # type-check + production build into web/dist
```

Highlights of the interactive view:

- **Plot builder** — add/remove plots and edit their area in m²
- **Plant picker** — search plants from the scraper run and choose quantities
- **Pareto explorer** — scatter plot of every Pareto-optimal solution, plus a compatibility/space slider. Moving the slider reweights the ranking and automatically focuses the best solution for the current weighting; clicking a point or list row selects it manually
- **Garden preview** — SVG rendering of the selected solution with per-plot breakdown, companion highlights, and unassigned plants

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
