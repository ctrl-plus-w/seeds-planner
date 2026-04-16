from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np

from api.schemas import (
    OptimizeRequest,
    OptimizeResponse,
    PlantInPlot,
    PlantSummary,
    PlantsResponse,
    PlotResult,
    SolutionResult,
)
from optimizer.classes.garden_data import GardenData
from optimizer.context import ProblemContext
from optimizer.data import load_garden_data
from optimizer.models import get_model
from optimizer.result import OptimizationResult
from optimizer.utils.fs import find_latest_run


class NoScrapeRunError(RuntimeError):
    pass


def _resolve_data_dir() -> Path:
    data_dir = find_latest_run()
    if data_dir is None:
        raise NoScrapeRunError(
            "No scrape runs found in .out/. Run 'seeds-scraper scrape' first."
        )
    return data_dir


def load_plants() -> PlantsResponse:
    data_dir = _resolve_data_dir()
    garden = load_garden_data(data_dir)

    plants: list[PlantSummary] = []
    for slug, info in garden.plants_by_slug.items():
        if not info.name:
            continue
        plants.append(
            PlantSummary(
                slug=slug,
                name=info.name,
                scientific_name=info.scientific_name,
                area=info.area,
                has_relations=slug in garden._slugs_with_relations,
            )
        )

    plants.sort(key=lambda p: (not p.has_relations, p.name.lower()))
    return PlantsResponse(
        run_id=data_dir.name,
        n_plants=len(plants),
        plants=plants,
    )


def _rank_solutions(result: OptimizationResult, compat_weight: float) -> list[int]:
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

    placement_weight = (1.0 - compat_weight) / 2.0
    scores = (
        compat_weight * f_norm[:, 0]
        + placement_weight * f_norm[:, 1]
        + placement_weight * f_norm[:, 2]
    )
    return list(np.argsort(scores))


def _build_solution_result(
    rank: int,
    assignments: np.ndarray,
    objectives: np.ndarray,
    ctx: ProblemContext,
    garden: GardenData,
) -> SolutionResult:
    plots: dict[int, list[int]] = defaultdict(list)
    unassigned_idx: list[int] = []
    for i, plot_id in enumerate(assignments):
        plot_id_int = int(plot_id)
        if plot_id_int > 0:
            plots[plot_id_int].append(i)
        else:
            unassigned_idx.append(i)

    plot_results: list[PlotResult] = []
    total_used_area = 0.0
    total_plot_area = 0.0
    for k in range(1, ctx.n_plots + 1):
        area = float(ctx.plot_areas[k - 1])
        plant_indices = plots.get(k, [])
        used = float(sum(ctx.plant_areas[i] for i in plant_indices))
        pct = (used / area * 100.0) if area > 0 else 0.0
        total_used_area += used
        total_plot_area += area

        plant_entries: list[PlantInPlot] = []
        for i in plant_indices:
            info = garden.plants_by_slug[ctx.plant_slugs[i]]
            companions_here: list[str] = []
            for j in plant_indices:
                if j == i:
                    continue
                pair = (min(i, j), max(i, j))
                if pair in ctx.companion_index_pairs:
                    companions_here.append(
                        garden.plants_by_slug[ctx.plant_slugs[j]].name
                    )
            plant_entries.append(
                PlantInPlot(
                    slug=info.slug,
                    name=info.name,
                    area=float(info.area),
                    companions_here=companions_here,
                )
            )

        plot_results.append(
            PlotResult(
                index=k,
                area=area,
                used_area=used,
                utilization=pct,
                plants=plant_entries,
            )
        )

    unassigned_names = [
        garden.plants_by_slug[ctx.plant_slugs[i]].name for i in unassigned_idx
    ]

    space_utilization = (
        (total_used_area / total_plot_area * 100.0) if total_plot_area > 0 else 0.0
    )
    n_unassigned = len(unassigned_idx)
    assigned_pct = (
        ((ctx.n_plants - n_unassigned) / ctx.n_plants * 100.0)
        if ctx.n_plants > 0
        else 100.0
    )

    return SolutionResult(
        rank=rank,
        compatibility=float(-objectives[0]),
        space_utilization=float(space_utilization),
        unassigned_count=n_unassigned,
        assigned_pct=float(assigned_pct),
        plots=plot_results,
        unassigned=unassigned_names,
    )


def run_optimization(req: OptimizeRequest) -> OptimizeResponse:
    data_dir = _resolve_data_dir()
    garden = load_garden_data(data_dir)

    expanded_slugs: list[str] = []
    seen_slugs: set[str] = set()
    for entry in req.plants:
        if entry.slug not in garden.plants_by_slug:
            raise ValueError(f"Unknown plant slug: {entry.slug}")
        if entry.slug in seen_slugs:
            raise ValueError(f"Duplicate plant slug: {entry.slug}")
        seen_slugs.add(entry.slug)
        expanded_slugs.extend([entry.slug] * entry.quantity)

    if len(expanded_slugs) < 2:
        raise ValueError(
            "Need at least 2 plant instances to optimize (sum of quantities)"
        )
    if not req.plot_areas or any(a <= 0 for a in req.plot_areas):
        raise ValueError("All plot areas must be positive numbers")

    ctx = ProblemContext.build(expanded_slugs, req.plot_areas, garden)

    model_cls = get_model("nsga2")
    args = argparse.Namespace(
        pop_size=req.pop_size,
        n_gen=req.n_gen,
        seed=req.seed,
        n_seeds=req.n_seeds,
    )
    model = model_cls(ctx, args)
    result = model.optimize()
    ranked = _rank_solutions(result, req.compat_weight)

    solutions = [
        _build_solution_result(
            rank=rank,
            assignments=result.solutions[idx].assignments,
            objectives=result.solutions[idx].objectives,
            ctx=ctx,
            garden=garden,
        )
        for rank, idx in enumerate(ranked, start=1)
    ]

    return OptimizeResponse(
        n_total_solutions=result.n_solutions,
        solutions=solutions,
    )
