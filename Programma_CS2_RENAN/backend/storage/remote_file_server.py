"""
Personal Cloud Storage Server

Lightweight FastAPI server for hosting CS2 demos.
Allows remote access from laptop to main PC (Host).

Features:
- Serve .dem files from archive directory
- Basic token authentication
- File listing and metadata
- P7-03: Per-IP rate limiting (10 req/min) to prevent brute-force API key guessing
"""

import os
import time
import threading
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.responses import FileResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from Programma_CS2_RENAN.core.config import get_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.storage_server")


# ---------------------------------------------------------------------------
# P7-03: Lightweight in-process rate limiter (no external dependencies)
# ---------------------------------------------------------------------------
RATE_LIMIT_MAX_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60


class _RateLimiter:
    """Thread-safe sliding-window rate limiter keyed by client IP."""

    def __init__(self, max_requests: int, window_seconds: int):
        self._max = max_requests
        self._window = window_seconds
        self._hits: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> Tuple[bool, int]:
        """Return (allowed, remaining) for the given key."""
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            timestamps = self._hits[key]
            # Prune expired entries
            self._hits[key] = [t for t in timestamps if t > cutoff]
            timestamps = self._hits[key]
            if len(timestamps) >= self._max:
                return False, 0
            timestamps.append(now)
            return True, self._max - len(timestamps)


_rate_limiter = _RateLimiter(RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that enforces per-IP rate limits on all endpoints
    except /health (used for monitoring)."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        allowed, remaining = _rate_limiter.is_allowed(client_ip)
        if not allowed:
            logger.warning("Rate limit exceeded for %s on %s", client_ip, request.url.path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


# Configuration
ARCHIVE_PATH = Path(get_setting("DEMO_ARCHIVE_PATH", "D:/CS2_Demos/Archive"))
API_KEY = get_setting("STORAGE_API_KEY", "")
API_KEY_NAME = "access_token"


@asynccontextmanager
async def _lifespan(_application: FastAPI):
    """Modern lifespan handler (replaces deprecated @app.on_event)."""
    logger.info("Storage Server starting... Serving: %s", ARCHIVE_PATH)
    if not API_KEY:
        logger.warning(
            "STORAGE_API_KEY is empty — all authenticated endpoints will return 503. "
            "Set STORAGE_API_KEY in settings to enable file operations."
        )
    if not ARCHIVE_PATH.exists():
        ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Macena Personal Cloud Storage", lifespan=_lifespan)
app.add_middleware(RateLimitMiddleware)

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    if not API_KEY:
        raise HTTPException(status_code=503, detail="Server API key not configured")
    if not api_key_header:
        raise HTTPException(status_code=403, detail="Missing API key")
    import hmac

    if hmac.compare_digest(api_key_header, API_KEY):
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")


class FileInfo(BaseModel):
    filename: str
    size_bytes: int
    modified_at: float


@app.get("/list", response_model=List[FileInfo])
async def list_files(api_key: str = Depends(get_api_key)):
    """List all available demos in archive."""
    files = []
    try:
        for entry in os.scandir(ARCHIVE_PATH):
            if entry.is_file() and entry.name.endswith(".dem"):
                files.append(
                    FileInfo(
                        filename=entry.name,
                        size_bytes=entry.stat().st_size,
                        modified_at=entry.stat().st_mtime,
                    )
                )
    except Exception as e:
        logger.error("Error listing files: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
    return files


@app.get("/download/{filename}")
async def download_file(filename: str, api_key: str = Depends(get_api_key)):
    """Download specific demo file."""
    file_path = (ARCHIVE_PATH / filename).resolve()
    # P2-04: Use is_relative_to instead of startswith to prevent prefix bypass
    # (e.g. /data vs /data2). Available in Python 3.9+.
    if not file_path.is_relative_to(ARCHIVE_PATH.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=file_path, filename=filename, media_type="application/octet-stream")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    ssl_keyfile: Optional[str] = None,
    ssl_certfile: Optional[str] = None,
):
    """Run the storage server.

    For TLS-encrypted traffic (recommended when not on localhost):
        run_server(ssl_keyfile="/path/to/key.pem", ssl_certfile="/path/to/cert.pem")

    Generate a self-signed certificate for testing:
        openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
    """
    if ssl_keyfile and ssl_certfile:
        logger.info("TLS enabled: cert=%s key=%s", ssl_certfile, ssl_keyfile)
    elif host != "127.0.0.1":
        logger.warning(
            "Running without TLS on non-localhost address %s:%d — "
            "API key will be transmitted in plaintext. Use ssl_keyfile/ssl_certfile "
            "for encrypted traffic.",
            host,
            port,
        )
    uvicorn.run(
        app,
        host=host,
        port=port,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Macena Personal Cloud Storage Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--ssl-keyfile", default=None, help="Path to TLS private key (.pem)")
    parser.add_argument("--ssl-certfile", default=None, help="Path to TLS certificate (.pem)")
    args = parser.parse_args()
    run_server(
        host=args.host,
        port=args.port,
        ssl_keyfile=args.ssl_keyfile,
        ssl_certfile=args.ssl_certfile,
    )
