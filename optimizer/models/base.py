from __future__ import annotations

import argparse
from abc import ABC, abstractmethod
from collections.abc import Generator

import numpy as np
from pymoo.indicators.hv import HV
from pymoo.optimize import minimize

from optimizer.context import ProblemContext
from optimizer.models.problem import CompanionPlantingProblem
from optimizer.result import OptimizationResult, Solution
from optimizer.utils.deduplication import canonicalize


class OptimizerModel(ABC):
    """Base class for all optimization models.

    Subclasses must implement ``_build_problem_and_algorithm`` and
    ``add_arguments``.  ``optimize``, ``optimize_streaming`` and
    ``_postprocess_results`` have concrete default implementations that
    can be overridden when needed.
    """

    name: str

    @staticmethod
    @abstractmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        """Add model-specific CLI arguments to the parser."""
        ...

    def __init__(self, ctx: ProblemContext, args: argparse.Namespace) -> None:
        self.ctx = ctx
        self.n_gen: int = args.n_gen
        self.seed: int | None = args.seed

    @abstractmethod
    def _build_problem_and_algorithm(self) -> tuple[CompanionPlantingProblem, object]:
        """Return ``(problem, algorithm)`` ready for pymoo."""
        ...

    # ------------------------------------------------------------------
    # Post-processing (override in subclasses that skip dedup)
    # ------------------------------------------------------------------

    def _postprocess_results(self, res) -> list[Solution]:
        """Deduplicate and convert pymoo result to Solution list."""
        if res.F is None or len(res.F) == 0:
            return []
        seen: set[tuple] = set()
        solutions: list[Solution] = []
        for i in range(len(res.F)):
            assignments = np.round(res.X[i]).astype(int)
            key = canonicalize(assignments, self.ctx.plant_slugs, self.ctx.n_plots)
            if key in seen:
                continue
            seen.add(key)
            solutions.append(Solution(assignments=assignments, objectives=res.F[i]))
        return solutions

    # ------------------------------------------------------------------
    # Batch optimization
    # ------------------------------------------------------------------

    def optimize(self) -> OptimizationResult:
        problem, algorithm = self._build_problem_and_algorithm()
        res = minimize(
            problem,
            algorithm,
            termination=("n_gen", self.n_gen),
            seed=self.seed,
            verbose=False,
        )
        return OptimizationResult(solutions=self._postprocess_results(res))

    # ------------------------------------------------------------------
    # Streaming optimization with per-generation hypervolume
    # ------------------------------------------------------------------

    def optimize_streaming(self) -> Generator[dict, None, None]:
        """Yield per-generation hypervolume progress, then yield the final result."""
        problem, algorithm = self._build_problem_and_algorithm()

        algorithm.setup(
            problem,
            termination=("n_gen", self.n_gen),
            seed=self.seed,
        )

        hv_indicator = HV(ref_point=np.array([0.0, 0.0]))

        while algorithm.has_next():
            algorithm.next()
            pop = algorithm.pop
            G = pop.get("G")
            F = pop.get("F")

            if G is not None and len(G) > 0:
                feasible_mask = np.all(G <= 0, axis=1)
                F_feasible = F[feasible_mask]
            else:
                F_feasible = F

            if len(F_feasible) > 0:
                hv = float(hv_indicator(F_feasible))
            else:
                hv = 0.0

            yield {
                "type": "progress",
                "generation": algorithm.n_gen,
                "hypervolume": hv,
            }

        res = algorithm.result()
        solutions = self._postprocess_results(res)
        yield {"type": "result", "result": OptimizationResult(solutions=solutions)}
