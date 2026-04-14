from __future__ import annotations

from collections import defaultdict

import numpy as np
from pymoo.core.problem import ElementwiseProblem

from optimizer.context import ProblemContext
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

        n_unassigned = int((assignments == 0).sum())
        utilization_score = utilization - 0.01 * n_unassigned / max(ctx.n_plants, 1)

        g = []
        for k in range(1, ctx.n_plots + 1):
            area_in_plot = sum(ctx.plant_areas[i] for i in plots.get(k, []))
            g.append(area_in_plot - ctx.plot_areas[k - 1])
        g.append(float(antag_violations))

        out["F"] = [-compat_score, -utilization_score]
        out["G"] = g