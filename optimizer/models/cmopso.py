from __future__ import annotations

import argparse

import numpy as np
from pymoo.algorithms.moo.cmopso import CMOPSO
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.optimize import minimize

from optimizer.context import ProblemContext
from optimizer.models.base import OptimizerModel
from optimizer.result import OptimizationResult, Solution
from optimizer.models.problem import CompanionPlantingProblem


class CMOPSOModel(OptimizerModel):
    name = "cmopso"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--pop-size",
            type=int,
            default=100,
            help="Population size for CMOPSO (default: 100)",
        )
        parser.add_argument(
            "--n-gen",
            type=int,
            default=200,
            help="Number of iterations (default: 200)",
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

        algorithm = CMOPSO(
            pop_size=self.pop_size,
            sampling=IntegerRandomSampling(),
            repair=RoundingRepair(),
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