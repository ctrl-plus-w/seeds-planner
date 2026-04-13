from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from optimizer.classes.garden_data import GardenData
from optimizer.utils.pairs import normalize_pair


@dataclass
class ProblemContext:
    """Domain data shared by all optimization models."""

    plant_slugs: list[str]
    plot_areas: np.ndarray
    garden: GardenData
    n_plants: int
    n_plots: int
    companion_index_pairs: set[tuple[int, int]]
    antagonist_index_pairs: set[tuple[int, int]]
    plant_areas: np.ndarray
    pref_weights: np.ndarray

    @classmethod
    def build(
        cls,
        plant_slugs: list[str],
        plot_areas: list[float],
        garden: GardenData,
        preference_weight: float = 0.1,
    ) -> ProblemContext:
        n_plants = len(plant_slugs)
        n_plots = len(plot_areas)

        companion_index_pairs: set[tuple[int, int]] = set()
        antagonist_index_pairs: set[tuple[int, int]] = set()

        for i in range(n_plants):
            for j in range(i + 1, n_plants):
                pair = normalize_pair(plant_slugs[i], plant_slugs[j])
                if pair in garden.companion_pairs:
                    companion_index_pairs.add((i, j))
                if pair in garden.antagonist_pairs:
                    antagonist_index_pairs.add((i, j))

        plant_areas = np.array(
            [garden.plants_by_slug[s].area for s in plant_slugs]
        )

        pref_weights = np.array(
            [
                1.0 - preference_weight * i / max(n_plants - 1, 1)
                for i in range(n_plants)
            ]
        )

        return cls(
            plant_slugs=plant_slugs,
            plot_areas=np.array(plot_areas),
            garden=garden,
            n_plants=n_plants,
            n_plots=n_plots,
            companion_index_pairs=companion_index_pairs,
            antagonist_index_pairs=antagonist_index_pairs,
            plant_areas=plant_areas,
            pref_weights=pref_weights,
        )
