"""
Knowledge Base Initialization Script

Populates the RAG knowledge base with:
1. Manual tactical knowledge (tactical_knowledge.json)
2. Automated pro demo mining
3. Validation and deduplication

Run this once to initialize the knowledge base.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlmodel import select

from Programma_CS2_RENAN.backend.knowledge.pro_demo_miner import auto_populate_from_pro_demos
from Programma_CS2_RENAN.backend.knowledge.rag_knowledge import KnowledgePopulator
from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database
from Programma_CS2_RENAN.backend.storage.db_models import TacticalKnowledge
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.knowledge_init")


def initialize_knowledge_base():
    """
    Initialize knowledge base with all sources.

    Steps:
    1. Initialize database
    2. Load manual knowledge from JSON
    3. Mine knowledge from pro demos
    4. Report statistics
    """
    logger.info("=== Knowledge Base Initialization ===\n")

    # Step 1: Initialize database
    logger.info("Step 1: Initializing database...")
    init_database()

    # Step 2: Load manual knowledge
    logger.info("Step 2: Loading manual tactical knowledge...")
    populator = KnowledgePopulator()

    json_path = (
        PROJECT_ROOT / "Programma_CS2_RENAN" / "backend" / "knowledge" / "tactical_knowledge.json"
    )

    if json_path.exists():
        try:
            populator.populate_from_json(json_path)
            logger.info("✓ Loaded manual knowledge from %s", json_path)
        except Exception as e:
            logger.error("Failed to load manual knowledge: %s", e)
    else:
        logger.warning("Manual knowledge file not found: %s", json_path)

    # Step 3: Mine pro demos
    logger.info("Step 3: Mining knowledge from pro demos...")
    try:
        count = auto_populate_from_pro_demos(limit=10)
        logger.info("✓ Mined %s entries from pro demos", count)
    except Exception as e:
        logger.error("Failed to mine pro demos: %s", e)

    # Step 4: Report statistics
    logger.info("\nStep 4: Knowledge Base Statistics")
    db = get_db_manager()

    with db.get_session() as session:
        total = session.exec(select(TacticalKnowledge)).all()

        # Count by category
        categories = {}
        maps = {}

        for entry in total:
            categories[entry.category] = categories.get(entry.category, 0) + 1
            if entry.map_name:
                maps[entry.map_name] = maps.get(entry.map_name, 0) + 1

        print(f"\n{'='*50}")
        print(f"Total Knowledge Entries: {len(total)}")
        print(f"{'='*50}\n")

        print("By Category:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat:15s}: {count:3d} entries")

        print("\nBy Map:")
        for map_name, count in sorted(maps.items(), key=lambda x: x[1], reverse=True):
            print(f"  {map_name:15s}: {count:3d} entries")

        print(f"\n{'='*50}")
        print("✓ Knowledge base initialization complete!")
        print(f"{'='*50}\n")


if __name__ == "__main__":
    initialize_knowledge_base()
