import { useEffect, useRef } from "react"
import Plotly from "plotly.js-basic-dist-min"
import type { HvPoint } from "@/api/types"

interface HypervolumePlotProps {
  hvCurve: HvPoint[]
  totalGenerations: number
  isStreaming: boolean
}

export function HypervolumePlot({
  hvCurve,
  totalGenerations,
  isStreaming,
}: HypervolumePlotProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const traces: Plotly.Data[] = [
      {
        type: "scatter",
        mode: "lines",
        x: hvCurve.map((p) => p.generation),
        y: hvCurve.map((p) => p.hypervolume),
        line: { color: "#16a34a", width: 2 },
        hovertemplate:
          "Gen %{x}<br>HV: %{y:.4f}<extra></extra>",
      },
    ]

    const layout: Partial<Plotly.Layout> = {
      xaxis: {
        title: { text: "Generation" },
        range: [0, totalGenerations],
      },
      yaxis: {
        title: { text: "Hypervolume" },
      },
      margin: { l: 60, r: 20, t: 20, b: 50 },
      showlegend: false,
      height: 300,
    }

    Plotly.react(el, traces, layout, { responsive: true, displayModeBar: false })
  }, [hvCurve, totalGenerations, isStreaming])

  useEffect(() => {
    return () => {
      const el = containerRef.current
      if (el) Plotly.purge(el)
    }
  }, [])

  return <div ref={containerRef} style={{ width: "100%" }} />
}
