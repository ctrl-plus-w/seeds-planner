import argparse
import time
from collections import defaultdict

import numpy as np
import pulp

from optimizer.context import ProblemContext
from optimizer.models.base import OptimizerModel
from optimizer.result import OptimizationResult, Solution
from optimizer.utils.deduplication import canonicalize
from optimizer.utils.pairs import colocated_pairs


class PulpModel(OptimizerModel):
    name = "pulp"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--timer-limit",
            type=int,
            default=60,
            help="Per-solve CBC time budget in seconds (default: 60). Total wall ≈ timer_limit · n_alpha.",
        )
        parser.add_argument(
            "--n-alpha",
            type=int,
            default=9,
            help="Number of α values in the sweep, including 0 and 1 (default: 9)",
        )
        parser.add_argument(
            "--gap-rel",
            type=float,
            default=0.01,
            help="CBC relative MIP gap; solve returns when incumbent is within this fraction of LP bound (default: 0.01)",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Silence per-α progress logging",
        )
        parser.add_argument("--n-gen", type=int, default=0)
        parser.add_argument("--seed", type=int, default=None)

    def __init__(self, ctx: ProblemContext, args: argparse.Namespace) -> None:
        self.ctx = ctx
        self.timer_limit = args.timer_limit
        self.n_alpha = max(2, args.n_alpha)
        self.gap_rel = args.gap_rel
        self.verbose = not args.quiet

        self.n_gen = getattr(args, "n_gen", 0)
        self.seed = getattr(args, "seed", None)

    def _build_problem_and_algorithm(self):
        raise NotImplementedError("Pulp utilise sa propre méthode d'optimisation")

    def build_model(
        self,
    ) -> tuple[pulp.LpProblem, dict, pulp.LpAffineExpression, pulp.LpAffineExpression]:
        """Build a type-level MILP formulation.

        Per-instance companion linearization (z[i,j,p] for every instance pair)
        scales with N_instances² and produces a model CBC can't solve in
        reasonable time on realistic plant counts (e.g. 4000 instance pairs →
        16k binary z's, 49k constraints, hours per solve). The instance-level
        symmetry also makes the LP relaxation degenerate, so branching has no
        signal to exploit.

        This formulation collapses to the type level: companion bonuses are
        tracked per (type_pair, plot) instead of per (instance_pair, plot).
        For 6 types × 4 plots that's ~40 binary y vars instead of 16k z vars
        — small enough for CBC to actually solve.

        Each y[t1,t2,p] is weighted by the SUM of all per-instance pref·pref
        products for that type pair. So if both types are present in the same
        plot, the model credits the maximum compat achievable from that pair.
        Combined with util pressure forcing plots to pack, the optimizer is
        nudged to colocate companion type pairs and naturally accumulates
        many real colocated instance pairs in the post-hoc evaluation.
        """
        ctx = self.ctx
        n_plants = ctx.n_plants
        n_plots = ctx.n_plots

        problem = pulp.LpProblem(self.name, pulp.LpMaximize)

        x = {
            (i, p): pulp.LpVariable(f"x_{i}_{p}", cat="Binary")
            for i in range(n_plants)
            for p in range(n_plots)
        }

        for i in range(n_plants):
            problem += pulp.lpSum(x[i, p] for p in range(n_plots)) <= 1

        for p in range(n_plots):
            problem += (
                pulp.lpSum(ctx.plant_areas[i] * x[i, p] for i in range(n_plants))
                <= ctx.plot_areas[p]
            )

        for i, j in ctx.antagonist_index_pairs:
            for p in range(n_plots):
                problem += x[i, p] + x[j, p] <= 1, f"antag_{i}_{j}_{p}"

        # Group instance indices by plant type (slug)
        type_to_indices: dict[str, list[int]] = defaultdict(list)
        for i, slug in enumerate(ctx.plant_slugs):
            type_to_indices[slug].append(i)

        # presence[t, p] = 1 iff at least one instance of type t is in plot p
        presence: dict[tuple[str, int], pulp.LpVariable] = {}
        for t, indices in type_to_indices.items():
            for p in range(n_plots):
                v = pulp.LpVariable(f"pres_{t}_{p}", cat="Binary")
                presence[t, p] = v
                # Each x[i,p] forces presence to 1
                for i in indices:
                    problem += v >= x[i, p], f"pres_ge_{t}_{p}_{i}"
                # No x[i,p] forces presence to 0
                problem += v <= pulp.lpSum(x[i, p] for i in indices), f"pres_le_{t}_{p}"

        # Aggregate companion pairs to type level, summing per-instance weights
        type_pair_weight: dict[tuple[str, str], float] = defaultdict(float)
        for i, j in ctx.companion_index_pairs:
            t1 = ctx.plant_slugs[i]
            t2 = ctx.plant_slugs[j]
            if t1 == t2:
                continue
            key = (t1, t2) if t1 < t2 else (t2, t1)
            type_pair_weight[key] += float(ctx.pref_weights[i] * ctx.pref_weights[j])

        # y[t1, t2, p] = presence[t1, p] AND presence[t2, p]
        y: dict[tuple[str, str, int], pulp.LpVariable] = {}
        for (t1, t2), _w in type_pair_weight.items():
            for p in range(n_plots):
                v = pulp.LpVariable(f"y_{t1}_{t2}_{p}", cat="Binary")
                y[t1, t2, p] = v
                problem += v <= presence[t1, p], f"y_p1_{t1}_{t2}_{p}"
                problem += v <= presence[t2, p], f"y_p2_{t1}_{t2}_{p}"
                problem += (
                    v >= presence[t1, p] + presence[t2, p] - 1,
                    f"y_lb_{t1}_{t2}_{p}",
                )

        self._type_pair_weight = type_pair_weight
        self._n_type_pairs = len(type_pair_weight)

        compat_expr = pulp.lpSum(
            w * y[t1, t2, p]
            for (t1, t2), w in type_pair_weight.items()
            for p in range(n_plots)
        )

        total_plot_area = float(ctx.plot_areas.sum())
        if total_plot_area > 0:
            util_expr = pulp.lpSum(
                (ctx.plant_areas[i] / total_plot_area) * x[i, p]
                for i in range(n_plants)
                for p in range(n_plots)
            )
        else:
            util_expr = pulp.lpSum([])

        problem += compat_expr, "total_score"

        return problem, x, compat_expr, util_expr

    def optimize(self) -> OptimizationResult:
        ctx = self.ctx
        problem, x, compat_expr, util_expr = self.build_model()

        # Upper bound on the model's compat_expr: each y[t1,t2,p] can fire
        # independently across plots, so the bound is n_plots · sum(weights).
        compat_max = ctx.n_plots * sum(self._type_pair_weight.values())

        # Scale both objectives to a common range [0, SCALE] so coefficients stay
        # well above CBC's MIP gap tolerance and primal heuristics get a strong
        # signal to push variables off zero.
        scale = 1000.0
        compat_term = (
            compat_expr * (scale / compat_max) if compat_max > 0 else compat_expr * 0.0
        )
        util_term = util_expr * scale

        raw_assignments: list[np.ndarray] = []
        t0 = time.perf_counter()

        if self.verbose:
            print(
                f"[pulp] starting α-sweep: {self.n_alpha} solves, "
                f"≤{self.timer_limit}s each, gapRel={self.gap_rel}"
            )
            print(
                f"[pulp] type-level model: {self._n_type_pairs} companion type pairs "
                f"(from {len(ctx.companion_index_pairs)} instance pairs), "
                f"compat_max={compat_max:.1f}"
            )

        # Floor on util weight so x always has a directional signal — otherwise
        # at α=1 the LP has no incentive to push x off zero (presence is bounded
        # by x but not vice versa) and CBC returns the trivial all-zero
        # incumbent.
        util_floor = 0.01

        for k, alpha in enumerate(np.linspace(0.0, 1.0, self.n_alpha)):
            util_weight = max(1.0 - alpha, util_floor)
            problem.setObjective(alpha * compat_term + util_weight * util_term)
            solver = pulp.PULP_CBC_CMD(
                msg=0, timeLimit=self.timer_limit, gapRel=self.gap_rel
            )
            problem.solve(solver)

            status = pulp.LpStatus[problem.status]
            assignments = self._extract_assignments(x)
            elapsed = time.perf_counter() - t0

            if assignments is None:
                if self.verbose:
                    print(
                        f"[pulp] α-sweep {k + 1}/{self.n_alpha}  α={alpha:.3f}  "
                        f"status={status}  (no incumbent)  elapsed={elapsed:.1f}s"
                    )
                continue

            compat, util = self._eval_objectives(assignments)
            raw_assignments.append(assignments)
            if self.verbose:
                print(
                    f"[pulp] α-sweep {k + 1}/{self.n_alpha}  α={alpha:.3f}  "
                    f"status={status}  compat={compat:.3f} util={util:.3f}  "
                    f"elapsed={elapsed:.1f}s"
                )

        solutions = self._dedupe_and_pareto_filter(raw_assignments)
        if self.verbose:
            print(
                f"[pulp] sweep done: {len(raw_assignments)} solves → "
                f"{len(solutions)} on Pareto front"
            )
        return OptimizationResult(solutions=solutions)

    def _extract_assignments(self, x: dict) -> np.ndarray | None:
        ctx = self.ctx
        n_plants = ctx.n_plants
        n_plots = ctx.n_plots
        assignments = np.zeros(n_plants, dtype=int)
        any_set = False
        for i in range(n_plants):
            for p in range(n_plots):
                v = pulp.value(x[i, p])
                if v is not None and v > 0.5:
                    assignments[i] = p + 1
                    any_set = True
                    break
        if not any_set and not self._all_vars_have_values(x):
            return None
        return assignments

    @staticmethod
    def _all_vars_have_values(x: dict) -> bool:
        for var in x.values():
            if pulp.value(var) is None:
                return False
        return True

    def _eval_objectives(self, assignments: np.ndarray) -> tuple[float, float]:
        ctx = self.ctx
        plots: dict[int, list[int]] = defaultdict(list)
        for i, plot_id in enumerate(assignments):
            if plot_id > 0:
                plots[int(plot_id)].append(i)

        compat = 0.0
        for i, j in colocated_pairs(plots):
            if (i, j) in ctx.companion_index_pairs:
                compat += ctx.pref_weights[i] * ctx.pref_weights[j]

        total_plot_area = float(ctx.plot_areas.sum())
        used_area = sum(
            ctx.plant_areas[i] for i, p in enumerate(assignments) if p > 0
        )
        util = (used_area / total_plot_area) if total_plot_area > 0 else 0.0
        return float(compat), float(util)

    def _dedupe_and_pareto_filter(
        self, raw_assignments: list[np.ndarray]
    ) -> list[Solution]:
        ctx = self.ctx
        seen: set[tuple] = set()
        unique: list[tuple[np.ndarray, np.ndarray]] = []
        for a in raw_assignments:
            key = canonicalize(a, ctx.plant_slugs, ctx.n_plots)
            if key in seen:
                continue
            seen.add(key)
            compat, util = self._eval_objectives(a)
            unique.append((a, np.array([-compat, -util])))

        keep: list[tuple[np.ndarray, np.ndarray]] = []
        for i, (_, fi) in enumerate(unique):
            dominated = False
            for j, (_, fj) in enumerate(unique):
                if i == j:
                    continue
                if np.all(fj <= fi) and np.any(fj < fi):
                    dominated = True
                    break
            if not dominated:
                keep.append(unique[i])

        return [Solution(assignments=a, objectives=f) for a, f in keep]
