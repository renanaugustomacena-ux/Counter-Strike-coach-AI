#!/bin/bash
# Re-aggregation pipeline — run in a separate terminal
# Populates roundstats, enriches playermatchstats, mines coaching experiences,
# and rebuilds the knowledge base + FAISS indexes.
#
# Prerequisites:
#   - venv activated: source ~/.venvs/cs2analyzer/bin/activate
#   - .dem files at PRO_DEMO_PATH from user_settings.json (currently /media/renan/New Volume/...)
#   - database.db accessible
#
# Usage:
#   source ~/.venvs/cs2analyzer/bin/activate
#   bash scripts/reaggregate.sh
#
# Expected runtime: 30-90 minutes depending on demo count
set -euo pipefail

cd "$(dirname "$0")/.."
echo "=== Re-aggregation Pipeline ==="
echo "Working directory: $(pwd)"
echo "Python: $(which python3)"
echo "Start time: $(date)"
echo ""

# Step 1: Populate RoundStats + enrich PlayerMatchStats from .dem files
echo "=== Step 1/4: Populate RoundStats (--full rebuild) ==="
echo "This re-parses all demos via demoparser2 and writes roundstats + enrichment fields."
echo ""
python3 tools/populate_round_stats.py --full
echo ""

# Step 2: Mine coaching experiences from roundstats
echo "=== Step 2/4: Mine Coaching Experiences ==="
echo "Scans roundstats for tactical scenarios (entry frags, multi-kills, eco forces, etc.)"
echo ""
python3 tools/mine_coaching_experience.py
echo ""

# Step 3: Rebuild knowledge base + FAISS indexes
echo "=== Step 3/4: Rebuild Knowledge Base ==="
echo "Loads tactical_knowledge.json, mines pro stat cards, rebuilds FAISS vector indexes."
echo ""
python3 -m Programma_CS2_RENAN.backend.knowledge.init_knowledge_base
echo ""

# Step 4: Verify row counts
echo "=== Step 4/4: Verification ==="
python3 -c "
import sqlite3
db = 'Programma_CS2_RENAN/backend/storage/database.db'
conn = sqlite3.connect(db)
print('=== Post-Aggregation Row Counts ===')
for table in ['playermatchstats', 'roundstats', 'playertickstate', 'coachingexperience', 'tacticalknowledge', 'ingestiontask']:
    count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    print(f'  {table}: {count:,}')

# Check enrichment quality
zero_enrich = conn.execute('''
    SELECT COUNT(*) FROM playermatchstats
    WHERE thrusmoke_kill_pct = 0.0
    AND wallbang_kill_pct = 0.0
    AND trade_kill_ratio = 0.0
''').fetchone()[0]
total = conn.execute('SELECT COUNT(*) FROM playermatchstats').fetchone()[0]
if total > 0:
    pct = (total - zero_enrich) / total * 100
    print(f'  Enrichment coverage: {pct:.1f}% ({total - zero_enrich}/{total} rows have non-zero enrichment)')
conn.close()
"
echo ""
echo "=== Re-aggregation complete: $(date) ==="
