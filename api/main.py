"""
GHOST API — FastAPI application.

This is the REST backend that powers the GHOST dashboard. It reads
from the same SQLite database that GHOST writes to during agent
monitoring, and exposes session data, trajectory scores, and
aggregate statistics via JSON endpoints.

Start with:
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.schema import init_db
from api.routes.sessions import router as sessions_router
from api.routes.stats import router as stats_router

# ─────────────────────────────────────────────
# Application
# ─────────────────────────────────────────────

logger = logging.getLogger("ghost.api")

app = FastAPI(
    title="GHOST API",
    description="General-purpose Healing & Oversight System for Tasks — REST API",
    version="0.1.0",
)

# CORS — allow the Next.js dashboard to call us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sessions_router)
app.include_router(stats_router)


# ─────────────────────────────────────────────
# Lifecycle Events
# ─────────────────────────────────────────────

@app.on_event("startup")
async def startup() -> None:
    """Initialize the database on startup."""
    init_db()
    logger.info("GHOST API started")
    print("[GHOST API] Server started — database initialized")


@app.on_event("shutdown")
async def shutdown() -> None:
    """Log shutdown."""
    logger.info("GHOST API stopped")
    print("[GHOST API] Server stopped")


# ─────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────

@app.get("/api/health")
async def health() -> dict:
    """Return server health status."""
    return {"status": "ok", "version": "0.1.0"}
