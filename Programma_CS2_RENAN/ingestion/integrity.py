import hashlib
import os

from Programma_CS2_RENAN.backend.data_sources.demo_format_adapter import (
    DEMO_MAGIC_LEGACY,
    DEMO_MAGIC_V2,
    MAX_DEMO_SIZE,
    MIN_DEMO_SIZE,
)
from Programma_CS2_RENAN.backend.data_sources.demo_format_adapter import (
    validate_demo_file as _adapter_validate,
)

# Legacy constants kept for backward compatibility but no longer used for validation
MIN_SIZE = 50_000  # 50 KB (sanity floor)
MAX_SIZE = 900_000_000  # 900 MB (safety ceiling)


def compute_sha256(path: str) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def validate_dem_file(path: str) -> bool:
    """
    Validate CS2 demo file integrity via DemoFormatAdapter.

    Args:
        path: Path to .dem file

    Returns:
        True if file passes all validation checks

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file fails validation (size, header, or unsupported format)
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Demo file does not exist: {path}")

    result = _adapter_validate(path)

    if not result["valid"]:
        error_msg = result.get("error", "Unknown validation failure")
        # Distinguish between unsupported format and other errors
        if result["version"] == "csgo_legacy":
            raise ValueError(f"Unsupported legacy CS:GO demo format: {path}")
        raise ValueError(f"{error_msg}: {path}")

    return True
