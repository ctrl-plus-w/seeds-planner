import type {
  HvPoint,
  OptimizeRequest,
  OptimizeResponse,
  PlantsResponse,
} from "./types";

const BASE_URL = "http://127.0.0.1:8000";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function fetchPlants(): Promise<PlantsResponse> {
  const res = await fetch(`${BASE_URL}/plants`);
  return handle<PlantsResponse>(res);
}

export async function postOptimize(
  req: OptimizeRequest,
): Promise<OptimizeResponse> {
  const res = await fetch(`${BASE_URL}/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return handle<OptimizeResponse>(res);
}

export function streamOptimize(
  req: OptimizeRequest,
  onProgress: (point: HvPoint) => void,
): { promise: Promise<OptimizeResponse>; abort: () => void } {
  const controller = new AbortController();

  const promise = (async () => {
    const res = await fetch(`${BASE_URL}/optimize/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
      signal: controller.signal,
    });

    if (!res.ok) {
      let detail = `${res.status} ${res.statusText}`;
      try {
        const body = await res.json();
        if (body?.detail) detail = body.detail;
      } catch {
        // ignore
      }
      throw new Error(detail);
    }

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalResult: OptimizeResponse | null = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const blocks = buffer.split("\n\n");
      buffer = blocks.pop()!;

      for (const block of blocks) {
        if (!block.trim()) continue;
        const lines = block.split("\n");
        let eventType = "";
        let data = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) eventType = line.slice(7);
          else if (line.startsWith("data: ")) data = line.slice(6);
        }

        if (eventType === "progress" && data) {
          onProgress(JSON.parse(data) as HvPoint);
        } else if (eventType === "result" && data) {
          finalResult = JSON.parse(data) as OptimizeResponse;
        }
      }
    }

    if (!finalResult) throw new Error("Stream ended without result");
    return finalResult;
  })();

  return { promise, abort: () => controller.abort() };
}
