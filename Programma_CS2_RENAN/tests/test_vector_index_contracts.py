"""Contract tests for vector_index loaders (R4 MED batch 10).

FAISS-independent: _stack_uniform is a staticmethod and the module imports
faiss inside try/except, so these run everywhere.
"""

import numpy as np

from Programma_CS2_RENAN.backend.knowledge.vector_index import VectorIndexManager


class TestStackUniform:
    """R4 MED: ragged embeddings (100-dim hash fallback vs 384-dim SBERT)
    made np.stack raise ValueError through the whole retrieval path."""

    def test_uniform_dims_pass_through(self):
        ids, vecs = VectorIndexManager._stack_uniform(
            "knowledge",
            [1, 2, 3],
            [np.ones(4, dtype=np.float32) * i for i in range(3)],
        )
        assert ids.tolist() == [1, 2, 3]
        assert vecs.shape == (3, 4)

    def test_non_modal_dims_dropped_loudly(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            ids, vecs = VectorIndexManager._stack_uniform(
                "experience",
                [10, 11, 12, 13],
                [
                    np.ones(384, dtype=np.float32),
                    np.ones(100, dtype=np.float32),  # hash-fallback row
                    np.ones(384, dtype=np.float32),
                    np.ones(384, dtype=np.float32),
                ],
            )
        assert ids.tolist() == [10, 12, 13], "the 100-dim row must be dropped"
        assert vecs.shape == (3, 384)
        assert any("non-modal dimension" in r.message for r in caplog.records)
        assert any("11" in r.message for r in caplog.records), "skipped id must be named"

    def test_empty_input(self):
        ids, vecs = VectorIndexManager._stack_uniform("knowledge", [], [])
        assert ids.size == 0
        assert vecs.shape == (0, 0)
