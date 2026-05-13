"""FastAPI app entrypoint."""

from __future__ import annotations

from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import accounts, auth, plaid, transactions

structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)
log = structlog.get_logger()

app = FastAPI(
    title="SecureLedger API",
    version="0.1.0",
    description="Security-first financial aggregator.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict[str, str]:
    return {"status": "ok", "env": settings.APP_ENV}


app.include_router(auth.router)
app.include_router(plaid.router)
app.include_router(accounts.router)
app.include_router(transactions.router)


# In production, the multi-stage Dockerfile copies the frontend build to
# /app/static. When that directory exists, mount it and add an SPA fallback
# so deep-link routes like /signup or /login serve index.html (React Router
# handles them client-side). The dev environment doesn't have this folder,
# so the API stays a pure JSON service when running locally.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if STATIC_DIR.exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        # API and meta routes are matched by routers above; if we land here
        # with /api/* or /healthz, it's a real 404, not an SPA route.
        if full_path.startswith("api/") or full_path == "healthz":
            raise HTTPException(status_code=404, detail="Not found")

        # Serve static assets directly when present (favicon, vite.svg, etc.)
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)

        # Otherwise: SPA route, hand back index.html
        index = STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Not found")
