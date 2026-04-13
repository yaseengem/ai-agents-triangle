"""
Claims Processing FastAPI application entry point.

Run from the agents/claims/apis/ directory:
  uvicorn main:app --host 0.0.0.0 --port 8001

IMPORTANT: Do NOT use --workers > 1.  The human-in-the-loop approval flow
relies on asyncio.Event objects stored in process memory; multiple workers
would each have isolated registries and POST /approve would miss the waiting
workflow coroutine.
"""

from __future__ import annotations

import os
import sys

# Ensure repo root is on the path before any local imports
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from utils.logger import setup_logging
from .routes import router

setup_logging()

app = FastAPI(
    title="Neural Claims API",
    version="1.0.0",
    description="Claims Processing agent — part of the Neural multi-agent platform.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("CLAIMS_API_PORT", "8001"))
    uvicorn.run("agents.claims.apis.main:app", host="0.0.0.0", port=port, reload=True)
