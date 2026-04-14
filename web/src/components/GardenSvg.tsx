import type { PlotResult } from "@/api/types"

const PALETTE = [
  "#16a34a",
  "#0ea5e9",
  "#f59e0b",
  "#dc2626",
  "#9333ea",
  "#0891b2",
  "#ca8a04",
  "#db2777",
  "#65a30d",
  "#7c3aed",
  "#0d9488",
  "#e11d48",
]

function colorForSlug(slug: string): string {
  let hash = 0
  for (let i = 0; i < slug.length; i++) {
    hash = (hash * 31 + slug.charCodeAt(i)) >>> 0
  }
  return PALETTE[hash % PALETTE.length]
}

interface CellData {
  slug: string
  name: string
  area: number
  isEmpty: boolean
}

interface Rect {
  x: number
  y: number
  w: number
  h: number
  data: CellData
}

interface ScaledItem {
  area: number
  data: CellData
}

function worstRatio(row: ScaledItem[], shortSide: number): number {
  if (row.length === 0) return Infinity
  const sum = row.reduce((s, i) => s + i.area, 0)
  if (sum <= 0) return Infinity
  const s2 = shortSide * shortSide
  const sum2 = sum * sum
  let worst = 0
  for (const item of row) {
    if (item.area <= 0) continue
    const ratio = Math.max((s2 * item.area) / sum2, sum2 / (s2 * item.area))
    if (ratio > worst) worst = ratio
  }
  return worst
}

function layoutRow(
  row: ScaledItem[],
  x: number,
  y: number,
  w: number,
  h: number,
): { rects: Rect[]; nextX: number; nextY: number; nextW: number; nextH: number } {
  const rowSum = row.reduce((s, i) => s + i.area, 0)
  const rects: Rect[] = []

  if (w <= h) {
    const rowH = rowSum / w
    let cx = x
    for (const item of row) {
      const itemW = item.area / rowH
      rects.push({ x: cx, y, w: itemW, h: rowH, data: item.data })
      cx += itemW
    }
    return { rects, nextX: x, nextY: y + rowH, nextW: w, nextH: h - rowH }
  } else {
    const colW = rowSum / h
    let cy = y
    for (const item of row) {
      const itemH = item.area / colW
      rects.push({ x, y: cy, w: colW, h: itemH, data: item.data })
      cy += itemH
    }
    return { rects, nextX: x + colW, nextY: y, nextW: w - colW, nextH: h }
  }
}

/** Squarified treemap (Bruls, Huijse, van Wijk). */
function squarify(items: ScaledItem[], x: number, y: number, w: number, h: number): Rect[] {
  const result: Rect[] = []
  let remaining = [...items].sort((a, b) => b.area - a.area).filter((i) => i.area > 0)
  let curX = x
  let curY = y
  let curW = w
  let curH = h

  while (remaining.length > 0) {
    const shortSide = Math.min(curW, curH)
    if (shortSide <= 0) break

    const row: ScaledItem[] = []
    while (remaining.length > 0) {
      const candidate = [...row, remaining[0]]
      const candidateRatio = worstRatio(candidate, shortSide)
      const currentRatio = row.length === 0 ? Infinity : worstRatio(row, shortSide)
      if (row.length === 0 || candidateRatio <= currentRatio) {
        row.push(remaining.shift()!)
      } else {
        break
      }
    }

    const laid = layoutRow(row, curX, curY, curW, curH)
    result.push(...laid.rects)
    curX = laid.nextX
    curY = laid.nextY
    curW = laid.nextW
    curH = laid.nextH
  }

  return result
}

function packPlot(plot: PlotResult, boxW: number, boxH: number): Rect[] {
  const items: ScaledItem[] = []
  const totalPhysical = plot.area > 0 ? plot.area : 1

  for (const p of plot.plants) {
    items.push({
      area: (p.area / totalPhysical) * (boxW * boxH),
      data: { slug: p.slug, name: p.name, area: p.area, isEmpty: false },
    })
  }

  const usedPhysical = plot.plants.reduce((s, p) => s + p.area, 0)
  const emptyPhysical = Math.max(0, plot.area - usedPhysical)
  if (emptyPhysical > 0.001) {
    items.push({
      area: (emptyPhysical / totalPhysical) * (boxW * boxH),
      data: { slug: "__empty__", name: "", area: emptyPhysical, isEmpty: true },
    })
  }

  return squarify(items, 0, 0, boxW, boxH)
}

interface GardenSvgProps {
  plots: PlotResult[]
}

export function GardenSvg({ plots }: GardenSvgProps) {
  const PLOT_W = 260
  const PLOT_H = 180
  const GAP = 20
  const PAD = 12
  const HEADER_H = 18
  const LEGEND_H = 56

  const cols = Math.min(plots.length, 2)
  const rows = Math.ceil(plots.length / cols)
  const cellH = PLOT_H + HEADER_H + LEGEND_H
  const totalW = cols * (PLOT_W + GAP) - GAP + PAD * 2
  const totalH = rows * (cellH + GAP) - GAP + PAD * 2

  return (
    <svg
      viewBox={`0 0 ${totalW} ${totalH}`}
      className="w-full h-auto"
      role="img"
      aria-label="Visualisation du jardin"
    >
      {plots.map((plot, idx) => {
        const col = idx % cols
        const row = Math.floor(idx / cols)
        const x = PAD + col * (PLOT_W + GAP)
        const y = PAD + row * (cellH + GAP)
        const rects = packPlot(plot, PLOT_W, PLOT_H)

        const grouped = new Map<string, { name: string; count: number; area: number }>()
        for (const p of plot.plants) {
          const ex = grouped.get(p.slug)
          if (ex) {
            ex.count += 1
            ex.area += p.area
          } else {
            grouped.set(p.slug, { name: p.name, count: 1, area: p.area })
          }
        }
        const legendItems = Array.from(grouped.entries())

        return (
          <g key={plot.index} transform={`translate(${x},${y})`}>
            <text
              x={0}
              y={12}
              fontSize={12}
              fontFamily="system-ui, sans-serif"
              fontWeight={600}
              fill="#292524"
            >
              Parcelle {plot.index}
            </text>
            <text
              x={PLOT_W}
              y={12}
              fontSize={11}
              fontFamily="system-ui, sans-serif"
              fill="#78716c"
              textAnchor="end"
            >
              {plot.area.toFixed(1)} m² · {plot.utilization.toFixed(0)}%
            </text>

            <rect
              x={0}
              y={HEADER_H}
              width={PLOT_W}
              height={PLOT_H}
              fill="#fafaf9"
              stroke="#a8a29e"
              strokeWidth={1}
              rx={4}
            />

            {rects.map((r, i) =>
              r.data.isEmpty ? (
                <rect
                  key={`empty-${i}`}
                  x={r.x}
                  y={r.y + HEADER_H}
                  width={r.w}
                  height={r.h}
                  fill="url(#emptyHatch)"
                  stroke="#d6d3d1"
                  strokeDasharray="3 2"
                  strokeWidth={1}
                  rx={2}
                >
                  <title>Espace libre — {r.data.area.toFixed(2)} m²</title>
                </rect>
              ) : (
                <g key={`${r.data.slug}-${i}`}>
                  <rect
                    x={r.x + 0.5}
                    y={r.y + HEADER_H + 0.5}
                    width={r.w - 1}
                    height={r.h - 1}
                    fill={colorForSlug(r.data.slug)}
                    fillOpacity={0.85}
                    stroke="#fff"
                    strokeWidth={1.5}
                    rx={2}
                  >
                    <title>{`${r.data.name} — ${r.data.area.toFixed(2)} m²`}</title>
                  </rect>
                  {r.w > 30 && r.h > 16 && (
                    <text
                      x={r.x + r.w / 2}
                      y={r.y + HEADER_H + r.h / 2}
                      fontSize={Math.min(11, Math.max(8, r.h / 4))}
                      fontFamily="system-ui, sans-serif"
                      fill="#fff"
                      fontWeight={600}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      pointerEvents="none"
                      style={{ paintOrder: "stroke", stroke: "rgba(0,0,0,0.25)", strokeWidth: 2 }}
                    >
                      {r.data.name.length > 14 ? r.data.name.slice(0, 13) + "…" : r.data.name}
                    </text>
                  )}
                </g>
              ),
            )}

            <g transform={`translate(0, ${HEADER_H + PLOT_H + 6})`}>
              {legendItems.slice(0, 6).map((entry, i) => {
                const [slug, info] = entry
                const lx = (i % 3) * (PLOT_W / 3)
                const ly = Math.floor(i / 3) * 22
                return (
                  <g key={slug} transform={`translate(${lx},${ly})`}>
                    <rect
                      x={0}
                      y={0}
                      width={10}
                      height={10}
                      fill={colorForSlug(slug)}
                      fillOpacity={0.85}
                      rx={1}
                    />
                    <text
                      x={14}
                      y={9}
                      fontSize={10}
                      fontFamily="system-ui, sans-serif"
                      fill="#44403c"
                    >
                      {info.name.length > 12 ? info.name.slice(0, 11) + "…" : info.name}
                      {info.count > 1 && (
                        <tspan fill="#a8a29e" fontWeight={600}>
                          {" ×"}
                          {info.count}
                        </tspan>
                      )}
                    </text>
                  </g>
                )
              })}
              {legendItems.length > 6 && (
                <text
                  x={0}
                  y={48}
                  fontSize={10}
                  fontFamily="system-ui, sans-serif"
                  fill="#a8a29e"
                >
                  + {legendItems.length - 6} autres
                </text>
              )}
            </g>
          </g>
        )
      })}

      <defs>
        <pattern id="emptyHatch" patternUnits="userSpaceOnUse" width={6} height={6}>
          <rect width={6} height={6} fill="#f5f5f4" />
          <path d="M 0 6 L 6 0" stroke="#e7e5e4" strokeWidth={1} />
        </pattern>
      </defs>
    </svg>
  )
}
