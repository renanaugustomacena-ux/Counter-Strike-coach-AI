# Macena CS2 Analyzer

**AI-Powered Tactical Coach for Counter-Strike 2**

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

---

## What Is This?

Macena CS2 Analyzer is a desktop application that acts as a personal AI coach for Counter-Strike 2. It ingests professional and user demo files, trains multiple neural network models, and delivers personalized tactical coaching by comparing your gameplay against professional standards.

The system learns from the best professional matches ever played and adapts its coaching to your individual playstyle — whether you're an AWPer, entry fragger, support, or any other role. The coaching pipeline fuses machine learning predictions with retrieved tactical knowledge, game theory analysis, and Bayesian belief modeling to produce actionable, context-aware advice.

Unlike static coaching tools that ship with pre-written tips, this system builds its intelligence from real professional gameplay data. At first launch the neural networks have random weights and zero tactical knowledge. Every demo you feed it makes the coach smarter, more nuanced, and more personalized.

---

## Table of Contents

- [Key Features](#key-features)
- [System Requirements](#system-requirements)
- [Quick Start](#quick-start)
- [Architecture Deep-Dive](#architecture-deep-dive)
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
- [License](#license)
- [Author](#author)

---

## Key Features

### AI Coaching Pipeline

- **4-Level Fallback Chain** — COPER > Hybrid > RAG > Base coaching, ensuring the system always produces useful advice regardless of model maturity
- **COPER Experience Bank** — Stores and retrieves past coaching experiences weighted by recency, effectiveness, and context similarity
- **RAG Knowledge Base** — Retrieval-Augmented Generation with professional reference patterns and tactical knowledge
- **Ollama Integration** — Optional local LLM for natural language polishing of coaching insights
- **Causal Attribution** — Every coaching recommendation includes a "why" explanation tracing back to specific gameplay decisions

### Neural Network Subsystems

- **RAP Coach** — 7-layer architecture combining perception, memory (LTC-Hopfield), strategy (Mixture-of-Experts with superposition), pedagogy (value function), position prediction, and causal attribution
- **JEPA Encoder** — Joint-Embedding Predictive Architecture for self-supervised pre-training with InfoNCE contrastive loss and EMA target encoder
- **VL-JEPA** — Vision-Language extension with 16 tactical concept alignment (positioning, utility, economy, engagement, decision, psychology)
- **AdvancedCoachNN** — LSTM + Mixture-of-Experts architecture for coaching weight prediction
- **Neural Role Head** — 5-role MLP classifier (entry, support, lurk, AWP, anchor) with KL-divergence and consensus gating
- **Bayesian Belief Models** — Opponent mental state tracking with adaptive calibration from match data

### Demo Analysis

- **Tick-Level Parsing** — Every tick of `.dem` files is parsed via demoparser2, preserving all game state (no tick decimation)
- **HLTV 2.0 Rating** — Computed per-match using the official HLTV 2.0 formula (kills, deaths, ADR, KAST%, survival, flash assists)
- **Round-by-Round Breakdowns** — Economy timeline, engagement analysis, utility usage, momentum tracking
- **Temporal Baseline Decay** — Tracks player skill evolution over time with exponential decay weighting

### Game Theory Analysis

- **Expectiminimax Trees** — Game-theoretic decision evaluation for strategic scenarios
- **Bayesian Death Probability** — Estimates survival likelihood based on position, equipment, and enemy state
- **Deception Index** — Quantifies positional unpredictability relative to professional baselines
- **Engagement Range Analysis** — Maps weapon selection against engagement distance distributions
- **Win Probability** — Real-time match win probability calculation
- **Momentum Tracking** — Round-to-round confidence and performance trajectory

### Desktop Application

- **Kivy + KivyMD Interface** — Cross-platform desktop app with MVVM architecture
- **Tactical 2D Map Viewer** — Real-time demo replay with player positions, kill events, bomb indicators, and AI ghost predictions
- **Match History** — Scrollable list of recent matches with color-coded ratings
- **Performance Dashboard** — Rating trends, per-map stats, strengths/weaknesses analysis, utility breakdowns
- **Coach Chat** — Interactive AI conversation with quick-action buttons and free-text questions
- **User Profile** — Steam integration with automatic match import
- **3 Visual Themes** — CS2 (orange), CS:GO (blue-gray), CS 1.6 (green) with cycling wallpapers

### Training and Automation

- **4-Daemon Session Engine** — Scanner (file discovery), Digester (demo processing), Teacher (model training), Pulse (health monitoring)
- **3-Stage Maturity Gating** — CALIBRATING (0-49 demos, 0.5x confidence) > LEARNING (50-199, 0.8x) > MATURE (200+, full)
- **Conviction Index** — 5-signal composite tracking belief entropy, gate specialization, concept focus, value accuracy, and role stability
- **Auto-Retraining** — Training triggers automatically at 10% demo count growth
- **Drift Detection** — Z-score based feature drift monitoring with automatic retraining flag
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

This creates a virtual environment, installs all dependencies, initializes the database, and sets up Playwright for HLTV scraping.

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

pip install -r Programma_CS2_RENAN/requirements.txt
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

pip install -r Programma_CS2_RENAN/requirements.txt
pip install Kivy==2.3.0 KivyMD==1.2.0
python -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database()"
pip install playwright && python -m playwright install chromium
```

### 5. Verify Installation

```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import kivy; print(f'Kivy: {kivy.__version__}')"
python -c "from Programma_CS2_RENAN.backend.nn.config import get_device; print(f'Device: {get_device()}')"
```

### 6. Launch

```bash
# Desktop application (Kivy GUI)
python Programma_CS2_RENAN/main.py

# Interactive console (live TUI with real-time panels)
python console.py

# One-shot CLI (build, test, audit, hospital, sanitize)
python goliath.py
```

> For the complete guide including API key setup, feature walkthroughs, and troubleshooting, see the [User Guide](docs/USER_GUIDE.md).

---

## Architecture Deep-Dive

### WATCH > LEARN > THINK > SPEAK Pipeline

The system is organized as a 4-stage pipeline that transforms raw demo files into personalized coaching:

```
WATCH (Ingestion)      LEARN (Training)       THINK (Inference)       SPEAK (Dialogue)
  Scanner daemon         Teacher daemon         COPER pipeline          Template + Ollama
  Demo parsing           3-stage maturity       RAG knowledge           Causal attribution
  Feature extraction     Multi-model training   Game theory             Pro comparisons
  Tick-level storage     Drift detection        Belief modeling         Severity scoring
```

**WATCH** — The Scanner daemon continuously monitors configured demo folders for new `.dem` files. When found, the Digester daemon parses every tick using demoparser2, extracts the canonical 25-dimensional feature vector, computes HLTV 2.0 ratings, and stores everything in per-match SQLite databases.

**LEARN** — The Teacher daemon automatically trains neural models when enough data accumulates. Training proceeds through 3 maturity stages (CALIBRATING > LEARNING > MATURE). Multiple architectures train in parallel: JEPA for self-supervised representation learning, RAP Coach for tactical decision modeling, NeuralRoleHead for player role classification.

**THINK** — At inference time, the COPER pipeline combines neural predictions with retrieved coaching experiences, RAG knowledge, and game theory analysis. A 4-level fallback chain (COPER > Hybrid > RAG > Base) ensures advice is always available regardless of model maturity.

**SPEAK** — Final coaching output is formatted with severity levels, causal attribution ("why this advice"), and optionally polished through a local Ollama LLM for natural language quality.

### 4-Daemon Session Engine

| Daemon | Role | Trigger |
|--------|------|---------|
| **Scanner (Hunter)** | Discovers new `.dem` files in configured folders | Periodic scan or file watcher |
| **Digester** | Parses demos, extracts features, computes ratings | New file detected by Scanner |
| **Teacher** | Trains neural models on accumulated data | 10% demo count growth threshold |
| **Pulse** | Health monitoring, drift detection, system status | Continuous background |

### COPER Coaching Pipeline

COPER (Coaching via Organized Pattern Experience Retrieval) is the primary coaching engine. It operates a 4-level fallback chain:

1. **COPER Mode** — Full pipeline: Experience Bank retrieval + RAG knowledge + neural model predictions + professional comparisons. Requires trained models.
2. **Hybrid Mode** — Combines neural predictions with template-based advice when some models are still calibrating.
3. **RAG Mode** — Pure retrieval: searches knowledge base for relevant coaching patterns without neural inference. Works with just ingested demos.
4. **Base Mode** — Template-based advice from statistical analysis (mean/std deviations from professional baselines). Works immediately.

### Neural Network Architectures

**RAP Coach (7-Layer Architecture)**

The RAP (Reasoning, Attribution, Prediction) Coach is the primary neural model. Its 7 layers process gameplay data through a cognitive pipeline:

| Layer | Function | Details |
|-------|----------|---------|
| 1. Perception | Visual + spatial encoding | Conv layers for view frames (64d), map state (32d), motion diff (32d) → 128d |
| 2. Memory | Recurrent belief tracking | LSTM + Hopfield network for associative memory. Input: 153d (128 perception + 25 metadata) → 256d hidden state |
| 3. Strategy | Decision optimization | Mixture-of-Experts with superposition for context-dependent decisions. 10 action weights |
| 4. Pedagogy | Value estimation | V-function evaluation with skill vector integration |
| 5. Position | Optimal placement | Predicts (dx, dy, dz) delta to optimal position (scale: 500 world units) |
| 6. Attribution | Causal diagnosis | 5-dimensional attribution explaining decision drivers |
| 7. Output | Aggregation | advice_probs, belief_state, value_estimate, gate_weights, optimal_pos, attribution |

**JEPA (Joint-Embedding Predictive Architecture)**

Self-supervised pre-training with:
- Context encoder + predictor → predicts target embeddings
- EMA-updated target encoder (momentum 0.996)
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
| 9-11 | pos_x, pos_y, pos_z | [-1, 1] | World coordinates (map-normalized) |
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
| 24 | team_economy | [0, 1] | Average team money / 16000 |

### 3-Stage Maturity Gating

Models progress through maturity gates based on ingested demo count:

| Stage | Demo Count | Confidence | Behavior |
|-------|-----------|------------|----------|
| **CALIBRATING** | 0-49 | 0.5x | Basic coaching, advice marked provisional |
| **LEARNING** | 50-199 | 0.8x | Intermediate, growing reliability |
| **MATURE** | 200+ | 1.0x | Full confidence, all subsystems contributing |

A parallel **Conviction Index** (0.0-1.0) tracks 5 neural signals: belief entropy, gate specialization, concept focus, value accuracy, and role stability. States: DOUBT (<0.30) > LEARNING (0.30-0.60) > CONVICTION (>0.60 stable 10+ epochs) > MATURE (>0.75 stable 20+ epochs). A sharp drop >20% triggers CRISIS state.

---

## Supported Maps

The system supports all 9 Active Duty competitive maps with pixel-accurate coordinate mapping:

| Map | Type | Calibration |
|-----|------|-------------|
| de_mirage | Single-level | pos (-3230, 1713), scale 5.0 |
| de_inferno | Single-level | pos (-2087, 3870), scale 4.9 |
| de_dust2 | Single-level | pos (-2476, 3239), scale 4.4 |
| de_overpass | Single-level | pos (-4831, 1781), scale 5.2 |
| de_ancient | Single-level | pos (-2953, 2164), scale 5.0 |
| de_anubis | Single-level | pos (-2796, 3328), scale 5.22 |
| de_train | Single-level | pos (-2477, 2392), scale 4.7 |
| de_nuke | **Multi-level** | pos (-3453, 2887), scale 7.0, Z-cutoff -495 |
| de_vertigo | **Multi-level** | pos (-3168, 1762), scale 4.0, Z-cutoff 11700 |

Multi-level maps (Nuke, Vertigo) use Z-axis cutoffs to separate upper and lower levels for accurate 2D rendering. The z_penalty feature (index 15) in the feature vector captures vertical distinctiveness for these maps.

---

## Technology Stack

### Core Dependencies

| Category | Package | Version | Purpose |
|----------|---------|---------|---------|
| **ML Framework** | PyTorch | Latest | Neural network training and inference |
| **Recurrent Nets** | ncps | Latest | Liquid Time-Constant (LTC) networks |
| **Associative Memory** | hopfield-layers | Latest | Hopfield network layers for memory |
| **Demo Parsing** | demoparser2 | 0.40.2 | CS2 demo file tick-level parsing |
| **CS2 Utilities** | awpy | 1.2.3 | CS2 analysis utilities |
| **UI Framework** | Kivy | 2.3.0 | Cross-platform desktop GUI |
| **UI Components** | KivyMD | 1.2.0 | Material Design widgets |
| **Database ORM** | SQLAlchemy + SQLModel | Latest | Database models and queries |
| **Migrations** | Alembic | Latest | Database schema migrations |
| **Web Scraping** | Playwright | 1.57.0 | Headless browser for HLTV |
| **HTTP Client** | HTTPX | 0.28.1 | Async HTTP requests |
| **Data Science** | NumPy, Pandas, SciPy, scikit-learn | Latest | Numerical computing and analysis |
| **Visualization** | Matplotlib | Latest | Chart generation |
| **Geometry** | Shapely | 2.1.2 | Spatial analysis |
| **Graphs** | NetworkX | Latest | Graph-based analysis |
| **Security** | cryptography | 46.0.3 | Credential encryption |
| **TUI** | Rich | 14.2.0 | Terminal UI for console mode |
| **API** | FastAPI + Uvicorn | 0.40.0 | Internal API server |
| **Validation** | Pydantic | Latest | Data validation and settings |
| **Testing** | pytest + pytest-cov + pytest-mock | 9.0.2 | Test framework and coverage |
| **Packaging** | PyInstaller | 6.17.0 | Binary distribution |
| **Templating** | Jinja2 | 3.1.6 | Report template rendering |
| **HTML Parsing** | BeautifulSoup4 + lxml | 4.12.3 | Web content extraction |
| **Config** | PyYAML | 6.0.3 | YAML configuration files |
| **Images** | Pillow | 12.0.0 | Image processing |
| **Keyring** | keyring | 25.6.0 | Secure credential storage |

### Windows-Only Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| kivy-deps.glew | 0.3.1 | OpenGL extension wrangler |
| kivy-deps.sdl2 | 0.7.0 | SDL2 multimedia library |
| kivy-deps.angle | 0.4.0 | ANGLE OpenGL ES backend |

---

## Project Structure

```
Counter-Strike-coach-AI/
|
+-- Programma_CS2_RENAN/                Main application package
|   +-- apps/desktop_app/               Kivy GUI (MVVM pattern)
|   |   +-- main.py                     App entry point
|   |   +-- layout.kv                   Kivy layout definition
|   |   +-- viewmodels/                 ViewModel layer (playback, ghost, chronovisor)
|   |   +-- screens/                    UI screens (tactical viewer, match history, performance,
|   |   |                               match detail, wizard, help, coach, settings, profile)
|   |   +-- widgets/                    Reusable UI components (tactical map, player sidebar,
|   |   |                               timeline scrubber, ghost pixel renderer)
|   |   +-- assets/                     Themes (CS2, CSGO, CS1.6), fonts, map radar images
|   |   +-- i18n/                       Translations (EN, IT, PT)
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
|   |   |   +-- config.py               Global NN configuration (dims, lr, batch size, device)
|   |   |   +-- jepa_model.py           JEPA encoder + VL-JEPA + ConceptLabeler
|   |   |   +-- jepa_trainer.py         JEPA training loop with drift monitoring
|   |   |   +-- training_orchestrator.py Multi-model training orchestration
|   |   |   +-- rap_coach/              RAP Coach model
|   |   |   |   +-- model.py            7-layer architecture (Perception-Memory-Strategy-
|   |   |   |   |                       Pedagogy-Position-Attribution-Output)
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
|   |   |   +-- round_utils.py          Round phase detection utilities
|   |   |
|   |   +-- services/                  Application services
|   |   |   +-- coaching_service.py     4-level coaching pipeline (COPER/Hybrid/RAG/Base)
|   |   |   +-- ollama_service.py       Local LLM integration for language polishing
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
|   |   +-- steam_locator.py           Auto-discover Steam CS2 demo paths
|   |   +-- integrity_check.py         Demo file validation
|   |
|   +-- observability/                 Monitoring and security
|   |   +-- rasp.py                    Runtime Application Self-Protection
|   |   +-- telemetry.py              TensorBoard metrics and conviction tracking
|   |   +-- logger_setup.py           Structured logging (cs2analyzer.* namespace)
|   |
|   +-- reporting/                     Output generation
|   |   +-- visualizer.py             Chart and graph rendering
|   |   +-- pdf_generator.py          PDF report generation
|   |
|   +-- tests/                         Test suite (390+ tests)
|   +-- data/                          Static data (knowledge base seeds, external datasets)
|
+-- docs/                              Documentation
|   +-- USER_GUIDE.md                  Complete user guide (EN)
|   +-- USER_GUIDE_IT.md               User guide (Italian)
|   +-- USER_GUIDE_PT.md               User guide (Portuguese)
|   +-- AI-cs2-coach-part1.md          Architecture documentation (Part 1)
|   +-- AI-cs2-coach-part2.md          Architecture documentation (Part 2)
|   +-- AI-cs2-coach-part3.md          Architecture documentation (Part 3)
|   +-- cybersecurity.md               Security analysis
|   +-- Studies/                        17 research papers covering:
|       +-- Studio_01                   Epistemic Foundations
|       +-- Studio_02                   Ingestion Algebra
|       +-- Studio_03                   Recurrent Networks
|       +-- Studio_04                   Reinforcement Learning
|       +-- Studio_05                   Perceptive Architecture
|       +-- Studio_06                   Cognitive Architecture
|       +-- Studio_07                   JEPA Architecture
|       +-- Studio_08                   Forensic Engineering
|       +-- Studio_09                   Feature Engineering
|       +-- Studio_10                   Database & Storage
|       +-- Studio_11                   Tri-Daemon Engine
|       +-- Studio_12                   Evaluation & Falsification
|       +-- Studio_13                   Explainability & Coaching Interface
|       +-- Studio_14                   Ethics, Privacy & Integrity
|       +-- Studio_15                   Hardware Optimization & Scaling
|       +-- Studio_16                   Maps & GNN
|       +-- Studio_17                   Sociotechnical Impact & Future
|
+-- tools/                             Validation and diagnostic tools
|   +-- headless_validator.py          Primary regression gate (245+ checks)
|   +-- Feature_Audit.py              Feature engineering audit
|   +-- portability_test.py           Cross-platform portability check
|   +-- dead_code_detector.py         Unused code detection
|   +-- dev_health.py                 Development environment health
|   +-- verify_all_safe.py            Safety verification
|   +-- db_health_diagnostic.py       Database health diagnostics
|   +-- generate_manifest.py          Integrity manifest generator
|   +-- Sanitize_Project.py           Distribution preparation
|   +-- build_pipeline.py             Build pipeline orchestration
|
+-- tests/                            Integration and verification tests
|   +-- forensics/                    Debug and forensic utilities
|
+-- scripts/                          Setup and deployment scripts
|   +-- Setup_Macena_CS2.ps1          Windows automated setup
|
+-- alembic/                          Database migration scripts
+-- console.py                        Interactive TUI entry point
+-- goliath.py                        Production CLI orchestrator
+-- run_full_training_cycle.py        Standalone training cycle runner
```

---

## Entry Points

The application provides 4 entry points for different use cases:

### Desktop Application (GUI)

```bash
python Programma_CS2_RENAN/main.py
```

Full graphical interface with tactical viewer, match history, performance dashboard, coach chat, and settings. Opens at 1280x720. On first launch, a 3-step setup wizard configures the Brain Data Root directory.

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

Standalone script that runs a complete training cycle outside the daemon engine. Useful for manual training or debugging.

---

## Validation and Quality

The project maintains a multi-level validation hierarchy:

| Tool | Scope | Command | Checks |
|------|-------|---------|--------|
| Headless Validator | Primary regression gate | `python tools/headless_validator.py` | 245+ checks |
| Pytest Suite | Logic and integration tests | `python -m pytest Programma_CS2_RENAN/tests/ -x -q` | 390+ tests |
| Feature Audit | Feature engineering integrity | `python tools/Feature_Audit.py` | Vector dimensions, ranges |
| Portability Test | Cross-platform compatibility | `python tools/portability_test.py` | Import checks, path handling |
| Dev Health | Development environment | `python tools/dev_health.py` | Dependencies, config |
| Dead Code Detector | Unused code scanning | `python tools/dead_code_detector.py` | Import analysis |
| Safety Verifier | Security checks | `python tools/verify_all_safe.py` | RASP, secrets scan |
| DB Health | Database diagnostics | `python tools/db_health_diagnostic.py` | Schema, WAL mode, integrity |
| Goliath Hospital | Comprehensive diagnostics | `python goliath.py doctor` | Full system health |

**CI/CD gates:** The headless validator must exit 0 before any commit is considered valid. Pre-commit hooks enforce code quality standards.

---

## Multi-Language Support

The application supports 3 languages across the entire UI:

| Language | UI | User Guide | README |
|----------|----|-----------|--------|
| English | Full | [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | [README.md](README.md) |
| Italian | Full | [docs/USER_GUIDE_IT.md](docs/USER_GUIDE_IT.md) | [README_IT.md](README_IT.md) |
| Portuguese | Full | [docs/USER_GUIDE_PT.md](docs/USER_GUIDE_PT.md) | [README_PT.md](README_PT.md) |

Language can be switched at runtime from Settings without restarting the application.

---

## Security Features

### Runtime Application Self-Protection (RASP)

- **Integrity Manifest** — SHA-256 hashes of all critical source files, verified at startup
- **Tamper Detection** — Alerts when source files have been modified since last manifest generation
- **Frozen Binary Validation** — Verifies PyInstaller bundle structure and execution environment
- **Suspicious Location Detection** — Warns when executed from unexpected filesystem paths

### Credential Security

- **OS Keyring Integration** — API keys (Steam, FaceIT) stored in Windows Credential Manager / Linux keyring, never in plaintext
- **No Hardcoded Secrets** — Settings file shows `"PROTECTED_BY_WINDOWS_VAULT"` placeholder
- **Cryptographic Operations** — Uses `cryptography==46.0.3` (vetted library, no custom crypto)

### Database Security

- **SQLite WAL Mode** — Write-Ahead Logging for safe concurrent access across all databases
- **Input Validation** — Pydantic models at ingestion boundary, parameterized SQL queries
- **Backup System** — Automated database backups with integrity verification

### Structured Logging

- All logging through `get_logger("cs2analyzer.<module>")` namespace
- No PII in log output
- Structured format for observability integration

---

## System Maturity

Not all subsystems are equally mature. The default coaching mode (COPER) is production-ready and does **not** depend on neural models. Neural-powered coaching improves as more demos are processed.

| Subsystem | Status | Score | Notes |
|-----------|--------|-------|-------|
| COPER Coaching | OPERATIVO | 8/10 | Experience bank + RAG + pro references. Works immediately. |
| Analytics Engine | OPERATIVO | 6/10 | HLTV 2.0 ratings, round breakdowns, economy timeline. |
| JEPA Base (InfoNCE) | OPERATIVO | 7/10 | Self-supervised pre-training, EMA target encoder. |
| Neural Role Head | OPERATIVO | 7/10 | 5-role MLP with KL-divergence, consensus gating. |
| RAP Coach (7-layer) | LIMITATO | 3/10 | Architecture complete (LTC+Hopfield), needs 200+ demos. |
| VL-JEPA (16 concepts) | LIMITATO | 2/10 | Concept alignment implemented, label quality improving. |

**Maturity tiers:**
- **CALIBRATING** (0-49 demos): 0.5x confidence, coaching heavily supplemented by COPER
- **LEARNING** (50-199 demos): 0.8x confidence, neural features gradually activated
- **MATURE** (200+ demos): Full confidence, all subsystems contributing

---

## Documentation

### User Guides

| Document | Description |
|----------|-------------|
| [User Guide (EN)](docs/USER_GUIDE.md) | Complete installation, setup wizard, API keys, all screens, demo acquisition, troubleshooting |
| [User Guide (IT)](docs/USER_GUIDE_IT.md) | Guida utente completa in italiano |
| [User Guide (PT)](docs/USER_GUIDE_PT.md) | Guia completo do usuario em portugues |

### Architecture Documentation

| Document | Description |
|----------|-------------|
| [Architecture Part 1](docs/AI-cs2-coach-part1.md) | System design and core architecture |
| [Architecture Part 2](docs/AI-cs2-coach-part2.md) | Neural network subsystems |
| [Architecture Part 3](docs/AI-cs2-coach-part3.md) | Coaching pipeline and knowledge management |
| [Cybersecurity Analysis](docs/cybersecurity.md) | Security posture and threat model |

### Research Papers (17 Studies)

The `docs/Studies/` folder contains 17 deep-dive research papers covering the theoretical foundations and engineering decisions behind each subsystem:

| # | Study | Topic |
|---|-------|-------|
| 01 | Epistemic Foundations | Knowledge representation and reasoning framework |
| 02 | Ingestion Algebra | Mathematical model of demo data processing |
| 03 | Recurrent Networks | LTC and Hopfield network theory |
| 04 | Reinforcement Learning | RL foundations for coaching decisions |
| 05 | Perceptive Architecture | Visual processing pipeline design |
| 06 | Cognitive Architecture | Belief modeling and decision systems |
| 07 | JEPA Architecture | Joint-Embedding Predictive Architecture theory |
| 08 | Forensic Engineering | Debug and diagnostic methodology |
| 09 | Feature Engineering | 25-dim vector design and validation |
| 10 | Database & Storage | SQLite WAL, per-match DBs, migration strategy |
| 11 | Tri-Daemon Engine | Multi-daemon architecture and lifecycle |
| 12 | Evaluation & Falsification | Testing and validation methodology |
| 13 | Explainability & Coaching | Causal attribution and user interface design |
| 14 | Ethics, Privacy & Integrity | Data protection and ethical AI considerations |
| 15 | Hardware & Scaling | Optimization for various hardware configurations |
| 16 | Maps & GNN | Spatial analysis and graph neural network approaches |
| 17 | Sociotechnical Impact | Future directions and societal implications |

---

## Feeding the Coach

The AI coach ships with no pre-trained knowledge. It learns exclusively from professional CS2 demo files. The quality of coaching is directly proportional to the quality and quantity of demos ingested.

### Demo Count Thresholds

| Pro Demos | Tier | Confidence | What Happens |
|-----------|------|------------|--------------|
| 0-9 | Not ready | 0% | Minimum 10 pro demos required for first training cycle |
| 10-49 | CALIBRATING | 50% | Basic coaching active, advice marked provisional |
| 50-199 | LEARNING | 80% | Growing reliability, increasingly personalized |
| 200+ | MATURE | 100% | Full confidence, maximum accuracy |

### Where to Get Pro Demos

1. Go to [hltv.org](https://www.hltv.org) > Results
2. Filter for top-tier events: Major Championships, IEM Katowice/Cologne, BLAST Premier, ESL Pro League, PGL Major
3. Select matches from top-20 ranked teams (Navi, FaZe, Vitality, G2, Spirit, Heroic)
4. Prefer BO3/BO5 series for maximum training data per download
5. Diversify across all Active Duty maps — a biased map distribution creates a biased coach
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

> For the complete step-by-step coaching cycle checklist and detailed storage guide, see the [User Guide](docs/USER_GUIDE.md).

---

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'kivy'` | Install Kivy deps: `pip install kivy-deps.glew==0.3.1 kivy-deps.sdl2==0.7.0 kivy-deps.angle==0.4.0 Kivy==2.3.0 KivyMD==1.2.0` (skip kivy-deps on Linux) |
| `CUDA not available` | Verify driver with `nvidia-smi`, reinstall PyTorch with `--index-url https://download.pytorch.org/whl/cu121` |
| `sentence-transformers not installed` | Non-blocking warning. Install with `pip install sentence-transformers` for enhanced embeddings, or ignore (TF-IDF fallback works) |
| App crashes with GL error | Set `KIVY_GL_BACKEND=angle_sdl2` (Windows) or `KIVY_GL_BACKEND=sdl2` (Linux) |
| `database is locked` | Close all Python processes and restart |
| Blank/white screen | Run from project root: `python Programma_CS2_RENAN/main.py`, verify `layout.kv` exists |
| Reset to factory state | Delete `Programma_CS2_RENAN/user_settings.json` and restart |

### Database Locations

| Database | Path | Content |
|----------|------|---------|
| Main | `Programma_CS2_RENAN/backend/storage/database.db` | Player stats, coaching state, training data |
| HLTV | `Programma_CS2_RENAN/backend/storage/hltv_metadata.db` | Professional player metadata |
| Knowledge | `Programma_CS2_RENAN/data/knowledge_base.db` | RAG knowledge base |
| Per-match | `{PRO_DEMO_PATH}/match_data/match_*.db` | Tick-level match data |

> For complete troubleshooting, see the [User Guide](docs/USER_GUIDE.md).

---

## License

This project is dual-licensed. Copyright (c) 2025-2026 Renan Augusto Macena.

You may choose either:
- **Proprietary License** — All Rights Reserved (default). Viewing for educational purposes is permitted.
- **Apache License 2.0** — Permissive open-source with patent protection.

See [LICENSE](LICENSE) for full terms.

---

## Author

**Renan Augusto Macena**

Built with passion by a Counter-Strike player with 10,000+ hours since 2004, combining deep game knowledge with AI engineering to create the ultimate coaching system.

> *"I've always wanted a professional guide -- like the real pro players have -- to understand what it truly looks like when someone trains the right way and plays the right way."*
