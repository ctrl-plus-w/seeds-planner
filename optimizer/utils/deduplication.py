import numpy as np

from pymoo.core.duplicate import DuplicateElimination


def canonicalize(x: np.ndarray, plant_slugs: list[str], n_plots: int) -> tuple:
    """Build a canonical key invariant to instance swaps of the same plant
    type but **aware of plot identity**.

    Returns a tuple of (slug bag per plot in plot-id order, sorted unassigned bag).
    Slugs within each plot are sorted so that swapping instances of the
    same type does not create a new key, but assigning different types to
    different plots (e.g. swapping a 2 m² and a 1 m² plot) *does*.
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
    plot_bags = tuple(tuple(sorted(plots.get(k, []))) for k in range(1, n_plots + 1))
    return plot_bags, tuple(sorted(unassigned))


class CanonicalDuplicateElimination(DuplicateElimination):
    """Treat visually identical solutions as duplicates.

    Two solutions are duplicates if they place the same plant *types* in the
    same plots, even when the underlying instance indices differ.
    Uses hash-based O(pop) dedup instead of pairwise O(pop²) comparison.
    """

    def __init__(self, plant_slugs: list[str], n_plots: int) -> None:
        super().__init__()
        self.plant_slugs = plant_slugs
        self.n_plots = n_plots

    def _do(self, pop, other, is_duplicate):
        seen: set[tuple] = set()

        if other is not None:
            for ind in other:
                seen.add(canonicalize(ind.X, self.plant_slugs, self.n_plots))

        for i, ind in enumerate(pop):
            key = canonicalize(ind.X, self.plant_slugs, self.n_plots)
            if key in seen:
                is_duplicate[i] = True
            else:
                seen.add(key)

        return is_duplicate
