from dataclasses import dataclass


@dataclass
class PlantInfo:
    slug: str
    name: str
    scientific_name: str
    width: float | None
    area: float
