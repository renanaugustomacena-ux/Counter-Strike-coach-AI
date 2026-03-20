"""
FAISS Vector Index Manager for RAG Knowledge System (AC-36-02).

Replaces brute-force O(n) cosine similarity with FAISS IndexFlatIP
for sub-linear approximate nearest neighbor search. Maintains dual
indexes for TacticalKnowledge and CoachingExperience tables.

Design:
    - IndexFlatIP on L2-normalized vectors gives cosine similarity
    - Lazy rebuild: mark_dirty() sets flag, rebuild before next search
    - Thread-safe: read-concurrent, write-exclusive via Lock
    - Graceful fallback: returns None if faiss not installed
    - Persists indexes to disk for fast startup
"""

import base64
import json
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlmodel import select

from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.vector_index")


def _deserialize_embedding(raw: str) -> np.ndarray:
    """Deserialize embedding from base64 (current) or legacy JSON format."""
    if raw.startswith("["):
        return np.array(json.loads(raw), dtype=np.float32)
    return np.frombuffer(base64.b64decode(raw), dtype=np.float32)


try:
    import faiss

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.info("faiss not installed — vector search will use brute-force fallback")

# Over-fetch multipliers for post-filter scenarios
OVERFETCH_KNOWLEDGE = 10  # category + map_name filters
OVERFETCH_EXPERIENCE = 20  # map + confidence + outcome + composite scoring


def _default_index_dir() -> Path:
    """Resolve index storage directory from config."""
    try:
        from Programma_CS2_RENAN.core.config import STORAGE_ROOT

        return Path(STORAGE_ROOT) / "indexes"
    except Exception:
        return Path(os.path.expanduser("~")) / ".cs2analyzer" / "indexes"


class VectorIndexManager:
    """FAISS-backed vector index for TacticalKnowledge and CoachingExperience.

    Maintains two named indexes ('knowledge', 'experience'), each mapping
    FAISS row positions to database primary keys. Indexes are persisted to
    disk and rebuilt lazily when marked dirty.
    """

    def __init__(self, persist_dir: Optional[Path] = None):
        if not FAISS_AVAILABLE:
            raise ImportError("faiss-cpu is required for VectorIndexManager")

        self._persist_dir = persist_dir or _default_index_dir()
        self._persist_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._indexes: Dict[str, "faiss.Index"] = {}
        self._id_maps: Dict[str, np.ndarray] = {}
        self._dirty: Dict[str, bool] = {"knowledge": False, "experience": False}

        # Load persisted indexes (or leave empty for lazy build)
        self._load_persisted()

    # ── Public API ──────────────────────────────────────────────────────

    def search(
        self, index_name: str, query_vec: np.ndarray, k: int
    ) -> Optional[List[Tuple[int, float]]]:
        """Search index for top-k nearest neighbors.

        Args:
            index_name: 'knowledge' or 'experience'
            query_vec: Query embedding (1-D array, any norm)
            k: Number of results

        Returns:
            List of (db_id, similarity_score), or None if index unavailable.
        """
        # Lazy rebuild if dirty
        if self._dirty.get(index_name, False):
            self.rebuild_from_db(index_name)

        idx = self._indexes.get(index_name)
        id_map = self._id_maps.get(index_name)
        if idx is None or id_map is None or idx.ntotal == 0:
            return None

        # Normalize query for cosine similarity via inner product
        qvec = query_vec.astype(np.float32).reshape(1, -1).copy()
        norm = np.linalg.norm(qvec)
        if norm == 0:
            logger.warning("Zero-norm query vector — no semantic content to search")
            return None
        qvec /= norm

        # Clamp k to index size
        actual_k = min(k, idx.ntotal)

        # FAISS search (thread-safe for IndexFlat reads)
        distances, indices = idx.search(qvec, actual_k)

        results = []
        for i in range(actual_k):
            faiss_idx = indices[0, i]
            if faiss_idx < 0:
                continue  # FAISS returns -1 for empty slots
            db_id = int(id_map[faiss_idx])
            score = float(distances[0, i])
            results.append((db_id, score))

        return results

    def rebuild_from_db(self, index_name: str) -> int:
        """Rebuild index from database. Thread-safe.

        Args:
            index_name: 'knowledge' or 'experience'

        Returns:
            Number of vectors indexed.
        """
        if index_name == "knowledge":
            ids, embeddings = self._load_knowledge_vectors()
        elif index_name == "experience":
            ids, embeddings = self._load_experience_vectors()
        else:
            raise ValueError(f"Unknown index: {index_name}")

        if len(ids) == 0:
            logger.info("No vectors found for '%s' index — skipping build", index_name)
            with self._lock:
                self._dirty[index_name] = False
            return 0

        self._build_index(index_name, ids, embeddings)
        logger.info(
            "Built '%s' index: %d vectors (%d-dim)", index_name, len(ids), embeddings.shape[1]
        )
        return len(ids)

    def mark_dirty(self, index_name: str) -> None:
        """Flag index for lazy rebuild on next search."""
        self._dirty[index_name] = True

    def index_size(self, index_name: str) -> int:
        """Return number of vectors in the named index."""
        idx = self._indexes.get(index_name)
        return idx.ntotal if idx is not None else 0

    # ── Internal: Index Build ───────────────────────────────────────────

    def _build_index(self, index_name: str, ids: np.ndarray, embeddings: np.ndarray) -> None:
        """Build FAISS IndexFlatIP from vectors and persist."""
        dim = embeddings.shape[1]

        # L2-normalize so inner product = cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-8)
        normalized = (embeddings / norms).astype(np.float32)

        idx = faiss.IndexFlatIP(dim)
        idx.add(normalized)

        with self._lock:
            self._indexes[index_name] = idx
            self._id_maps[index_name] = ids
            self._dirty[index_name] = False

        # Persist to disk
        self._save(index_name)

    def _save(self, index_name: str) -> None:
        """Persist index + ID map to disk."""
        idx = self._indexes.get(index_name)
        id_map = self._id_maps.get(index_name)
        if idx is None or id_map is None:
            return

        try:
            idx_path = self._persist_dir / f"{index_name}.faiss"
            ids_path = self._persist_dir / f"{index_name}_ids.npy"
            faiss.write_index(idx, str(idx_path))
            np.save(str(ids_path), id_map)
            logger.debug("Persisted '%s' index to %s", index_name, idx_path)
        except Exception as e:
            logger.warning("Failed to persist '%s' index: %s", index_name, e)

    def _load_persisted(self) -> None:
        """Load persisted indexes from disk."""
        for name in ("knowledge", "experience"):
            idx_path = self._persist_dir / f"{name}.faiss"
            ids_path = self._persist_dir / f"{name}_ids.npy"

            if idx_path.exists() and ids_path.exists():
                try:
                    idx = faiss.read_index(str(idx_path))
                    id_map = np.load(str(ids_path))
                    self._indexes[name] = idx
                    self._id_maps[name] = id_map
                    logger.info("Loaded '%s' index from disk: %d vectors", name, idx.ntotal)
                except Exception as e:
                    logger.warning("Failed to load '%s' index: %s", name, e)

    # ── Internal: DB Extraction ─────────────────────────────────────────

    def _load_knowledge_vectors(self) -> Tuple[np.ndarray, np.ndarray]:
        """Extract (ids, embeddings) from TacticalKnowledge table."""
        from Programma_CS2_RENAN.backend.storage.db_models import TacticalKnowledge

        db = get_db_manager()
        ids_list = []
        vecs_list = []

        with db.get_session() as session:
            entries = session.exec(select(TacticalKnowledge)).all()
            for entry in entries:
                if not entry.embedding or entry.id is None:
                    continue
                try:
                    vec = np.array(json.loads(entry.embedding), dtype=np.float32)
                    ids_list.append(entry.id)
                    vecs_list.append(vec)
                except (json.JSONDecodeError, ValueError):
                    logger.warning("Skipped knowledge entry %s: bad embedding", entry.id)

        if not ids_list:
            return np.array([], dtype=np.int64), np.empty((0, 0), dtype=np.float32)

        return np.array(ids_list, dtype=np.int64), np.stack(vecs_list)

    def _load_experience_vectors(self) -> Tuple[np.ndarray, np.ndarray]:
        """Extract (ids, embeddings) from CoachingExperience table."""
        from Programma_CS2_RENAN.backend.storage.db_models import CoachingExperience

        db = get_db_manager()
        ids_list = []
        vecs_list = []

        # Batch load to prevent OOM on large tables
        BATCH_SIZE = 5000
        offset = 0

        with db.get_session() as session:
            while True:
                entries = session.exec(
                    select(CoachingExperience)
                    .where(CoachingExperience.embedding.isnot(None))
                    .offset(offset)
                    .limit(BATCH_SIZE)
                ).all()

                if not entries:
                    break

                for entry in entries:
                    if entry.id is None:
                        continue
                    try:
                        vec = _deserialize_embedding(entry.embedding)
                        ids_list.append(entry.id)
                        vecs_list.append(vec)
                    except Exception:
                        pass

                offset += BATCH_SIZE

        if not ids_list:
            return np.array([], dtype=np.int64), np.empty((0, 0), dtype=np.float32)

        return np.array(ids_list, dtype=np.int64), np.stack(vecs_list)


# ── Singleton ───────────────────────────────────────────────────────────

_index_manager_instance: Optional[VectorIndexManager] = None
_index_manager_lock = threading.Lock()


def get_vector_index_manager() -> Optional[VectorIndexManager]:
    """Get singleton VectorIndexManager, or None if FAISS unavailable."""
    if not FAISS_AVAILABLE:
        return None

    global _index_manager_instance
    if _index_manager_instance is None:
        with _index_manager_lock:
            if _index_manager_instance is None:
                try:
                    _index_manager_instance = VectorIndexManager()
                except Exception as e:
                    logger.warning("Failed to initialize VectorIndexManager: %s", e)
                    return None

    return _index_manager_instance
