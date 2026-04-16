from __future__ import annotations

from pydantic import BaseModel, Field


class PlantSummary(BaseModel):
    slug: str
    name: str
    scientific_name: str
    area: float
    has_relations: bool


class PlantsResponse(BaseModel):
    run_id: str
    n_plants: int
    plants: list[PlantSummary]


class PlantQuantity(BaseModel):
    slug: str
    quantity: int = Field(..., ge=1, le=200)


class OptimizeRequest(BaseModel):
    plants: list[PlantQuantity] = Field(..., min_length=1)
    plot_areas: list[float] = Field(..., min_length=1)
    pop_size: int = 200
    n_gen: int = 400
    seed: int | None = None
    n_seeds: int = Field(1, ge=1)
    compat_weight: float = Field(0.5, ge=0.0, le=1.0)


class PlantInPlot(BaseModel):
    slug: str
    name: str
    area: float
    companions_here: list[str]


class PlotResult(BaseModel):
    index: int
    area: float
    used_area: float
    utilization: float
    plants: list[PlantInPlot]


class SolutionResult(BaseModel):
    rank: int
    compatibility: float
    space_utilization: float
    plots: list[PlotResult]
    unassigned: list[str]


class OptimizeResponse(BaseModel):
    n_total_solutions: int
    solutions: list[SolutionResult]
