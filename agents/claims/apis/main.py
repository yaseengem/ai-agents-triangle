"""
Calvin — Claims Processing FastAPI application entry point.

Run from the repo root:
  uvicorn agents.claims.apis.main:app --host 0.0.0.0 --port 8001 --reload
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
    title="Calvin — ABC Insurance Claims API",
    version="2.0.0",
    description="Calvin: multi-agent claims processing (Strands Agents-as-Tools pattern).",
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
