# Re-Ingestion & Training Guide

After the data curation and audit fixes (April 2026), a full re-ingestion is needed
to populate all features correctly. This guide covers the complete pipeline.

## Prerequisites

- Python 3.10+ with the project venv activated (`source ~/.venvs/cs2analyzer/bin/activate`)
- Pro .dem files in `DEMO_PRO_PLAYERS/` directory (97 files as of 2026-04-11; 564 per-match DBs already parsed)
- ~25 GB free disk space (19.5 GB monolith DB + per-match DBs)

## Step-by-Step

### 1. Pull latest code and initialize

```bash
cd /path/to/Counter-Strike-coach-AI-main
git pull origin main
pip install -r requirements.txt

# Initialize DB schema (adds has_helmet, has_defuser, kast columns if missing)
python -c "
from Programma_CS2_RENAN.backend.storage.database import init_database
init_database()
print('Schema initialized.')
"
```

### 2. Full re-ingestion of all pro demos

This re-parses every .dem file with the corrected field mappings (ducking, flash_duration,
has_helmet, has_defuser) and rebuilds the monolith playertickstate table.

```bash
# Set the DEMO_PRO_PLAYERS path in the script if different on this machine
# Edit tools/ingest_pro_demos.py line 17: DEMO_BASE = Path("/your/path/to/DEMO_PRO_PLAYERS")

python tools/ingest_pro_demos.py --full
```

**Expected output:** playertickstate rows across all demos, playermatchstats rows (scales with demo count).
**Expected time:** 1-3 hours depending on disk speed.

### 3. Build the composite index (if not already present)

```bash
python -c "
import sqlite3
conn = sqlite3.connect('Programma_CS2_RENAN/backend/storage/database.db', timeout=120)
conn.execute('PRAGMA journal_mode=WAL')
# Check if index exists
idx = conn.execute(\"SELECT name FROM sqlite_master WHERE type='index' AND name='idx_pts_demo_player_tick'\").fetchone()
if idx:
    print('Composite index already exists.')
else:
    print('Creating composite index (may take 10-30 min on 70M rows)...')
    conn.execute('CREATE INDEX idx_pts_demo_player_tick ON playertickstate(demo_name, player_name, tick)')
    conn.commit()
    print('Index created.')
conn.close()
"
```

### 4. Populate RoundStats from .dem files

```bash
python tools/populate_round_stats.py
```

**Expected output:** roundstats rows across all demos with per-round KAST flags (scales with demo count; ~24K+ expected with full 97-demo corpus).

### 5. Repair KAST in PlayerMatchStats

```bash
python tools/repair_kast.py
```

**Expected output:** avg_kast drops from ~0.91 (inflated) to ~0.71 (event-accurate).

### 6. Mine CoachingExperience from RoundStats

```bash
python tools/mine_coaching_experience.py
```

**Expected output:** ~3,000-4,000 CoachingExperience records (entry frags, multi-kills, trades, eco upsets, utility).

### 7. Mine map-specific TacticalKnowledge

```bash
python -c "
from Programma_CS2_RENAN.backend.storage.database import init_database
init_database()
from Programma_CS2_RENAN.backend.knowledge.pro_demo_miner import ProStatsMiner
miner = ProStatsMiner()
count = miner.mine_map_specific_knowledge()
print(f'Map-specific entries created: {count}')
"
```

### 8. Verify data integrity

```bash
python tools/headless_validator.py
# Must show: VERDICT: PASS (308/313 passed, 5 warnings for optional deps is OK)
```

### 9. JEPA Pre-training

```bash
python -m Programma_CS2_RENAN.backend.nn.jepa_train --mode pretrain
```

**Expected:** 50 epochs on pro player sequences (500 ticks each, 25-dim vectors). Sequence count scales with demo corpus.
Model saved to `models/jepa_model.pt`.

### 10. (Optional) JEPA Fine-tuning on user demos

Only after ingesting your own demos:

```bash
python -m Programma_CS2_RENAN.backend.nn.jepa_train --mode finetune
```

## Verification Checklist

After re-ingestion, run this quick check:

```bash
python -c "
import sqlite3
con = sqlite3.connect('Programma_CS2_RENAN/backend/storage/database.db', timeout=30)

# Tick features alive?
for col in ['is_crouching', 'is_blinded', 'has_helmet', 'has_defuser']:
    nz = con.execute(f'SELECT COUNT(*) FROM (SELECT {col} FROM playertickstate WHERE tick > 100000 LIMIT 5000) WHERE {col} != 0').fetchone()[0]
    print(f'{col}: {nz/50:.1f}% non-zero')

# KAST repaired?
kast = con.execute('SELECT AVG(avg_kast) FROM playermatchstats WHERE is_pro=1').fetchone()[0]
print(f'avg_kast: {kast:.4f} (should be ~0.71)')

# Tables populated?
for table in ['roundstats', 'coachingexperience', 'tacticalknowledge']:
    n = con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    print(f'{table}: {n:,} rows')

con.close()
"
```

**Expected:**
- is_crouching: ~1-2% non-zero
- is_blinded: ~0.5-1% non-zero
- has_helmet: ~14-20% non-zero
- has_defuser: ~6-10% non-zero
- avg_kast: ~0.71
- roundstats: ~8,000+
- coachingexperience: ~3,000+
- tacticalknowledge: ~500+
