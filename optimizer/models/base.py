from __future__ import annotations

import argparse
from abc import ABC, abstractmethod

from optimizer.context import ProblemContext
from optimizer.result import OptimizationResult


class OptimizerModel(ABC):
    """Base class for all optimization models."""

    name: str

    @staticmethod
    @abstractmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        """Add model-specific CLI arguments to the parser."""
        ...

    @abstractmethod
    def __init__(self, ctx: ProblemContext, args: argparse.Namespace) -> None:
        """Initialize the model with problem context and parsed CLI args."""
        ...

    @abstractmethod
    def optimize(self) -> OptimizationResult:
        """Run the optimization and return results."""
        ...
