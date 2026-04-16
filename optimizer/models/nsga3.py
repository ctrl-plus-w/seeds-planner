from __future__ import annotations

import argparse

from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.operators.sampling.rnd import IntegerRandomSampling
from pymoo.util.ref_dirs import get_reference_directions

from optimizer.context import ProblemContext
from optimizer.models.base import OptimizerModel
from optimizer.models.problem import CompanionPlantingProblem
from optimizer.utils.deduplication import CanonicalDuplicateElimination


class NSGA3Model(OptimizerModel):
    """NSGA-III (Reference-direction-based NSGA) pour l'optimisation
    multi-objectif sous contraintes.

    Algorithme à décomposition utilisant des directions de référence
    (DAS-Dennis) pour maintenir la diversité sur le front de Pareto.
    """

    name = "nsga3"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--pop-size", type=int, default=100)
        parser.add_argument("--n-partitions", type=int, default=99)
        parser.add_argument("--n-gen", type=int, default=400)
        parser.add_argument("--seed", type=int, default=None)

    def __init__(self, ctx: ProblemContext, args: argparse.Namespace) -> None:
        super().__init__(ctx, args)
        self.pop_size = args.pop_size

        if hasattr(args, "n_partitions") and args.n_partitions is not None:
            n_partitions = args.n_partitions
        else:
            n_partitions = max(getattr(args, "pop_size", 13) - 1, 3)

        self.ref_dirs = get_reference_directions(
            "das-dennis", 2, n_partitions=n_partitions
        )

    def _build_problem_and_algorithm(self) -> tuple[CompanionPlantingProblem, NSGA3]:
        problem = CompanionPlantingProblem(self.ctx)
        algorithm = NSGA3(
            ref_dirs=self.ref_dirs,
            pop_size=self.pop_size,
            sampling=IntegerRandomSampling(),
            crossover=SBX(
                n_offsprings=1, prob=0.9, eta=3, vtype=float, repair=RoundingRepair()
            ),
            mutation=PM(eta=3, vtype=float, repair=RoundingRepair()),
            eliminate_duplicates=CanonicalDuplicateElimination(self.ctx.plant_slugs, self.ctx.n_plots),
        )
        return problem, algorithm
