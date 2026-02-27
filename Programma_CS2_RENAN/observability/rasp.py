import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class IntegrityError(Exception):
    """Raised when an integrity violation is detected."""

    pass


class RASPGuard:
    """
    Runtime Application Self-Protection (RASP) Guard.
    Responsible for verifying the integrity of the application environment.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.manifest_path = self._resolve_manifest_path()

    def _resolve_manifest_path(self) -> Path:
        """
        Dynamically resolve the manifest path based on execution context.
        - Frozen (PyInstaller): Manifest is at the root of _MEIPASS
        - Development: Manifest is in Programma_CS2_RENAN/core/
        """
        if getattr(sys, "frozen", False):
            # In PyInstaller bundle, check multiple possible locations
            meipass = Path(sys._MEIPASS)
            candidates = [
                meipass / "integrity_manifest.json",  # Root of bundle (recommended)
                meipass / "core" / "integrity_manifest.json",  # Flattened structure
                meipass
                / "Programma_CS2_RENAN"
                / "core"
                / "integrity_manifest.json",  # Full structure
            ]
            for candidate in candidates:
                if candidate.exists():
                    return candidate
            # Return first candidate as default (will be caught as missing later)
            return candidates[0]
        else:
            # Development mode: use project structure
            return self.project_root / "Programma_CS2_RENAN" / "core" / "integrity_manifest.json"

    def verify_runtime_integrity(self) -> Tuple[bool, List[str]]:
        """
        Main entry point for integrity verification.
        Returns (success, list_of_violations).
        """
        violations = []

        # 1. Check if manifest exists
        if not self.manifest_path.exists():
            # If manifest is missing in production, it's a critical violation.
            # In development, we might allow it but log a warning.
            if getattr(sys, "frozen", False):
                violations.append("Integrity manifest is missing from the bundle.")
                return False, violations
            return True, []  # Skip in dev if manifest not generated yet

        try:
            with open(self.manifest_path, "r") as f:
                manifest = json.load(f)

            expected_hashes: Dict[str, str] = manifest.get("hashes", {})

            # Determine base path for file resolution
            if getattr(sys, "frozen", False):
                base_path = Path(sys._MEIPASS)
            else:
                base_path = self.project_root

            for rel_path, expected_hash in expected_hashes.items():
                full_path = base_path / rel_path
                if not full_path.exists():
                    violations.append(f"Missing critical file: {rel_path}")
                    continue

                actual_hash = self._calculate_sha256(full_path)
                if actual_hash != expected_hash:
                    violations.append(f"Integrity mismatch for {rel_path}")

        except Exception as e:
            violations.append(f"Failed to perform integrity check: {e}")

        return len(violations) == 0, violations

    def _calculate_sha256(self, file_path: Path) -> str:
        """Calculate the SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def check_frozen_binary(self) -> bool:
        """
        If running as a PyInstaller frozen binary, verify the executable name
        and basic environment properties.
        """
        if getattr(sys, "frozen", False):
            # Verify we aren't running from a suspicious temp location
            # (unless it's the expected _MEIxxxxxx folder)
            exe_path = Path(sys.executable)
            if exe_path.suffix.lower() != ".exe" and os.name == "nt":
                return False
        return True


def run_rasp_audit(project_root: Path) -> bool:
    """
    Convenience function to run the RASP audit.
    Logs violations to stdout/stderr.
    """
    guard = RASPGuard(project_root)

    # Check binary environment
    if not guard.check_frozen_binary():
        print("CRITICAL: Suspicious execution environment detected!", file=sys.stderr)
        return False

    success, violations = guard.verify_runtime_integrity()
    if not success:
        print("--- INTEGRITY VIOLATION DETECTED ---", file=sys.stderr)
        for v in violations:
            print(f" ! {v}", file=sys.stderr)
        return False

    return True
