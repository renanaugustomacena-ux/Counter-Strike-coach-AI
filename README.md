# Macena CS2 Analyzer

[![CI Pipeline](https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI/actions/workflows/build.yml/badge.svg)](https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI/actions/workflows/build.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Proprietary%20%7C%20Apache--2.0-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-313%20validator%20%7C%201794%20pytest-brightgreen.svg)]()

**AI-Powered Tactical Coach for Counter-Strike 2**

> **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

---

## What Is It?

Macena CS2 Analyzer is a desktop application that serves as your personal AI coach for Counter-Strike 2. It analyzes professional and user demo files, trains multiple neural network models, and delivers personalized tactical coaching by comparing your gameplay to professional standards.

The system learns from the best professional matches ever played and adapts its coaching to your individual playstyle — whether you are an AWPer, entry fragger, support, or any other role. The coaching pipeline fuses machine learning predictions with retrieved tactical knowledge, game-theory-based analysis, and Bayesian belief modeling to produce actionable, context-aware advice.

Unlike static coaching tools with pre-written tips, this system builds its intelligence from real professional gameplay data. On first boot the neural networks have random weights and zero tactical knowledge. Every demo you feed it makes the coach smarter, more nuanced, and more personalized.

---

## Table of Contents

- [Key Features](#key-features)
- [System Requirements](#system-requirements)
- [Quick Start](#quick-start)
- [Architectural Overview](#architectural-overview)
- [Supported Maps](#supported-maps)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Entry Points](#entry-points)
- [Validation and Quality](#validation-and-quality)
- [Multi-Language Support](#multi-language-support)
- [Security Features](#security-features)
- [System Maturity](#system-maturity)
- [Documentation](#documentation)
- [Feeding the Coach](#feeding-the-coach)
- [Troubleshooting](#troubleshooting)
- [Complete Documentation Index](#complete-documentation-index)
- [License](#license)
- [Author](#author)

---

## Key Features

### AI Coaching Pipeline

- **4-Level Fallback Chain** — COPER > Hybrid > RAG > Base, ensuring the system always produces useful advice regardless of model maturity
- **COPER Experience Bank** — Stores and retrieves past coaching experiences weighted by recency, effectiveness, and context similarity
- **RAG Knowledge Base** — Retrieval-Augmented Generation with professional reference patterns and tactical knowledge
- **Ollama Integration** — Optional local LLM for natural-language refinement of coaching insights
- **Causal Attribution** — Every coaching recommendation includes a "why" explanation traceable to specific gameplay decisions

### Neural Network Subsystems

- **RAP Coach** — 7-layer architecture combining perception, memory (LTC-Hopfield), strategy (Mixture-of-Experts with superposition), pedagogy (value function), position prediction, causal attribution, and output aggregation
- **JEPA Encoder** — Joint-Embedding Predictive Architecture for self-supervised pre-training with InfoNCE contrastive loss and EMA target encoder
- **VL-JEPA** — Vision-Language extension with 16 tactical concept alignment (positioning, utility, economy, engagement, decision, psychology)
- **AdvancedCoachNN** — LSTM + Mixture-of-Experts architecture for coaching weight prediction
- **Neural Role Head** — 5-role MLP classifier (entry, support, lurk, AWP, anchor) with KL-divergence and consensus gating
- **Bayesian Belief Models** — Opponent mental state tracking with adaptive calibration from match data

### Demo Analysis

- **Tick-Level Parsing** — Every tick of `.dem` files is analyzed via demoparser2, preserving full game state (no tick decimation)
- **HLTV 2.0 Rating** — Calculated per match using the official HLTV 2.0 formula (kills, deaths, ADR, KAST%, survival, flash assists)
- **Round-by-Round Breakdown** — Economy timeline, engagement analysis, utility usage, momentum tracking
- **Temporal Baseline Decay** — Tracks player skill evolution over time with exponential decay weighting

### Game-Theory Analysis

- **Expectiminimax Trees** — Game-theoretic decision evaluation for strategic scenarios
- **Bayesian Death Probability** — Estimates survival likelihood based on position, equipment, and enemy state
- **Deception Index** — Quantifies positional unpredictability relative to professional baselines
- **Engagement Range Analysis** — Maps weapon selection against engagement distance distributions
- **Win Probability** — Real-time win probability calculation
- **Momentum Tracking** — Round-by-round confidence and performance trajectory

### Desktop Application

- **Qt Desktop Application** — PySide6/Qt frontend (primary) with MVVM pattern. Legacy Kivy/KivyMD retained for reference only
- **2D Tactical Viewer** — Real-time demo replay with player positions, kill events, bomb indicators, and AI ghost predictions
- **Match History** — Scrollable match list with color-coded ratings
- **Performance Dashboard** — Rating trends, per-map stats, strength/weakness analysis, utility breakdown
- **Coach Chat** — Interactive AI conversation with quick-action buttons and free-text questions
- **User Profile** — Steam integration with automatic match import
- **3 Visual Themes** — CS2 (orange), CS:GO (blue-grey), CS 1.6 (green) with rotating wallpapers

### Training and Automation

- **4-Daemon Session Engine** — Scanner (file discovery), Digester (demo processing), Teacher (model training), Pulse (health monitoring)
- **3-Stage Maturity Gating** — CALIBRATING (0-49 demos, 0.5x confidence) > LEARNING (50-199, 0.8x) > MATURE (200+, full)
- **Conviction Index** — 5-signal composite tracking belief entropy, gate specialization, concept focus, value accuracy, and role stability
- **Auto-Retraining** — Training triggers automatically at 10% growth in demo count
- **Drift Detection** — Z-score-based feature drift monitoring with automatic retraining flag
- **Coach Introspection Observatory** — TensorBoard integration with maturity state machine, embedding projector, and conviction tracking

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 / Ubuntu 22.04 | Windows 10/11 |
| Python | 3.10 | 3.10 or 3.12 |
| RAM | 8 GB | 16 GB |
| GPU | None (CPU mode) | NVIDIA GTX 1650+ (CUDA 12.1) |
| Disk | 3 GB free | 5 GB free |
| Display | 1280x720 | 1920x1080 |

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI.git
cd Counter-Strike-coach-AI
```

### 2. Automated Setup (Windows)

```powershell
.\scripts\Setup_Macena_CS2.ps1
```

Creates a virtual environment, installs all dependencies, initializes the database, and configures Playwright for HLTV scraping.

**For NVIDIA GPU support**, after the script completes:

```powershell
.\venv_win\Scripts\pip.exe install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 3. Manual Setup (Windows)

```powershell
python -m venv venv_win
.\venv_win\Scripts\activate

# PyTorch (choose ONE):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu       # CPU only
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121     # NVIDIA GPU

pip install -r requirements.txt
python -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database()"
pip install playwright && python -m playwright install chromium
```

### 4. Manual Setup (Linux)

```bash
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev libsdl2-dev libglew-dev build-essential

python3.10 -m venv venv_linux
source venv_linux/bin/activate

# PyTorch (choose ONE):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu       # CPU only
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121     # NVIDIA GPU

pip install -r requirements.txt
python -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database()"
pip install playwright && python -m playwright install chromium
```

### 5. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Steam API key and preferences (see comments in file)
```

### 6. Verify Installation

```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import PySide6; print(f'PySide6: {PySide6.__version__}')"
python -c "from Programma_CS2_RENAN.backend.nn.config import get_device; print(f'Device: {get_device()}')"
```

### 7. Optional: Pro Coaching Baseline

To build coaching baselines from professional match data, two additional components are needed:

**Docker + FlareSolverr** (for automated HLTV pro stats scraping):

```bash
# Install Docker Desktop: https://docs.docker.com/desktop/
# Then start FlareSolverr:
docker compose up -d
```

FlareSolverr bypasses Cloudflare protection on hltv.org. Without it, the Hunter daemon cannot scrape professional player statistics. You can still use the coach with your own demo files — pro baselines enhance coaching quality but are not required.

**RAP Coach dependencies** (optional experimental architecture):

```bash
pip install -r requirements-rap.txt
```

Required only if you enable `USE_RAP_MODEL=True` in settings. The default JEPA model works without these.

### 8. Launch

```bash
# Desktop application (Qt GUI — recommended)
./launch.sh

# Or manually:
python -m Programma_CS2_RENAN.apps.qt_app.app

# Interactive console (live TUI with real-time panels)
python console.py

# One-shot CLI (build, test, audit, hospital, sanitize)
python goliath.py
```

> For the complete guide with API configuration, feature walkthroughs, and troubleshooting, see the [User Guide](docs/guides/USER_GUIDE.md).

---

## Architectural Overview

### WATCH > LEARN > THINK > SPEAK Pipeline

The system is organized as a 4-stage pipeline that transforms raw demo files into personalized coaching:

```
WATCH (Ingestion)      LEARN (Training)       THINK (Inference)       SPEAK (Dialogue)
  Scanner Daemon         Teacher Daemon         COPER Pipeline          Template + Ollama
  Demo parsing           3-stage maturity       RAG Knowledge           Causal attribution
  Feature extraction     Multi-model training   Game theory             Pro comparisons
  Tick storage           Drift detection        Belief modeling         Severity scoring
```

**WATCH** — The Scanner daemon continuously monitors configured demo folders for new `.dem` files. When found, the Digester daemon parses every tick using demoparser2, extracts the canonical 25-dimensional feature vector, calculates HLTV 2.0 ratings, and stores everything in per-match SQLite databases.

**LEARN** — The Teacher daemon automatically trains neural models when sufficient data accumulates. Training progresses through 3 maturity stages (CALIBRATING > LEARNING > MATURE). Multiple architectures train in parallel: JEPA for self-supervised representation learning, RAP Coach for tactical decision modeling, NeuralRoleHead for player role classification.

**THINK** — At inference time, the COPER pipeline combines neural predictions with retrieved coaching experiences, RAG knowledge, and game-theory analysis. A 4-level fallback chain (COPER > Hybrid > RAG > Base) ensures advice is always available regardless of model maturity.

**SPEAK** — Final coaching output is formatted with severity levels, causal attribution ("why this advice"), and optionally refined through a local Ollama LLM for natural language quality.

### 4-Daemon Session Engine

| Daemon | Role | Trigger |
|--------|------|---------|
| **Scanner (Hunter)** | Discovers new `.dem` files in configured folders | Periodic scan or file watcher |
| **Digester** | Parses demos, extracts features, calculates ratings | New file detected by Scanner |
| **Teacher** | Trains neural models on accumulated data | 10% growth threshold in demo count |
| **Pulse** | Health monitoring, drift detection, system state | Continuous background |

### COPER Coaching Pipeline

COPER (Coaching via Organized Pattern Experience Retrieval) is the primary coaching engine. It operates a 4-level fallback chain:

1. **COPER Mode** — Full pipeline: Experience Bank retrieval + RAG knowledge + neural model predictions + professional comparisons. Requires trained models.
2. **Hybrid Mode** — Combines neural predictions with template-based advice when some models are still calibrating.
3. **RAG Mode** — Pure retrieval: searches for relevant coaching patterns in the knowledge base without neural inference. Works with ingested demos alone.
4. **Base Mode** — Template-based advice from statistical analysis (mean/std deviations from professional baselines). Works immediately.

### Neural Network Architectures

**RAP Coach (7-Layer Architecture)**

The RAP (Reasoning, Attribution, Prediction) Coach is the primary neural model. Its 7 layers process gameplay data through a cognitive pipeline:

| Layer | Function | Details |
|-------|----------|---------|
| 1. Perception | Visual + spatial encoding | Conv layers for view frame (64d), map state (32d), movement diff (32d) -> 128d |
| 2. Memory | Recurrent belief tracking | LSTM + Hopfield network for associative memory. Input: 153d (128 perception + 25 metadata) -> 256d hidden state |
| 3. Strategy | Decision optimization | Mixture-of-Experts with superposition for context-dependent decisions. 10 action weights |
| 4. Pedagogy | Value estimation | V-function estimation with skill vector integration |
| 5. Position | Optimal placement | Predicts (dx, dy, dz) delta to optimal position (scale: 500 world units) |
| 6. Attribution | Causal diagnosis | 5-dimensional attribution explaining decision drivers |
| 7. Output | Aggregation | advice_probs, belief_state, value_estimate, gate_weights, optimal_pos, attribution |

**JEPA (Joint-Embedding Predictive Architecture)**

Self-supervised pre-training with:
- Context encoder + predictor -> predicts target embedding
- Target encoder updated via EMA (momentum 0.996)
- InfoNCE contrastive loss with in-batch negatives
- Latent dimension: 128

**VL-JEPA (Vision-Language Extension)**

Extends JEPA with 16 tactical concept alignment:
- Concepts: positioning (3), utility (2), economy (2), engagement (4), decision (2), psychology (3)
- Concept alignment loss + diversity regularization
- Outcome-based labeling from RoundStats (kills, deaths, equipment, round result)

**Other Models:**
- **AdvancedCoachNN** — LSTM (hidden=128) + Mixture-of-Experts (4 experts, top-k=2) for coaching weight prediction
- **NeuralRoleHead** — 5-role MLP classifier with KL-divergence gating and consensus voting
- **RoleClassifier** — Lightweight role detection from tick features

### 25-Dimensional Feature Vector

Every game tick is represented as a canonical 25-dimensional vector (`METADATA_DIM=25`):

| Index | Feature | Range | Description |
|-------|---------|-------|-------------|
| 0 | health | [0, 1] | HP / 100 |
| 1 | armor | [0, 1] | Armor / 100 |
| 2 | has_helmet | {0, 1} | Helmet equipped |
| 3 | has_defuser | {0, 1} | Defuse kit |
| 4 | equipment_value | [0, 1] | Normalized equipment cost |
| 5 | is_crouching | {0, 1} | Crouching stance |
| 6 | is_scoped | {0, 1} | Scoped weapon active |
| 7 | is_blinded | {0, 1} | Flash effect |
| 8 | enemies_visible | [0, 1] | Visible enemy count (normalized) |
| 9-11 | pos_x, pos_y, pos_z | [-1, 1] | World coordinates (per-map normalized) |
| 12-13 | view_yaw_sin, view_yaw_cos | [-1, 1] | View angle (cyclic encoding) |
| 14 | view_pitch | [-1, 1] | Vertical view angle |
| 15 | z_penalty | [0, 1] | Vertical distinctiveness (multi-level maps) |
| 16 | kast_estimate | [0, 1] | Kill/Assist/Survive/Trade ratio |
| 17 | map_id | [0, 1] | Deterministic map hash (MD5-based) |
| 18 | round_phase | {0, .33, .66, 1} | Pistol / Eco / Force / Full buy |
| 19 | weapon_class | [0, 1] | Knife=0, Pistol=.2, SMG=.4, Rifle=.6, Sniper=.8, Heavy=1 |
| 20 | time_in_round | [0, 1] | Seconds / 115 |
| 21 | bomb_planted | {0, 1} | Bomb planted flag |
| 22 | teammates_alive | [0, 1] | Count / 4 |
| 23 | enemies_alive | [0, 1] | Count / 5 |
| 24 | team_economy | [0, 1] | Team average money / 16000 |

### 3-Stage Maturity Gating

Models progress through maturity gates based on ingested demo count:

| Stage | Demo Count | Confidence | Behavior |
|-------|-----------|------------|----------|
| **CALIBRATING** | 0-49 | 0.5x | Base coaching, advice marked as provisional |
| **LEARNING** | 50-199 | 0.8x | Intermediate, growing reliability |
| **MATURE** | 200+ | 1.0x | Full confidence, all subsystems contribute |

A parallel **Conviction Index** (0.0-1.0) tracks 5 neural signals: belief entropy, gate specialization, concept focus, value accuracy, and role stability. States: DOUBT (<0.30) > LEARNING (0.30-0.60) > CONVICTION (>0.60 stable for 10+ epochs) > MATURE (>0.75 stable for 20+ epochs). A sharp drop >20% triggers the CRISIS state.

---

## Supported Maps

The system supports all 9 competitive Active Duty maps with pixel-accurate coordinate mapping:

| Map | Type | Calibration |
|-----|------|-------------|
| de_mirage | Single level | pos (-3230, 1713), scale 5.0 |
| de_inferno | Single level | pos (-2087, 3870), scale 4.9 |
| de_dust2 | Single level | pos (-2476, 3239), scale 4.4 |
| de_overpass | Single level | pos (-4831, 1781), scale 5.2 |
| de_ancient | Single level | pos (-2953, 2164), scale 5.0 |
| de_anubis | Single level | pos (-2796, 3328), scale 5.22 |
| de_train | Single level | pos (-2477, 2392), scale 4.7 |
| de_nuke | **Multi-level** | pos (-3453, 2887), scale 7.0, Z-cutoff -495 |
| de_vertigo | **Multi-level** | pos (-3168, 1762), scale 4.0, Z-cutoff 11700 |

Multi-level maps (Nuke, Vertigo) use Z-axis cutoffs to separate upper and lower levels for accurate 2D rendering. The z_penalty feature (index 15) in the feature vector captures vertical distinctiveness for these maps.

---

## Technology Stack

### Core Dependencies

| Category | Package | Version | Purpose |
|----------|---------|---------|---------|
| **ML Framework** | PyTorch | Latest | Neural network training and inference |
| **Recurrent Networks** | ncps | Latest | Liquid Time-Constant (LTC) networks |
| **Associative Memory** | hopfield-layers | Latest | Hopfield network layers for memory |
| **Demo Parsing** | demoparser2 | 0.40.2 | Tick-level CS2 demo file parsing |
| **UI Framework (primary)** | PySide6 | 6.8+ | Qt-based cross-platform desktop GUI |
| **UI Framework (legacy)** | Kivy + KivyMD | 2.3.0 / 1.2.0 | Legacy reference only |
| **Database ORM** | SQLAlchemy + SQLModel | Latest | Database models and queries |
| **Migrations** | Alembic | Latest | Database schema migrations |
| **Web Scraping** | Playwright | 1.57.0 | Headless browser for HLTV |
| **HTTP Client** | HTTPX | 0.28.1 | Async HTTP requests |
| **Data Science** | NumPy, Pandas, SciPy, scikit-learn | Latest | Numerical computation and analysis |
| **Visualization** | Matplotlib | Latest | Chart generation |
| **Graphs** | NetworkX | Latest | Graph-based analysis |
| **Security** | cryptography | 46.0.3 | Credential encryption |
| **TUI** | Rich | 14.2.0 | Terminal UI for console mode |
| **API** | FastAPI + Uvicorn | 0.40.0 | Internal API server |
| **Validation** | Pydantic | Latest | Data validation and settings |
| **Testing** | pytest + pytest-cov + pytest-mock | 9.0.2 | Test framework and coverage |
| **Packaging** | PyInstaller | 6.17.0 | Binary distribution |
| **Templating** | Jinja2 | 3.1.6 | Template rendering for reports |
| **HTML Parsing** | BeautifulSoup4 + lxml | 4.12.3 | Web content extraction |
| **Config** | PyYAML | 6.0.3 | YAML configuration files |
| **Images** | Pillow | 12.0.0 | Image processing |
| **Keyring** | keyring | 25.6.0 | Secure credential storage |

---

## Project Structure

```
Counter-Strike-coach-AI/
|
+-- Programma_CS2_RENAN/                Main application package
|   +-- apps/
|   |   +-- qt_app/                     PySide6/Qt GUI (primary, MVVM + Signals)
|   |   |   +-- app.py                  Qt entry point
|   |   |   +-- main_window.py          QMainWindow with sidebar navigation
|   |   |   +-- core/                   AppState singleton, ThemeEngine, Worker pattern
|   |   |   +-- screens/               13 screens (home, tactical viewer, match history,
|   |   |   |                           match detail, performance, coach, settings,
|   |   |   |                           wizard, help, profile, steam/faceit config)
|   |   |   +-- viewmodels/            Signal-driven ViewModels (QObject + Signal/Slot)
|   |   |   +-- widgets/               Charts (radar, momentum, economy, sparkline),
|   |   |                               tactical (map widget, player sidebar, timeline)
|   |   +-- desktop_app/               Kivy/KivyMD GUI (legacy fallback)
|   |       +-- main.py                 Kivy entry point
|   |       +-- layout.kv               KivyMD layout definition
|   |       +-- screens/                Kivy screen classes
|   |       +-- widgets/                Kivy widget components
|   |       +-- viewmodels/             Kivy-style ViewModels
|   |       +-- assets/                 Themes (CS2, CSGO, CS1.6), fonts, map radar images
|   |       +-- i18n/                   Translations (EN, IT, PT)
|   |
|   +-- backend/
|   |   +-- analysis/                   Game theory and statistical analysis
|   |   |   +-- belief_model.py         Bayesian opponent mental state tracking
|   |   |   +-- game_tree.py            Expectiminimax decision trees
|   |   |   +-- momentum.py             Round momentum and confidence trends
|   |   |   +-- role_classifier.py      Player role detection (entry, support, lurk, AWP, anchor)
|   |   |   +-- blind_spots.py          Map awareness and positional weaknesses
|   |   |   +-- deception_index.py      Positional unpredictability metric
|   |   |   +-- entropy_analysis.py     Decision randomness quantification
|   |   |   +-- engagement_range.py     Weapon-distance distribution analysis
|   |   |   +-- utility_economy.py      Grenade spending efficiency
|   |   |   +-- win_probability.py      Real-time win probability calculation
|   |   |
|   |   +-- data_sources/              External data integration
|   |   |   +-- demo_parser.py          demoparser2 wrapper (tick-level extraction)
|   |   |   +-- hltv_api_service.py     HLTV professional metadata scraping
|   |   |   +-- steam_api_service.py    Steam profile and match data
|   |   |   +-- faceit_api_service.py   FaceIT match data integration
|   |   |
|   |   +-- nn/                         Neural network subsystems
|   |   |   +-- config.py               Global NN config (dimensions, lr, batch size, device)
|   |   |   +-- jepa_model.py           JEPA encoder + VL-JEPA + ConceptLabeler
|   |   |   +-- jepa_trainer.py         JEPA training loop with drift monitoring
|   |   |   +-- training_orchestrator.py Multi-model training orchestration
|   |   |   +-- rap_coach/              RAP Coach model
|   |   |   |   +-- model.py            7-layer architecture
|   |   |   |   +-- trainer.py          RAP-specific training loop
|   |   |   |   +-- memory.py           LTC + Hopfield memory module
|   |   |   +-- layers/                 Shared neural components
|   |   |       +-- superposition.py    Context-dependent superposition layer
|   |   |       +-- moe.py             Mixture-of-Experts gating
|   |   |
|   |   +-- processing/                Feature engineering and data processing
|   |   |   +-- feature_engineering/
|   |   |   |   +-- vectorizer.py       Canonical 25-dim feature extraction (METADATA_DIM=25)
|   |   |   |   +-- tensor_factory.py   View/map tensor construction for RAP Coach
|   |   |   +-- heatmap/               Spatial heatmap generation
|   |   |   +-- validation/            Drift detection, data quality checks
|   |   |
|   |   +-- knowledge/                 Knowledge management
|   |   |   +-- rag_knowledge.py        RAG retrieval for coaching patterns
|   |   |   +-- experience_bank.py      COPER experience storage and retrieval
|   |   |
|   |   +-- services/                  Application services
|   |   |   +-- coaching_service.py     4-level coaching pipeline (COPER/Hybrid/RAG/Base)
|   |   |   +-- ollama_service.py       Local LLM integration for language refinement
|   |   |
|   |   +-- storage/                   Database layer
|   |       +-- database.py            SQLite WAL-mode connection management
|   |       +-- models.py              SQLAlchemy/SQLModel ORM definitions
|   |       +-- backup.py              Automated database backup
|   |       +-- match_data_manager.py  Per-match SQLite database management
|   |
|   +-- core/                          Core application services
|   |   +-- session_engine.py           4-daemon engine (Scanner, Digester, Teacher, Pulse)
|   |   +-- map_manager.py             Map loading, coordinate calibration, Z-cutoffs
|   |   +-- asset_manager.py           Theme and asset resolution
|   |   +-- spatial_data.py            Spatial coordinate systems
|   |
|   +-- ingestion/                     Demo ingestion pipeline
|   |   +-- steam_locator.py           Auto-discovery of Steam CS2 demo paths
|   |   +-- integrity_check.py         Demo file validation
|   |
|   +-- observability/                 Monitoring and security
|   |   +-- rasp.py                    Runtime Application Self-Protection
|   |   +-- telemetry.py              TensorBoard metrics and conviction tracking
|   |   +-- logger_setup.py           Structured logging (cs2analyzer.* namespace)
|   |
|   +-- reporting/                     Output generation
|   |   +-- visualizer.py             Chart and diagram rendering
|   |   +-- pdf_generator.py          PDF report generation
|   |
|   +-- tests/                         Test suite (1,515+ tests)
|   +-- data/                          Static data (seed knowledge base, external datasets)
|
+-- docs/                              Documentation
|   +-- USER_GUIDE.md                  Complete user guide (EN)
|   +-- USER_GUIDE_IT.md               User guide (Italian)
|   +-- USER_GUIDE_PT.md               User guide (Portuguese)
|   +-- Book-Coach-1A.md               Vision book — Neural core
|   +-- Book-Coach-1B.md               Vision book — RAP Coach & data sources
|   +-- Book-Coach-2.md                Vision book — Services & infrastructure
|   +-- Book-Coach-3.md                Vision book — Program logic & UI
|   +-- cybersecurity.md               Security analysis
|   +-- Studies/                        17 research papers
|
+-- tools/                             Validation and diagnostic tools
|   +-- headless_validator.py          Primary regression gate (313 checks, 24 phases)
|   +-- Feature_Audit.py              Feature engineering audit
|   +-- portability_test.py           Cross-platform compatibility checks
|   +-- dead_code_detector.py         Unused code scanning
|   +-- dev_health.py                 Development environment health
|   +-- verify_all_safe.py            Safety verification
|   +-- db_health_diagnostic.py       Database health diagnostics
|   +-- Sanitize_Project.py           Distribution preparation
|   +-- build_pipeline.py             Build pipeline orchestration
|
+-- tests/                            Integration and verification tests
+-- scripts/                          Setup and deployment scripts
+-- alembic/                          Database migration scripts
+-- .github/workflows/build.yml       Cross-platform CI/CD pipeline
+-- console.py                        Interactive TUI entry point
+-- goliath.py                        Production CLI orchestrator
+-- run_full_training_cycle.py        Standalone training cycle runner
```

---

## Entry Points

The application provides 4 entry points for different use cases:

### Desktop Application (Qt GUI — Primary)

```bash
python -m Programma_CS2_RENAN.apps.qt_app.app
```

Full graphical interface with tactical viewer, match history, performance dashboard, coach chat, and settings. Opens at 1280x720. On first launch, a 4-step wizard configures the Brain Data Root directory.

### Desktop Application (Kivy GUI — Legacy)

```bash
python Programma_CS2_RENAN/main.py
```

Original Kivy/KivyMD interface. Maintained as fallback for environments where Qt is unavailable.

### Interactive Console (TUI)

```bash
python console.py
```

Terminal UI with real-time panels for development and runtime control. Commands organized by subsystem:

| Command Group | Examples |
|---------------|----------|
| **ML Pipeline** | `ml start`, `ml stop`, `ml pause`, `ml resume`, `ml throttle 0.5`, `ml status` |
| **Ingestion** | `ingest start`, `ingest stop`, `ingest mode continuous 5`, `ingest scan` |
| **Build & Test** | `build run`, `build verify`, `test all`, `test headless`, `test hospital` |
| **System** | `sys status`, `sys audit`, `sys baseline`, `sys db`, `sys vacuum`, `sys resources` |
| **Config** | `set steam /path`, `set faceit KEY`, `set config key value` |
| **Services** | `svc restart coaching` |

### Production CLI (Goliath)

```bash
python goliath.py <command>
```

Master orchestrator for production builds, releases, and diagnostics:

| Command | Description | Flags |
|---------|-------------|-------|
| `build` | Industrial build pipeline | `--test-only` |
| `sanitize` | Clean project for distribution | `--force` |
| `integrity` | Generate integrity manifest | |
| `audit` | Verify data and features | `--demo <path>` |
| `db` | Database schema management | `--force` |
| `doctor` | Clinical diagnostics | `--department <name>` |
| `baseline` | Temporal baseline decay status | |

### Training Cycle Runner

```bash
python run_full_training_cycle.py
```

Standalone script that executes a full training cycle outside the daemon engine. Useful for manual training or debugging.

---

## Validation and Quality

The project maintains a multi-level validation hierarchy:

| Tool | Scope | Command | Checks |
|------|-------|---------|--------|
| Headless Validator | Primary regression gate | `python tools/headless_validator.py` | 313 checks, 24 phases |
| Pytest Suite | Logic and integration tests | `python -m pytest Programma_CS2_RENAN/tests/ -x -q` | 1,794+ tests |
| Feature Audit | Feature engineering integrity | `python tools/Feature_Audit.py` | Vector dimensions, ranges |
| Portability Test | Cross-platform compatibility | `python tools/portability_test.py` | Import checks, paths |
| Dev Health | Development environment | `python tools/dev_health.py` | Dependencies, config |
| Dead Code Detector | Unused code scanning | `python tools/dead_code_detector.py` | Import analysis |
| Safety Verifier | Security checks | `python tools/verify_all_safe.py` | RASP, secrets scan |
| DB Health | Database diagnostics | `python tools/db_health_diagnostic.py` | Schema, WAL mode, integrity |
| Goliath Hospital | Full diagnostics | `python goliath.py doctor` | Complete system health |

**CI/CD Gate:** The headless validator must return exit code 0 before any commit is considered valid. Pre-commit hooks enforce code quality standards. The CI pipeline runs on both Ubuntu and Windows with SHA-pinned GitHub Actions.

---

## Multi-Language Support

The application supports 3 languages across the entire UI:

| Language | UI | User Guide | README |
|----------|-----|-----------|--------|
| English | Complete | [docs/guides/USER_GUIDE.md](docs/guides/USER_GUIDE.md) | [README.md](README.md) |
| Italiano | Complete | [docs/guides/USER_GUIDE_IT.md](docs/guides/USER_GUIDE_IT.md) | [README_IT.md](README_IT.md) |
| Portugues | Complete | [docs/guides/USER_GUIDE_PT.md](docs/guides/USER_GUIDE_PT.md) | [README_PT.md](README_PT.md) |

Language can be changed at runtime from Settings without restarting the application.

---

## Security Features

### Runtime Application Self-Protection (RASP)

- **Integrity Manifest** — SHA-256 hashes of all critical source files, verified at startup
- **Tampering Detection** — Warns when source files have been modified since last manifest generation
- **Frozen Binary Validation** — Verifies PyInstaller bundle structure and execution environment
- **Suspicious Location Detection** — Warns when running from unexpected filesystem paths

### Credential Security

- **OS Keyring Integration** — API keys (Steam, FaceIT) stored in Windows Credential Manager / Linux keyring, never in plaintext
- **No Hardcoded Secrets** — Settings file shows the placeholder `"PROTECTED_BY_WINDOWS_VAULT"`
- **Cryptographic Operations** — Uses `cryptography==46.0.3` (vetted library, no custom crypto)

### Database Security

- **SQLite WAL Mode** — Write-Ahead Logging for safe concurrent access across all databases
- **Input Validation** — Pydantic models at the ingestion boundary, parameterized SQL queries
- **Backup System** — Automated database backups with integrity verification

### Structured Logging

- All logging through the `get_logger("cs2analyzer.<module>")` namespace
- No PII in log output
- Structured format for observability integration

---

## System Maturity

Not all subsystems are equally mature. The default coaching mode (COPER) is production-ready and does **not** depend on neural models. Neural coaching improves as more demos are processed.

| Subsystem | Status | Score | Notes |
|-----------|--------|-------|-------|
| COPER Coaching | OPERATIONAL | 8/10 | Experience bank + RAG + pro references. Works immediately. |
| Analytical Engine | OPERATIONAL | 6/10 | HLTV 2.0 rating, round breakdown, economy timeline. |
| Base JEPA (InfoNCE) | OPERATIONAL | 7/10 | Self-supervised pre-training, EMA target encoder. |
| Neural Role Head | OPERATIONAL | 7/10 | 5-role MLP with KL-divergence, consensus gating. |
| RAP Coach (7 layers) | LIMITED | 3/10 | Full architecture (LTC+Hopfield), needs 200+ demos. |
| VL-JEPA (16 concepts) | LIMITED | 2/10 | Concept alignment implemented, label quality improving. |

**Maturity levels:**
- **CALIBRATING** (0-49 demos): 0.5x confidence, coaching heavily supplemented by COPER
- **LEARNING** (50-199 demos): 0.8x confidence, neural features gradually activated
- **MATURE** (200+ demos): Full confidence, all subsystems contribute

---

## Documentation

### User Guides

| Document | Description |
|----------|-------------|
| [User Guide (EN)](docs/guides/USER_GUIDE.md) | Complete installation, setup wizard, API keys, all screens, demo acquisition, troubleshooting |
| [Guida Utente (IT)](docs/guides/USER_GUIDE_IT.md) | Full user guide in Italian |
| [Guia do Usuario (PT)](docs/guides/USER_GUIDE_PT.md) | Full user guide in Portuguese |

### Architecture Documentation

| Document | Description |
|----------|-------------|
| [Book-Coach-1A](docs/books/Book-Coach-1A.md) | Neural core: JEPA, VL-JEPA, AdvancedCoachNN, MaturityObservatory |
| [Book-Coach-1B](docs/books/Book-Coach-1B.md) | RAP Coach (7 components), data sources (demo, HLTV, Steam, FACEIT) |
| [Book-Coach-2](docs/books/Book-Coach-2.md) | Services, analysis engines, knowledge/COPER, database, training |
| [Book-Coach-3](docs/books/Book-Coach-3.md) | Full program logic, Qt UI, ingestion, tools, tests, build |
| [Cybersecurity Analysis](docs/archive/cybersecurity.md) | Security posture and threat model |

### Research Papers (17 Studies)

The `docs/Studies/` folder contains 17 in-depth research papers covering the theoretical foundations and engineering decisions behind every subsystem:

| # | Study | Topic |
|---|-------|-------|
| 01 | Epistemic Foundations | Knowledge representation and reasoning framework |
| 02 | Ingestion Algebra | Mathematical model of demo data processing |
| 03 | Recurrent Networks | LTC and Hopfield network theory |
| 04 | Reinforcement Learning | RL foundations for coaching decisions |
| 05 | Perceptive Architecture | Visual processing pipeline design |
| 06 | Cognitive Architecture | Belief modeling and decision systems |
| 07 | JEPA Architecture | Joint-Embedding Predictive Architecture theory |
| 08 | Forensic Engineering | Debugging and diagnostic methodology |
| 09 | Feature Engineering | 25-dimensional vector design and validation |
| 10 | Database and Storage | SQLite WAL, per-match DB, migration strategy |
| 11 | Tri-Daemon Engine | Multi-daemon architecture and lifecycle |
| 12 | Evaluation and Falsification | Testing and validation methodology |
| 13 | Explainability and Coaching | Causal attribution and coaching UI design |
| 14 | Ethics, Privacy and Integrity | Data protection and AI ethics |
| 15 | Hardware and Scaling | Optimization for various hardware configurations |
| 16 | Maps and GNN | Spatial analysis and graph neural network approaches |
| 17 | Sociotechnical Impact | Future directions and social implications |

---

## Feeding the Coach

The AI coach ships with no pre-trained knowledge. It learns exclusively from professional CS2 demo files. Coaching quality is directly proportional to the quality and quantity of ingested demos.

### Demo Count Thresholds

| Pro Demos | Level | Confidence | What Happens |
|-----------|-------|------------|--------------|
| 0-9 | Not ready | 0% | Minimum 10 pro demos required for first training cycle |
| 10-49 | CALIBRATING | 50% | Base coaching active, advice marked as provisional |
| 50-199 | LEARNING | 80% | Growing reliability, increasingly personalized |
| 200+ | MATURE | 100% | Full confidence, maximum accuracy |

### Where to Find Pro Demos

1. Go to [hltv.org](https://www.hltv.org) > Results
2. Filter for top-tier events: Major Championship, IEM Katowice/Cologne, BLAST Premier, ESL Pro League, PGL Major
3. Select matches from top-20 teams (Navi, FaZe, Vitality, G2, Spirit, Heroic)
4. Prefer BO3/BO5 series to maximize training data per download
5. Diversify across all Active Duty maps — an imbalanced distribution creates an imbalanced coach
6. Download the "GOTV Demo" or "Watch Demo" link

### Storage Planning

`.dem` files are typically 300-850 MB each. Plan your storage accordingly:

| Demos | Raw Files | Match DBs | Total |
|-------|-----------|-----------|-------|
| 10 | ~5 GB | ~1 GB | ~6 GB |
| 50 | ~30 GB | ~5 GB | ~35 GB |
| 100 | ~60 GB | ~10 GB | ~70 GB |
| 200 | ~120 GB | ~20 GB | ~140 GB |

Three separate storage locations:

| Location | Content | Recommendation |
|----------|---------|----------------|
| Core Database | Player stats, coaching state, HLTV metadata | Stays in program folder |
| Brain Data Root | AI model weights, logs, knowledge base | SSD recommended |
| Pro Demo Folder | Raw .dem files + per-match SQLite databases | Largest, HDD acceptable |

### TensorBoard Monitoring

```bash
tensorboard --logdir runs/coach_training
```

Open [http://localhost:6006](http://localhost:6006) to monitor conviction index, maturity state transitions, gate specialization, and training loss curves.

> For the complete step-by-step coaching cycle checklist and detailed storage guide, see the [User Guide](docs/guides/USER_GUIDE.md).

---

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'PySide6'` | Install Qt dependencies: `pip install PySide6` |
| `ModuleNotFoundError: No module named 'kivy'` | For legacy UI: `pip install Kivy==2.3.0 KivyMD==1.2.0` (plus kivy-deps on Windows) |
| `CUDA not available` | Verify driver with `nvidia-smi`, reinstall PyTorch with `--index-url https://download.pytorch.org/whl/cu121` |
| `sentence-transformers not installed` | Non-blocking warning. Install with `pip install sentence-transformers` for improved embeddings, or ignore (TF-IDF fallback works) |
| `database is locked` | Close all Python processes and restart |
| Factory reset | Delete `Programma_CS2_RENAN/user_settings.json` and restart |

### Database Locations

| Database | Path | Content |
|----------|------|---------|
| Main | `Programma_CS2_RENAN/backend/storage/database.db` | Player stats, coaching state, training data |
| HLTV | `Programma_CS2_RENAN/backend/storage/hltv_metadata.db` | Professional player metadata |
| Knowledge | `Programma_CS2_RENAN/data/knowledge_base.db` | RAG knowledge base |
| Per-match | `{PRO_DEMO_PATH}/match_data/match_*.db` | Tick-level match data |

> For complete troubleshooting, see the [User Guide](docs/guides/USER_GUIDE.md).

---

## Complete Documentation Index

Every README and technical document in the project. Click any link to open the document.

### Book Coach Series (PDF)

- [Ultimate CS2 Coach — Sistema AI](docs/books/Book-Coach-1.pdf)
- [Ultimate CS2 Coach — Parte 1A — Il Cervello](docs/books/Book-Coach-1A.pdf)
- [Ultimate CS2 Coach — Parte 1B — I Sensi e lo Specialista](docs/books/Book-Coach-1B.pdf)
- [Ultimate CS2 Coach — Parte 2 — Servizi, Analisi e Database](docs/books/Book-Coach-2.pdf)
- [Ultimate CS2 Coach — Parte 3 — Programma, UI, Tools e Build](docs/books/Book-Coach-3.pdf)

### Root

- [README (EN)](README.md) — [Italiano](README_IT.md) — [Portugues](README_PT.md)

### Engineering

- [Engineering Handoff](docs/ENGINEERING_HANDOFF.md) — Master reference: full codebase audit, 75 work items, execution plan, product roadmap

### Infrastructure

- [CI/CD Pipeline & GitHub Configuration](.github/README.md) — [Italiano](.github/README_IT.md) — [Portugues](.github/README_PT.md)
- [Database Migration System — Alembic](alembic/README.md) — [Italiano](alembic/README_IT.md) — [Portugues](alembic/README_PT.md)
- [Documentation Index](docs/README.md) — [Italiano](docs/README_IT.md) — [Portugues](docs/README_PT.md)
- [The Studies — Bibliotheca](docs/Studies/README.md) — [Italiano](docs/Studies/README_IT.md) — [Portugues](docs/Studies/README_PT.md)
- [Build and Setup Scripts](scripts/README.md) — [Italiano](scripts/README_IT.md) — [Portugues](scripts/README_PT.md)
- [Root-Level Verification and Forensic Tests](tests/README.md) — [Italiano](tests/README_IT.md) — [Portugues](tests/README_PT.md)
- [Root-Level Project Tools](tools/README.md) — [Italiano](tools/README_IT.md) — [Portugues](tools/README_PT.md)
- [Packaging — Build & Distribution](packaging/README.md) — [Italiano](packaging/README_IT.md) — [Portugues](packaging/README_PT.md)

### Main Package

- [Programma_CS2_RENAN](Programma_CS2_RENAN/README.md) — [Italiano](Programma_CS2_RENAN/README_IT.md) — [Portugues](Programma_CS2_RENAN/README_PT.md)
- [Core Systems](Programma_CS2_RENAN/core/README.md) — [Italiano](Programma_CS2_RENAN/core/README_IT.md) — [Portugues](Programma_CS2_RENAN/core/README_PT.md)
- [Data — Application Data & Configuration](Programma_CS2_RENAN/data/README.md) — [Italiano](Programma_CS2_RENAN/data/README_IT.md) — [Portugues](Programma_CS2_RENAN/data/README_PT.md)
- [Assets — Static Resources](Programma_CS2_RENAN/assets/README.md) — [Italiano](Programma_CS2_RENAN/assets/README_IT.md) — [Portugues](Programma_CS2_RENAN/assets/README_PT.md)
- [Models — Neural Network Checkpoint Storage](Programma_CS2_RENAN/models/README.md) — [Italiano](Programma_CS2_RENAN/models/README_IT.md) — [Portugues](Programma_CS2_RENAN/models/README_PT.md)
- [Validation and Diagnostic Tools](Programma_CS2_RENAN/tools/README.md) — [Italiano](Programma_CS2_RENAN/tools/README_IT.md) — [Portugues](Programma_CS2_RENAN/tools/README_PT.md)
- [Test Suite](Programma_CS2_RENAN/tests/README.md) — [Italiano](Programma_CS2_RENAN/tests/README_IT.md) — [Portugues](Programma_CS2_RENAN/tests/README_PT.md)

### Apps — User Interface

- [Apps — User Interface Layer](Programma_CS2_RENAN/apps/README.md) — [Italiano](Programma_CS2_RENAN/apps/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/README_PT.md)
- [Qt Desktop Application (Primary)](Programma_CS2_RENAN/apps/qt_app/README.md) — [Italiano](Programma_CS2_RENAN/apps/qt_app/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/qt_app/README_PT.md)
- [Desktop Application (Legacy Kivy/KivyMD)](Programma_CS2_RENAN/apps/desktop_app/README.md) — [Italiano](Programma_CS2_RENAN/apps/desktop_app/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/desktop_app/README_PT.md)

### Backend

- [Backend](Programma_CS2_RENAN/backend/README.md) — [Italiano](Programma_CS2_RENAN/backend/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/README_PT.md)
- [Analysis — Game Theory & Statistical Engines](Programma_CS2_RENAN/backend/analysis/README.md) — [Italiano](Programma_CS2_RENAN/backend/analysis/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/analysis/README_PT.md)
- [Coaching — Multi-Mode Coaching Pipeline](Programma_CS2_RENAN/backend/coaching/README.md) — [Italiano](Programma_CS2_RENAN/backend/coaching/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/coaching/README_PT.md)
- [Control — Application Orchestration & Daemon Management](Programma_CS2_RENAN/backend/control/README.md) — [Italiano](Programma_CS2_RENAN/backend/control/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/control/README_PT.md)
- [Data Sources — External Integrations](Programma_CS2_RENAN/backend/data_sources/README.md) — [Italiano](Programma_CS2_RENAN/backend/data_sources/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/data_sources/README_PT.md)
- [HLTV Professional Data Scraping](Programma_CS2_RENAN/backend/data_sources/hltv/README.md) — [Italiano](Programma_CS2_RENAN/backend/data_sources/hltv/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/data_sources/hltv/README_PT.md)
- [Backend Ingestion — File Watching & Resource Governance](Programma_CS2_RENAN/backend/ingestion/README.md) — [Italiano](Programma_CS2_RENAN/backend/ingestion/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/ingestion/README_PT.md)
- [Knowledge — RAG & Experience Bank](Programma_CS2_RENAN/backend/knowledge/README.md) — [Italiano](Programma_CS2_RENAN/backend/knowledge/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/knowledge/README_PT.md)
- [Knowledge Base — In-App Help System](Programma_CS2_RENAN/backend/knowledge_base/README.md) — [Italiano](Programma_CS2_RENAN/backend/knowledge_base/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/knowledge_base/README_PT.md)
- [Onboarding — New User Flow Management](Programma_CS2_RENAN/backend/onboarding/README.md) — [Italiano](Programma_CS2_RENAN/backend/onboarding/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/onboarding/README_PT.md)
- [Progress — Longitudinal Performance Tracking](Programma_CS2_RENAN/backend/progress/README.md) — [Italiano](Programma_CS2_RENAN/backend/progress/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/progress/README_PT.md)
- [Reporting — Dashboard Analytics Engine](Programma_CS2_RENAN/backend/reporting/README.md) — [Italiano](Programma_CS2_RENAN/backend/reporting/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/reporting/README_PT.md)
- [Application Service Layer](Programma_CS2_RENAN/backend/services/README.md) — [Italiano](Programma_CS2_RENAN/backend/services/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/services/README_PT.md)
- [Database Storage Layer](Programma_CS2_RENAN/backend/storage/README.md) — [Italiano](Programma_CS2_RENAN/backend/storage/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/storage/README_PT.md)

### Neural Networks

- [Neural Network Subsystem](Programma_CS2_RENAN/backend/nn/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/README_PT.md)
- [RAP Coach — 7-Layer Recurrent Architecture](Programma_CS2_RENAN/backend/nn/rap_coach/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/rap_coach/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/rap_coach/README_PT.md)
- [Advanced — Experimental Module Stub](Programma_CS2_RENAN/backend/nn/advanced/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/advanced/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/advanced/README_PT.md)

### Processing & Feature Engineering

- [Processing — Data Pipeline & Feature Engineering](Programma_CS2_RENAN/backend/processing/README.md) — [Italiano](Programma_CS2_RENAN/backend/processing/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/processing/README_PT.md)
- [Professional Baselines & Meta Drift Detection](Programma_CS2_RENAN/backend/processing/baselines/README.md) — [Italiano](Programma_CS2_RENAN/backend/processing/baselines/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/processing/baselines/README_PT.md)
- [Feature Engineering — Unified Feature Extraction](Programma_CS2_RENAN/backend/processing/feature_engineering/README.md) — [Italiano](Programma_CS2_RENAN/backend/processing/feature_engineering/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/processing/feature_engineering/README_PT.md)

### Ingestion Pipelines

- [Demo Ingestion Pipelines](Programma_CS2_RENAN/ingestion/README.md) — [Italiano](Programma_CS2_RENAN/ingestion/README_IT.md) — [Portugues](Programma_CS2_RENAN/ingestion/README_PT.md)
- [Ingestion Pipeline Implementations](Programma_CS2_RENAN/ingestion/pipelines/README.md) — [Italiano](Programma_CS2_RENAN/ingestion/pipelines/README_IT.md) — [Portugues](Programma_CS2_RENAN/ingestion/pipelines/README_PT.md)
- [Demo File Registry & Lifecycle Management](Programma_CS2_RENAN/ingestion/registry/README.md) — [Italiano](Programma_CS2_RENAN/ingestion/registry/README_IT.md) — [Portugues](Programma_CS2_RENAN/ingestion/registry/README_PT.md)

### Observability & Reporting

- [Observability & Runtime Protection](Programma_CS2_RENAN/observability/README.md) — [Italiano](Programma_CS2_RENAN/observability/README_IT.md) — [Portugues](Programma_CS2_RENAN/observability/README_PT.md)
- [Visualization & Report Generation](Programma_CS2_RENAN/reporting/README.md) — [Italiano](Programma_CS2_RENAN/reporting/README_IT.md) — [Portugues](Programma_CS2_RENAN/reporting/README_PT.md)

---

## License

This project is dual-licensed. Copyright (c) 2025-2026 Renan Augusto Macena.

You may choose either:
- **Proprietary License** — All Rights Reserved (default). Viewing for educational purposes is permitted.
- **Apache License 2.0** — Permissive open source with patent protection.

See [LICENSE](LICENSE) for full terms.

---

## Author

**Renan Augusto Macena**

Built with passion by a Counter-Strike player with over 10,000 hours since 2004, combining deep game knowledge with AI engineering to create the ultimate coaching system.

> *"I always wished for a professional guide — like the real pro players have — to understand what it truly looks like when someone trains the right way and plays the right way."*
