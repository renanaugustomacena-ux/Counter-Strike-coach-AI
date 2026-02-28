import torch

from Programma_CS2_RENAN.backend.nn.rap_coach.model import RAPCoachModel
from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.test_arch")


def test_rap_forward_pass():
    logger.info("Initializing RAP-Coach Architecture Verification...")

    output_dim = 10
    batch_size = 2
    seq_len = 5

    model = RAPCoachModel(metadata_dim=METADATA_DIM, output_dim=output_dim)

    # Controlled inputs — use 64x64 to match TrainingTensorConfig (F3-38)
    view_frame = torch.randn(batch_size, 3, 64, 64)
    map_frame = torch.randn(batch_size, 3, 64, 64)
    motion_diff = torch.randn(batch_size, 3, 64, 64)
    metadata = torch.randn(batch_size, seq_len, METADATA_DIM)
    skill_vec = torch.zeros(batch_size, 10)
    skill_vec[:, 5] = 1.0  # Tier 5 player

    logger.info("Input Metadata Shape: %s", metadata.shape)

    # Forward Pass (with skill)
    outputs = model(view_frame, map_frame, motion_diff, metadata, skill_vec=skill_vec)

    # Verify Outputs
    assert outputs["advice_probs"].shape == (batch_size, output_dim), "Strategy output mismatch"
    assert outputs["belief_state"].shape == (
        batch_size,
        seq_len,
        64,
    ), "Memory/Belief state mismatch"
    assert outputs["value_estimate"].shape == (batch_size, 1), "Pedagogy/Evaluation mismatch"

    logger.info("[SUCCESS] RAP-Coach Forward Pass Verified.")
    logger.info("Advice Probabilities Sample: %s", outputs["advice_probs"][0][:3])
    logger.info("Belief State (Last Tick): %s", outputs["belief_state"][0, -1, :3])


if __name__ == "__main__":
    test_rap_forward_pass()
