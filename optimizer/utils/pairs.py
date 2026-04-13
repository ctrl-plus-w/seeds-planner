from __future__ import annotations

from collections.abc import Generator


def normalize_pair(a: str, b: str) -> tuple[str, str]:
    return min(a, b), max(a, b)


def colocated_pairs(
    plots: dict[int, list[int]],
) -> Generator[tuple[int, int], None, None]:
    for plant_indices in plots.values():
        for a in range(len(plant_indices)):
            for b in range(a + 1, len(plant_indices)):
                i, j = plant_indices[a], plant_indices[b]
                yield min(i, j), max(i, j)
