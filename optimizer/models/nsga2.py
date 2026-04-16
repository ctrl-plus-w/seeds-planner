from __future__ import annotations

import argparse

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.operators.sampling.rnd import IntegerRandomSampling

from optimizer.context import ProblemContext
from optimizer.models.base import OptimizerModel
from optimizer.models.problem import CompanionPlantingProblem
from optimizer.utils.deduplication import CanonicalDuplicateElimination


class NSGA2Model(OptimizerModel):
    """NSGA-II sur une instance dont les quantités ont été expansées en amont
    (une variable de décision par unité de plante, cf. api/service.py)."""

    name = "nsga2"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--pop-size", type=int, default=200)
        parser.add_argument("--n-gen", type=int, default=400)
        parser.add_argument("--seed", type=int, default=None)
        parser.add_argument(
            "--n-seeds",
            type=int,
            default=1,
            help="Number of diverse seeds used to build the initial population (default: 1)",
        )

    def __init__(self, ctx: ProblemContext, args: argparse.Namespace) -> None:
        super().__init__(ctx, args)
        self.pop_size = args.pop_size
        self.n_seeds = args.n_seeds

    def _build_initial_population(
        self, problem: CompanionPlantingProblem
    ) -> np.ndarray:
        """Generate n_seeds sub-populations with different RNGs and stack them."""
        rng = np.random.default_rng(self.seed)
        sub_seeds = rng.integers(0, 2**31, size=self.n_seeds)

        sampler = IntegerRandomSampling()
        parts = [
            sampler._do(problem, self.pop_size, random_state=np.random.default_rng(s))
            for s in sub_seeds
        ]
        return np.vstack(parts)

    def _build_problem_and_algorithm(self) -> tuple[CompanionPlantingProblem, NSGA2]:
        problem = CompanionPlantingProblem(self.ctx)
        sampling = self._build_initial_population(problem)
        algorithm = NSGA2(
            pop_size=self.pop_size,
            sampling=sampling,
            crossover=SBX(prob=0.9, eta=3, vtype=float, repair=RoundingRepair()),
            mutation=PM(eta=3, vtype=float, repair=RoundingRepair()),
            eliminate_duplicates=CanonicalDuplicateElimination(self.ctx.plant_slugs, self.ctx.n_plots),
        )
        return problem, algorithm
