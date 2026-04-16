import numpy as np

from pymoo.core.duplicate import DuplicateElimination


def canonicalize(x: np.ndarray, plant_slugs: list[str]) -> tuple:
    """Build a canonical key invariant to plot-label permutation AND
    instance swaps of the same plant type.

    Returns a sorted tuple of (sorted slug bag per plot, sorted unassigned bag).
    Two solutions that put the same *types* of plants in the same plots
    always produce the same key.
    """
    assignments = np.round(x).astype(int)
    plots: dict[int, list[str]] = {}
    unassigned: list[str] = []
    for i, plot_id in enumerate(assignments):
        plot_id = int(plot_id)
        if plot_id > 0:
            plots.setdefault(plot_id, []).append(plant_slugs[i])
        else:
            unassigned.append(plant_slugs[i])
    plot_bags = tuple(sorted(tuple(sorted(slugs)) for slugs in plots.values()))
    return plot_bags, tuple(sorted(unassigned))


class CanonicalDuplicateElimination(DuplicateElimination):
    """Treat visually identical solutions as duplicates.

    Two solutions are duplicates if they place the same plant *types* in the
    same plots, even when the underlying instance indices differ.
    Uses hash-based O(pop) dedup instead of pairwise O(pop²) comparison.
    """

    def __init__(self, plant_slugs: list[str]) -> None:
        super().__init__()
        self.plant_slugs = plant_slugs

    def _do(self, pop, other, is_duplicate):
        seen: set[tuple] = set()

        if other is not None:
            for ind in other:
                seen.add(canonicalize(ind.X, self.plant_slugs))

        for i, ind in enumerate(pop):
            key = canonicalize(ind.X, self.plant_slugs)
            if key in seen:
                is_duplicate[i] = True
            else:
                seen.add(key)

        return is_duplicate
