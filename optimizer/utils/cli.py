import sys

from optimizer.classes.garden_data import GardenData
from optimizer.data import resolve_plant


def parse_plot_areas(areas: str) -> list[float]:
    plot_areas: list[float] = []

    try:
        plot_areas = [float(s.strip()) for s in areas if s.strip()]
    except ValueError as e:
        print("Error: plot areas must be numbers (e.g. '6,6,8,14')")
        sys.exit(1)

    if not plot_areas or any(a <= 0 for a in plot_areas):
        print("Error: all plot areas must be positive numbers")
        sys.exit(1)

    return plot_areas


def parse_plant_slugs(garden: GardenData, slugs: str) -> list[str]:
    raw_plants = [s.strip() for s in slugs if s.strip()]
    plant_slugs: list[str] = []
    seen: set[str] = set()

    print("Resolving plants:")

    for query in raw_plants:
        slug = resolve_plant(query, garden)
        if slug is None:

            print(f"  Error: could not find plant '{query}'")
            sys.exit(1)
        if slug in seen:
            print(f"  Warning: skipping duplicate '{query}' ({slug})")
            continue

        seen.add(slug)
        info = garden.plants_by_slug[slug]

        print(f"  {query} -> {info.name} ({slug}, area={info.area:.2f} m^2)")
        plant_slugs.append(slug)

    if len(plant_slugs) < 2:
        print("Error: need at least 2 plants to optimize")
        sys.exit(1)

    return plant_slugs
