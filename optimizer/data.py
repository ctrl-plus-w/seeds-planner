from __future__ import annotations

import json
import difflib
from pathlib import Path

from optimizer.classes.garden_data import GardenData
from optimizer.classes.plant_info import PlantInfo

from optimizer.utils.pairs import normalize_pair
from optimizer.utils.parsing import DEFAULT_WIDTH, parse_width


def load_garden_data(data_dir: Path) -> GardenData:
    plants_path = data_dir / "plants.json"
    companions_path = data_dir / "companions.json"

    if not plants_path.exists():
        raise FileNotFoundError(f"{plants_path} not found")
    if not companions_path.exists():
        raise FileNotFoundError(f"{companions_path} not found")

    with open(plants_path, encoding="utf-8") as f:
        raw_plants: list[dict] = json.load(f)

    plants_by_slug: dict[str, PlantInfo] = {}
    search_index: dict[str, list[str]] = {}

    def _add_to_index(key: str, slug: str) -> None:
        key = key.lower()

        if key not in search_index:
            search_index[key] = []

        if slug not in search_index[key]:
            search_index[key].append(slug)

    for p in raw_plants:
        slug = p["slug"]
        name = p.get("name", "")
        scientific_name = p.get("scientific_name", "")

        width: float | None = None
        for attr in p.get("data", []):
            if attr["key"] == "Width":
                width = parse_width(attr["value"])
                break

        effective_width = width if width is not None else DEFAULT_WIDTH
        area = effective_width**2

        plants_by_slug[slug] = PlantInfo(
            slug=slug,
            name=name,
            scientific_name=scientific_name,
            width=width,
            area=area,
        )

        _add_to_index(slug, slug)
        if name:
            _add_to_index(name, slug)
        if scientific_name:
            _add_to_index(scientific_name, slug)

    with open(companions_path, encoding="utf-8") as f:
        raw_companions: list[dict] = json.load(f)

    companion_pairs: set[tuple[str, str]] = set()
    antagonist_pairs: set[tuple[str, str]] = set()
    slugs_with_relations: set[str] = set()

    for entry in raw_companions:
        slug_a = entry["slug"]
        comps = entry.get("companions", [])
        antags = entry.get("antagonists", [])

        if comps or antags:
            slugs_with_relations.add(slug_a)

        for comp in comps:
            pair = normalize_pair(slug_a, comp["slug"])
            companion_pairs.add(pair)
            slugs_with_relations.add(comp["slug"])

        for antag in antags:
            pair = normalize_pair(slug_a, antag["slug"])
            antagonist_pairs.add(pair)
            slugs_with_relations.add(antag["slug"])

    companion_pairs -= antagonist_pairs

    return GardenData(
        plants_by_slug=plants_by_slug,
        companion_pairs=companion_pairs,
        antagonist_pairs=antagonist_pairs,
        _search_index=search_index,
        _slugs_with_relations=slugs_with_relations,
    )


def _pick_best_slug(slugs: list[str], garden: GardenData) -> str:
    with_data = [s for s in slugs if s in garden._slugs_with_relations]
    if with_data:
        return with_data[0]
    return slugs[0]


def resolve_plant(query: str, garden: GardenData) -> str | None:
    q = query.strip()
    ql = q.lower()

    if q in garden.plants_by_slug:
        return q

    if ql in garden._search_index:
        slugs = garden._search_index[ql]
        return _pick_best_slug(slugs, garden)

    name_matches: list[str] = []
    slug_matches: list[str] = []

    for key, slugs in garden._search_index.items():
        if ql not in key:
            continue

        for slug in slugs:
            info = garden.plants_by_slug[slug]
            if ql in info.name.lower():
                name_matches.append(slug)
            else:
                slug_matches.append(slug)

    candidates = name_matches or slug_matches

    if candidates:
        seen: set[str] = set()
        unique = []

        for s in candidates:
            if s not in seen:
                seen.add(s)
                unique.append(s)

        best = _pick_best_slug(unique, garden)

        if len(unique) > 1:
            print(
                f"  Warning: '{q}' matches multiple plants, using: "
                f"{garden.plants_by_slug[best].name} ({best})"
            )
        return best

    name_keys = [
        key
        for key, slugs in garden._search_index.items()
        if any(
            garden.plants_by_slug[s].name.lower() == key
            or garden.plants_by_slug[s].scientific_name.lower() == key
            for s in slugs
        )
    ]

    close = difflib.get_close_matches(ql, name_keys, n=3, cutoff=0.6)

    if close:
        slugs = garden._search_index[close[0]]
        best = _pick_best_slug(slugs, garden)
        print(
            f"  Warning: '{q}' not found exactly, using closest match: "
            f"{garden.plants_by_slug[best].name} ({best})"
        )
        return best

    return None
