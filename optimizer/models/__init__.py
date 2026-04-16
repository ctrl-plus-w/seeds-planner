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


from optimizer.models.nsga2_initial import NSGA2InitialModel  # noqa: E402
from optimizer.models.nsga2_quantity import NSGA2QuantityModel  # noqa: E402
from optimizer.models.ctaea import CTAEAModel  # noqa: E402

register_model(NSGA2InitialModel)
register_model(NSGA2QuantityModel)
register_model(CTAEAModel)
