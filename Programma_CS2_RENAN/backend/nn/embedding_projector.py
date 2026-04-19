"""
Embedding Projector — Layer 4 of the Coach Introspection Observatory.

Captures high-dimensional embeddings at periodic intervals and projects them
for visualization via TensorBoard's Embedding Projector and UMAP images.

Projections reveal:
    Belief Space  — clusters forming = conviction, scattered = doubt
    Concept Space — concepts spreading = differentiation, collapsing = confusion

Usage:
    from Programma_CS2_RENAN.backend.nn.embedding_projector import EmbeddingProjector

    projector = EmbeddingProjector(tb_writer=writer, interval=5)
    # ... pass to CallbackRegistry ...
"""

from typing import List

import torch

from Programma_CS2_RENAN.backend.nn.training_callbacks import TrainingCallback
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.embedding_projector")

# Concept names for TensorBoard metadata
_CONCEPT_NAMES = [
    "pos_aggressive",
    "pos_passive",
    "pos_exposed",
    "util_effective",
    "util_wasteful",
    "econ_efficient",
    "econ_wasteful",
    "engage_favorable",
    "engage_unfavorable",
    "trade_responsive",
    "trade_isolated",
    "rot_fast",
    "info_gathered",
    "momentum_leveraged",
    "clutch_composed",
    "aggression_calibrated",
]

# UMAP availability
try:
    import umap  # type: ignore[import-untyped]

    _UMAP_AVAILABLE = True
except ImportError:
    umap = None  # type: ignore[assignment]
    _UMAP_AVAILABLE = False

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _MPL_AVAILABLE = True
except ImportError:
    matplotlib = None  # type: ignore[assignment]
    plt = None  # type: ignore[assignment]
    _MPL_AVAILABLE = False


class EmbeddingProjector(TrainingCallback):
    """
    Captures and projects high-dimensional embeddings for visualization.

    At every `interval` epochs:
      1. Exports belief vectors to TensorBoard Embedding Projector
      2. Exports concept embeddings with metadata labels
      3. Generates UMAP 2D projection images (if umap-learn installed)
    """

    def __init__(self, tb_writer=None, interval: int = 5):
        self._writer = tb_writer
        self._interval = max(1, interval)
        self._active = tb_writer is not None

        if _UMAP_AVAILABLE:
            logger.info("UMAP available — embedding projections enabled (interval=%d)", interval)
        else:
            logger.warning(
                "umap-learn not installed — UMAP embedding projections disabled. "
                "Install with: pip install umap-learn"
            )

    def on_epoch_end(
        self,
        epoch: int,
        train_loss: float,
        val_loss: float,
        model,
        **kwargs,
    ) -> None:
        if not self._active or epoch % self._interval != 0:
            return

        with torch.no_grad():
            self._project_belief_vectors(model, epoch)
            self._project_concept_embeddings(model, epoch)

    # ── Belief Vector Projection ─────────────────────────────────────

    def _project_belief_vectors(self, model, epoch: int) -> None:
        """Export belief vectors to TensorBoard Embedding Projector + UMAP image."""
        belief = getattr(model, "_last_belief_batch", None)
        if belief is None or not isinstance(belief, torch.Tensor):
            return
        if belief.dim() < 2 or belief.shape[0] < 3:
            return

        belief_cpu = belief.cpu().float()

        # TensorBoard Embedding Projector (interactive 3D PCA/t-SNE)
        self._writer.add_embedding(
            belief_cpu,
            global_step=epoch,
            tag="belief_vectors",
        )

        # UMAP 2D projection image
        if _UMAP_AVAILABLE and _MPL_AVAILABLE and belief_cpu.shape[0] >= 5:
            self._generate_umap_figure(
                belief_cpu.numpy(),
                title=f"Belief Space — Epoch {epoch}",
                tag="embeddings/belief_umap",
                epoch=epoch,
            )

    # ── Concept Embedding Projection ─────────────────────────────────

    def _project_concept_embeddings(self, model, epoch: int) -> None:
        """Export learned concept prototype embeddings with labels."""
        concept_embs = getattr(model, "concept_embeddings", None)
        if concept_embs is None:
            return

        emb_data = concept_embs.weight.data.cpu().float()
        num_concepts = min(emb_data.shape[0], len(_CONCEPT_NAMES))
        labels = _CONCEPT_NAMES[:num_concepts]

        self._writer.add_embedding(
            emb_data[:num_concepts],
            metadata=labels,
            global_step=epoch,
            tag="concept_prototypes",
        )

        # UMAP image for concept embedding space
        if _UMAP_AVAILABLE and _MPL_AVAILABLE and num_concepts >= 5:
            self._generate_concept_umap(
                emb_data[:num_concepts].numpy(),
                labels,
                epoch,
            )

    # ── UMAP Generation ──────────────────────────────────────────────

    def _generate_umap_figure(
        self,
        embeddings,
        title: str,
        tag: str,
        epoch: int,
        labels=None,
    ) -> None:
        """Generate UMAP 2D projection and log as TensorBoard figure."""
        if umap is None or plt is None:
            return
        try:
            n_neighbors = min(15, max(2, embeddings.shape[0] - 1))
            reducer = umap.UMAP(
                n_components=2,
                random_state=42,
                n_neighbors=n_neighbors,
                min_dist=0.1,
            )
            projection = reducer.fit_transform(embeddings)

            fig, ax = plt.subplots(1, 1, figsize=(8, 6))
            scatter = ax.scatter(
                projection[:, 0],
                projection[:, 1],
                c=range(len(projection)),
                cmap="viridis",
                alpha=0.7,
                s=20,
            )
            ax.set_title(title, fontsize=12)
            ax.set_xlabel("UMAP-1")
            ax.set_ylabel("UMAP-2")
            fig.colorbar(scatter, ax=ax, label="Sample index")
            fig.tight_layout()

            self._writer.add_figure(tag, fig, epoch)
            plt.close(fig)
        except Exception as e:
            logger.debug("UMAP projection failed (non-critical): %s", e)

    def _generate_concept_umap(self, embeddings, labels: List[str], epoch: int) -> None:
        """Generate UMAP projection of concept prototypes with labels."""
        if umap is None or plt is None:
            return
        try:
            n_neighbors = min(5, max(2, embeddings.shape[0] - 1))
            reducer = umap.UMAP(
                n_components=2,
                random_state=42,
                n_neighbors=n_neighbors,
                min_dist=0.3,
            )
            projection = reducer.fit_transform(embeddings)

            fig, ax = plt.subplots(1, 1, figsize=(10, 8))
            ax.scatter(projection[:, 0], projection[:, 1], s=80, c="steelblue", alpha=0.8)

            for i, label in enumerate(labels):
                ax.annotate(
                    label,
                    (projection[i, 0], projection[i, 1]),
                    fontsize=8,
                    ha="center",
                    va="bottom",
                )

            ax.set_title(f"Concept Embedding Space — Epoch {epoch}", fontsize=12)
            ax.set_xlabel("UMAP-1")
            ax.set_ylabel("UMAP-2")
            fig.tight_layout()

            self._writer.add_figure("embeddings/concept_umap", fig, epoch)
            plt.close(fig)
        except Exception as e:
            logger.debug("Concept UMAP failed (non-critical): %s", e)
