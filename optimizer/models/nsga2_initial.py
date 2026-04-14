from __future__ import annotations

import argparse

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.optimize import minimize

from optimizer.context import ProblemContext
from optimizer.models.base import OptimizerModel
from optimizer.models.problem import CompanionPlantingProblem
from optimizer.result import OptimizationResult, Solution


class NSGA2InitialModel(OptimizerModel):
    """Baseline NSGA-II: random integer sampling, no domain-aware repair.

    Kept for comparison against `nsga2-quantity`. Tends to leave parcels
    underfilled on tight instances because nothing pushes the search toward
    dense layouts."""

    name = "nsga2-initial"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--pop-size", type=int, default=100)
        parser.add_argument("--n-gen", type=int, default=200)
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

        return OptimizationResult(
            solutions=[
                Solution(
                    assignments=np.round(res.X[i]).astype(int),
                    objectives=res.F[i],
                )
                for i in range(len(res.F))
            ]
        )
