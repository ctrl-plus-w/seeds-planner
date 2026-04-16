import argparse

import numpy as np
import pulp

from optimizer.context import ProblemContext
from optimizer.models.base import OptimizerModel
from optimizer.result import OptimizationResult, Solution


class PulpModel(OptimizerModel):
    name = 'pulp'

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            '--plant-bonus',
            type=float,
            default=0.5,
            help='Plant bonus added by plant sharing the plot(default: 0.5)',
        )
        parser.add_argument(
            '--plants-malus',
            type=float,
            default=0.5,
            help='Plant malus added by plant sharing the plot(default: 0.5)',
        )
        parser.add_argument(
            '--timer-limit',
            type=int,
            default=60,
            help='Time limit in seconds (default: 60)',
        )

    def __init__(self, ctx: ProblemContext, args: argparse.Namespace) -> None:
        self.ctx = ctx
        self.plant_bonus = args.plant_bonus
        self.plants_malus = args.plants_malus
        self.timer_limit = args.timer_limit

    def build_model(self) -> tuple[pulp.LpProblem, dict]:
        ctx = self.ctx
        n_plants = ctx.n_plants
        n_plots = ctx.n_plots

        problem = pulp.LpProblem(self.name, pulp.LpMaximize)

        x = {
            (i, p): pulp.LpVariable(f"x_{i}_{p}", cat='Binary')
            for i in range(n_plants)
            for p in range(n_plots)
        }

        #Contrainte 1 plante dans 1 parcelle
        for i in range(n_plants):
            problem += pulp.lpSum(x[i, p] for p in range(n_plots)) <= 1

        #Contrainte 2 pas plus de plantes que la capacité d'une parcelle
        for p in range(n_plots):
            problem += (
                pulp.lpSum(ctx.plant_areas[i] * x[i, p] for i in range(n_plants)) <= ctx.plot_areas[p]
            )

        #Contrainte pour ne pas autoriser des plantes antagonistes dans le même plot.
        for (i, j) in ctx.antagonist_index_pairs:
            for p in range(n_plots):
                problem += x[i, p] + x[j, p] <= 1, f"antag_{i}_{j}_{p}"

        all_pairs = ctx.companion_index_pairs
        z: dict[tuple[int, int, int], pulp.LpVariable] = {}

        for (i, j) in all_pairs:
            for p in range(n_plots):
                var = pulp.LpVariable(f"z_{i}_{j}_{p}", cat="Binary")
                z[i, j, p] = var
                problem += var <= x[i, p], f"z_xi_{i}_{j}_{p}"
                problem += var <= x[j, p], f"z_xj_{i}_{j}_{p}"
                problem += var >= x[i, p] + x[j, p] - 1, f"z_lb_{i}_{j}_{p}"

        plants_planted = pulp.lpSum(
            x[i, p]
            for i in range(n_plants)
            for p in range(n_plots)
        )

        companion_score = pulp.lpSum(
            self.plant_bonus * ctx.pref_weights[i] * ctx.pref_weights[j] * z[i, j, p]
            for (i, j) in ctx.companion_index_pairs
            for p in range(n_plots)
        )

        # problem += companion_score - antagonist_score, "total_score"
        problem += plants_planted + companion_score, "total_score"

        return problem, x

    def optimize(self) -> OptimizationResult:
        ctx = self.ctx
        n_plants = ctx.n_plants
        n_plots = ctx.n_plots

        problem, x = self.build_model()

        solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=self.timer_limit)
        problem.solve(solver)

        status = pulp.LpStatus[problem.status]
        if status not in ("Optimal", "Not Solved"):
            return OptimizationResult(solutions=[])

        assignments = np.zeros(n_plants, dtype=int)
        for i in range(n_plants):
            for p in range(n_plots):
                if pulp.value(x[i, p]) is not None and pulp.value(x[i, p]) > 0.5:
                    assignments[i] = p + 1
                    break

        obj_value = pulp.value(problem.objective) or 0.0

        total_area = float(ctx.plot_areas.sum())
        used_area = sum(
            ctx.plant_areas[i]
            for i in range(n_plants)
            if assignments[i] > 0
        )
        utilization = (used_area / total_area) if total_area > 0 else 0.0
        objectives = np.array([-obj_value, -utilization])

        solution = Solution(assignments=assignments, objectives=objectives)
        return OptimizationResult(solutions=[solution])