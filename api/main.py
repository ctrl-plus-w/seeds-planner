from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from api.schemas import OptimizeRequest, OptimizeResponse, PlantsResponse
from api.service import NoScrapeRunError, load_plants, run_optimization, run_optimization_stream

app = FastAPI(
    title="Seeds Planner API",
    version="0.1.0",
    description="HTTP API around the seeds-planner optimizer.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/plants", response_model=PlantsResponse)
def get_plants() -> PlantsResponse:
    try:
        return load_plants()
    except NoScrapeRunError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/optimize", response_model=OptimizeResponse)
def post_optimize(req: OptimizeRequest) -> OptimizeResponse:
    try:
        return run_optimization(req)
    except NoScrapeRunError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/optimize/stream")
def post_optimize_stream(req: OptimizeRequest):
    try:
        return StreamingResponse(
            run_optimization_stream(req),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except NoScrapeRunError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def run() -> None:
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    run()
