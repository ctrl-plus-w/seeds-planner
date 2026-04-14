import type {
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
