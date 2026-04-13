from __future__ import annotations

import argparse
from collections import defaultdict

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.optimize import minimize

from optimizer.context import ProblemContext
from optimizer.models.base import OptimizerModel
from optimizer.result import OptimizationResult, Solution
from optimizer.utils.pairs import colocated_pairs


class CompanionPlantingProblem(ElementwiseProblem):
    """pymoo problem wrapper around ProblemContext."""

    def __init__(self, ctx: ProblemContext):
        self.ctx = ctx
        super().__init__(
            n_var=ctx.n_plants,
            n_obj=2,
            n_ieq_constr=ctx.n_plots + 1,
            xl=np.zeros(ctx.n_plants),
            xu=np.full(ctx.n_plants, ctx.n_plots),
        )

    def _evaluate(self, x, out, *args, **kwargs):
        ctx = self.ctx
        assignments = np.round(x).astype(int)

        plots: dict[int, list[int]] = defaultdict(list)
        for i, plot_id in enumerate(assignments):
            if plot_id > 0:
                plots[plot_id].append(i)

        compat_score = 0.0
        antag_violations = 0
        for i, j in colocated_pairs(plots):
            if (i, j) in ctx.companion_index_pairs:
                compat_score += ctx.pref_weights[i] * ctx.pref_weights[j]
            if (i, j) in ctx.antagonist_index_pairs:
                antag_violations += 1

        total_plot_area = ctx.plot_areas.sum()
        total_assigned = sum(
            ctx.plant_areas[i] for i, a in enumerate(assignments) if a > 0
        )
        utilization = total_assigned / total_plot_area if total_plot_area > 0 else 0.0

        g = []
        for k in range(1, ctx.n_plots + 1):
            area_in_plot = sum(ctx.plant_areas[i] for i in plots.get(k, []))
            g.append(area_in_plot - ctx.plot_areas[k - 1])
        g.append(float(antag_violations))

        out["F"] = [-compat_score, -utilization]
        out["G"] = g


class NSGA2Model(OptimizerModel):
    name = "nsga2"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--pop-size",
            type=int,
            default=100,
            help="Population size for NSGA-II (default: 100)",
        )
        parser.add_argument(
            "--n-gen",
            type=int,
            default=200,
            help="Number of generations (default: 200)",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Random seed for reproducibility",
        )

    def __init__(self, ctx: ProblemContext, args: argparse.Namespace) -> None:
        self.ctx = ctx
        self.pop_size = args.pop_size
        self.n_gen = args.n_gen
        self.seed = args.seed

    def optimize(self) -> OptimizationResult:
        problem = CompanionPlantingProblem(self.ctx)

        algorithm = NSGA2(
            pop_size=self.pop_size,
            sampling=IntegerRandomSampling(),
            crossover=SBX(prob=0.9, eta=3, vtype=float, repair=RoundingRepair()),
            mutation=PM(eta=3, vtype=float, repair=RoundingRepair()),
            eliminate_duplicates=True,
        )

        res = minimize(
            problem,
            algorithm,
            termination=("n_gen", self.n_gen),
            seed=self.seed,
            verbose=False,
        )

        if res.F is None or len(res.F) == 0:
            return OptimizationResult(solutions=[])

        solutions = []
        for i in range(len(res.F)):
            solutions.append(
                Solution(
                    assignments=np.round(res.X[i]).astype(int),
                    objectives=res.F[i],
                )
            )
        return OptimizationResult(solutions=solutions)
