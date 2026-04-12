"""
RAG Knowledge Base Module

Implements Retrieval-Augmented Generation for contextual coaching insights.

Components:
    - Vector embeddings (Sentence-BERT)
    - Semantic search (cosine similarity)
    - Knowledge retrieval
    - Contextual insight generation

Adheres to GEMINI.md principles:
    - Explicit state management
    - Performance optimization
    - Clear separation of concerns
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sqlmodel import select

from Programma_CS2_RENAN.backend.knowledge.round_utils import (  # F5-20: shared utility
    infer_round_phase,
)
from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import TacticalKnowledge
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.rag_knowledge")


class KnowledgeEmbedder:
    """
    Generate vector embeddings for tactical knowledge.

    Uses Sentence-BERT (all-MiniLM-L6-v2) for semantic embeddings.
    Falls back to simple TF-IDF if sentence-transformers not available.

    Task 2.10.1: Now tracks embedding version to detect stale embeddings
    and trigger automatic re-embedding when the model changes.
    """

    # Increment when embedding model changes OR seed knowledge corpus is materially refreshed.
    # v2 → v3: Coach Book refactor (2026-04, Premier S4 active duty alignment, +categories
    # mid_round / retakes_post_plant / aim_and_duels). Existing v2 rows must be re-embedded
    # via trigger_reembedding() — see init_knowledge_base.initialize_knowledge_base().
    CURRENT_VERSION = "v3"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.embedding_dim = 384

        self._is_fallback = False  # exposed via is_fallback property (SA-27)
        try:
            from sentence_transformers import SentenceTransformer

            needs_download = not self._is_model_cached(model_name)
            if needs_download:
                logger.info("SBERT model '%s' not cached — download will start", model_name)
                self._notify_download_start(model_name)

            self.model = SentenceTransformer(model_name)
            logger.info("Loaded embedding model: %s", model_name)

            if needs_download:
                self._notify_download_complete(model_name)
        except ImportError:
            logger.warning("sentence-transformers not installed. Using fallback embeddings.")
            self.embedding_dim = 100  # Fallback dimension
            self._is_fallback = True
        except Exception as e:
            # H-01: Log non-import failures (corrupt model, disk error, etc.)
            logger.error("H-01: Failed to load embedding model %s: %s", model_name, e)
            self.embedding_dim = 100
            self._is_fallback = True

    @property
    def is_fallback(self) -> bool:
        """Whether embedder is using degraded fallback (SA-27: public accessor)."""
        return self._is_fallback

    @staticmethod
    def _is_model_cached(model_name: str) -> bool:
        """Check if SBERT model is already downloaded."""
        cache_dir = os.environ.get(
            "SENTENCE_TRANSFORMERS_HOME",
            os.path.join(os.path.expanduser("~"), ".cache", "torch", "sentence_transformers"),
        )
        model_path = os.path.join(cache_dir, model_name.replace("/", "_"))
        return os.path.isdir(model_path)

    @staticmethod
    def _notify_download_start(model_name: str):
        """Emit a toast notification about the SBERT download."""
        try:
            from Programma_CS2_RENAN.backend.storage.state_manager import get_state_manager

            get_state_manager().add_notification(
                "knowledge",
                "INFO",
                f"Downloading AI language model ({model_name}). "
                f"This only happens once (~400 MB).",
            )
        except Exception:
            pass  # Don't block SBERT load over a notification failure

    @staticmethod
    def _notify_download_complete(model_name: str):
        """WR-10: Emit toast notification after SBERT download completes."""
        try:
            from Programma_CS2_RENAN.backend.storage.state_manager import get_state_manager

            get_state_manager().add_notification(
                "knowledge",
                "INFO",
                f"AI language model ({model_name}) downloaded and ready.",
            )
        except Exception:
            pass

    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.

        Args:
            text: Input text

        Returns:
            Embedding vector [embedding_dim]
        """
        if self.model is not None:
            return self.model.encode(text, convert_to_numpy=True)
        else:
            # Fallback: Simple hash-based embedding
            return self._fallback_embed(text)

    def _fallback_embed(self, text: str) -> np.ndarray:
        """Bag-of-words hash-projection fallback (R-02).

        Hashes each word to a dimension, producing sparse-then-normalized vectors.
        Texts sharing words get nonzero cosine similarity, unlike the previous
        seed-based random approach where semantically similar texts were orthogonal.
        """
        import hashlib

        vec = np.zeros(self.embedding_dim, dtype=np.float32)
        for word in text.lower().split():
            h = int(hashlib.md5(word.encode(), usedforsecurity=False).hexdigest()[:8], 16)
            idx = h % self.embedding_dim
            sign = 1.0 if (h // self.embedding_dim) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def check_embedding_compatibility(self, stored_dim: int) -> bool:
        """
        Check if stored embeddings are compatible with current model.

        Task 2.10.1: Returns False if dimension mismatch detected,
        indicating that embeddings need to be regenerated.

        Args:
            stored_dim: Dimension of stored embedding vector

        Returns:
            bool: True if compatible, False if re-embedding needed
        """
        if stored_dim != self.embedding_dim:
            # R-01-alt: Log version/dimension mismatch for diagnostics
            logger.warning(
                "R-01-alt: Embedding dimension mismatch: stored=%d, current=%d "
                "(model=%s, version=%s). Reembedding recommended.",
                stored_dim,
                self.embedding_dim,
                self.model_name,
                self.CURRENT_VERSION,
            )
            return False
        return True

    def trigger_reembedding(self) -> int:
        """
        Re-embed all TacticalKnowledge entries with mismatched dimensions.

        Task 2.10.1: Called when embedding model changes to ensure
        all stored embeddings are compatible with current model.

        Returns:
            int: Number of entries re-embedded
        """
        from sqlmodel import select

        from Programma_CS2_RENAN.backend.storage.database import get_db_manager
        from Programma_CS2_RENAN.backend.storage.db_models import TacticalKnowledge

        db = get_db_manager()
        count = 0

        # Limit to prevent OOM on large knowledge bases (F5-03).
        MAX_REEMBED_BATCH = 5_000
        with db.get_session() as session:
            entries = session.exec(select(TacticalKnowledge).limit(MAX_REEMBED_BATCH)).all()

            for entry in entries:
                try:
                    embedding = json.loads(entry.embedding)

                    # Check if re-embedding is needed
                    if len(embedding) != self.embedding_dim:
                        # Re-embed using title + description + situation
                        text = f"{entry.title}. {entry.description}. {entry.situation}"
                        new_embedding = self.embed(text)
                        entry.embedding = json.dumps(new_embedding.tolist())
                        session.add(entry)
                        count += 1
                        logger.info("Re-embedded: %s", entry.title)
                except Exception as e:
                    logger.warning("Failed to re-embed %s: %s", entry.id, e)

            session.commit()

        # AC-36-02: Invalidate FAISS index after re-embedding
        if count > 0:
            from Programma_CS2_RENAN.backend.knowledge.vector_index import get_vector_index_manager

            index_mgr = get_vector_index_manager()
            if index_mgr:
                index_mgr.mark_dirty("knowledge")

        logger.info("Re-embedded %s knowledge entries", count)
        return count


class KnowledgeRetriever:
    """
    Semantic search over tactical knowledge base.

    Uses cosine similarity for ranking.
    """

    def __init__(self):
        # F5-23: init_database() removed — must be called once at app startup, not per-constructor.
        self.db = get_db_manager()
        self.embedder = KnowledgeEmbedder()
        # H-01: Surface degraded embedder state to retriever consumers
        if self.embedder.is_fallback:
            logger.warning(
                "H-01: KnowledgeRetriever using fallback embeddings (dim=%d). "
                "RAG retrieval quality will be degraded.",
                self.embedder.embedding_dim,
            )

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        category: Optional[str] = None,
        map_name: Optional[str] = None,
    ) -> List[TacticalKnowledge]:
        """
        Retrieve most relevant tactical knowledge.

        Uses FAISS vector index when available (AC-36-02), falling back
        to brute-force cosine similarity if FAISS is not installed.

        Args:
            query: Search query (e.g., "low ADR on T-side")
            top_k: Number of results
            category: Filter by category
            map_name: Filter by map

        Returns:
            List of TacticalKnowledge entries, ranked by relevance
        """
        query_embedding = self.embedder.embed(query)

        # H-02: Validate embedding dimensionality matches expected model output
        if query_embedding.shape[0] != self.embedder.embedding_dim:
            logger.error(
                "H-02: Query embedding dim %d != expected %d — dimension mismatch",
                query_embedding.shape[0],
                self.embedder.embedding_dim,
            )
            return []

        # AC-36-02: FAISS fast-path — O(1) index lookup instead of O(n) brute-force
        from Programma_CS2_RENAN.backend.knowledge.vector_index import (
            OVERFETCH_KNOWLEDGE,
            get_vector_index_manager,
        )

        index_mgr = get_vector_index_manager()
        if index_mgr is not None:
            overfetch_k = top_k * OVERFETCH_KNOWLEDGE
            candidates = index_mgr.search("knowledge", query_embedding, overfetch_k)
            if candidates:
                result = self._fetch_and_filter(candidates, category, map_name, top_k)
                if result is not None:
                    return result

        # Brute-force fallback (original implementation)
        return self._brute_force_retrieve(query_embedding, top_k, category, map_name)

    def _fetch_and_filter(
        self,
        candidates: List,
        category: Optional[str],
        map_name: Optional[str],
        top_k: int,
    ) -> Optional[List[TacticalKnowledge]]:
        """Fetch DB records from FAISS candidates, post-filter, return top-k."""
        candidate_ids = [db_id for db_id, _ in candidates]
        score_map = {db_id: score for db_id, score in candidates}

        with self.db.get_session() as session:
            entries = session.exec(
                select(TacticalKnowledge).where(TacticalKnowledge.id.in_(candidate_ids))
            ).all()

            if not entries:
                return None

            # Post-filter by metadata
            filtered = entries
            if category:
                filtered = [e for e in filtered if e.category == category]
            if map_name:
                filtered = [e for e in filtered if e.map_name == map_name]

            if not filtered:
                return None

            # Rank by FAISS similarity score
            filtered.sort(key=lambda e: score_map.get(e.id, 0), reverse=True)
            top_entries = filtered[:top_k]
            top_ids = [e.id for e in top_entries]

        self._update_usage_counts(top_ids)
        return top_entries

    def _brute_force_retrieve(
        self,
        query_embedding: np.ndarray,
        top_k: int,
        category: Optional[str],
        map_name: Optional[str],
    ) -> List[TacticalKnowledge]:
        """Original brute-force cosine similarity search."""
        with self.db.get_session() as session:
            stmt = select(TacticalKnowledge)

            if category:
                stmt = stmt.where(TacticalKnowledge.category == category)
            if map_name:
                stmt = stmt.where(TacticalKnowledge.map_name == map_name)

            stmt = stmt.limit(500)
            knowledge_entries = session.exec(stmt).all()

            if not knowledge_entries:
                logger.warning("No knowledge entries found")
                return []

            similarities = []
            for entry in knowledge_entries:
                entry_embedding = np.array(json.loads(entry.embedding))
                similarity = self._cosine_similarity(query_embedding, entry_embedding)
                similarities.append((entry, similarity))

            similarities.sort(key=lambda x: x[1], reverse=True)
            top_entries = [entry for entry, _ in similarities[:top_k]]
            top_ids = [e.id for e in top_entries]

        self._update_usage_counts(top_ids)
        return top_entries

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)

    def _update_usage_counts(self, knowledge_ids: List[int]):
        """Increment usage count for retrieved knowledge (batch update)."""
        if not knowledge_ids:
            return
        from sqlmodel import update

        with self.db.get_session() as session:
            # Single UPDATE instead of N individual SELECTs (WR-61)
            session.exec(
                update(TacticalKnowledge)
                .where(TacticalKnowledge.id.in_(knowledge_ids))
                .values(usage_count=TacticalKnowledge.usage_count + 1)
            )


class KnowledgePopulator:
    """
    Populate knowledge base with tactical insights.

    Sources:
        - Map-specific tactics (JSON files)
        - Pro demo analysis
        - Community best practices
    """

    def __init__(self):
        # F5-23: init_database() removed — must be called once at app startup, not per-constructor.
        self.db = get_db_manager()
        self.embedder = KnowledgeEmbedder()

    def add_knowledge(
        self,
        title: str,
        description: str,
        category: str,
        situation: str,
        map_name: Optional[str] = None,
        pro_example: Optional[str] = None,
    ) -> TacticalKnowledge:
        """
        Add new tactical knowledge to database.

        Args:
            title: Knowledge title
            description: Detailed description
            category: Category (positioning, economy, utility, aim)
            situation: Tactical situation
            map_name: Optional map name
            pro_example: Optional pro demo reference

        Returns:
            Created TacticalKnowledge entry
        """
        # Generate embedding
        text = f"{title}. {description}. {situation}"
        embedding = self.embedder.embed(text)

        # Create knowledge entry
        knowledge = TacticalKnowledge(
            title=title,
            description=description,
            category=category,
            situation=situation,
            map_name=map_name,
            pro_example=pro_example,
            embedding=json.dumps(embedding.tolist()),
        )

        # Save to database
        with self.db.get_session() as session:
            session.add(knowledge)
            session.commit()
            session.refresh(knowledge)

        # AC-36-02: Signal FAISS index rebuild
        from Programma_CS2_RENAN.backend.knowledge.vector_index import get_vector_index_manager

        index_mgr = get_vector_index_manager()
        if index_mgr:
            index_mgr.mark_dirty("knowledge")

        logger.info("Added knowledge: %s", title)
        return knowledge

    # Allow-list for kwargs splat into add_knowledge() — protects against
    # forward-compat fields (e.g. tags, revision) appearing in book JSON files.
    _ALLOWED_ENTRY_KEYS = frozenset(
        ("title", "description", "category", "situation", "map_name", "pro_example")
    )

    def populate_from_json(self, json_path: Path) -> int:
        """
        Populate knowledge from a JSON file or a Coach Book index file.

        Two accepted formats:

        1. **Legacy single-file format** — `{"knowledge": [{...}, ...]}`.
           Used by `tactical_knowledge.json` (kept as a fallback).

        2. **Coach Book index format** — `{"version": "...", "files": ["a.json", ...]}`.
           Used by `book/index.json`. Each referenced file is itself a legacy single-file
           JSON (`{"knowledge": [...]}`) and is loaded relative to the index file.

        Entries are filtered against `_ALLOWED_ENTRY_KEYS` so unknown fields in book
        files do not crash the loader (forward-compat).

        Returns:
            Number of knowledge entries successfully added.
        """
        json_path = Path(json_path)
        with open(json_path, "r") as f:
            data = json.load(f)

        # Coach Book index detection: presence of "files" key (no "knowledge" key).
        if "files" in data and "knowledge" not in data:
            book_dir = json_path.parent
            version = data.get("version", "unknown")
            file_list = data.get("files", [])
            logger.info(
                "Loading Coach Book index version=%s with %d file(s) from %s",
                version,
                len(file_list),
                book_dir,
            )
            total = 0
            for rel_name in file_list:
                child_path = book_dir / rel_name
                if not child_path.exists():
                    logger.error(
                        "Coach Book file missing: %s (referenced by %s)", child_path, json_path
                    )
                    continue
                total += self._populate_single_file(child_path)
            logger.info(
                "Coach Book load complete: %d entries from %d file(s)", total, len(file_list)
            )
            return total

        # Legacy single-file path
        return self._populate_single_file(json_path, _data=data)

    def _populate_single_file(self, json_path: Path, _data: Optional[Dict[str, Any]] = None) -> int:
        """Load a single `{"knowledge": [...]}` file. Returns count added."""
        if _data is None:
            with open(json_path, "r") as f:
                _data = json.load(f)

        count = 0
        for entry in _data.get("knowledge", []):
            # Strip unknown keys before kwargs splat (forward-compat).
            filtered = {k: v for k, v in entry.items() if k in self._ALLOWED_ENTRY_KEYS}
            unknown = set(entry.keys()) - self._ALLOWED_ENTRY_KEYS
            if unknown:
                logger.debug(
                    "Stripped unknown keys %s from entry '%s' in %s",
                    sorted(unknown),
                    entry.get("title", "<no-title>"),
                    json_path.name,
                )
            try:
                self.add_knowledge(**filtered)
                count += 1
            except TypeError as e:
                logger.error(
                    "Failed to add entry '%s' from %s: %s",
                    entry.get("title", "<no-title>"),
                    json_path.name,
                    e,
                )

        logger.info("Populated %s knowledge entries from %s", count, json_path.name)
        return count


_cached_retriever: Optional[KnowledgeRetriever] = None
_seed_checked: bool = False


def ensure_seed_knowledge_loaded():
    """Load hand-curated seed knowledge if DB lacks intent-category entries.

    Checks once per process. Only creates KnowledgePopulator (and loads SBERT)
    when seed data actually needs to be written.
    """
    global _seed_checked
    if _seed_checked:
        return
    _seed_checked = True

    db = get_db_manager()
    with db.get_session() as session:
        existing = session.exec(
            select(TacticalKnowledge).where(TacticalKnowledge.category == "positioning").limit(1)
        ).first()
        if existing:
            return  # Seed data already present

    seed_path = Path(__file__).parent / "tactical_knowledge.json"
    if not seed_path.exists():
        logger.debug("Seed knowledge file not found: %s", seed_path)
        return

    populator = KnowledgePopulator()
    populator.populate_from_json(seed_path)
    logger.info("Loaded seed tactical knowledge (%s)", seed_path.name)


def _get_retriever() -> KnowledgeRetriever:
    """Return a cached KnowledgeRetriever to avoid reloading SBERT per call."""
    global _cached_retriever
    if _cached_retriever is None:
        _cached_retriever = KnowledgeRetriever()
    return _cached_retriever


def generate_rag_coaching_insight(
    player_stats: Dict[str, float], map_name: Optional[str] = None
) -> str:
    """
    Generate RAG-enhanced coaching insight.

    Args:
        player_stats: Player statistics (e.g., {"avg_adr": 65, "avg_kills": 15})
        map_name: Optional map name for context

    Returns:
        Contextual coaching insight
    """
    retriever = _get_retriever()

    # Construct query from stats
    query_parts = []
    if player_stats.get("avg_adr", 0) < 75:
        query_parts.append("low ADR")
    if player_stats.get("avg_kills", 0) < 18:
        query_parts.append("low kills")
    if player_stats.get("kd_ratio", 0) < 1.0:
        query_parts.append("negative K/D")

    query = " ".join(query_parts) if query_parts else "general improvement"

    # Retrieve relevant knowledge
    knowledge = retriever.retrieve(query, top_k=2, map_name=map_name)

    if not knowledge:
        return "Practice aim and positioning to improve your stats."

    # Generate contextual insight
    insight_parts = []
    for k in knowledge:
        insight_parts.append(
            f"{k.title}: {k.description}"
        )  # Emoji stripped — presentation is UI concern
        if k.pro_example:
            insight_parts.append(f"   Pro example: {k.pro_example}")

    return "\n".join(insight_parts)


def generate_unified_coaching_insight(
    player_stats: Dict[str, float],
    tick_data: Optional[Dict[str, Any]] = None,
    map_name: Optional[str] = None,
) -> str:
    """
    Generate unified coaching insight combining RAG knowledge + Experience Bank.

    This is the recommended entry point for COPER-style coaching that
    combines tactical knowledge with learned experiences.

    Args:
        player_stats: Player statistics (e.g., {"avg_adr": 65})
        tick_data: Optional current tick state for context
        map_name: Optional map name

    Returns:
        Unified coaching insight with pro references
    """
    insight_parts = []

    # 1. Get RAG tactical knowledge
    try:
        rag_insight = generate_rag_coaching_insight(player_stats, map_name)
        if rag_insight and "Practice aim" not in rag_insight:
            insight_parts.append("Tactical Knowledge:")
            insight_parts.append(rag_insight)
    except Exception as e:
        logger.warning("RAG retrieval failed: %s", e)

    # 2. Get Experience Bank insights (if tick data available)
    if tick_data:
        try:
            from Programma_CS2_RENAN.backend.knowledge.experience_bank import (
                ExperienceContext,
                get_experience_bank,
            )

            bank = get_experience_bank()  # Singleton — avoids re-loading SBERT model (F5-04)

            # Build context
            context = ExperienceContext(
                map_name=map_name or "unknown",
                round_phase=infer_round_phase(tick_data),
                side=tick_data.get("team", "T"),
                position_area=tick_data.get("position_area"),
            )

            # Get synthesized advice
            advice = bank.synthesize_advice(context)

            if advice.experiences_used > 0:
                insight_parts.append("\nExperience-Based Advice:")
                insight_parts.append(advice.narrative)

                if advice.pro_references:
                    insight_parts.append("\nPro References:")
                    for ref in advice.pro_references:
                        insight_parts.append(f"  - {ref}")

        except Exception as e:
            logger.warning("Experience Bank retrieval failed: %s", e)

    if not insight_parts:
        return "Keep practicing! Analyze your demos to build personalized coaching insights."

    return "\n".join(insight_parts)


# F5-20: _infer_round_phase extracted to round_utils.infer_round_phase (shared utility).
