import { useEffect, useMemo, useState } from "react"
import type { HvPoint, OptimizeResponse, PlantInPlot, SolutionResult } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { GardenSvg } from "./GardenSvg"
import { HypervolumePlot } from "./HypervolumePlot"
import { ParetoPlot } from "./ParetoPlot"

interface AggregatedPlant {
  slug: string
  name: string
  count: number
  totalArea: number
  companions: string[]
}

function aggregate(plants: PlantInPlot[]): AggregatedPlant[] {
  const map = new Map<string, AggregatedPlant>()
  for (const p of plants) {
    const existing = map.get(p.slug)
    if (existing) {
      existing.count += 1
      existing.totalArea += p.area
      for (const c of p.companions_here) {
        if (!existing.companions.includes(c)) existing.companions.push(c)
      }
    } else {
      map.set(p.slug, {
        slug: p.slug,
        name: p.name,
        count: 1,
        totalArea: p.area,
        companions: [...new Set(p.companions_here)],
      })
    }
  }
  return Array.from(map.values())
}

function aggregateUnassigned(names: string[]): string[] {
  const counts = new Map<string, number>()
  for (const n of names) counts.set(n, (counts.get(n) ?? 0) + 1)
  return Array.from(counts.entries()).map(([name, n]) => (n > 1 ? `${name} × ${n}` : name))
}


interface ResultsViewProps {
  result: OptimizeResponse
  hvCurve?: HvPoint[]
}

function rerankSolutions(
  solutions: SolutionResult[],
  compatWeight: number,
): SolutionResult[] {
  if (solutions.length === 0) return solutions

  const normalize = (vals: number[]) => {
    const min = Math.min(...vals)
    const max = Math.max(...vals)
    const span = max - min
    return vals.map((v) => (span > 0 ? (v - min) / span : 0))
  }

  const cN = normalize(solutions.map((s) => s.compatibility))
  const uN = normalize(solutions.map((s) => s.space_utilization))

  const scored = solutions.map((s, i) => ({
    sol: s,
    score: compatWeight * cN[i] + (1 - compatWeight) * uN[i],
  }))
  scored.sort((a, b) => b.score - a.score)
  return scored.map((entry, i) => ({ ...entry.sol, rank: i + 1 }))
}

export function ResultsView({ result, hvCurve }: ResultsViewProps) {
  const [compatWeight, setCompatWeight] = useState<number>(0.5)

  const ranked = useMemo(
    () => rerankSolutions(result.solutions, compatWeight),
    [result.solutions, compatWeight],
  )

  const solutionKey = (s: SolutionResult) =>
    `${s.compatibility.toFixed(4)}|${s.space_utilization.toFixed(4)}`

  const [selectedKey, setSelectedKey] = useState<string>(() =>
    ranked.length > 0 ? solutionKey(ranked[0]) : "",
  )

  useEffect(() => {
    if (ranked.length > 0) {
      setSelectedKey(solutionKey(ranked[0]))
    }
  }, [compatWeight, result.solutions])

  const selected =
    ranked.find((s) => solutionKey(s) === selectedKey) ?? ranked[0]

  if (result.solutions.length === 0) {
    return (
      <Card>
        <CardContent>
          <p className="text-sm text-stone-500">
            Aucune solution réalisable. Essayez d'augmenter la taille des parcelles ou de réduire le nombre de plantes.
          </p>
        </CardContent>
      </Card>
    )
  }

  const selectByRank = (rank: number) => {
    const s = ranked.find((sol) => sol.rank === rank)
    if (s) setSelectedKey(solutionKey(s))
  }

  const compatPct = Math.round(compatWeight * 100)
  const utilPct = 100 - compatPct

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Front de Pareto</CardTitle>
          <p className="text-xs text-stone-500">
            {result.n_total_solutions} solutions Pareto-optimales · clique sur un point ou dans la liste pour voir la parcelle
          </p>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs text-stone-600 mb-1">
              <span>
                Priorité : <span className="font-semibold text-green-700">compatibilité {compatPct}%</span>
                <span className="text-stone-400"> · </span>
                <span className="font-semibold text-sky-700">placement {utilPct}%</span>
              </span>
              <span className="text-stone-400">déplace le curseur pour reclasser les solutions</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={compatPct}
              onChange={(e) => setCompatWeight(Number(e.target.value) / 100)}
              className="w-full accent-green-600"
              aria-label="Pondération compatibilité vs espace utilisé"
            />
            <div className="flex justify-between text-[10px] text-stone-400 mt-0.5">
              <span>← privilégier le placement</span>
              <span>privilégier les compagnonnages →</span>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_220px] gap-4">
            <ParetoPlot
              solutions={ranked}
              selectedRank={selected.rank}
              onSelect={selectByRank}
            />
            <ol className="max-h-80 overflow-auto rounded-md border border-stone-200 divide-y divide-stone-100 text-xs">
              {ranked.map((s) => {
                const isActive = s.rank === selected.rank
                return (
                  <li key={solutionKey(s)}>
                    <button
                      type="button"
                      onClick={() => setSelectedKey(solutionKey(s))}
                      className={`w-full text-left px-3 py-2 transition-colors ${
                        isActive
                          ? "bg-green-50 text-green-900 font-medium"
                          : "hover:bg-stone-50 text-stone-700"
                      }`}
                    >
                      <span className="font-mono text-stone-400 mr-2">#{s.rank}</span>
                      compat <span className="font-semibold">{s.compatibility.toFixed(2)}</span>
                      <span className="text-stone-400"> · </span>
                      <span className="font-semibold">{s.space_utilization.toFixed(0)}%</span> espace
                    </button>
                  </li>
                )
              })}
            </ol>
          </div>
        </CardContent>
      </Card>

      {hvCurve && hvCurve.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Convergence</CardTitle>
            <p className="text-xs text-stone-500">
              Hypervolume sur {hvCurve.length} générations
            </p>
          </CardHeader>
          <CardContent>
            <HypervolumePlot
              hvCurve={hvCurve}
              totalGenerations={hvCurve.length}
              isStreaming={false}
            />
          </CardContent>
        </Card>
      )}

      <Card key={selected.rank}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Solution #{selected.rank}</CardTitle>
            <div className="flex gap-4 text-sm">
              <span>
                <span className="text-stone-500">Compatibilité</span>{" "}
                <span className="font-semibold text-stone-900">
                  {selected.compatibility.toFixed(2)}
                </span>
              </span>
              <span>
                <span className="text-stone-500">Espace utilisé</span>{" "}
                <span className="font-semibold text-stone-900">
                  {selected.space_utilization.toFixed(0)}%
                </span>
              </span>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <GardenSvg plots={selected.plots} />

          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            {selected.plots.map((plot) => (
              <div key={plot.index} className="rounded-md border border-stone-100 bg-stone-50 p-3">
                <div className="font-medium text-stone-900 mb-1">
                  Parcelle {plot.index} — {plot.used_area.toFixed(2)} / {plot.area.toFixed(1)} m²
                </div>
                {plot.plants.length === 0 ? (
                  <div className="text-stone-400 italic text-xs">vide</div>
                ) : (
                  <ul className="space-y-1 text-xs text-stone-700">
                    {aggregate(plot.plants).map((p) => (
                      <li key={p.slug}>
                        <span className="font-medium">
                          {p.name}
                          {p.count > 1 && <span className="text-stone-500"> × {p.count}</span>}
                        </span>
                        <span className="text-stone-400 ml-2">
                          ({p.totalArea.toFixed(2)} m²)
                        </span>
                        {p.companions.length > 0 && (
                          <span className="text-green-700 ml-2">
                            ♥ {p.companions.join(", ")}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>

          {selected.unassigned.length > 0 && (
            <div className="mt-3 text-xs text-stone-500">
              <span className="font-medium">Non placées :</span>{" "}
              {aggregateUnassigned(selected.unassigned).join(", ")}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
