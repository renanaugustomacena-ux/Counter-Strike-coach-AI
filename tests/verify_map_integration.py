import os
import sys
from unittest.mock import MagicMock

import torch

# Path setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Programma_CS2_RENAN.backend.processing.state_reconstructor import RAPStateReconstructor


# Mock PlayerTickState
class MockTick:
    def __init__(self, pos_x=0.0, pos_y=0.0):
        self.health = 100
        self.armor = 100
        self.is_crouching = False
        self.is_scoped = False
        self.equipment_value = 5000
        self.enemies_visible = 0
        self.is_blinded = False
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.pos_z = 0.0
        self.view_x = 0.0
        self.view_y = 0.0
        self.map_name = "de_mirage"


def verify_map_integration():
    print("Verifying Map Fundaments Integration...")

    # 1. Instantiate Reconstructor
    recon = RAPStateReconstructor()
    print(f"Reconstructor metadata_dim: {recon.metadata_dim}")
    if recon.metadata_dim != 18:
        print("FAILED: metadata_dim should be 18")
        return False

    print("Map Tensors Loaded:", list(recon.map_tensors.keys()))
    if "de_mirage" not in recon.map_tensors:
        print("FAILED: de_mirage map tensors not loaded")
        return False

    # 2. Test reconstruction with dummy ticks
    # Test point at A site Mirage (approx -375, -1690)
    # The map_tensors.json says A is [-375.0, -1690.0, -160.0]
    # Distance should be 0 or very small

    tick_at_a = MockTick(-375.0, -1690.0)
    result = recon.reconstruct_belief_tensors([tick_at_a])

    metadata = result["metadata"]
    # Shape should be (1, 1, 18)
    print(f"Metadata tensor shape: {metadata.shape}")
    if metadata.shape[2] != 18:
        print(f"FAILED: Tensor 3rd dim is {metadata.shape[2]}, expected 18")
        return False

    # Check features (indices 12 to 17 are map context)
    # 0-11 are base features.
    # 12: Dist A (should be close to 0)
    # 13: Dist B (should be > 0)

    features = metadata[0, 0]
    dist_a = features[12].item()
    dist_b = features[13].item()

    print(f"Dist A feature: {dist_a}")
    print(f"Dist B feature: {dist_b}")

    if dist_a > 0.1:  # Allow some float wiggle or z-diff (z is 0 in mock, -160 in json)
        # diff in z is 160. 160/4000 = 0.04. So it should be small.
        print(f"WARNING: Dist A seems high ({dist_a}). Z-diff impact?")

    if dist_b < dist_a:
        print("FAILED: Dist B should be > Dist A for this location")
        return False

    print("SUCCESS: Map integration verified.")
    return True


if __name__ == "__main__":
    try:
        if verify_map_integration():
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"CRITICAL FAILIURE: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
