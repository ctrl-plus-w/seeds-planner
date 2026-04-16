import { useCallback, useRef, useState } from "react"
import type { HvPoint, OptimizeRequest, OptimizeResponse } from "@/api/types"
import { streamOptimize } from "@/api/client"

interface StreamingState {
  status: "idle" | "streaming" | "success" | "error"
  hvCurve: HvPoint[]
  data: OptimizeResponse | null
  error: Error | null
  currentGeneration: number
  totalGenerations: number
}

const INITIAL_STATE: StreamingState = {
  status: "idle",
  hvCurve: [],
  data: null,
  error: null,
  currentGeneration: 0,
  totalGenerations: 0,
}

export function useStreamingOptimize() {
  const [state, setState] = useState<StreamingState>(INITIAL_STATE)
  const abortRef = useRef<(() => void) | null>(null)

  const mutate = useCallback((req: OptimizeRequest) => {
    abortRef.current?.()

    setState({
      status: "streaming",
      hvCurve: [],
      data: null,
      error: null,
      currentGeneration: 0,
      totalGenerations: req.n_gen ?? 400,
    })

    const { promise, abort } = streamOptimize(req, (point) => {
      setState((prev) => ({
        ...prev,
        currentGeneration: point.generation,
        hvCurve: [...prev.hvCurve, point],
      }))
    })

    abortRef.current = abort

    promise
      .then((data) =>
        setState((prev) => ({ ...prev, status: "success", data })),
      )
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return
        setState((prev) => ({ ...prev, status: "error", error: err }))
      })
  }, [])

  const cancel = useCallback(() => {
    abortRef.current?.()
    abortRef.current = null
    setState(INITIAL_STATE)
  }, [])

  return {
    ...state,
    isPending: state.status === "streaming",
    isError: state.status === "error",
    mutate,
    cancel,
  }
}
