"""FastAPI application entry point — mirrors cmd/server/main.go."""

import argparse
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import AppConfig
from app.core.security.auth import set_server_token
from app.executor.executor import Executor

# Module-level globals for cross-module access (lazy pattern)
_app_config: AppConfig | None = None
_executor: Executor | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    global _app_config, _executor

    # Parse CLI args manually for the standalone case
    parser = argparse.ArgumentParser(description="openlink server")
    parser.add_argument("-dir", "--root_dir", default=None, help="working directory")
    parser.add_argument("-port", "--port", type=int, default=None, help="server port")
    parser.add_argument("-timeout", "--timeout", type=int, default=None, help="command timeout")
    args, _ = parser.parse_known_args()

    _app_config = AppConfig()
    if args.root_dir:
        _app_config.root_dir = args.root_dir
    if args.port:
        _app_config.port = args.port
    if args.timeout:
        _app_config.timeout = args.timeout

    # Set token for auth middleware
    set_server_token(_app_config.token)

    # Initialize executor and register tools
    _executor = Executor(_app_config)
    _executor.register_tools()

    yield

    _app_config = None
    _executor = None


app = FastAPI(
    title="openlink",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — identical to Go: allow all origins, methods, headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Error handler ─────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "error": str(exc)},
    )


# ── Routes ────────────────────────────────────────────────────────────────

from app.api.router import api_router  # noqa: E402
app.include_router(api_router)


# ── Serve Vue 3 frontend as static files (only when built) ──────────────────

_FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
_HAS_FRONTEND = os.path.isdir(_FRONTEND_DIST)

if _HAS_FRONTEND:
    app.mount("/app", StaticFiles(directory=_FRONTEND_DIST, html=True), name="frontend")

    # SPA fallback: Starlette's StaticFiles html=True doesn't catch all SPA routes,
    # so we use middleware to serve index.html for any /app/* 404.
    @app.middleware("http")
    async def spa_fallback(request: Request, call_next):
        response = await call_next(request)
        if response.status_code == 404 and request.url.path.startswith("/app/"):
            # Don't fallback for asset requests (has file extension)
            _, ext = os.path.splitext(request.url.path)
            if not ext or ext in (".html", ".htm"):
                index_path = os.path.join(_FRONTEND_DIST, "index.html")
                if os.path.isfile(index_path):
                    return FileResponse(index_path)
        return response


# ── CLI entry point ───────────────────────────────────────────────────────

def run():
    """Entry point for `openlink` CLI command (pyproject.toml scripts)."""
    parser = argparse.ArgumentParser(description="openlink server")
    parser.add_argument("-dir", "--root_dir", default=None, help="working directory")
    parser.add_argument("-port", "--port", type=int, default=39527, help="server port")
    parser.add_argument("-timeout", "--timeout", type=int, default=60, help="command timeout")
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
