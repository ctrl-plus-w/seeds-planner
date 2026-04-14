export interface PlantSummary {
  slug: string
  name: string
  scientific_name: string
  area: number
  has_relations: boolean
}

export interface PlantsResponse {
  run_id: string
  n_plants: number
  plants: PlantSummary[]
}

export interface PlantQuantity {
  slug: string
  quantity: number
}

export interface OptimizeRequest {
  plants: PlantQuantity[]
  plot_areas: number[]
  pop_size?: number
  n_gen?: number
  seed?: number | null
  compat_weight?: number
}

export interface PlantInPlot {
  slug: string
  name: string
  area: number
  companions_here: string[]
}

export interface PlotResult {
  index: number
  area: number
  used_area: number
  utilization: number
  plants: PlantInPlot[]
}

export interface SolutionResult {
  rank: number
  compatibility: number
  space_utilization: number
  plots: PlotResult[]
  unassigned: string[]
}

export interface OptimizeResponse {
  n_total_solutions: number
  solutions: SolutionResult[]
}
