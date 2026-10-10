"""Call Bell Router API.

Runs locally with `uvicorn app.main:app --reload` (from backend/src) and on AWS Lambda through `handler`.
Phase 0 exposes only /health; Phase 1 adds the endpoints in docs/openapi.yaml.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

VERSION = "0.1.0"

app = FastAPI(
    title="Call Bell Router API",
    version=VERSION,
    description="Routes patient call-bell requests to the right department. Synthetic data only.",
)

cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "call-bell-router", "version": VERSION}


handler = Mangum(app, lifespan="off")
