from dataclasses import dataclass, field

from optimizer.classes.plant_info import PlantInfo


@dataclass
class GardenData:
    plants_by_slug: dict[str, PlantInfo]
    companion_pairs: set[tuple[str, str]]
    antagonist_pairs: set[tuple[str, str]]

    _search_index: dict[str, list[str]] = field(default_factory=dict, repr=False)
    _slugs_with_relations: set[str] = field(default_factory=set, repr=False)
