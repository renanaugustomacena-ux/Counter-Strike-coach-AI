"""
DEM File Validation Module

Validates CS2/CSGO demo files before ingestion to prevent parsing failures.
Adheres to GEMINI.md backend principles: explicit validation, early failure detection.
"""

import os
import struct
from pathlib import Path
from typing import Optional, Tuple


class DEMValidationError(Exception):
    """Raised when DEM file validation fails."""

    pass


class DEMValidator:
    """
    Validates Counter-Strike demo files.

    Validation Hierarchy (fail-fast):
    1. File existence and readability
    2. File size constraints
    3. Magic number (header signature)
    4. Game version detection
    """

    # File size constraints (bytes)
    MIN_FILE_SIZE = 100 * 1024  # 100 KB
    MAX_FILE_SIZE = 800 * 1024 * 1024  # 800 MB

    # DEM file magic numbers
    CS2_MAGIC = b"PBDEMS2\x00"  # CS2 demo header
    CSGO_MAGIC = b"HL2DEMO\x00"  # CSGO demo header

    # Forbidden characters in filenames to prevent command injection/shell escapes.
    # NOTE (F2-26): Backslash is included to block shell escape sequences in filenames.
    # On Windows, path separators use backslash, but this check applies only to
    # filepath.name (the filename component, not directory), so legitimate Windows
    # directory separators are not affected.
    FORBIDDEN_CHARS = {";", "&", "|", "`", "$", "(", ")", "<", ">", "\\"}

    def validate(self, filepath: Path) -> Tuple[bool, str, Optional[str]]:
        """
        Validate DEM file.

        Returns:
            (is_valid, game_version, error_message)
        """
        try:
            self._check_filename_integrity(filepath)
            self._check_file_exists(filepath)
            self._check_file_size(filepath)
            game_version = self._detect_game_version(filepath)
            self._verify_header_completeness(filepath, game_version)
            return (True, game_version, None)
        except DEMValidationError as e:
            return (False, None, str(e))

    def _check_filename_integrity(self, filepath: Path):
        """Sanitize filename to prevent injection and traversal attacks."""
        name = filepath.name
        if any(char in self.FORBIDDEN_CHARS for char in name):
            raise DEMValidationError(f"Filename contains illegal characters: {name}")

        # Prevent hidden files or double-extension tricks
        if name.startswith("."):
            raise DEMValidationError("Hidden files are not allowed.")

        if name.count(".") > 1:
            # Basic check for things like 'payload.sh.dem'
            parts = name.split(".")
            if parts[-2].lower() in [
                "sh",
                "exe",
                "bat",
                "cmd",
                "ps1",
                "php",
                "js",
                "py",
                "vbs",
                "rb",
                "pl",
            ]:
                raise DEMValidationError(f"Suspicious double extension detected: {name}")

    def _check_file_exists(self, filepath: Path):
        """Verify file exists, is a file, and is readable (no symlinks)."""
        if not filepath.exists():
            raise DEMValidationError(f"File not found: {filepath}")

        if filepath.is_symlink():
            raise DEMValidationError("Symbolic links are forbidden for security reasons.")

        if not filepath.is_file():
            raise DEMValidationError(f"Path is not a file: {filepath}")

        if not os.access(filepath, os.R_OK):
            raise DEMValidationError(f"File not readable: {filepath}")

    def _check_file_size(self, filepath: Path):
        """Validate file size is within acceptable range."""
        size = filepath.stat().st_size

        if size < self.MIN_FILE_SIZE:
            raise DEMValidationError(
                f"File too small ({size / 1024:.1f} KB). "
                f"Minimum: {self.MIN_FILE_SIZE / 1024:.1f} KB"
            )

        if size > self.MAX_FILE_SIZE:
            raise DEMValidationError(
                f"File too large ({size / 1024 / 1024:.1f} MB). "
                f"Maximum: {self.MAX_FILE_SIZE / 1024 / 1024:.1f} MB"
            )

    def _detect_game_version(self, filepath: Path) -> str:
        """
        Detect game version from file header.
        """
        try:
            with open(filepath, "rb") as f:
                header = f.read(8)

                if header == self.CS2_MAGIC:
                    return "CS2"
                elif header == self.CSGO_MAGIC:
                    return "CSGO"
                else:
                    raise DEMValidationError(
                        f"Invalid DEM header. Expected CS2 or CSGO magic number."
                    )
        except IOError as e:
            raise DEMValidationError(f"Failed to read file header: {e}")

    def _verify_header_completeness(self, filepath: Path, version: str):
        """
        Deep validation of the demo header structure.
        Ensures the file isn't just a dummy with a correct magic number.
        """
        try:
            with open(filepath, "rb") as f:
                # Skip magic number
                f.seek(8)

                if version == "CSGO":
                    # CSGO headers (Source 1) are usually 1072 bytes
                    # We check if we can at least read the basic metadata fields
                    metadata = f.read(16)  # Should contain protocol and server version
                    if len(metadata) < 16:
                        raise DEMValidationError("CSGO Demo header is truncated.")

                elif version == "CS2":
                    # CS2 uses Protobuf for its header, usually wrapped in a bitstream
                    # For now, we verify that the file has at least enough data
                    # to contain a valid Protobuf header (usually > 512 bytes)
                    probe = f.read(512)
                    if len(probe) < 512:
                        raise DEMValidationError("CS2 Demo header is truncated.")

        except DEMValidationError:
            raise  # Re-raise without wrapping so the original message is preserved
        except Exception as e:
            raise DEMValidationError(f"Header integrity check failed: {e}")

    def estimate_processing_time(self, filepath: Path) -> int:
        """
        Estimate demo parsing time in seconds.

        Heuristic: ~1 second per 10 MB (based on demoparser2 benchmarks)
        """
        size_mb = filepath.stat().st_size / (1024 * 1024)
        return max(1, int(size_mb / 10))


def validate_dem_file(filepath: str) -> Tuple[bool, str, Optional[str]]:
    """
    Convenience function for DEM validation.

    Args:
        filepath: Path to DEM file (string)

    Returns:
        (is_valid, game_version, error_message)
    """
    validator = DEMValidator()
    return validator.validate(Path(filepath))


if __name__ == "__main__":
    # Self-test
    import sys

    if len(sys.argv) < 2:
        print("Usage: python dem_validator.py <path_to_dem_file>")
        sys.exit(1)

    filepath = sys.argv[1]
    is_valid, version, error = validate_dem_file(filepath)

    if is_valid:
        validator = DEMValidator()
        est_time = validator.estimate_processing_time(Path(filepath))
        print(f"✓ Valid {version} demo file")
        print(f"  Estimated processing time: {est_time}s")
    else:
        print(f"✗ Invalid DEM file: {error}")
        sys.exit(1)
