from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from optimizer.context import ProblemContext
from optimizer.data import load_garden_data
from optimizer.models import MODEL_REGISTRY, get_model
from optimizer.utils.cli import parse_plant_slugs, parse_plot_areas
from optimizer.utils.fs import find_latest_run

MODEL_DEFAULTS: dict[str, dict] = {
    "nsga2": {"pop_size": 200, "n_gen": 400},
    "cmopso": {"pop_size": 500, "n_gen": 300},
    "ctaea": {"n_gen": 300, "n_partitions": 99},
}


@dataclass
class RunMetrics:
    model: str
    run_index: int
    seed: int
    n_solutions: int
    best_compatibility: float
    best_utilization: float
    final_hypervolume: float
    execution_time: float
    hv_history: list[float]


def _make_model_args(model_name: str, seed: int) -> argparse.Namespace:
    defaults = MODEL_DEFAULTS.get(model_name, {})
    return argparse.Namespace(
        pop_size=defaults.get("pop_size", 200),
        n_gen=defaults.get("n_gen", 400),
        seed=seed,
        n_seeds=1,
        n_partitions=defaults.get("n_partitions", 99),
    )


def _run_single(
    model_name: str,
    model_cls: type,
    ctx: ProblemContext,
    run_index: int,
    seed: int,
) -> RunMetrics:
    args = _make_model_args(model_name, seed)
    model = model_cls(ctx, args)

    hv_history: list[float] = []
    final_hv = 0.0
    n_solutions = 0
    best_compat = 0.0
    best_util = 0.0

    t0 = time.perf_counter()

    for event in model.optimize_streaming():
        if event["type"] == "progress":
            hv_history.append(event["hypervolume"])
            final_hv = event["hypervolume"]
        elif event["type"] == "result":
            result = event["result"]
            n_solutions = result.n_solutions
            if n_solutions > 0:
                best_compat = float(max(-s.objectives[0] for s in result.solutions))
                best_util = float(max(-s.objectives[1] for s in result.solutions))

    elapsed = time.perf_counter() - t0

    return RunMetrics(
        model=model_name,
        run_index=run_index,
        seed=seed,
        n_solutions=n_solutions,
        best_compatibility=best_compat,
        best_utilization=best_util,
        final_hypervolume=final_hv,
        execution_time=round(elapsed, 2),
        hv_history=hv_history,
    )


def _log_run(model_name: str, n_runs: int, metrics: RunMetrics) -> None:
    print(
        f"[{model_name:<7}] run {metrics.run_index + 1}/{n_runs}"
        f"  seed={metrics.seed}"
        f"  solutions={metrics.n_solutions}"
        f"  compat={metrics.best_compatibility:.2f}"
        f"  util={metrics.best_utilization * 100:.1f}%"
        f"  hv={metrics.final_hypervolume:.3f}"
        f"  time={metrics.execution_time:.1f}s",
        flush=True,
    )


def _benchmark_model(
    model_name: str,
    model_cls: type,
    ctx: ProblemContext,
    n_runs: int,
    base_seed: int,
    max_workers: int = 1,
) -> list[RunMetrics]:
    runs: list[RunMetrics] = []

    if max_workers <= 1:
        for i in range(n_runs):
            seed = base_seed + i
            try:
                metrics = _run_single(model_name, model_cls, ctx, i, seed)
            except Exception as e:
                print(f"[{model_name:<7}] run {i + 1}/{n_runs}  seed={seed}  ERROR: {e}")
                continue
            _log_run(model_name, n_runs, metrics)
            runs.append(metrics)
        return runs

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run_single, model_name, model_cls, ctx, i, base_seed + i): i
            for i in range(n_runs)
        }
        for future in as_completed(futures):
            i = futures[future]
            try:
                metrics = future.result()
            except Exception as e:
                print(f"[{model_name:<7}] run {i + 1}/{n_runs}  seed={base_seed + i}  ERROR: {e}")
                continue
            _log_run(model_name, n_runs, metrics)
            runs.append(metrics)

    runs.sort(key=lambda r: r.run_index)
    return runs


def _compute_summary(runs: list[RunMetrics]) -> dict[str, dict[str, float]]:
    if not runs:
        return {}
    fields = [
        "n_solutions",
        "best_compatibility",
        "best_utilization",
        "final_hypervolume",
        "execution_time",
    ]
    summary: dict[str, dict[str, float]] = {}
    for field in fields:
        values = np.array([getattr(r, field) for r in runs], dtype=float)
        summary[field] = {
            "mean": round(float(values.mean()), 4),
            "std": round(float(values.std()), 4),
            "min": round(float(values.min()), 4),
            "max": round(float(values.max()), 4),
        }
    return summary


def _print_summary_table(
    summaries: dict[str, dict[str, dict[str, float]]],
    n_runs: int,
) -> None:
    print(f"\n{'=' * 80}")
    print(f"  Benchmark Summary ({n_runs} run{'s' if n_runs > 1 else ''} each)")
    print(f"{'=' * 80}")

    header = (
        f"{'Model':<10}"
        f"{'#Solutions':>14}"
        f"{'Best Compat':>16}"
        f"{'Best Util':>16}"
        f"{'Final HV':>16}"
        f"{'Time (s)':>14}"
    )
    print(header)
    print("-" * len(header))

    for model_name, summary in summaries.items():

        def fmt(field: str, pct: bool = False) -> str:
            s = summary[field]
            if pct:
                return f"{s['mean'] * 100:.1f} ± {s['std'] * 100:.1f}%"
            if field == "n_solutions":
                return f"{s['mean']:.1f} ± {s['std']:.1f}"
            return f"{s['mean']:.2f} ± {s['std']:.2f}"

        print(
            f"{model_name:<10}"
            f"{fmt('n_solutions'):>14}"
            f"{fmt('best_compatibility'):>16}"
            f"{fmt('best_utilization', pct=True):>16}"
            f"{fmt('final_hypervolume'):>16}"
            f"{fmt('execution_time'):>14}"
        )

    print(f"{'=' * 80}\n")


def _write_json(
    all_runs: dict[str, list[RunMetrics]],
    summaries: dict[str, dict[str, dict[str, float]]],
    metadata: dict,
    output_path: Path,
) -> None:
    data = {
        "metadata": metadata,
        "runs": [asdict(r) for runs in all_runs.values() for r in runs],
        "summaries": summaries,
    }
    output_path.write_text(json.dumps(data, indent=2))
    print(f"Results written to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="seeds-benchmark",
        description="Benchmark optimization models by running each N times and comparing metrics",
    )
    parser.add_argument(
        "-p",
        "--plants",
        required=True,
        help="Comma-separated plant names/slugs with optional quantities (e.g. 'tomato:3,basil:2,carrot')",
    )
    parser.add_argument(
        "-k",
        "--plots",
        required=True,
        help="Comma-separated plot areas in m^2 (e.g. '6,6,8,14')",
    )
    parser.add_argument(
        "-d",
        "--data-dir",
        type=Path,
        default=None,
        help="Path to data directory (default: latest run in .out/)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of runs per algorithm (default: 5)",
    )
    parser.add_argument(
        "--models",
        default=None,
        help="Comma-separated models to benchmark (default: all). Available: "
        + ", ".join(sorted(MODEL_REGISTRY.keys())),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Base random seed; run i gets seed+i (default: 42)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=os.cpu_count() or 1,
        help="Max parallel processes per model (default: number of CPUs)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark_results.json"),
        help="JSON output file path (default: benchmark_results.json)",
    )

    args = parser.parse_args()

    # Resolve models
    if args.models:
        model_names = [m.strip() for m in args.models.split(",")]
        for name in model_names:
            if name not in MODEL_REGISTRY:
                available = ", ".join(sorted(MODEL_REGISTRY.keys()))
                print(f"Error: unknown model '{name}'. Available: {available}")
                sys.exit(1)
    else:
        model_names = sorted(MODEL_REGISTRY.keys())

    # Load data
    data_dir = args.data_dir
    if data_dir is None:
        data_dir = find_latest_run()
        if data_dir is None:
            print(
                "Error: no scrape runs found in .out/. Run 'seeds-scraper scrape' first."
            )
            sys.exit(1)
        print(f"Using data from: {data_dir.name}")

    try:
        garden = load_garden_data(data_dir)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(
        f"Loaded {len(garden.plants_by_slug)} plants, "
        f"{len(garden.companion_pairs)} companion pairs, "
        f"{len(garden.antagonist_pairs)} antagonist pairs",
    )

    plant_slugs = parse_plant_slugs(garden, args.plants.split(","))
    plot_areas = parse_plot_areas(args.plots.split(","))

    print(
        f"\nBenchmarking {len(plant_slugs)} plants across {len(plot_areas)} plots"
        f" — {args.runs} run{'s' if args.runs > 1 else ''} per model"
    )
    print(f"Plot areas: {', '.join(f'{a:.1f} m^2' for a in plot_areas)}")
    print(f"Models: {', '.join(model_names)}")
    print(f"Base seed: {args.seed}")
    print(f"Workers: {args.workers}\n")

    ctx = ProblemContext.build(plant_slugs, plot_areas, garden)

    all_runs: dict[str, list[RunMetrics]] = {}
    summaries: dict[str, dict[str, dict[str, float]]] = {}

    for model_name in model_names:
        model_cls = get_model(model_name)
        runs = _benchmark_model(model_name, model_cls, ctx, args.runs, args.seed, args.workers)
        all_runs[model_name] = runs
        summaries[model_name] = _compute_summary(runs)
        print()

    _print_summary_table(summaries, args.runs)

    metadata = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "plants": args.plants,
        "plots": args.plots,
        "n_runs_per_model": args.runs,
        "base_seed": args.seed,
        "models": model_names,
    }
    _write_json(all_runs, summaries, metadata, args.output)


if __name__ == "__main__":
    main()
