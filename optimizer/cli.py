from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from optimizer.context import ProblemContext
from optimizer.data import load_garden_data
from optimizer.models import MODEL_REGISTRY, get_model
from optimizer.result import OptimizationResult
from optimizer.utils.cli import parse_plant_slugs, parse_plot_areas
from optimizer.utils.fs import find_latest_run


def _format_solution(
    idx: int,
    total: int,
    assignments: np.ndarray,
    ctx: ProblemContext,
    objectives: np.ndarray,
) -> str:
    garden = ctx.garden
    plant_slugs = ctx.plant_slugs
    plot_areas = ctx.plot_areas
    plant_areas = ctx.plant_areas

    compat = -objectives[0]
    utilization = -objectives[1] * 100

    lines = [
        f"=== Solution {idx}/{total} ===",
        f"Compatibility: {compat:.1f} | Space used: {utilization:.1f}%",
        "",
    ]

    plots: dict[int, list[int]] = defaultdict(list)
    unassigned: list[int] = []
    for i, plot_id in enumerate(assignments):
        if plot_id > 0:
            plots[plot_id].append(i)
        else:
            unassigned.append(i)

    companion_idx = ctx.companion_index_pairs

    for k in range(1, ctx.n_plots + 1):
        area = plot_areas[k - 1]
        plant_indices = plots.get(k, [])
        used = sum(plant_areas[i] for i in plant_indices)
        pct = (used / area * 100) if area > 0 else 0
        lines.append(f"  Plot {k} ({area:.1f} m^2) -- {used:.2f} m^2 used ({pct:.0f}%)")

        for i in plant_indices:
            info = garden.plants_by_slug[plant_slugs[i]]
            companions_here = []
            for j in plant_indices:
                if j == i:
                    continue
                pair = (min(i, j), max(i, j))
                if pair in companion_idx:
                    companions_here.append(garden.plants_by_slug[plant_slugs[j]].name)

            comp_str = ""
            if companions_here:
                comp_str = f"  companions here: {', '.join(companions_here)}"
            lines.append(f"    - {info.name} ({info.area:.2f} m^2){comp_str}")

        if not plant_indices:
            lines.append("    (empty)")
        lines.append("")

    if unassigned:
        names = [garden.plants_by_slug[plant_slugs[i]].name for i in unassigned]
        lines.append(f"  Unassigned: {', '.join(names)}")
        lines.append("")

    return "\n".join(lines)


def _rank_solutions(result: OptimizationResult, top: int) -> list[int]:
    """Rank solutions by weighted normalized objectives and return top indices."""
    if result.n_solutions == 0:
        return []

    F = np.array([s.objectives for s in result.solutions])
    f_norm = F.copy()
    for col in range(f_norm.shape[1]):
        col_min = f_norm[:, col].min()
        col_max = f_norm[:, col].max()
        if col_max > col_min:
            f_norm[:, col] = (f_norm[:, col] - col_min) / (col_max - col_min)
        else:
            f_norm[:, col] = 0.0

    scores = 0.6 * f_norm[:, 0] + 0.4 * f_norm[:, 1]
    order = np.argsort(scores)
    return list(order[: min(top, len(order))])


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="seeds-optimizer",
        description="Optimize companion plant placement across garden plots",
    )
    parser.add_argument(
        "-p",
        "--plants",
        required=True,
        help="Comma-separated plant names or slugs, in preference order",
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
        "--model",
        default="nsga2",
        choices=sorted(MODEL_REGISTRY.keys()),
        help="Optimization model to use (default: nsga2)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of Pareto-optimal solutions to display (default: 5)",
    )

    # Two-phase parsing: get --model first, then add model-specific args
    pre_args, _ = parser.parse_known_args()
    model_cls = get_model(pre_args.model)
    model_cls.add_arguments(parser)
    args = parser.parse_args()

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
        f"\nOptimizing {len(plant_slugs)} plants across {len(plot_areas)} plots "
        f"using {model_cls.name}...",
    )
    print(f"Plot areas: {', '.join(f'{a:.1f} m^2' for a in plot_areas)}")

    ctx = ProblemContext.build(plant_slugs, plot_areas, garden)

    model = model_cls(ctx, args)
    result = model.optimize()

    if result.n_solutions == 0:
        print(
            "\nNo feasible solution found. Consider:\n"
            "  - Reducing the number of plants\n"
            "  - Increasing plot sizes\n"
            "  - Checking for antagonist conflicts between your plants\n"
        )
        sys.exit(1)

    print(f"\nFound {result.n_solutions} Pareto-optimal solution(s)\n")

    ranked = _rank_solutions(result, args.top)
    for rank, sol_idx in enumerate(ranked, 1):
        sol = result.solutions[sol_idx]
        output = _format_solution(
            rank, len(ranked), sol.assignments, ctx, sol.objectives
        )
        print(output)


if __name__ == "__main__":
    main()
