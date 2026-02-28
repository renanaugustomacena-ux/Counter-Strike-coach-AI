"""
Personal Cloud Storage Server

Lightweight FastAPI server for hosting CS2 demos.
Allows remote access from laptop to main PC (Host).

Features:
- Serve .dem files from archive directory
- Basic token authentication
- File listing and metadata
"""

import os
from pathlib import Path
from typing import List

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.responses import FileResponse
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel

from Programma_CS2_RENAN.core.config import get_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.storage_server")

app = FastAPI(title="Macena Personal Cloud Storage")

# Configuration
ARCHIVE_PATH = Path(get_setting("DEMO_ARCHIVE_PATH", "D:/CS2_Demos/Archive"))
API_KEY = get_setting("STORAGE_API_KEY", "")
API_KEY_NAME = "access_token"

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


@app.on_event("startup")
async def startup_event():
    logger.info("Storage Server starting... Serving: %s", ARCHIVE_PATH)
    if not ARCHIVE_PATH.exists():
        ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)


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
    if not str(file_path).startswith(str(ARCHIVE_PATH.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=file_path, filename=filename, media_type="application/octet-stream")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def run_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the storage server."""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
