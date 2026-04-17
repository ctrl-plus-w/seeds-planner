from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from optimizer.models.base import OptimizerModel

MODEL_REGISTRY: dict[str, type[OptimizerModel]] = {}


def register_model(cls: type[OptimizerModel]) -> None:
    MODEL_REGISTRY[cls.name] = cls


def get_model(name: str) -> type[OptimizerModel]:
    if name not in MODEL_REGISTRY:
        available = ", ".join(sorted(MODEL_REGISTRY.keys()))
        raise ValueError(f"Unknown model '{name}'. Available: {available}")
    return MODEL_REGISTRY[name]


from optimizer.models.cmopso import CMOPSOModel  # noqa: E402
from optimizer.models.nsga2 import NSGA2Model  # noqa: E402
from optimizer.models.nsga3 import NSGA3Model  # noqa: E402
from optimizer.models.pulp import PulpModel  # noqa: E402

register_model(NSGA2Model)
register_model(CMOPSOModel)
register_model(NSGA3Model)

register_model(PulpModel)
