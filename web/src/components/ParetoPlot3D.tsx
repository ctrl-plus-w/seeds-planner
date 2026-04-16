import { useEffect, useRef } from "react"
import Plotly from "plotly.js-gl3d-dist-min"
import type { SolutionResult } from "@/api/types"

interface ParetoPlot3DProps {
  solutions: SolutionResult[]
  selectedRank: number
  onSelect: (rank: number) => void
}

export function ParetoPlot3D({ solutions, selectedRank, onSelect }: ParetoPlot3DProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const selected = solutions.filter((s) => s.rank === selectedRank)
    const others = solutions.filter((s) => s.rank !== selectedRank)

    const traces: Plotly.Data[] = [
      {
        type: "scatter3d",
        mode: "markers",
        name: "",
        x: others.map((s) => s.compatibility),
        y: others.map((s) => s.space_utilization),
        z: others.map((s) => s.assigned_pct),
        text: others.map((s) => `#${s.rank}`),
        marker: { size: 3, color: "#0ea5e9", opacity: 0.75 },
        hovertemplate:
          "#%{text}<br>Compat: %{x:.2f}<br>Espace: %{y:.0f}%<br>Placées: %{z:.0f}%<extra></extra>",
        customdata: others.map((s) => s.rank),
      },
      {
        type: "scatter3d",
        mode: "markers",
        name: "",
        x: selected.map((s) => s.compatibility),
        y: selected.map((s) => s.space_utilization),
        z: selected.map((s) => s.assigned_pct),
        text: selected.map((s) => `#${s.rank}`),
        marker: { size: 6, color: "#16a34a", opacity: 1 },
        hovertemplate:
          "#%{text}<br>Compat: %{x:.2f}<br>Espace: %{y:.0f}%<br>Placées: %{z:.0f}%<extra></extra>",
        customdata: selected.map((s) => s.rank),
      },
    ]

    const layout: Partial<Plotly.Layout> = {
      scene: {
        xaxis: { title: { text: "Compatibilité" } },
        yaxis: { title: { text: "Espace utilisé (%)" } },
        zaxis: { title: { text: "Plantes placées (%)" } },
      },
      margin: { l: 0, r: 0, t: 0, b: 0 },
      showlegend: false,
      height: 400,
    }

    Plotly.react(el, traces, layout, { responsive: true, displayModeBar: false })

    const plotEl = el as unknown as Plotly.PlotlyHTMLElement
    const handleClick = (data: Plotly.PlotMouseEvent) => {
      const point = data.points?.[0]
      if (point?.customdata) onSelect(point.customdata as number)
    }
    plotEl.on("plotly_click", handleClick)

    return () => {
      plotEl.removeAllListeners?.("plotly_click")
    }
  }, [solutions, selectedRank, onSelect])

  useEffect(() => {
    return () => {
      const el = containerRef.current
      if (el) Plotly.purge(el)
    }
  }, [])

  return <div ref={containerRef} style={{ width: "100%" }} />
}
