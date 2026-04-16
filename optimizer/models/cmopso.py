from __future__ import annotations

import argparse

import numpy as np
from pymoo.algorithms.moo.cmopso import CMOPSO
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.operators.sampling.rnd import IntegerRandomSampling

from optimizer.context import ProblemContext
from optimizer.models.base import OptimizerModel
from optimizer.models.problem import CompanionPlantingProblem
from optimizer.result import Solution


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
        super().__init__(ctx, args)
        self.pop_size = args.pop_size

    def _build_problem_and_algorithm(self) -> tuple[CompanionPlantingProblem, CMOPSO]:
        problem = CompanionPlantingProblem(self.ctx)
        algorithm = CMOPSO(
            pop_size=self.pop_size,
            sampling=IntegerRandomSampling(),
            repair=RoundingRepair(),
        )
        return problem, algorithm

    def _postprocess_results(self, res) -> list[Solution]:
        """CMOPSO does not deduplicate results."""
        if res.F is None or len(res.F) == 0:
            return []
        return [
            Solution(
                assignments=np.round(res.X[i]).astype(int),
                objectives=res.F[i],
            )
            for i in range(len(res.F))
        ]
