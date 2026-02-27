import os
import sys

# --- Path Stabilization ---
script_dir = os.path.dirname(os.path.abspath(__file__))
# script is in tests/forensics
# root is up 2 levels
root = os.path.dirname(os.path.dirname(script_dir))
if root not in sys.path:
    sys.path.insert(0, root)

from Programma_CS2_RENAN.core.spatial_data import SPATIAL_REGISTRY, get_map_metadata


def test_spatial_integrity():
    print("--- Testing Spatial Engine Integrity ---")

    # 1. Registry Check
    print(f"Maps Registered: {len(SPATIAL_REGISTRY)}")
    assert "de_mirage" in SPATIAL_REGISTRY, "Mirage missing!"

    # 2. Logic Check: Mirage T-Spawn
    # Approx T-Spawn: X=1296, Y=-360
    # Mirage Meta: X=-3230, Y=1713, Scale=5.0

    # Manual Calc:
    # pixel_x = (1296 - (-3230)) / 5.0 = 4526 / 5 = 905.2
    # pixel_y = (1713 - (-360)) / 5.0 = 2073 / 5 = 414.6
    # norm_x = 905.2 / 1024 = 0.88
    # norm_y = 414.6 / 1024 = 0.40

    mirage = get_map_metadata("de_mirage")
    nx, ny = mirage.world_to_radar(1296, -360)

    print(f"Mirage T-Spawn (1296, -360) -> Norm({nx:.4f}, {ny:.4f})")

    assert 0.88 <= nx <= 0.89, f"X projection failed: {nx}"
    assert 0.40 <= ny <= 0.41, f"Y projection failed: {ny}"

    print("SUCCESS: Spatial Engine logic is sound.")


if __name__ == "__main__":
    try:
        test_spatial_integrity()
    except Exception as e:
        print(f"FAILURE: {e}")
        sys.exit(1)
