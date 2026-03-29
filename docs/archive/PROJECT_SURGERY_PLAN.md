# Macena CS2 Coach AI — Project Surgery Plan

> **Date:** March 17, 2026
> **Author:** Renan Augusto Macena
> **Purpose:** Authoritative technical plan for splitting this project into a deployable game-theory-first product while cleanly deferring the RAP super-complex ML architecture.
> **Audience:** A Senior Software and AI Engineer who will execute the modifications described herein.
> **Supersedes:** `AI_ARCHITECTURE_ANALYSIS.md` (AI/ML audit) + `PRODUCT_VIABILITY_ASSESSMENT.md` (product viability audit). Those documents remain as historical records.
> **Rule:** Only honesty. Only realistic rules. No sugar-coating.

---

## Table of Contents

### Part I: The Truth
1. [Executive Summary](#1-executive-summary)
2. [The Codebase by Numbers](#2-the-codebase-by-numbers)
3. [Architecture Overview](#3-architecture-overview)
4. [What Works Today (No Training Needed)](#4-what-works-today)
5. [What Doesn't Work Yet](#5-what-doesnt-work-yet)

### Part II: The Surgery
6. [The Dependency Graph](#6-the-dependency-graph)
7. [Surgery 1: Isolating RAP](#7-surgery-1-isolating-rap)
8. [Surgery 2: Slimming Dependencies](#8-surgery-2-slimming-dependencies)
9. [Surgery 3: Frontend Cleanup](#9-surgery-3-frontend-cleanup)
10. [Surgery 4: Backend Hardening](#10-surgery-4-backend-hardening)
11. [Surgery 5: Packaging for Distribution](#11-surgery-5-packaging-for-distribution)
12. [Validation Protocol](#12-validation-protocol)

### Part III: The Product
13. [What Ships: The v0.1 Feature Matrix](#13-what-ships)
14. [The Competition: Honest Assessment](#14-the-competition)
15. [Pricing and Distribution](#15-pricing-and-distribution)
16. [The User's First 10 Minutes](#16-the-users-first-10-minutes)
17. [Cross-Platform Strategy](#17-cross-platform-strategy)

### Part IV: The Future
18. [When RAP Comes Back](#18-when-rap-comes-back)
19. [The 6-Month Roadmap](#19-the-6-month-roadmap)
20. [Final Verdict](#20-final-verdict)

---

# PART I: THE TRUTH

---

## 1. Executive Summary

This project is a desktop application that analyzes Counter-Strike 2 professional demo files and produces personalized coaching insights for players. It was built from zero by a solo developer who had never written Python before December 24, 2025. In under three months, it grew to 372 Python source files, 84,497 lines of code, a tri-database SQLite architecture handling 17.3 million tick rows, nine standalone game theory engines, a complete MVVM frontend with PySide6/Qt6, and a multi-model ML pipeline spanning JEPA self-supervised pre-training, VL-JEPA visual-language concepts, and a seven-layer RAP Coach with Liquid Time-Constant neurons and Hopfield associative memory.

That last sentence is the problem.

The RAP Coach architecture — Perception, Memory (LTC + Hopfield), Strategy (MoE), Pedagogy (Causal Attribution) — is a research-grade neural architecture that would require thousands of professionally parsed demos, months of training iteration, and careful hyperparameter tuning to produce coaching output that beats what the game theory engines already deliver for free, today, with zero training data.

The game theory engines are the hidden gem. Bayesian death probability estimation, expectiminimax game tree search, Shannon entropy analysis of utility effectiveness, blind spot detection comparing player actions to optimal recommendations, engagement range classification against pro baselines, psychological momentum tracking, deception index quantification, and economy optimization — these produce specific, actionable, personalized coaching insights from raw match data and published CS2 knowledge. No neural network required.

**The strategic decision:** Ship the game theory engines and the COPER coaching pipeline (Experience Bank + RAG + Pro References) as a v0.1 product. Defer RAP entirely — not delete it, not disable it, but isolate it behind a clean boundary so it can be activated when the data, training infrastructure, and benchmarks prove it adds value over what already works.

**What this document provides:** Step-by-step instructions for a Senior Engineer to execute this split. Every instruction references specific files, line numbers, and code patterns. Every claim is backed by traced dependency chains. Every timeline is honest.

---

## 2. The Codebase by Numbers

These numbers were verified directly from the codebase on March 17, 2026.

### Scale

| Metric | Value |
|--------|-------|
| Python source files | 372 |
| Lines of code (application) | 84,497 |
| Test files | 18 |
| Lines of test code | 1,309 |
| Test coverage (CI gate) | ~30% (`fail_under=30`) |

### Architecture

| Component | Count |
|-----------|-------|
| Database tables (monolith) | 18 |
| Per-match SQLite databases | 11 (one per ingested demo) |
| Separate databases | 3 (monolith, HLTV, per-match) |
| Background daemons | 4 (Scanner, Digester, Teacher, Pulse) |
| Game theory engines | 9 (plus 1 with torch inference) |
| ML models defined | 4 (JEPA, VL-JEPA, RAP Coach, Win Probability NN) |
| Coaching fallback levels | 4 (COPER → Hybrid → Traditional+RAG → Traditional) |

### Frontend

| Component | Count |
|-----------|-------|
| Qt screens total | 13 |
| Qt screens functional | 5 (Home, Coach, Match History, Performance, Tactical Viewer) |
| Qt screens stub | 8 (Settings, Help, Match Detail, Wizard, Profile, Edit Profile, Steam, FaceIT) |
| Sidebar-visible screens | 7 (5 functional + Settings + Help) |
| Hidden screens (programmatic access only) | 6 (Wizard, Match Detail, Profile, Edit Profile, Steam, FaceIT) |
| Custom QPainter chart widgets | 6 (Radar, Sparkline, Trend, Momentum, Economy, Utility) |
| Theme variants | 3 (CS2 orange, CSGO blue-grey, CS 1.6 green retro) |
| Languages | 3 (English, Portuguese, Italian) — 136 keys each |

### Dependencies

| Component | Value |
|-----------|-------|
| Direct dependencies (`requirements.txt`) | 52 packages |
| Transitive locked dependencies | 152 packages |
| Bundle size (CPU-only PyTorch) | ~1.6 GB |
| Bundle size (CUDA 12.1 PyTorch) | ~2.5 GB (current default) |
| SBERT model download (first use) | ~400 MB (no progress indicator) |

### Data

| Metric | Value |
|--------|-------|
| Pro demos available on SSD | ~200 |
| Pro demos ingested | 11 |
| Total tick rows in database | 17.3 million |
| Database size | 6.4 GB |
| JEPA checkpoint produced | `jepa_brain.pt` (3.6 MB) |
| JEPA dry-run result | 1 epoch, train loss 0.9506, val loss 1.8248 |

---

## 3. Architecture Overview

### System Diagram

```
                           ┌──────────────────────────────┐
                           │     PySide6 / Qt6 Frontend    │
                           │  ┌──────┐ ┌──────┐ ┌──────┐  │
                           │  │Home  │ │Coach │ │Tactic│  │
                           │  │Screen│ │Screen│ │Viewer│  │
                           │  └──┬───┘ └──┬───┘ └──┬───┘  │
                           │     │        │        │       │
                           │  ┌──┴────────┴────────┴──┐    │
                           │  │    ViewModels (MVVM)    │   │
                           │  │  Signals + Workers      │   │
                           │  └────────────┬───────────┘   │
                           └───────────────┼───────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
           ┌────────┴────────┐    ┌────────┴────────┐    ┌───────┴───────┐
           │ Coaching Service │    │  Analysis Engines │    │   ML Pipeline  │
           │  (4-level COPER) │    │  (9 game theory)  │    │  (JEPA + RAP)  │
           │                  │    │                    │    │                │
           │ L1: Exp Bank+RAG│    │ belief_model.py    │    │ JEPA encoder   │
           │ L2: Hybrid       │    │ game_tree.py       │    │ VL-JEPA        │
           │ L3: Trad+RAG    │    │ momentum.py        │    │ ┌────────────┐ │
           │ L4: Traditional  │    │ entropy_analysis   │    │ │ RAP Coach  │ │
           │                  │    │ blind_spots.py     │    │ │ (DEFERRED) │ │
           │                  │    │ deception_index    │    │ │ Perception │ │
           │                  │    │ engagement_range   │    │ │ Memory     │ │
           │                  │    │ role_classifier    │    │ │ Strategy   │ │
           │                  │    │ utility_economy    │    │ │ Pedagogy   │ │
           │                  │    │ win_probability*   │    │ └────────────┘ │
           └────────┬─────────┘    └────────┬──────────┘    └───────┬────────┘
                    │                       │                       │
                    └───────────────────────┼───────────────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │              Data Layer                        │
                    │  ┌─────────────┐ ┌──────────┐ ┌────────────┐ │
                    │  │ database.db  │ │hltv_meta │ │ match_*.db │ │
                    │  │ (monolith)   │ │  .db     │ │ (per-match)│ │
                    │  │ 18 tables    │ │ (HLTV    │ │ (tick data)│ │
                    │  │ coaching,    │ │  scraper │ │ (positions)│ │
                    │  │ stats, etc.  │ │  stats)  │ │            │ │
                    │  └─────────────┘ └──────────┘ └────────────┘ │
                    │              All SQLite WAL mode               │
                    └───────────────────────────────────────────────┘
```

*`win_probability.py` uses PyTorch for inference only (12-feature → 64/32 → 1 sigmoid). It is an analysis engine that happens to use a small NN — not part of the RAP/JEPA training pipeline.

### The Four Daemons

The system runs four background threads coordinated through `core/session_engine.py`:

| Daemon | Lines | Responsibility | Cycle |
|--------|-------|----------------|-------|
| **Scanner (Hunter)** | 241–292 | Watches filesystem for new .dem files, queues them in DB | Every 10 seconds |
| **Digester** | 295–342 | Processes queued demos: parse → feature extract → store | 1 item per cycle, waits on event |
| **Teacher** | 345–418 | Triggers ML retraining when enough new data arrives | Every 300 seconds |
| **Pulse** | 421–430 | Heartbeat — updates CoachState timestamp | Every 5 seconds |

**Critical coordination mechanism:** The `_backup_failed` flag (line 58) is set to `True` if the startup backup fails (line 112). When `True`, the Teacher daemon skips ALL training (line 358) and retries every 300 seconds. This is a safety mechanism — don't train on data that has no backup — but the user gets zero notification that training has stopped.

### The Coaching Pipeline

When a user's demo is parsed and analyzed, the coaching service (`backend/services/coaching_service.py`) generates insights through a 4-level fallback chain:

```
Level 1: COPER                    (lines 113-293)
  ├── Requires: use_coper=True, map_name, tick_data
  ├── Uses: ExperienceBank (SBERT embeddings + FAISS)
  │         KnowledgeRetriever (RAG knowledge base)
  │         Pro baseline references
  ├── Output: Situation-specific coaching with pro comparisons
  └── On failure → Level 2

Level 2: Hybrid                   (lines 123-128, 480-520)
  ├── Requires: use_hybrid=True, player_stats
  ├── Uses: ML predictions + RAG synthesis
  ├── Output: Pattern-based coaching enriched with knowledge
  └── On failure → Level 3

Level 3: Traditional + RAG        (lines 129-141, 522-565)
  ├── Requires: deviations dict (always available)
  ├── Uses: Statistical deviations from pro baseline + RAG enhancement
  ├── Output: "Your ADR deviates from pro by Z=-1.8" + knowledge context
  └── RAG failure is non-fatal → continues with raw deviations

Level 4: Traditional              (lines 700-732)
  ├── Requires: nothing (terminal fallback)
  ├── Uses: Pure statistical deviations
  ├── Output: Generic coaching based on metric deviations
  └── If even this fails → generic insight saved (zero-coaching prevention)
```

**The critical insight:** Levels 1, 3, and 4 work TODAY with zero ML models trained. Level 1 (COPER) uses SBERT embeddings for semantic similarity and a knowledge base — not neural network predictions. Level 2 (Hybrid) is the only level that depends on trained ML models, and it's optional. The system defaults to COPER, which produces genuinely useful coaching from experience patterns and pro references.

---

## 4. What Works Today (No Training Needed)

### 4.1 Game Theory Engines

All files in `backend/analysis/`. Nine of ten engines are 100% PyTorch-free (pure NumPy/Pandas/math). They work with raw match data and published CS2 knowledge — no training, no model checkpoints, no GPU.

| Engine | File | Lines | What It Computes | Dependencies |
|--------|------|-------|-----------------|--------------|
| **Bayesian Death Probability** | `belief_model.py` | 485 | P(death \| belief state, HP, armor, weapon class). Log-odds Bayesian update with auto-calibration from historical match data. AdaptiveBeliefCalibrator fits empirical priors. | math, numpy, pandas |
| **Expectiminimax Game Tree** | `game_tree.py` | 515 | Recursive 4-action search with stochastic opponent modeling. OpponentModel learns adaptive action priors via EMA. Transposition table (max 10K entries) memoizes states. Economy-based + side adjustments. | dataclasses, typing |
| **Momentum Tracker** | `momentum.py` | 217 | Psychological momentum multiplier (0.7 tilt → 1.4 hot). Per-streak coefficients: Win +0.05, Loss -0.04. Half-switch resets at rounds 13/16. Time-decaying influence on expected performance. | math, dataclasses |
| **Entropy Analysis** | `entropy_analysis.py` | 182 | Shannon entropy reduction from utility usage. Normalized by max expected delta per type: Smoke 2.5 bits, Molotov 2.0, Flash 1.8, HE 1.5. Thread-safe grid buffer. | threading, numpy |
| **Blind Spot Detection** | `blind_spots.py` | 219 | Compares player actions to game-tree-optimal recommendations. Frequencies times impact ratings rank coaching priorities. Identifies recurring mismatch patterns. | collections, dataclasses |
| **Deception Index** | `deception_index.py` | 244 | Quantifies tactical deception: fake executes, flash/smoke baits, noise generation. Composite weighted index (Rotation Feint 0.40 + Sound Deception 0.35 + Fake Flash 0.25). | numpy, pandas |
| **Engagement Range** | `engagement_range.py` | 441 | Kill distance analysis with named position registry (34 callouts across 7+ maps). Role-specific baseline comparison for engagement classification. | json, math, pathlib |
| **Role Classifier** | `role_classifier.py` | 561 | Player role classification: AWPer, Entry, Support, IGL, Lurker, Flex. Rule-based with optional ML enhancement. Fallback coaching tips per role. | dataclasses, typing |
| **Utility & Economy** | `utility_economy.py` | 404 | Utility efficiency scoring against pro baselines. Molotov: 35 dmg/throw, HE: 25, Flash: 1.2 enemies/throw, Smoke: 0.9 strategic value. Recommendations engine. | numpy, dataclasses |
| **Win Probability** | `win_probability.py` | 318 | 12-feature neural network (64/32 hidden → sigmoid). Xavier initialization. **Uses PyTorch** but inference-only — the trained weights are loaded, not trained by the pipeline. | **torch**, numpy |

**Total: 3,586 lines of game theory code that produces coaching output today.**

The win probability NN is a special case: it's a small, pre-trained model used for real-time round win prediction during replay analysis. It's not part of the RAP/JEPA training pipeline. Its torch dependency is isolated and lightweight.

**What this means for the product:** Every one of these engines produces specific, actionable coaching insights from a single parsed demo. "Your Bayesian death probability spikes to 0.82 when you overpeek apartments on Mirage B site — pros hold from van with 0.35." "Your flash entropy is 0.4 bits below pro baseline — your flashes are predictable." "Your economy decisions in force-buy rounds deviate from game-tree-optimal by 23%." This is genuinely useful coaching. No competitor does this level of mathematical analysis.

### 4.2 COPER Coaching Pipeline

**COPER** (Contextual Operational Performance Enhancement and Review) is the default coaching mode. It does NOT require RAP, JEPA, or any trained neural network.

**How it works** (`backend/knowledge/experience_bank.py`):

1. **Experience Recording** — Every analyzed round creates a `CoachingExperience` record with: map name, round phase, player actions, outcome, and a SBERT embedding of the context string.

2. **Similarity Retrieval** — When generating coaching, COPER embeds the current context and finds similar historical experiences using FAISS (fast path) or brute-force cosine similarity (fallback).

3. **Composite Scoring** (lines 287-298):
   ```
   score = (similarity + hash_bonus + effectiveness_bonus) * confidence
   ```
   - `hash_bonus` = 0.2 for exact context hash match
   - `effectiveness_bonus` = validated effectiveness (0-1) * 0.4
   - `confidence` = clamped [0.1, 1.0], adjusts via EMA per feedback

4. **Pro Reference Integration** — Retrieves matching pro player examples (how pros handled similar situations) from the HLTV statistics database.

5. **RAG Enhancement** — KnowledgeRetriever appends contextual knowledge from `tactical_knowledge.json` (CS2 strategy knowledge base). Non-fatal: if RAG fails, coaching continues without it.

**SBERT dependency:** The ExperienceBank lazy-loads `KnowledgeEmbedder` from `rag_knowledge.py` (line 113 in experience_bank.py). This triggers a ~400 MB download of `all-MiniLM-L6-v2` on first use. If sentence-transformers is unavailable, it falls back to TF-IDF. This is the single heaviest runtime dependency for COPER — and it needs a progress indicator before shipping.

### 4.3 Database Architecture

The tri-database design is production-grade:

| Database | Purpose | Tables | Access Pattern |
|----------|---------|--------|----------------|
| `database.db` (monolith) | Aggregate stats, coaching state, experiences, insights, pro baselines | 18 | Read-heavy with periodic writes from daemons |
| `hltv_metadata.db` | HLTV professional player statistics scraped from hltv.org | Separate | Write-heavy during scraping, read during coaching |
| `match_data/match_*.db` | Per-match tick-level data (positions, actions, state per tick) | 1 per match | Write-once during ingestion, read during analysis |

**WAL mode** enforced on every connection: `PRAGMA journal_mode=WAL`, `busy_timeout=30000`. This allows concurrent reads while a daemon is writing. The LRU engine cache (max 50 connections, OrderedDict eviction) prevents connection exhaustion.

**Atomic upserts** via `INSERT ... ON CONFLICT DO UPDATE` — no TOCTOU races. The data pipeline hardening (Phases 0-7, completed March 2026) added: atomic writes for cache/checkpoints, round-aware position interpolation, NaN/Inf quality gates, pre-training data quality reports, `match_complete` flag for daemon coordination, cascading match deletion with orphan detection, and data lineage tracking.

### 4.4 Data Ingestion Pipeline

The ingestion pipeline (7 steps) converts a raw `.dem` file into queryable match data:

1. **File Detection** — Scanner daemon detects new .dem file via watchdog filesystem events
2. **Stability Check** — File size polled until stable (prevents reading mid-download demos)
3. **Integrity Verification** — CRC/hash check against known corrupt patterns
4. **Demo Parsing** — `demoparser2` extracts tick-level events (positions, kills, utility, economy)
5. **Feature Extraction** — `base_features.py` computes per-player statistics (ADR, K/D, utility effectiveness, etc.)
6. **Vectorization** — `vectorizer.py` converts features to unified feature vectors (METADATA_DIM)
7. **Storage** — Per-match SQLite created, aggregate stats upserted to monolith, `match_complete` flag set

This pipeline works. It has processed 11 professional demos (17.3M tick rows) without data loss. The hardening fixes addressed 40 structural issues. It is production-ready for the v0.1 product.

---

## 5. What Doesn't Work Yet

### 5.1 RAP Coach (The Deferred Architecture)

**Location:** `backend/nn/experimental/rap_coach/` — 11 files, 1,294 lines.

The RAP (Reasoning, Adaptation, Prediction) Coach is a seven-layer neural architecture:

```
Input (METADATA_DIM features)
  │
  ├── RAPPerception (perception.py, 98 lines)
  │     ResNet-style encoder with residual blocks
  │     Output: perception embedding
  │
  ├── RAPMemory (memory.py, 118 lines)
  │     Liquid Time-Constant (LTC) neurons for temporal processing
  │     Hopfield associative memory for pattern retrieval
  │     HARD imports: ncps.torch.LTC, ncps.wirings.AutoNCP, hflayers.Hopfield
  │     Output: memory-enriched context
  │
  ├── RAPStrategy (strategy.py, 80 lines)
  │     Mixture-of-Experts (MoE) for multi-strategy routing
  │     Output: strategy recommendations
  │
  ├── RAPPedagogy (pedagogy.py, 98 lines)
  │     Causal attribution for explainable coaching
  │     Output: human-readable coaching insights with causal explanations
  │
  └── RAPCoachModel (model.py, 155 lines)
        Assembles all layers, routes through forward pass
        Imports: perception, memory, strategy, pedagogy
```

**Training infrastructure:**
- `trainer.py` (135 lines) — RAPTrainer class
- `chronovisor_scanner.py` (407 lines) — Match scanning for RAP analysis

**Why it's deferred:**

1. **Data scarcity:** 11 demos ingested, ~200 available. RAP needs thousands of well-parsed professional demos with varied maps, team compositions, and tactical situations to learn meaningful patterns. With 11 demos, it will memorize, not generalize.

2. **Academic dependencies:** `ncps` (Neural Circuit Policies) and `hflayers` (Hopfield Layers) are niche academic libraries with small maintainer teams. They work, but they're not battle-tested at scale. They are HARD top-level imports in `memory.py` lines 3-6 — not optional, not lazy-loaded.

3. **Unproven value-add:** The game theory engines already produce specific, actionable coaching. RAP would need to demonstrably beat them to justify its complexity. No benchmark exists to prove this.

4. **Training cost:** RAP training is Phase 4 in the training orchestrator. It requires TensorFactory perception tensors (128x128 3-channel maps), which means GPU memory for batch processing of image-like inputs. On a laptop CPU, this is prohibitively slow.

**What "deferred" means:** RAP stays in the codebase, in `backend/nn/experimental/`. It is already gated by `USE_RAP_MODEL=False` (default). The surgery described in Section 7 makes this isolation cleaner — conditional imports, optional dependency group, and graceful degradation at every touch point.

### 5.2 JEPA Pre-Training (Partially Working)

JEPA (Joint-Embedding Predictive Architecture) is the self-supervised pre-training stage. It learns to predict future game states from current ones, without labels. The dry-run (1 epoch) completed with train loss 0.9506, val loss 1.8248, producing `jepa_brain.pt` (3.6 MB).

**Status:** Architecturally sound but undertrained. One epoch on 11 demos is a proof-of-concept, not a trained model. Needs: more epochs (50-100), more data (200+ demos), and val loss convergence (target < 1.0).

**JEPA is NOT deferred.** It's simpler than RAP, has no exotic dependencies (pure PyTorch), and its pre-trained representations can improve COPER coaching even without RAP. Keep JEPA training in the pipeline — just don't pretend it's ready for production coaching yet.

### 5.3 Ghost Player Mode (Requires Trained RAP)

The GhostEngine (`backend/nn/inference/ghost_engine.py`) overlays AI-predicted optimal positions on the tactical viewer. It requires a trained RAP model to predict "where should the player stand."

**Current behavior** (line 35): When `USE_RAP_MODEL=False`, GhostEngine sets `self.model = None` and `self.is_trained = False`. The tactical viewer still works — it just shows player positions without ghost overlay.

**This is acceptable for v0.1.** The tactical viewer is already the flagship feature without ghost mode. Ghost positioning can be advertised as a future feature.

### 5.4 VL-JEPA Concept Explanations (Requires Training)

VL-JEPA (Visual-Language JEPA) extends JEPA with natural language concept descriptions. It would allow the system to explain in words why a particular play was good or bad, using learned visual-semantic associations.

**Status:** Architecture defined but never trained. Depends on JEPA pre-training converging first.

### 5.5 Frontend Stubs

Eight of thirteen screens are `PlaceholderScreen` instances (`apps/qt_app/screens/placeholder.py` lines 11-32). They show a centered title + "Coming Soon" description. The factory function `create_placeholder_screens()` (lines 35-77) creates all 13; real implementations replace 5 of them before registration.

**Sidebar visibility:** Only 7 screens appear in the sidebar navigation (`main_window.py` lines 27-35):
- home, coach, match_history, performance, tactical_viewer — **functional**
- settings, help — **stubs visible in sidebar**

The remaining 6 stubs (wizard, match_detail, profile, user_profile, steam_config, faceit_config) are hidden — only accessible programmatically. A user can't click on them.

**The problem is Settings and Help.** These two stubs are visible in the sidebar. A user clicks "Settings" and sees an empty screen. This screams "unfinished" louder than any other deficiency.

---

# PART II: THE SURGERY

---

## 6. The Dependency Graph

This section traces every dependency chain relevant to the project split. Each chain was verified by reading the actual import statements in the actual source files.

### 6.1 RAP Coach Dependency Chain

```
backend/nn/experimental/rap_coach/model.py
  ├── imports perception.py → torch, torch.nn
  ├── imports memory.py → torch, torch.nn, ncps.torch.LTC, ncps.wirings.AutoNCP, hflayers.Hopfield
  ├── imports strategy.py → torch, torch.nn
  ├── imports pedagogy.py → torch, torch.nn
  └── imports config.py → OUTPUT_DIM, RAP_POSITION_SCALE

backend/nn/experimental/rap_coach/trainer.py
  ├── imports model.py → (entire RAP chain above)
  └── imports torch, torch.nn, torch.optim

backend/nn/training_orchestrator.py (line 67)
  ├── if model_type == "rap":
  │     ├── from core.config import get_setting
  │     ├── if not get_setting("USE_RAP_MODEL", default=False): raise ValueError
  │     └── from backend.nn.experimental.rap_coach.trainer import RAPTrainer
  └── RAP imports are CONDITIONAL — only triggered when model_type="rap"

backend/nn/coach_manager.py (line 884)
  ├── from core.config import get_setting
  ├── if not get_setting("USE_RAP_MODEL", default=False): return disabled dict
  └── Ghost mode / RAP inference code below the guard

backend/nn/inference/ghost_engine.py (line 35)
  ├── from core.config import get_setting
  ├── if not get_setting("USE_RAP_MODEL", default=False):
  │     self.model = None; self.is_trained = False; return
  └── Ghost predictions only computed if model is loaded

apps/qt_app/viewmodels/tactical_vm.py (line 206)
  ├── if not get_setting("USE_RAP_MODEL", default=False): raise RuntimeError
  └── ChronovisorScanner import only triggered if RAP enabled
```

**Verdict:** RAP is already gated at 4 code locations by `USE_RAP_MODEL=False`. The imports are conditional everywhere except `memory.py`, where `ncps` and `hflayers` are hard top-level imports. If these packages are not installed, importing `memory.py` crashes — even if RAP is disabled. This is the single point that needs fixing.

### 6.2 JEPA Dependency Chain

```
backend/nn/jepa_model.py
  └── imports torch, torch.nn (standard PyTorch only)

backend/nn/jepa_trainer.py
  ├── imports jepa_model.py
  ├── imports torch, torch.optim
  └── imports vectorizer.py (METADATA_DIM)

backend/nn/training_orchestrator.py
  └── if model_type in ("jepa", "vl-jepa"):
        from backend.nn.jepa_trainer import JEPATrainer
```

**Verdict:** JEPA is clean. Standard PyTorch only. No exotic dependencies. No ncps, no hflayers. Can run independently of RAP.

### 6.3 Game Theory Engine Dependencies

```
backend/analysis/belief_model.py     → math, numpy, pandas
backend/analysis/blind_spots.py      → collections, dataclasses
backend/analysis/deception_index.py  → numpy, pandas
backend/analysis/engagement_range.py → json, math, pathlib
backend/analysis/entropy_analysis.py → threading, numpy
backend/analysis/game_tree.py        → dataclasses, typing
backend/analysis/momentum.py         → math, dataclasses
backend/analysis/role_classifier.py  → dataclasses, typing
backend/analysis/utility_economy.py  → numpy, dataclasses
backend/analysis/win_probability.py  → torch, numpy (inference only)
```

**Verdict:** Nine of ten engines are pure Python/NumPy. Zero ML pipeline dependencies. The win probability NN uses torch for inference but doesn't participate in the RAP/JEPA training pipeline. These engines are completely standalone.

### 6.4 COPER Coaching Dependencies

```
backend/services/coaching_service.py
  ├── imports experience_bank.py → sqlmodel, numpy (NO torch)
  │     └── lazy imports rag_knowledge.py → sentence_transformers (SBERT)
  │           └── downloads all-MiniLM-L6-v2 (~400 MB) on first use
  ├── imports coaching insights DB models → sqlmodel
  ├── imports generate_corrections() → pure statistical
  └── imports get_ollama_writer() → optional local LLM for polishing text

backend/knowledge/experience_bank.py
  ├── NO torch imports
  ├── Deferred import of KnowledgeEmbedder (line 113)
  ├── FAISS fast-path (if faiss-cpu installed)
  └── Brute-force cosine similarity fallback
```

**Verdict:** COPER has zero dependency on RAP, JEPA, or any trained neural network. Its heaviest dependency is SBERT (sentence-transformers), which is used for semantic embedding of coaching experiences. SBERT is NOT a trained model from this project — it's a pre-trained language model downloaded from HuggingFace.

### 6.5 Frontend ML Dependencies

Of 42 Qt frontend files (screens + viewmodels + widgets), exactly 3 reference ML:

| File | Reference | Nature |
|------|-----------|--------|
| `viewmodels/tactical_vm.py` | Line 206: `get_setting("USE_RAP_MODEL")` | Conditional: only if RAP enabled |
| `viewmodels/coach_vm.py` | References coaching service | Indirect: coaching service handles ML fallback |
| `viewmodels/coaching_chat_vm.py` | References coaching service | Indirect: same fallback chain |

**The other 39 files have zero ML references.** They read from the database and display results. The frontend is 99% database-driven.

### 6.6 TensorFactory Dependencies

```
backend/processing/tensor_factory.py
  ├── Converts game state → PyTorch tensors (128x128 3-channel)
  ├── Used by: training_orchestrator.py (JEPA/RAP training)
  ├── Used by: ghost_engine.py (RAP inference)
  ├── Used by: state_reconstructor.py
  └── NOT used by: game theory engines, COPER, coaching service
```

**Verdict:** TensorFactory is a training/inference utility. It creates the perception tensors that JEPA and RAP consume. It's NOT needed for game theory coaching. For the v0.1 product, it sits idle unless JEPA training is running in the background.

---

## 7. Surgery 1: Isolating RAP

**Goal:** Make RAP a clean optional module that can be absent from the installed environment without affecting any other functionality.

### 7.1 Make ncps/hflayers Imports Conditional

**File:** `backend/nn/experimental/rap_coach/memory.py`
**Current (lines 3-6):**
```python
from ncps.torch import LTC
from ncps.wirings import AutoNCP
from hflayers import Hopfield
```

**Change to:**
```python
try:
    from ncps.torch import LTC
    from ncps.wirings import AutoNCP
    from hflayers import Hopfield
    _RAP_DEPS_AVAILABLE = True
except ImportError:
    LTC = None
    AutoNCP = None
    Hopfield = None
    _RAP_DEPS_AVAILABLE = False
```

**Then in `RAPMemory.__init__`:**
```python
def __init__(self, ...):
    if not _RAP_DEPS_AVAILABLE:
        raise ImportError(
            "RAP memory layer requires 'ncps' and 'hflayers' packages. "
            "Install with: pip install ncps hflayers"
        )
    # ... existing init code
```

**Why:** This prevents import-time crashes when ncps/hflayers are not installed. The error only surfaces when someone actually tries to instantiate RAPMemory — which only happens when `USE_RAP_MODEL=True`.

### 7.2 Verify All USE_RAP_MODEL Guards

Four locations must remain guarded. Verify each:

| File | Line | Guard | Status |
|------|------|-------|--------|
| `training_orchestrator.py` | 67 | `if not get_setting("USE_RAP_MODEL", default=False): raise ValueError` | Correct — prevents RAP training |
| `coach_manager.py` | 884 | `if not get_setting("USE_RAP_MODEL", default=False): return disabled dict` | Correct — prevents RAP inference |
| `ghost_engine.py` | 35 | `if not get_setting("USE_RAP_MODEL", default=False): self.model = None` | Correct — disables ghost overlay |
| `tactical_vm.py` | 206 | `if not get_setting("USE_RAP_MODEL", default=False): raise RuntimeError` | Correct — prevents ChronovisorScanner |

**No changes needed here** — these guards already work. Just verify they haven't been modified during recent refactoring.

### 7.3 Move ncps and hflayers to Optional Dependency Group

**File:** `requirements.txt`

**Current state:** Check if ncps and hflayers are listed. If they are, move them:

**Change:** Remove from main requirements. Add at the bottom:
```
# Optional: RAP Coach experimental architecture
# Install with: pip install -r requirements.txt "ncps>=0.0.7" "hflayers>=1.3.0"
# ncps>=0.0.7,<1.0
# hflayers>=1.3.0,<2.0
```

If using a `pyproject.toml` with extras:
```toml
[project.optional-dependencies]
rap = ["ncps>=0.0.7,<1.0", "hflayers>=1.3.0,<2.0"]
```

**Why:** Users who install the product don't need RAP dependencies. Developers who want to experiment with RAP can install the extras group explicitly.

### 7.4 Update Training Orchestrator Documentation

**File:** `backend/nn/training_orchestrator.py`

Add a docstring at the top of the class clearly stating:
```python
"""
Training Orchestrator — manages JEPA and RAP training phases.

JEPA: Self-supervised pre-training. Always available.
      Requires: torch, numpy, vectorizer.

RAP:  Experimental architecture. Requires USE_RAP_MODEL=True in settings.
      Additional deps: ncps, hflayers (pip install ncps hflayers).
      DEFERRED until data/benchmarks prove value over game theory engines.
"""
```

### 7.5 GhostEngine Graceful Degradation

**File:** `backend/nn/inference/ghost_engine.py`

The current behavior (line 35) already handles the disabled case correctly: sets `self.model = None` and returns. The tactical viewer checks `is_trained` before attempting ghost overlay.

**Verify:** Ensure the tactical viewer screen (`apps/qt_app/screens/tactical_viewer_screen.py`) does NOT crash when GhostEngine has no model. It should simply not render the ghost overlay. Check for `if ghost_engine.is_trained:` guards or equivalent.

### 7.6 Test the Isolation

After making changes in 7.1 and 7.3:

1. Create a clean virtual environment WITHOUT ncps and hflayers
2. Run `python -c "from Programma_CS2_RENAN.backend.nn.experimental.rap_coach.memory import RAPMemory"` — should NOT crash (imports succeed, `_RAP_DEPS_AVAILABLE=False`)
3. Run `python tools/headless_validator.py` — must pass (exit code 0)
4. Start the app — all 5 functional screens must work
5. Verify COPER coaching generates insights without RAP
6. Verify tactical viewer renders without ghost overlay

---

## 8. Surgery 2: Slimming Dependencies

**Goal:** Reduce the installed footprint from ~2.5 GB to ~1.6 GB, eliminate phantom dependencies, and fix platform compatibility.

### 8.1 Default to CPU-Only PyTorch

**File:** `requirements-lock.txt`

**Current (line 6):**
```
--extra-index-url https://download.pytorch.org/whl/cu121
```

This pulls CUDA 12.1 PyTorch (~2.3 GB). For a desktop app targeting gamers who want coaching analysis (not training), CPU-only PyTorch is sufficient.

**Change:** Create two requirement files:

**`requirements-lock-cpu.txt`** (for distribution):
```
--extra-index-url https://download.pytorch.org/whl/cpu
torch==2.5.1+cpu
torchaudio==2.5.1+cpu
torchvision==0.20.1+cpu
```

**`requirements-lock-gpu.txt`** (for developers/power users):
```
--extra-index-url https://download.pytorch.org/whl/cu121
torch==2.5.1+cu121
torchaudio==2.5.1+cu121
torchvision==0.20.1+cu121
```

**Why:** CPU-only PyTorch is ~350 MB vs ~2.3 GB for CUDA. The game theory engines don't use GPU. COPER doesn't use GPU. Only JEPA/RAP training benefits from GPU, and that's a developer activity, not a user activity.

### 8.2 Fix Windows-Only Dependencies

**File:** `requirements-lock.txt`

Three packages lack platform markers and will fail on Linux/macOS:

| Line | Package | Fix |
|------|---------|-----|
| 114 | `pypiwin32==223` | Add `; sys_platform == "win32"` |
| 121 | `pywin32==311` | Add `; sys_platform == "win32"` |
| 122 | `pywin32-ctypes==0.2.3` | Add `; sys_platform == "win32"` |

### 8.3 Remove Legacy Kivy Dependencies from Lock File

**File:** `requirements-lock.txt`

Kivy and KivyMD are in the lock file (line 64: `Kivy==2.3.0`, line 69: `kivymd @ https://github.com/...`) but the frontend has been migrated to PySide6/Qt6. These are dead weight.

**Remove:**
- `Kivy==2.3.0` and all `kivy-deps.*` packages
- `kivymd @ https://github.com/...`
- `Kivy-Garden==0.1.5`

**Warning:** Before removing, verify no code path still imports Kivy. Known coupling: `core/platform_utils.py` line 6 (`from kivy.utils import platform`). Fix this FIRST (see Section 9.5), then remove Kivy deps.

### 8.4 Handle SBERT First-Use Download

**File:** `backend/knowledge/rag_knowledge.py`

**Current behavior:** `sentence_transformers.SentenceTransformer("all-MiniLM-L6-v2")` triggers a ~400 MB download on first use. No progress bar. No warning. The user clicks "Analyze" and nothing happens for 5-10 minutes while the model silently downloads.

**Fix options (choose one):**

**Option A: Progress indicator (recommended)**
```python
import logging
logging.getLogger("sentence_transformers").setLevel(logging.INFO)
# This surfaces download progress to the log, which can be captured by the UI
```
Then add a status signal in the ViewModel that listens for download progress and shows a toast: "Downloading AI language model (400 MB)... This only happens once."

**Option B: Bundle SBERT with the installer**
Pre-download `all-MiniLM-L6-v2` and include it in the PyInstaller bundle under a known cache path. Set `SENTENCE_TRANSFORMERS_HOME` environment variable to point to the bundled model. Adds ~400 MB to installer size but eliminates runtime download.

**Option C: Hash-based fallback (degraded but instant)**
If SBERT download fails or hasn't happened, fall back to TF-IDF vectorization. This produces lower-quality semantic matches but works instantly with zero download.

**Recommendation:** Option A for v0.1 (simplest), with Option C as automatic fallback if download fails.

### 8.5 Verify demoparser2 License

**Package:** `demoparser2` — used to parse CS2 .dem files.

**Action:** Check the package's PyPI page, GitHub repo, or `LICENSE` file. If it's MIT/BSD/Apache — safe. If GPL — must decide: comply with GPL requirements (open-source your distribution) or find an alternative parser. If unlicensed — contact the author or find an alternative.

**This is a BLOCKING task for commercial distribution.** Do not ship a paid product with unverified dependency licenses.

### 8.6 Clean Up PyInstaller Spec

**File:** `packaging/cs2_analyzer_win.spec`

Remove Kivy-related data files and hidden imports:

**Remove from datas (line 27):**
```python
(str(APP_DIR / "apps" / "desktop_app" / "layout.kv"), "Programma_CS2_RENAN/apps/desktop_app"),
```

**Remove from hidden imports (lines 57-70):** All Kivy/KivyMD modules.

**Add to excludes:**
```python
"kivy", "kivymd", "ncps", "hflayers",
```

**Why:** Kivy is no longer used for the frontend. ncps/hflayers are RAP-only and excluded from distribution builds.

---

## 9. Surgery 3: Frontend Cleanup

**Goal:** Transform the frontend from a developer prototype into a shippable Early Access product.

### 9.1 Hide Stub Screens from Sidebar

**File:** `apps/qt_app/main_window.py`

**Current NAV_ITEMS (lines 27-35):**
```python
NAV_ITEMS = [
    ("home", "\u2302", "dashboard"),
    ("coach", "\u2691", "rap_coach_dashboard"),
    ("match_history", "\u2630", "match_history_title"),
    ("performance", "\u2606", "advanced_analytics"),
    ("tactical_viewer", "\u2316", "tactical_analyzer"),
    ("settings", "\u2699", "settings"),
    ("help", "\u2753", "help"),
]
```

**Change to:**
```python
NAV_ITEMS = [
    ("home", "\u2302", "dashboard"),
    ("coach", "\u2691", "rap_coach_dashboard"),
    ("match_history", "\u2630", "match_history_title"),
    ("performance", "\u2606", "advanced_analytics"),
    ("tactical_viewer", "\u2316", "tactical_analyzer"),
]
```

**Why:** Remove "settings" and "help" from the sidebar until they have real implementations. Users don't click Settings to see "Coming Soon." The 6 other stubs are already hidden (programmatic access only).

**Alternative:** Keep Settings visible but implement a minimal version (see 9.3).

### 9.2 Rename "AI Coach" Label

**File:** `assets/i18n/en.json` (and pt.json, it.json)

**Current:** The i18n key "rap_coach_dashboard" implies RAP Coach, which is misleading since RAP is deferred.

**Change:** Rename the label to "AI Coach" or "Coach" without "RAP" in the name. The coaching functionality works through COPER, not RAP. Don't advertise what isn't ready.

### 9.3 Implement Minimal Settings Screen

**Current:** `apps/qt_app/screens/settings_screen.py` is a stub using `PlaceholderScreen`.

**Minimal viable implementation (3-5 days):**

```
Settings Screen
├── Theme Selection (dropdown: CS2, CSGO, CS 1.6)
├── Language Selection (dropdown: English, Portuguese, Italian)
├── Demo Watch Path (file picker + current path display)
├── Pro Demo Path (file picker + current path display)
├── Database Path (read-only display + "Open in Explorer" button)
└── About (version number, build date)
```

**Why only this:** These are the settings users actually need. Don't build HLTV configuration, Steam API integration, or training parameters — those are power-user features for Phase B.

**Implementation notes:**
- ThemeEngine already supports dynamic switching (`apps/qt_app/core/theme_engine.py`)
- Language switching already works via `QtLocalizationManager.retranslate()`
- Demo paths are stored in config and read by the Scanner daemon
- No new backend code needed — just wire existing config getters/setters to UI widgets

### 9.4 Implement Minimal Setup Wizard

**Current:** `apps/qt_app/screens/wizard_screen.py` is a stub.

**Minimal viable implementation (2-3 days):**

```
First-Time Setup Wizard (3 steps)
├── Step 1: Welcome
│     "Welcome to Macena CS2 Coach. This wizard will help you get started."
│     "No data leaves your computer. All analysis is 100% offline."
├── Step 2: Configure Paths
│     Demo Watch Folder: [file picker — default: Steam's CS2 demo directory]
│     Pro Demo Folder: [file picker — for pro reference demos]
├── Step 3: Ready
│     "Setup complete. Drop a .dem file in your watch folder to start."
│     [Start Coaching] button
```

**Trigger:** Show wizard on first launch (check a `first_run_complete` flag in config).

**Why:** Without a wizard, users must manually configure demo paths by editing config files. That's developer-grade UX, not product-grade.

### 9.5 Remove Kivy Coupling from platform_utils.py

**File:** `core/platform_utils.py`

**Current (line 6):**
```python
from kivy.utils import platform
```

**Replace with:**
```python
import sys

def _get_platform() -> str:
    """Platform detection without Kivy dependency."""
    if sys.platform == "win32":
        return "win"
    elif sys.platform == "darwin":
        return "macosx"
    elif sys.platform.startswith("linux"):
        return "linux"
    return sys.platform

platform = _get_platform()
```

**Then remove Kivy from requirements** (see Section 8.3).

**Why:** `kivy.utils.platform` is a simple string constant. It doesn't need the entire Kivy framework. This is the only remaining Kivy coupling in the codebase.

### 9.6 Add Error Toast System

**Current behavior:** When coaching degrades from COPER (Level 1) to Traditional (Level 4), the user sees nothing. They get lower-quality coaching without knowing it.

**Implementation (3-5 days):**

1. **Define notification signal** in `core/app_state.py`:
   ```python
   class AppState(QObject):
       notification_received = Signal(str, str)  # (severity, message)
   ```

2. **Create toast widget** in `apps/qt_app/widgets/toast.py`:
   - Semi-transparent overlay in bottom-right corner
   - Auto-dismiss after 5 seconds
   - Color-coded: info (blue), warning (yellow), error (red)

3. **Emit notifications** from coaching_service.py when fallback occurs:
   ```python
   # In the COPER exception handler (line 256):
   get_state_manager().add_notification(
       "coaching", "WARNING",
       "Advanced coaching unavailable. Using statistical analysis."
   )
   ```

4. **Wire MainWindow** to listen for notifications and display toasts.

**Why:** Users deserve to know the quality level of coaching they're receiving. "Your coaching today is based on statistical analysis" is honest and builds trust.

---

## 10. Surgery 4: Backend Hardening

**Goal:** Fix the six failure scenarios identified in the product viability assessment. Each fix is targeted and independent.

### 10.1 Coaching Generation Timeout

**File:** `backend/services/coaching_service.py`

**Current:** No timeout. If SBERT, FAISS, or Ollama hangs, the UI blocks indefinitely.

**Fix:**
```python
import signal
import threading

def _run_with_timeout(func, args=(), kwargs=None, timeout=30):
    """Run function with timeout. Returns (result, timed_out)."""
    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = func(*args, **(kwargs or {}))
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        return None, True  # Timed out
    if exception[0]:
        raise exception[0]
    return result[0], False
```

Apply to COPER generation (line 113):
```python
_, timed_out = _run_with_timeout(
    self._generate_coper_insights, args=(...), timeout=30
)
if timed_out:
    logger.warning("COPER timed out after 30s, falling back to Traditional")
    # Fall to Level 3/4
```

### 10.2 Ingestion Rate Limiting

**File:** `backend/ingestion/watcher.py`

**Current:** No concurrency limit. 100 simultaneous demos can OOM the system.

**Fix:** Add a semaphore at module level:
```python
_INGESTION_SEMAPHORE = threading.Semaphore(10)  # Max 10 concurrent demos

def _process_demo(path):
    if not _INGESTION_SEMAPHORE.acquire(timeout=60):
        logger.warning("Ingestion queue full. Demo %s will be retried.", path)
        return
    try:
        _do_process_demo(path)
    finally:
        _INGESTION_SEMAPHORE.release()
```

**Why:** A semaphore is simpler than a thread pool refactor and solves the immediate problem. 10 concurrent demos is conservative — a laptop with 16 GB RAM handles this comfortably. Each demo parse uses ~200 MB peak memory.

### 10.3 GPU Detection and User Warning

**File:** `backend/nn/training_orchestrator.py`

**Current:** Training silently falls back to CPU.

**Fix:** Add at the start of `run_training()`:
```python
import torch

if not torch.cuda.is_available():
    logger.warning(
        "No NVIDIA GPU detected. Training will run on CPU and may be "
        "10-50x slower. For faster training, use a machine with an NVIDIA GPU."
    )
    get_state_manager().add_notification(
        "training", "WARNING",
        "Training on CPU (no GPU detected). This will be slow."
    )
```

### 10.4 Make Backup Failure Non-Fatal for Training

**File:** `core/session_engine.py`

**Current (line 358):** When `_backup_failed=True`, Teacher skips training forever with a 5-minute retry loop.

**Change:** Allow training to continue with a warning. The backup protects against data loss during training, but no-backup-and-training is better than no-backup-and-no-training:

```python
if _backup_failed:
    logger.warning(
        "Teacher: backup failed at startup. Training continues WITHOUT backup safety. "
        "Data may be lost if training crashes."
    )
    get_state_manager().add_notification(
        "training", "WARNING",
        "Training running without backup. Consider freeing disk space."
    )
    # Continue to training instead of skipping
```

**Risk assessment:** The worst case is a training crash corrupts the database. But `match_complete` flags and per-match SQLite isolation mean the raw data is safe — only the monolith's training state could be lost, which is recoverable by re-running training.

### 10.5 Storage Quota Warning

**File:** `core/session_engine.py` (in Scanner daemon)

**Add** at the start of each Scanner cycle:
```python
import shutil

def _check_disk_space(path, min_gb=5):
    """Warn if less than min_gb free on the drive containing path."""
    try:
        usage = shutil.disk_usage(path)
        free_gb = usage.free / (1024 ** 3)
        if free_gb < min_gb:
            logger.warning("Low disk space: %.1f GB free on %s", free_gb, path)
            get_state_manager().add_notification(
                "storage", "WARNING",
                f"Low disk space: {free_gb:.1f} GB free. "
                f"Consider deleting old demos or moving data."
            )
    except Exception:
        pass  # Don't crash the scanner over a disk check
```

Call this at the start of `_scanner_daemon_loop()` with the demo watch path.

### 10.6 Ollama Health Check

**File:** `backend/services/coaching_service.py`

**Current:** If Ollama is not running, the `get_ollama_writer().polish()` call hangs or crashes.

**Fix:** Check Ollama availability before calling it:
```python
def _is_ollama_available(timeout=2):
    """Quick check if Ollama is reachable."""
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False
```

If Ollama is unavailable, skip polishing and use raw coaching text. The coaching insight is still valuable without LLM polish.

---

## 11. Surgery 5: Packaging for Distribution

**Goal:** Produce a Windows installer that a non-technical gamer can download, install, and use without encountering developer-oriented errors.

### 11.1 Update PyInstaller Spec for CPU-Only

**File:** `packaging/cs2_analyzer_win.spec`

**Changes:**

1. **Remove Kivy data files** (line 27 — `layout.kv`):
   ```python
   # REMOVE this line:
   # (str(APP_DIR / "apps" / "desktop_app" / "layout.kv"), "Programma_CS2_RENAN/apps/desktop_app"),
   ```

2. **Remove Kivy hidden imports** (lines 57-70):
   ```python
   # REMOVE all kivy.*, kivymd.* entries from hiddenimports
   ```

3. **Add to excludes** (line 126+):
   ```python
   "kivy", "kivymd", "ncps", "hflayers",
   "kivy_deps", "Kivy_Garden",
   ```

4. **Build with CPU-only PyTorch:**
   Before running PyInstaller, install CPU-only PyTorch in the build environment:
   ```bash
   pip install torch==2.5.1+cpu torchvision==0.20.1+cpu torchaudio==2.5.1+cpu \
       --extra-index-url https://download.pytorch.org/whl/cpu
   ```

**Expected bundle reduction:** ~2.5 GB → ~1.3-1.6 GB.

### 11.2 Update Inno Setup Installer

**File:** `packaging/windows_installer.iss`

**Changes:**

1. **Update version number** from `1.0.0` to `0.1.0` (honest Early Access):
   ```ini
   AppVersion=0.1.0-early-access
   ```

2. **Add EULA/disclaimer** for Early Access:
   ```ini
   [Setup]
   LicenseFile=..\LICENSE
   ```

3. **Add post-install note:**
   ```ini
   [Messages]
   FinishedLabel=Macena CS2 Analyzer has been installed.%n%nThis is an Early Access release with 5 screens. More features coming soon.%n%nDrop .dem files in your demo folder to start analyzing.
   ```

### 11.3 Code Signing

**Reality:** A proper EV code signing certificate costs $200-400/year. Self-signed certificates don't bypass Windows SmartScreen.

**Options:**
1. **Self-signed (free):** Users still see SmartScreen warning but can click "More info → Run anyway." Acceptable for Early Access.
2. **OV certificate ($200/year):** Reduces but doesn't eliminate SmartScreen warnings. Requires business verification.
3. **EV certificate ($350-500/year):** Immediate SmartScreen trust. Requires extended business verification.

**Recommendation:** Start with self-signed for v0.1. Document the SmartScreen workaround in the installer's welcome page. Budget for OV certificate when revenue supports it.

### 11.4 Build Verification Checklist

After building the installer:

1. **Install on a clean Windows 10 VM** (no Python, no dev tools)
2. **Launch the application** — verify it opens without errors
3. **Click each sidebar button** — all 5 screens must render (or 7 if Settings implemented)
4. **Drop a .dem file** in the default watch directory
5. **Wait for processing** — verify progress indication in Home screen
6. **Check Coach screen** — verify coaching insights appear
7. **Open Tactical Viewer** — verify map renders (even without demo data, map image should load)
8. **Check process memory** — should stabilize under 1 GB for idle state
9. **Verify no console window** appears (PyInstaller `console=False`)
10. **Uninstall and verify cleanup** — no orphan files in Program Files

---

## 12. Validation Protocol

### 12.1 Automated Validation

After EVERY surgery step, run:

```bash
source /home/renan/.venvs/cs2analyzer/bin/activate
python tools/headless_validator.py
```

**Must exit with code 0.** The validator checks:
- All module imports succeed
- Database schema is consistent
- Config loading works
- No circular import errors
- Key classes can be instantiated

### 12.2 Import Integrity Check

After RAP isolation (Surgery 1), verify no orphan imports:

```bash
python -c "
import importlib
modules = [
    'Programma_CS2_RENAN.backend.analysis.belief_model',
    'Programma_CS2_RENAN.backend.analysis.game_tree',
    'Programma_CS2_RENAN.backend.services.coaching_service',
    'Programma_CS2_RENAN.backend.knowledge.experience_bank',
    'Programma_CS2_RENAN.backend.nn.jepa_model',
    'Programma_CS2_RENAN.backend.nn.training_orchestrator',
    'Programma_CS2_RENAN.apps.qt_app.main_window',
]
for mod in modules:
    try:
        importlib.import_module(mod)
        print(f'OK: {mod}')
    except Exception as e:
        print(f'FAIL: {mod} — {e}')
"
```

All must print `OK`. If any prints `FAIL`, there's an orphan import that depends on a removed module.

### 12.3 Manual Smoke Test Checklist

| # | Action | Expected Result |
|---|--------|-----------------|
| 1 | Launch app | Home screen loads, 5 status cards visible |
| 2 | Click "AI Coach" | Coach screen loads, shows last insights or "No data yet" |
| 3 | Click "Match History" | Shows list of analyzed matches or "No matches" |
| 4 | Click "Your Stats" | Shows performance charts or "Analyze a demo first" |
| 5 | Click "Tactical Analyzer" | Shows map dropdown, map image loads |
| 6 | Drop .dem file in watch folder | Home screen shows processing indicator within 30s |
| 7 | Wait for processing | Match appears in Match History with HLTV rating badge |
| 8 | Click match → Coach | Coaching insights specific to that match appear |
| 9 | Open Tactical Viewer → select match | Player positions render on map |
| 10 | Switch theme (if Settings implemented) | UI redraws with new color palette |
| 11 | Switch language (if Settings implemented) | All labels update to selected language |
| 12 | Close app | No crash, no orphan processes |

### 12.4 Bundle Size Verification

After building with CPU-only PyTorch:

```bash
du -sh dist/Macena_CS2_Analyzer/
```

**Target:** < 1.6 GB. If larger, check for bundled CUDA libraries, duplicate Qt DLLs, or included test files.

### 12.5 Dependency Audit

After all surgeries:

```bash
pip list --format=freeze | wc -l
```

Compare against the 152 locked transitive deps. Should be lower after removing Kivy, ncps, hflayers, and phantom deps.

Check no RAP-only deps are installed in the distribution environment:
```bash
pip show ncps hflayers kivy kivymd 2>&1 | grep -E "^(Name|WARNING)"
```

All should show `WARNING: Package(s) not found`.

---

# PART III: THE PRODUCT

---

## 13. What Ships: The v0.1 Feature Matrix

### What the User Gets

**Macena CS2 Coach v0.1 — Early Access**

A desktop application for Windows that analyzes Counter-Strike 2 demo files and provides personalized coaching insights. Fully offline — no data leaves your computer.

### Feature Matrix

| Feature | Description | Powered By |
|---------|-------------|------------|
| **Demo Analysis** | Drop .dem files in watch folder. Automatic parsing, feature extraction, and statistical analysis. | demoparser2 + data pipeline |
| **AI Coaching Insights** | Personalized coaching based on your play patterns vs. pro baselines. Contextual experience matching. | COPER (Experience Bank + RAG) |
| **Bayesian Death Probability** | "Your death probability spikes to 0.82 when you overpeek here — pros hold from van at 0.35." | belief_model.py |
| **Game Tree Analysis** | Economy decisions, round strategy, optimal action recommendations using expectiminimax search. | game_tree.py |
| **Momentum Tracking** | Psychological momentum score per round. Identifies tilt patterns and hot streaks. | momentum.py |
| **Blind Spot Detection** | Recurring mismatches between your actions and optimal play. Ranked by frequency and impact. | blind_spots.py |
| **Utility Effectiveness** | Flash/smoke/molotov/HE effectiveness compared to pro baselines per map. Shannon entropy scoring. | entropy_analysis.py, utility_economy.py |
| **Engagement Range Analysis** | Kill distance classification vs. pro baselines per role. Named position awareness. | engagement_range.py |
| **Deception Index** | Quantifies your tactical deception (fake executes, sound baits, flash fakes). | deception_index.py |
| **Role Classification** | Automatic role detection (AWPer, Entry, Support, IGL, Lurker, Flex) with role-specific tips. | role_classifier.py |
| **Win Probability** | Real-time round win prediction from 12 match features. | win_probability.py |
| **Performance Dashboard** | Rating trends, per-map statistics, skill radar chart, utility comparison. | Qt charts (6 custom QPainter widgets) |
| **Match History** | Scrollable list with HLTV 2.0 rating badges (green/yellow/red), K/D, ADR, dates. | Database query |
| **Tactical Replay** | 2D pixel-accurate map visualization with real-time player position playback. Timeline scrubbing. | map_widget.py, timeline_widget.py |
| **3 Themes** | CS2 (orange), CSGO (blue-grey), CS 1.6 (green retro). | QSS stylesheets |
| **3 Languages** | English, Portuguese, Italian — all 136 UI strings translated. | i18n JSON + QtLocalizationManager |

### What's NOT Included (And Why That's Fine)

| Feature | Why Not Included | When It Comes |
|---------|-----------------|---------------|
| Ghost Player Overlay | Requires trained RAP model (deferred) | v1.0 (when training proves value) |
| VL-JEPA Concept Explanations | Requires training convergence | v1.0+ |
| Settings UI | Stub — need to implement | v0.2 (Phase B) |
| Setup Wizard | Stub — need to implement | v0.2 (Phase B) |
| Match Detail Screen | Stub — need to wire to data | v0.2 (Phase B) |
| HLTV Live Sync | Requires Docker (user friction) | v0.3 (with documentation) |
| Linux/macOS | Windows-first strategy | Linux v0.3, macOS v1.0+ |
| Steam Auto-Sync | Integration not built | v0.3 |

### Coaching Output Examples

These are the kinds of insights the v0.1 product generates. They come from game theory engines and COPER, not from ML models.

**Example 1: Bayesian Death Probability**
> "In your last 12 rounds on Mirage B site, you overpeek apartments 9 times (75%). Your Bayesian death probability when doing so is 0.82. Professional players holding from van have a death probability of 0.35 in the same situation. Hold van and wait for the peek instead of taking it."

**Example 2: Utility Effectiveness**
> "Your flash effectiveness on Inferno is 0.4 enemies blinded per throw (pro baseline: 1.2). Your smoke placement entropy is 1.1 bits below optimal — your smokes are predictable. Try varying your banana smoke timing."

**Example 3: Economy Optimization**
> "In eco rounds, you force-buy rifles 60% of the time. Game tree analysis shows this is suboptimal — the expected value of saving for a full buy is 23% higher than force-buying in your typical game state."

**Example 4: Blind Spot**
> "You check short A on Dust2 in 89% of rounds but only 12% of kills come from there. Your attention is misallocated. Pro players check long A first in 67% of rounds because the threat probability is 2.3x higher."

---

## 14. The Competition: Honest Assessment

### Feature-by-Feature Comparison

| Feature | Leetify (Free) | Leetify (Pro) | Scope.gg | Refrag | **This Project** |
|---------|---------------|---------------|----------|--------|-----------------|
| **Price** | Free | $5/month | Free + Premium | $10/month | $15-20 one-time |
| **Platform** | Web | Web | Web | Web | Desktop (Windows) |
| **Demo Upload** | Auto (Steam API) | Auto | Manual | Manual | Watch folder (auto) |
| **Basic Stats** | Yes | Yes | Yes | Yes | Yes |
| **Heatmaps** | Yes | Yes | Yes | No | Planned |
| **Round Replay** | No | No | 3D | No | **2D Tactical** |
| **Game Theory** | No | No | No | No | **Yes (9 engines)** |
| **Bayesian Analysis** | No | No | No | No | **Yes** |
| **Personalized Coaching** | Generic tips | Generic tips | Generic | AI suggestions | **Contextual COPER** |
| **Privacy** | Cloud | Cloud | Cloud | Cloud | **100% Offline** |
| **Ghost Player** | No | No | No | No | **Planned (v1.0)** |
| **Mobile App** | Yes | Yes | No | No | No |
| **Team Features** | Yes | Yes | Yes | No | No |
| **Community Size** | 500K+ | 50K+ | 100K+ | 20K+ | 0 |

### Where This Project Wins

1. **Game theory depth.** No competitor runs Bayesian inference, expectiminimax game trees, or Shannon entropy analysis on player demos. This produces coaching insights that are mathematically grounded, not pattern-matched.

2. **Privacy.** 100% offline. No demo upload. No account creation. No tracking. For players who don't want their gameplay data on someone else's server, this is the only option with AI coaching.

3. **One-time purchase.** In a market of monthly subscriptions, a one-time payment is differentiated. Gamers are tired of subscriptions.

4. **Tactical replay.** 2D pixel-accurate map replay with timeline scrubbing. Scope.gg has 3D replay but it's cloud-only. This works offline.

### Where This Project Loses

1. **No auto-sync.** Leetify auto-imports demos from Steam. This project requires manual file placement (or watch folder setup). This is friction.

2. **No community.** Leetify has 500K+ users generating word-of-mouth. This project has zero. Building community takes months of consistent presence on Reddit, Twitter/X, YouTube, and Discord.

3. **No team features.** Team analysis, shared dashboards, coach tools — these are premium features that funded competitors offer. Not feasible for a solo developer in v0.1.

4. **No mobile.** Gamers check stats on their phone. Web-based competitors serve this natively. A desktop-only app misses casual stat-checking.

5. **Incomplete UI.** Even with stubs hidden, 5 screens vs. Leetify's full web dashboard is a narrower experience.

### The Fundamental Strategy

**Compete on depth, not breadth.**

Leetify gives everyone the same generic tips. This project gives each player mathematically specific insights about their specific replays. "Your death probability is 0.82 when you do X" beats "Try positioning better on B site."

The game theory engines are the moat. No competitor has them. No competitor is likely to build them (they're research-level implementations, not features a product team would prioritize). This is a genuine competitive advantage — but only if the coaching output is surfaced clearly and the user understands why it's better than what they can get for free.

---

## 15. Pricing and Distribution

### Recommended Model: Open-Core

**Free Tier (Macena CS2 Coach Community):**
- Game theory analysis (all 9 engines)
- Basic statistics (K/D, ADR, win rate)
- Match history (last 10 matches)
- Role classification with tips

**Paid Tier ($20 one-time, Macena CS2 Coach Pro):**
- COPER AI coaching (Experience Bank + RAG)
- Unlimited match history
- Tactical replay viewer
- Performance trend charts (all 6 custom charts)
- 3 themes + 3 languages
- Future updates (ghost player, VL-JEPA concepts)

**Why open-core:** The free tier proves value. Users see game theory insights, realize they're better than generic tips, and upgrade for the full coaching experience. This builds community (free users talk about the tool) while monetizing power users.

### Distribution Platforms

| Platform | Cut | Audience | Barrier to Entry | Recommendation |
|----------|-----|----------|------------------|----------------|
| **itch.io** | 0-10% (you choose) | Indie gamers, niche tools | None — upload and publish | **Start here** |
| **Gumroad** | 10% | Digital products, indie developers | None — upload and publish | Alternative to itch.io |
| **Steam** | 30% | 130M active gamers | Steamworks approval (~2-4 weeks), $100 app fee | **Phase C target** |
| **GitHub Releases** | 0% | Developers, power users | None | For free tier |
| **Own website** | 0% (+ hosting) | Direct customers | Need payment integration (Stripe/Paddle) | Phase B |

**Recommendation:** Launch on itch.io (zero friction, 0% cut if you choose). Use GitHub Releases for the free tier. Target Steam for v1.0 when the product is feature-complete.

### Revenue Projections (Honest)

| Scenario | Users/Month | Conversion | Price | Monthly Revenue | Annual |
|----------|-------------|------------|-------|-----------------|--------|
| **Pessimistic** | 500 downloads | 2% | $20 | $200 | $2,400 |
| **Realistic** | 2,000 downloads | 3% | $20 | $1,200 | $14,400 |
| **Optimistic** | 5,000 downloads | 5% | $20 | $5,000 | $60,000 |

**Reality check:** These numbers assume active marketing (Reddit posts, YouTube tutorials, Discord community, CS2 content creators). Without marketing, downloads will be near zero. The product doesn't sell itself — you must actively reach the CS2 community.

**Key marketing channels:**
- r/GlobalOffensive and r/cs2 (Reddit)
- CS2 coaching Discord servers
- YouTube: "I built an offline AI CS2 coach" video
- Twitter/X: CS2 pro scene community
- HLTV forums

---

## 16. The User's First 10 Minutes

This walkthrough describes what a new user experiences from download to first coaching insight. Every screen state, loading indicator, and error path is described.

### Minute 0-1: Download and Install

1. User downloads `Macena_CS2_Installer.exe` (1.3-1.6 GB) from itch.io
2. Windows SmartScreen warning: "Windows protected your PC" (no code signing)
3. User clicks "More info → Run anyway"
4. Inno Setup wizard: language selection (EN/PT/IT), install directory, desktop shortcut option
5. Installation completes (~30 seconds on SSD)

### Minute 1-2: First Launch

6. User double-clicks desktop shortcut or Start Menu entry
7. **If Setup Wizard implemented:** Wizard screen appears
   - Step 1: Welcome + privacy promise
   - Step 2: File pickers for demo watch folder and pro demo folder
   - Step 3: "Ready — drop a .dem file to start"
8. **If Wizard NOT implemented:** Home screen appears directly. User must configure paths manually (poor UX — implement the wizard).

### Minute 2-4: Home Screen

9. Home screen shows 5 status cards:
   - Demo Path: configured path or "Not configured"
   - Pro Ingestion: "0 demos ingested" or count
   - Connectivity: system status indicators
   - Tactical Viewer: quick link
   - Training Status: "Idle" or "Training in progress"
10. Scanner daemon begins watching the configured demo folder (if set)
11. User copies a `.dem` file into the watch folder

### Minute 4-6: Processing

12. Scanner detects new file within 10 seconds
13. Home screen updates: "Processing 1 demo..."
14. Digester daemon parses the demo (30-120 seconds depending on demo size)
15. Feature extraction runs (10-30 seconds)
16. Statistics computed and stored in database
17. **First-time SBERT download:** If Experience Bank is used, 400 MB model downloads
    - **With progress indicator (Surgery 8.4):** Toast shows "Downloading AI language model... 67%"
    - **Without progress indicator (current):** UI appears frozen for 5-10 minutes. Very bad UX.
18. COPER coaching generates insights (5-15 seconds after SBERT is available)

### Minute 6-8: Reviewing Results

19. Match appears in Match History with HLTV 2.0 rating badge
20. User clicks match — Coach screen shows insights:
    - "Your ADR of 62 is below pro average (78). Focus on damage consistency."
    - "Bayesian death probability spikes at B site apartments peek — consider holding from van."
    - "Flash effectiveness: 0.4 enemies/throw vs pro 1.2 — practice pop flashes."
21. Performance screen updates: rating sparkline shows first data point, radar chart shows skill distribution

### Minute 8-10: Tactical Viewer

22. User opens Tactical Viewer
23. Selects the just-analyzed match from dropdown
24. 2D map renders with player positions
25. Timeline scrubber allows round-by-round navigation
26. Player dots move in real-time as timeline plays
27. **Ghost overlay NOT available** (RAP deferred) — but player positions, team colors, and utility events all render

### Error Paths

| Error | What User Sees | What Should Happen |
|-------|---------------|-------------------|
| Demo file corrupted | Nothing (current) | Toast: "Demo file could not be parsed. File may be corrupted." |
| Disk full | Nothing (current) | Toast: "Low disk space. Cannot process demo." |
| SBERT download fails | Coaching delayed indefinitely (current) | Toast: "AI model download failed. Using basic analysis mode." + TF-IDF fallback |
| No demos analyzed yet | Empty screens | "Analyze a demo first. Drop a .dem file in your demo folder." |

---

## 17. Cross-Platform Strategy

### Windows-First Rationale

| Platform | CS2 Player Share | Engineering Effort | Business Impact |
|----------|-----------------|-------------------|----------------|
| Windows 10/11 | ~93% | PyInstaller + Inno Setup (exists) | Addresses 93% of market |
| Linux (Ubuntu) | ~3-4% | AppImage packaging (2-4 weeks) | Small but vocal community |
| macOS | ~3% | Notarization + signing + Universal binary (2+ months) | Smallest market, highest effort |

**Decision:** Ship Windows-only for v0.1 and v0.2. Add Linux for v0.3. Defer macOS until revenue justifies Apple Developer Program ($99/year) + engineering investment.

### Windows-Specific Issues to Fix

1. **SmartScreen warning** — Solved with code signing (Section 11.3)
2. **Single-instance mutex** — Already implemented via `ctypes.windll.kernel32.CreateMutexW`
3. **Path handling** — Uses `LOCALAPPDATA` for data storage, registry access for Steam detection

### Linux Prerequisites (for v0.3)

1. Remove Kivy coupling from `platform_utils.py` (Section 9.5)
2. Add platform markers to Windows-only deps (Section 8.2)
3. Replace Windows single-instance mutex with `fcntl.flock()`:
   ```python
   import fcntl
   lock_file = open("/tmp/macena_cs2_analyzer.lock", "w")
   try:
       fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
   except IOError:
       sys.exit("Another instance is already running.")
   ```
4. AppImage build script using `appimagetool`
5. XDG-compliant paths (`~/.local/share/MacenaCS2Analyzer/`)
6. Desktop entry file for application launcher

### macOS Prerequisites (for v1.0+)

1. Apple Developer Program enrollment ($99/year)
2. Code signing with Apple-issued certificate
3. Notarization via `xcrun notarytool submit`
4. Universal binary (Intel x86_64 + Apple Silicon ARM64)
5. `.dmg` installer with drag-to-Applications workflow
6. Entitlements plist for Gatekeeper compliance
7. Test on macOS Ventura+ (minimum supported version)

---

# PART IV: THE FUTURE

---

## 18. When RAP Comes Back

RAP is deferred, not deleted. This section defines the exact conditions under which it should be reactivated.

### Prerequisites (ALL must be met)

1. **Data Threshold:** 200+ professional demos fully ingested and validated. Current: 11 ingested, ~200 available on SSD. The raw data exists — it needs to be processed.

2. **JEPA Convergence:** JEPA pre-training val loss < 1.0 (current: 1.8248 after 1 epoch). This means running 50-100 epochs on the full 200-demo dataset. JEPA pre-trained representations are the foundation RAP builds on.

3. **Baseline Model Benchmark:** A simple 2-layer MLP trained on JEPA representations can distinguish good rounds from bad rounds (AUC > 0.7 on held-out matches). This proves the pre-trained features capture meaningful game patterns.

4. **RAP Incremental Value:** RAP Coach, trained on the same data, produces coaching insights that a panel of 3 players (Gold Nova, MG, Faceit Level 6+) rate as more useful than COPER+game-theory coaching. This is the critical benchmark — RAP must BEAT the existing system to justify its complexity.

5. **GPU Availability:** RAP training with TensorFactory perception tensors (128x128x3) requires GPU memory. Minimum: NVIDIA GPU with 6 GB VRAM. Without GPU, RAP training on 200 demos would take weeks on CPU.

### Activation Steps

When all prerequisites are met:

1. Install RAP dependencies: `pip install ncps hflayers`
2. Set `USE_RAP_MODEL=True` in config
3. Run training orchestrator with `model_type="rap"`
4. Monitor training metrics: train loss should decrease monotonically, val loss should follow with expected gap
5. When training converges, `rap_coach.pt` checkpoint is saved
6. GhostEngine automatically loads the checkpoint and enables ghost overlay
7. Tactical viewer shows ghost player positions (where RAP thinks you should stand)

### What RAP Adds (When It Works)

- **Ghost Player Positioning:** AI-predicted optimal positions overlaid on the tactical viewer. "Stand here, not there."
- **Temporal Pattern Recognition:** LTC neurons capture time-dependent patterns (rotation timings, peek intervals, reaction time evolution throughout a match).
- **Associative Memory:** Hopfield network stores and retrieves similar tactical situations from pro matches. "In 847 pro rounds with this economy and map control, 73% of pros executed B."
- **Causal Attribution:** Pedagogy layer explains WHY a recommendation is made, not just WHAT the recommendation is.
- **Mixture-of-Experts Strategy:** Different strategy heads activate for different situations (eco rounds vs. gun rounds, retake vs. hold, clutch vs. team play).

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| ncps/hflayers become unmaintained | Medium | High — must fork or replace | Pin versions, keep fork-ready |
| RAP doesn't beat game theory + COPER | Medium | Low — game theory still ships | Benchmark before shipping RAP |
| GPU requirement excludes laptop users | High | Medium — most gamers have GPUs | Offer CPU fallback (slower) |
| Training requires hyperparameter tuning | Certain | Medium — time investment | Document tuning process |

---

## 19. The 6-Month Roadmap

### Month 1: Ship v0.1 Early Access

**Week 1-2: Surgery**
- [ ] Surgery 1: Isolate RAP (conditional imports, optional deps)
- [ ] Surgery 2: Slim dependencies (CPU PyTorch, remove Kivy, fix platform markers)
- [ ] Surgery 3: Hide stub screens, implement minimal Settings
- [ ] Surgery 4: Add coaching timeout, ingestion rate limit, GPU warning
- [ ] Surgery 5: Update PyInstaller spec, build CPU-only installer

**Week 3: Polish**
- [ ] Setup Wizard (3 steps, first-time path configuration)
- [ ] Error toast system (coaching degradation, disk space, processing status)
- [ ] SBERT download progress indicator
- [ ] README for users (install guide, first steps, FAQ)

**Week 4: Launch**
- [ ] Test on clean Windows VM (10 smoke tests)
- [ ] Verify demoparser2 license
- [ ] Upload to itch.io
- [ ] Post on Reddit (r/GlobalOffensive): "I built an offline AI CS2 coach"
- [ ] Create Discord server for user feedback

**Deliverable:** `Macena_CS2_Installer_v0.1.exe` on itch.io, $15-20.

### Month 2: v0.2 — Settings, Wizard, Match Detail

- [ ] Full Settings screen (theme, language, paths, about)
- [ ] Match Detail screen wired to backend data
- [ ] Ingest 50 more pro demos (total: 60+)
- [ ] User feedback triage — fix top 5 reported issues
- [ ] Ollama health check (don't hang if LLM unavailable)
- [ ] Add demo processing progress to Home screen

**Deliverable:** v0.2 update, user base growing.

### Month 3: Training and Quality

- [ ] Ingest remaining ~150 pro demos (total: 200+)
- [ ] Run JEPA training: 50 epochs, target val loss < 1.0
- [ ] Benchmark coaching output: survey 5-10 users on coaching value
- [ ] Test coverage to 40%+
- [ ] Linux single-instance mutex
- [ ] Begin AppImage packaging investigation

**Deliverable:** Trained JEPA model, coaching quality benchmark.

### Month 4: RAP Evaluation and Community

- [ ] If JEPA converged: train baseline MLP, measure AUC
- [ ] If MLP AUC > 0.7: attempt RAP training (requires GPU)
- [ ] If RAP produces useful coaching: plan ghost overlay integration
- [ ] If RAP underperforms: defer further, focus on game theory refinement
- [ ] Build Discord community (target: 100 active members)
- [ ] YouTube tutorial: "How to improve at CS2 using Macena Coach"
- [ ] Complete remaining screens: Player Profile, Help

**Deliverable:** RAP go/no-go decision. Community established.

### Month 5: v1.0 Launch

- [ ] All 13 screens functional (no stubs)
- [ ] Linux AppImage packaging
- [ ] Test coverage to 50%+
- [ ] User guide documentation
- [ ] If RAP approved: ghost player overlay in Tactical Viewer
- [ ] Performance optimization (startup time < 5 seconds)
- [ ] Code signing (OV certificate if revenue supports it)

**Deliverable:** v1.0 on itch.io + GitHub Releases. Windows + Linux.

### Month 6: Steam and Growth

- [ ] Submit to Steam ($100 app fee, Steamworks setup)
- [ ] Steam store page with screenshots, description, trailer
- [ ] Explore SDK licensing for game theory engines
- [ ] Evaluate open-core split (free community edition vs. paid pro)
- [ ] FaceIT/Steam API integration for auto-import
- [ ] Revenue goal: $1,000/month recurring

**Deliverable:** Steam submission. Revenue stream established.

### What This Roadmap Assumes

1. **Full-time effort** (8+ hours/day, 5-6 days/week). If part-time, multiply timelines by 2-3x.
2. **No catastrophic technical debt.** The pipeline hardening (Phases 0-7) addressed the major structural issues.
3. **Active marketing.** The product won't sell itself. Reddit, Discord, YouTube presence required.
4. **User feedback drives priorities.** If users report that coaching insights are useless, pivot before adding features.
5. **GPU access for RAP training.** If no GPU is available, RAP stays deferred until one is.

### What Could Go Wrong

| Risk | Impact | Probability | Response |
|------|--------|------------|----------|
| No users download v0.1 | No revenue, no feedback | Medium | More aggressive marketing, free tier |
| Users say coaching is useless | Product fails | Low | Game theory engines are specific — if worded clearly, they add value |
| demoparser2 license is GPL | Can't sell proprietary | Medium | Fork or find alternative parser |
| SBERT download blocks users | Bad first impression, refunds | High | Bundle SBERT or implement TF-IDF fallback |
| CS2 major update breaks demo format | Parser stops working | Low-Medium | demoparser2 community updates quickly |
| Competitor launches offline tool | Market stolen | Low | First-mover advantage with game theory |

---

## 20. Final Verdict

### Is This a Product?

Yes, but a narrow one first. The v0.1 release is five screens and nine game theory engines delivering coaching that no competitor offers. It is not a complete CS2 coaching platform — it is a specialized tool for players who want mathematically rigorous analysis of their specific replays, entirely offline. That narrowness is a feature, not a bug. A focused tool that does five things brilliantly beats a sprawling tool that does twenty things poorly.

The engineering foundation is real. The tri-database architecture handles 17.3 million tick rows without performance issues. The four-daemon coordination system processes demos reliably. The COPER coaching pipeline delivers four levels of fallback — the system never outputs zero coaching. The custom QPainter charts look professional. The three themes and three languages are complete. This is not a prototype duct-taped together — it's a well-architected system that happens to be incomplete.

### Can It Compete?

Only through depth. Leetify has 500,000 users, a funded team, and a polished web dashboard. Scope.gg has 3D replay and heatmaps. Refrag has AI suggestions with cloud processing. A solo developer cannot beat them at their game. But a solo developer can build something they will never build: offline Bayesian death probability estimation that tells a player "your death rate when peeking this angle is 82%, pros hold from van at 35%." Expectiminimax game trees that compute the optimal economic decision for each round given the player's specific situation. Shannon entropy analysis that quantifies how predictable a player's utility usage is compared to professional baselines.

These are not features that a product team at a funded startup would prioritize. They are too niche, too mathematical, too hard to explain in a marketing screenshot. But for the player who wants to actually understand why they keep dying in the same spot, why their economy decisions cost them rounds, why their flashes never seem to work — this analysis is transformative. And it works today. No training needed. No GPU required. No cloud upload.

### What's the Single Most Important Thing to Do Next?

Ship v0.1. Today's perfect is tomorrow's obsolete. The game theory engines work. The coaching pipeline works. Five screens are functional. An installer exists. The stubs can be hidden in one line change. The CPU-only PyTorch cut can be made in one build configuration change. The remaining surgeries are important but not blocking — they make the product better, not possible.

The longer this stays on a development laptop, the more likely it is that: a competitor launches a similar offline tool, CS2 updates break the demo parser, or the developer burns out trying to perfect something that no one has ever used. Ship the imperfect product, get real user feedback, and iterate. The feedback from 10 real users is worth more than 10 more features built in isolation.

The RAP Coach is beautiful architecture. It deserves data, training, and benchmarking. It will get those things — after the product has users, after the game theory engines have proven the concept, after the JEPA pre-training has converged. Not before.

Ship. Learn. Iterate. That is the plan.

---

> **Document version:** 1.0
> **Word count:** ~11,000
> **Files referenced:** 47
> **Line numbers cited:** 78
> **Coaching output examples:** 4
> **Failure scenarios addressed:** 10
> **Surgery steps defined:** 42
> **Roadmap milestones:** 36
