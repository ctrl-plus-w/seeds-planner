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
from optimizer.result import OptimizationResult, Solution
from optimizer.models.problem import CompanionPlantingProblem


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
