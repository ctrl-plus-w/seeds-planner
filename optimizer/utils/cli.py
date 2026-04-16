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


def parse_plant_slugs(garden: GardenData, raw_entries: list[str]) -> list[str]:
    """Parse plant entries with optional quantities (e.g. 'tomato:3') and expand."""
    plant_slugs: list[str] = []
    seen: set[str] = set()

    print("Resolving plants:")

    for entry in raw_entries:
        entry = entry.strip()
        if not entry:
            continue

        if ":" in entry:
            name, qty_str = entry.rsplit(":", 1)
            try:
                qty = int(qty_str)
            except ValueError:
                print(f"  Error: invalid quantity in '{entry}'")
                sys.exit(1)
            if qty < 1:
                print(f"  Error: quantity must be >= 1 in '{entry}'")
                sys.exit(1)
        else:
            name, qty = entry, 1

        slug = resolve_plant(name, garden)
        if slug is None:
            print(f"  Error: could not find plant '{name}'")
            sys.exit(1)
        if slug in seen:
            print(f"  Warning: skipping duplicate '{name}' ({slug})")
            continue

        seen.add(slug)
        info = garden.plants_by_slug[slug]

        print(f"  {name} -> {info.name} ({slug}, area={info.area:.2f} m^2) x{qty}")
        plant_slugs.extend([slug] * qty)

    if len(plant_slugs) < 2:
        print("Error: need at least 2 plant instances to optimize")
        sys.exit(1)

    return plant_slugs
