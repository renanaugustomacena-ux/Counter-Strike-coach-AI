"""JEPA v2 encoder package.

Self-contained implementation of the JEPA v2 architecture.  Never imports
from ``jepa_model.py`` or ``jepa_trainer.py`` (CORREZIONE_NUCLEO_NEURALE
Parte III section 4, D-14).
"""

from Programma_CS2_RENAN.backend.nn.jepa_v2.blocks import (
    CausalSelfAttention,
    FiLM,
    RMSNorm,
    SwiGLU,
    TransformerBlock,
)
from Programma_CS2_RENAN.backend.nn.jepa_v2.config import JepaV2Config
from Programma_CS2_RENAN.backend.nn.jepa_v2.encoder import EncoderV2
from Programma_CS2_RENAN.backend.nn.jepa_v2.losses import jepa_v2_loss
from Programma_CS2_RENAN.backend.nn.jepa_v2.predictor import PredictorV2
from Programma_CS2_RENAN.backend.nn.jepa_v2.projector import ProjectorV2
from Programma_CS2_RENAN.backend.nn.jepa_v2.sigreg import SIGReg, sigreg_batch, sigreg_temporal
from Programma_CS2_RENAN.backend.nn.jepa_v2.tokenizer import TokenizerV2

__all__ = [
    "JepaV2Config",
    "SIGReg",
    "sigreg_batch",
    "sigreg_temporal",
    "RMSNorm",
    "SwiGLU",
    "CausalSelfAttention",
    "TransformerBlock",
    "FiLM",
    "TokenizerV2",
    "EncoderV2",
    "ProjectorV2",
    "PredictorV2",
    "jepa_v2_loss",
]
