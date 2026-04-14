from __future__ import annotations

import argparse

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.duplicate import DuplicateElimination
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.optimize import minimize

from optimizer.context import ProblemContext
from optimizer.models.base import OptimizerModel
from optimizer.models.problem import CompanionPlantingProblem
from optimizer.result import OptimizationResult, Solution


def _canonicalize(x: np.ndarray) -> tuple[int, ...]:
    """Renumber plot IDs by order of first non-zero appearance.

    E.g. [2, 0, 3, 2, 1] -> (1, 0, 2, 1, 3).
    This ensures that two solutions differing only by plot-label permutation
    map to the same canonical form.
    """
    mapping: dict[int, int] = {0: 0}
    next_id = 1
    out = []
    for v in np.round(x).astype(int):
        v = int(v)
        if v not in mapping:
            mapping[v] = next_id
            next_id += 1
        out.append(mapping[v])
    return tuple(out)


class CanonicalDuplicateElimination(DuplicateElimination):
    """Treat solutions that are plot-label permutations as duplicates.

    Uses hash-based O(pop) dedup instead of pairwise O(pop²) comparison.
    """

    def _do(self, pop, other, is_duplicate):
        seen: set[tuple[int, ...]] = set()

        if other is not None:
            for ind in other:
                seen.add(_canonicalize(ind.X))

        for i, ind in enumerate(pop):
            key = _canonicalize(ind.X)
            if key in seen:
                is_duplicate[i] = True
            else:
                seen.add(key)

        return is_duplicate


class NSGA2QuantityModel(OptimizerModel):
    """NSGA-II sur une instance dont les quantités ont été expansées en amont
    (une variable de décision par unité de plante, cf. api/service.py)."""

    name = "nsga2-quantity"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--pop-size", type=int, default=200)
        parser.add_argument("--n-gen", type=int, default=400)
        parser.add_argument("--seed", type=int, default=None)

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
            eliminate_duplicates=CanonicalDuplicateElimination(),
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

        seen: set[tuple[int, ...]] = set()
        solutions: list[Solution] = []
        for i in range(len(res.F)):
            assignments = np.round(res.X[i]).astype(int)
            key = _canonicalize(assignments)
            if key in seen:
                continue
            seen.add(key)
            solutions.append(Solution(assignments=assignments, objectives=res.F[i]))

        return OptimizationResult(solutions=solutions)
