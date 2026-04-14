import { useEffect, useMemo, useState } from "react"
import type { OptimizeResponse, PlantInPlot, SolutionResult } from "@/api/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { GardenSvg } from "./GardenSvg"

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

interface ParetoPlotProps {
  solutions: SolutionResult[]
  selectedRank: number
  onSelect: (rank: number) => void
}

interface SolutionGroup {
  cx: number
  cy: number
  members: SolutionResult[]
}

function ParetoPlot({ solutions, selectedRank, onSelect }: ParetoPlotProps) {
  const W = 560
  const H = 320
  const PAD_L = 56
  const PAD_R = 16
  const PAD_T = 16
  const PAD_B = 44

  const { xMin, xMax, yMin, yMax } = useMemo(() => {
    const xs = solutions.map((s) => s.compatibility)
    const ys = solutions.map((s) => s.space_utilization)
    const xMin = Math.min(...xs)
    const xMax = Math.max(...xs)
    const yMin = Math.min(...ys)
    const yMax = Math.max(...ys)
    const xPad = (xMax - xMin) * 0.05 || 1
    const yPad = (yMax - yMin) * 0.05 || 1
    return { xMin: xMin - xPad, xMax: xMax + xPad, yMin: yMin - yPad, yMax: yMax + yPad }
  }, [solutions])

  const groups = useMemo<SolutionGroup[]>(() => {
    const map = new Map<string, SolutionResult[]>()
    for (const s of solutions) {
      const key = `${s.compatibility.toFixed(3)}|${s.space_utilization.toFixed(3)}`
      const arr = map.get(key)
      if (arr) arr.push(s)
      else map.set(key, [s])
    }
    return Array.from(map.values()).map((members) => ({
      cx: members[0].compatibility,
      cy: members[0].space_utilization,
      members,
    }))
  }, [solutions])

  const plotW = W - PAD_L - PAD_R
  const plotH = H - PAD_T - PAD_B

  const sx = (x: number) =>
    PAD_L + ((x - xMin) / (xMax - xMin || 1)) * plotW
  const sy = (y: number) =>
    PAD_T + plotH - ((y - yMin) / (yMax - yMin || 1)) * plotH

  const xTicks = 5
  const yTicks = 5

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full h-auto"
      role="img"
      aria-label="Front de Pareto"
    >
      <rect
        x={PAD_L}
        y={PAD_T}
        width={plotW}
        height={plotH}
        fill="#fafaf9"
        stroke="#e7e5e4"
      />

      {Array.from({ length: xTicks + 1 }, (_, i) => {
        const t = i / xTicks
        const x = PAD_L + t * plotW
        const value = xMin + t * (xMax - xMin)
        return (
          <g key={`xt-${i}`}>
            <line x1={x} x2={x} y1={PAD_T} y2={PAD_T + plotH} stroke="#f5f5f4" />
            <line x1={x} x2={x} y1={PAD_T + plotH} y2={PAD_T + plotH + 4} stroke="#a8a29e" />
            <text
              x={x}
              y={PAD_T + plotH + 16}
              fontSize={10}
              fontFamily="system-ui, sans-serif"
              fill="#78716c"
              textAnchor="middle"
            >
              {value.toFixed(1)}
            </text>
          </g>
        )
      })}

      {Array.from({ length: yTicks + 1 }, (_, i) => {
        const t = i / yTicks
        const y = PAD_T + plotH - t * plotH
        const value = yMin + t * (yMax - yMin)
        return (
          <g key={`yt-${i}`}>
            <line x1={PAD_L} x2={PAD_L + plotW} y1={y} y2={y} stroke="#f5f5f4" />
            <line x1={PAD_L - 4} x2={PAD_L} y1={y} y2={y} stroke="#a8a29e" />
            <text
              x={PAD_L - 8}
              y={y + 3}
              fontSize={10}
              fontFamily="system-ui, sans-serif"
              fill="#78716c"
              textAnchor="end"
            >
              {value.toFixed(0)}
            </text>
          </g>
        )
      })}

      <text
        x={PAD_L + plotW / 2}
        y={H - 8}
        fontSize={11}
        fontFamily="system-ui, sans-serif"
        fill="#44403c"
        textAnchor="middle"
      >
        Compatibilité →
      </text>
      <text
        x={14}
        y={PAD_T + plotH / 2}
        fontSize={11}
        fontFamily="system-ui, sans-serif"
        fill="#44403c"
        textAnchor="middle"
        transform={`rotate(-90 14 ${PAD_T + plotH / 2})`}
      >
        Espace utilisé (%) →
      </text>

      {groups.map((g) => {
        const cx = sx(g.cx)
        const cy = sy(g.cy)
        const containsSelected = g.members.some((m) => m.rank === selectedRank)
        const count = g.members.length
        const baseR = count > 1 ? 7 : 5
        const r = containsSelected ? baseR + 3 : baseR
        const ranks = g.members.map((m) => `#${m.rank}`).join(", ")
        return (
          <g
            key={`${g.cx}-${g.cy}`}
            onClick={() => onSelect(g.members[0].rank)}
            style={{ cursor: "pointer" }}
          >
            <circle
              cx={cx}
              cy={cy}
              r={r}
              fill={containsSelected ? "#16a34a" : "#0ea5e9"}
              fillOpacity={containsSelected ? 1 : 0.75}
              stroke="#fff"
              strokeWidth={1.5}
            >
              <title>
                {`${ranks} — compat ${g.cx.toFixed(2)} · ${g.cy.toFixed(0)}%`}
              </title>
            </circle>
            {count > 1 && (
              <text
                x={cx + r + 3}
                y={cy + 3}
                fontSize={10}
                fontFamily="system-ui, sans-serif"
                fill="#44403c"
                fontWeight={600}
                pointerEvents="none"
              >
                ×{count}
              </text>
            )}
          </g>
        )
      })}
    </svg>
  )
}

interface ResultsViewProps {
  result: OptimizeResponse
}

function rerankSolutions(
  solutions: SolutionResult[],
  compatWeight: number,
): SolutionResult[] {
  if (solutions.length === 0) return solutions
  const compats = solutions.map((s) => s.compatibility)
  const utils = solutions.map((s) => s.space_utilization)
  const cMin = Math.min(...compats)
  const cMax = Math.max(...compats)
  const uMin = Math.min(...utils)
  const uMax = Math.max(...utils)
  const cSpan = cMax - cMin
  const uSpan = uMax - uMin
  const scored = solutions.map((s) => {
    const cN = cSpan > 0 ? (s.compatibility - cMin) / cSpan : 0
    const uN = uSpan > 0 ? (s.space_utilization - uMin) / uSpan : 0
    return {
      sol: s,
      score: compatWeight * cN + (1 - compatWeight) * uN,
    }
  })
  scored.sort((a, b) => b.score - a.score)
  return scored.map((entry, i) => ({ ...entry.sol, rank: i + 1 }))
}

export function ResultsView({ result }: ResultsViewProps) {
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
                <span className="font-semibold text-sky-700">espace {utilPct}%</span>
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
              <span>← privilégier l'espace</span>
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
                      <span className="font-semibold">{s.space_utilization.toFixed(0)}%</span>
                    </button>
                  </li>
                )
              })}
            </ol>
          </div>
        </CardContent>
      </Card>

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
