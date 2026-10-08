"""FastAPI application entry point for openlink."""

import argparse
import logging
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
    else:
        # Project convention: the backend is always run from backend/, and the
        # user-facing root is the repo root (cwd's parent). Without this
        # normalization, paths like "backend/app/..." would resolve to
        # <backend>/backend/app/... (double-backend).
        _app_config.root_dir = os.path.abspath(os.path.join(os.getcwd(), ".."))
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
    version="1.4.0",
    lifespan=lifespan,
)

# CORS — allow all origins, methods, headers
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
# The `openlink` console script entrypoint was removed from pyproject.toml —
# run() parsed -dir/-port/-timeout but never forwarded them to uvicorn
# (which starts without lifespan), so the args were silently dropped.
# Use the working path: uv run python -m app.main -dir <workspace> -port 39527
# When run() is fixed to wire CLI args through to AppConfig, restore the
# [project.scripts] entry in pyproject.toml and this stub can go.

def _configure_uvicorn_logging():
    """Prepend a timestamp to uvicorn's default access/error log lines."""
    datefmt = "%Y-%m-%d %H:%M:%S"
    default_fmt = "%(asctime)s %(levelname)s: %(message)s"

    class _UvicornAccessFormatter(logging.Formatter):
        _REASONS = {
            200: "OK", 201: "Created", 204: "No Content",
            301: "Moved Permanently", 302: "Found", 304: "Not Modified",
            400: "Bad Request", 401: "Unauthorized", 403: "Forbidden",
            404: "Not Found", 405: "Method Not Allowed", 422: "Unprocessable Entity",
            500: "Internal Server Error", 502: "Bad Gateway", 503: "Service Unavailable",
        }

        def format(self, record: logging.LogRecord) -> str:
            msg = record.getMessage()
            status = record.args[-1] if record.args else None
            reason = self._REASONS.get(status) if isinstance(status, int) else None
            if reason:
                msg = f"{msg} {reason}"
            return f"{self.formatTime(record, datefmt)} {record.levelname}: {msg}"

    for name, fmt in (
        ("uvicorn", default_fmt),
        ("uvicorn.error", default_fmt),
    ):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        logger = logging.getLogger(name)
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False

    access_handler = logging.StreamHandler(sys.stdout)
    access_handler.setFormatter(_UvicornAccessFormatter())
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers = [access_handler]
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False


def run():
    """Entry point kept for `python -m app.main` direct invocation."""
    parser = argparse.ArgumentParser(description="openlink server")
    parser.add_argument("-dir", "--root_dir", default=None, help="working directory")
    parser.add_argument("-port", "--port", type=int, default=39527, help="server port")
    parser.add_argument("-timeout", "--timeout", type=int, default=60, help="command timeout")
    args = parser.parse_args()

    from app.core.logging_setup import setup_file_logging
    _log_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    _log_path = setup_file_logging(_log_root)
    if _log_path:
        print(f"[openlink] logging to {_log_path}", file=sys.__stdout__)

    _configure_uvicorn_logging()

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=args.port,
        reload=False,
        log_config=None,
    )


if __name__ == "__main__":
    run()
