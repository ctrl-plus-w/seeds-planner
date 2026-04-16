from __future__ import annotations

import argparse

import numpy as np
from pymoo.algorithms.moo.ctaea import CTAEA
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.optimize import minimize
from pymoo.util.ref_dirs import get_reference_directions

from optimizer.context import ProblemContext
from optimizer.models.base import OptimizerModel
from optimizer.models.problem import CompanionPlantingProblem
from optimizer.result import OptimizationResult, Solution
from optimizer.utils.deduplication import CanonicalDuplicateElimination, canonicalize


class CTAEAModel(OptimizerModel):
    """CTAEA (Constrained Two-Archive EA) sur une instance dont les quantités
    ont été expansées en amont.

    Algorithme à décomposition avec deux archives (Convergence + Diversité),
    conçu pour l'optimisation multi-objectif sous contraintes.
    """

    name = "ctaea"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--n-partitions", type=int, default=99)
        parser.add_argument("--n-gen", type=int, default=400)
        parser.add_argument("--seed", type=int, default=None)

    def __init__(self, ctx: ProblemContext, args: argparse.Namespace) -> None:
        self.ctx = ctx
        self.n_gen = args.n_gen
        self.seed = args.seed

        if hasattr(args, "n_partitions") and args.n_partitions is not None:
            n_partitions = args.n_partitions
        else:
            n_partitions = max(getattr(args, "pop_size", 13) - 1, 3)

        self.ref_dirs = get_reference_directions(
            "das-dennis", 2, n_partitions=n_partitions
        )

    def optimize(self) -> OptimizationResult:
        problem = CompanionPlantingProblem(self.ctx)

        algorithm = CTAEA(
            ref_dirs=self.ref_dirs,
            sampling=IntegerRandomSampling(),
            crossover=SBX(
                n_offsprings=1, prob=0.9, eta=3, vtype=float, repair=RoundingRepair()
            ),
            mutation=PM(eta=3, vtype=float, repair=RoundingRepair()),
            eliminate_duplicates=CanonicalDuplicateElimination(self.ctx.plant_slugs),
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

        seen: set[tuple] = set()
        solutions: list[Solution] = []
        for i in range(len(res.F)):
            assignments = np.round(res.X[i]).astype(int)
            key = canonicalize(assignments, self.ctx.plant_slugs)
            if key in seen:
                continue
            seen.add(key)
            solutions.append(Solution(assignments=assignments, objectives=res.F[i]))

        return OptimizationResult(solutions=solutions)
