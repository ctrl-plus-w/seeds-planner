from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Solution:
    """A single candidate solution.

    Attributes:
        assignments: shape (n_plants,), int values 0..n_plots
                     (0 = unassigned, 1..n_plots = plot number)
        objectives:  shape (n_objectives,), minimization convention
                     (negative = better)
    """

    assignments: np.ndarray
    objectives: np.ndarray


@dataclass
class OptimizationResult:
    """Output from any optimization model."""

    solutions: list[Solution]

    @property
    def n_solutions(self) -> int:
        return len(self.solutions)
