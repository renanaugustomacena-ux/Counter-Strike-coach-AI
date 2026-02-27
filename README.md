# Macena CS2 Analyzer

**AI-Powered Tactical Coach for Counter-Strike 2**

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

---

## What Is This?

Macena CS2 Analyzer is a desktop application that acts as a personal AI coach for Counter-Strike 2. It ingests professional and user demo files, trains multiple neural network models, and delivers personalized tactical coaching by comparing your gameplay against professional standards.

The system learns from the best professional matches ever played and adapts its coaching to your individual playstyle — whether you're an AWPer, entry fragger, support, or any other role.

---

## Key Features

- **AI Coaching Pipeline** — 4-level fallback chain (COPER > Hybrid > RAG > Base) that fuses ML predictions with retrieved tactical knowledge
- **6 AI Subsystems** — JEPA encoder, VL-JEPA vision-language alignment, RAP Coach (6-layer architecture with LTC-Hopfield memory), LSTM+MoE, Neural Role Head, Bayesian belief models
- **Tri-Daemon Engine** — Background automation with Hunter (file scanner), Digester (demo processor), and Teacher (model trainer) daemons
- **Coach Introspection Observatory** — TensorBoard integration with maturity state machine, embedding projector, and conviction tracking
- **Demo Analysis** — Tick-level parsing of `.dem` files via demoparser2, with HLTV 2.0 rating computation, round-by-round breakdowns, and momentum tracking
- **Game Theory Analysis** — Expectiminimax trees, Bayesian death probability estimation, deception index, engagement range analysis
- **Desktop App** — Kivy + KivyMD interface with tactical 2D map viewer, match history, performance dashboard, coach chat, and radar charts
- **Spatial Intelligence** — Multi-level map support (Nuke, Vertigo), pixel-accurate coordinate mapping, Z-cutoff handling
- **3-Stage Maturity Gating** — Models progress through CALIBRATING > LEARNING > MATURE with automatic quality gates
- **COPER Experience Bank** — Stores and retrieves past coaching experiences weighted by recency, effectiveness, and context similarity
- **Temporal Baseline Decay** — Tracks player skill evolution over time with exponential decay weighting
- **Ollama Integration** — Optional local LLM for natural language polishing of coaching insights

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
git clone https://github.com/renanaugustomacena-ux/Macena_cs2_analyzer.git
cd Macena_cs2_analyzer
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

### 3. Manual Setup

```bash
python -m venv venv_win
# Windows:
.\venv_win\Scripts\activate
# Linux:
source venv_win/bin/activate

pip install -r requirements.txt
python -c "from backend.storage.database import init_db; init_db()"
playwright install chromium
```

### 4. Launch

```bash
# Desktop application (Kivy GUI)
python Programma_CS2_RENAN/apps/desktop_app/main.py

# Interactive console (live TUI with real-time panels)
python console.py

# One-shot CLI (build, test, audit, hospital, sanitize)
python goliath.py
```

> For the complete guide including API key setup, feature walkthroughs, and troubleshooting, see the [User Guide](docs/USER_GUIDE.md).

---

## Architecture Overview

The system is organized into 6 AI subsystems working as a unified pipeline:

```
WATCH (Ingestion)  -->  LEARN (Training)  -->  THINK (Inference)  -->  SPEAK (Dialogue)
    Hunter daemon        Teacher daemon         COPER pipeline        Template + Ollama
    Demo parsing         3-stage maturity       RAG knowledge         Causal attribution
    Feature extraction   Multi-model training   Game theory           Pro comparisons
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| UI | Kivy + KivyMD |
| ML | PyTorch, ncps (LTC), Hopfield networks |
| Database | SQLite (WAL mode) |
| Migrations | Alembic |
| Scraping | Playwright |
| Observability | TensorBoard, Sentry |

### Project Structure

```
Programma_CS2_RENAN/
  apps/desktop_app/     Kivy UI (MVVM pattern)
  backend/
    analysis/           Game theory, belief models, momentum
    data_sources/       Demo parser, HLTV metadata
    nn/                 Neural networks (RAP Coach, JEPA, VL-JEPA)
      rap_coach/        6-layer RAP model with LTC-Hopfield memory
    processing/         Feature engineering, heatmaps, validation
    knowledge/          RAG knowledge base, COPER experience bank
    services/           Coaching service, Ollama integration
    storage/            DB models, migrations, backup
  core/                 Asset manager, map manager, session engine
  ingestion/            Steam locator, integrity checks
  observability/        RASP, telemetry
  reporting/            Visualizer, PDF generators
docs/                   User guides (EN/IT/PT), technical studies
tools/                  Validation suite, diagnostics, audit tools
```

---

## Validation & Quality

The project maintains a multi-level validation hierarchy:

| Tool | Scope | Command |
|------|-------|---------|
| Headless Validator | Regression gate (79 checks) | `python tools/headless_validator.py` |
| Pytest Suite | Logic tests (390+ tests) | `python -m pytest tests/ -x -q` |
| Backend Validator | Build health (40 checks) | `python tools/backend_validator.py` |
| Goliath Hospital | Comprehensive diagnostics | `python tools/Goliath_Hospital.py` |

---

## Documentation

| Document | Description |
|----------|-------------|
| [User Guide](docs/USER_GUIDE.md) | Complete installation and usage guide |
| [User Guide (IT)](docs/USER_GUIDE_IT.md) | Guida utente in italiano |
| [User Guide (PT)](docs/USER_GUIDE_PT.md) | Guia do usuario em portugues |
| [Project Architecture](docs/Progetto-Renan-Cs2-AI-Coach.md) | Full system architecture (Italian) |
| [Technical Studies](docs/Studies/) | 17 deep-dive research papers |
| [JEPA Analysis](jepa.md) | JEPA architecture deep analysis |
| [Console Architecture](CONSOLE_ARCHITECTURE.md) | Control console design |
| [Audit Report](MASTER_AUDIT_REPORT.md) | Final audit: 59 findings, 56 resolved |
| [Changelog](CHANGELOG.md) | Version history |

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

> *"I've always wanted a professional guide — like the real pro players have — to understand what it truly looks like when someone trains the right way and plays the right way."*

---

# User Guide

Complete guide to install, configure, and use the Macena CS2 Analyzer on Windows or Linux.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Installation](#2-installation)
3. [First Launch & Setup Wizard](#3-first-launch--setup-wizard)
4. [Configuring API Keys (Steam & FaceIT)](#4-configuring-api-keys-steam--faceit)
5. [Home Screen](#5-home-screen)
6. [Settings Page](#6-settings-page)
7. [Coach Screen & AI Chat](#7-coach-screen--ai-chat)
8. [Match History](#8-match-history)
9. [Match Detail](#9-match-detail)
10. [Performance Dashboard](#10-performance-dashboard)
11. [Tactical Viewer (2D Map Widget)](#11-tactical-viewer-2d-map-widget)
12. [User Profile](#12-user-profile)
13. [Feeding the Coach: Demo Acquisition & Storage Guide](#13-feeding-the-coach-demo-acquisition--storage-guide)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 / Ubuntu 22.04 | Windows 10/11 |
| Python | 3.10 | 3.10 or 3.12 |
| RAM | 8 GB | 16 GB |
| GPU | None (CPU mode) | NVIDIA GTX 1650+ (CUDA 12.1) |
| Disk | 3 GB free | 5 GB free |
| Display | 1280x720 | 1920x1080 |

---

## 2. Installation

### 2.1 Clone the Repository

```bash
git clone https://github.com/renanaugustomacena-ux/Macena_cs2_analyzer.git
cd Macena_cs2_analyzer
```

### 2.2 Windows (Automated Setup)

Open **PowerShell** in the project root and run:

```powershell
.\scripts\Setup_Macena_CS2.ps1
```

This script will:
- Verify Python 3.10+ is installed
- Create a virtual environment (`venv_win/`)
- Install PyTorch (CPU version) and all dependencies
- Initialize the database
- Install Playwright (Chromium browser for HLTV scraping)

**For GPU support** (NVIDIA only), after the script completes:

```powershell
.\venv_win\Scripts\pip.exe install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 2.3 Windows (Manual Setup)

If the PowerShell script fails or you prefer manual installation:

```powershell
# Create virtual environment
python -m venv venv_win
.\venv_win\Scripts\activate

# Install PyTorch (choose ONE):
# CPU only:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
# NVIDIA GPU (CUDA 12.1):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install all other dependencies
pip install -r Programma_CS2_RENAN/requirements.txt

# Initialize database
python -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database()"

# Install Playwright browser
pip install playwright
python -m playwright install chromium
```

### 2.4 Linux (Ubuntu/Debian)

```bash
# System dependencies
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev
sudo apt install -y libsdl2-dev libglew-dev build-essential

# Create virtual environment
python3.10 -m venv venv_linux
source venv_linux/bin/activate

# Install PyTorch (choose ONE):
# CPU only:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
# NVIDIA GPU (CUDA 12.1):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install dependencies (skip Windows-only kivy-deps if pip complains)
pip install -r Programma_CS2_RENAN/requirements.txt
pip install Kivy==2.3.0 KivyMD==1.2.0

# Initialize database
python -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database()"

# Install Playwright browser
pip install playwright
python -m playwright install chromium
```

### 2.5 Verify Installation

```bash
# Activate your venv first, then:
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import kivy; print(f'Kivy: {kivy.__version__}')"
python -c "from Programma_CS2_RENAN.backend.nn.config import get_device; print(f'Device: {get_device()}')"
```

Expected output (GPU example):
```
PyTorch: 2.5.1+cu121
Kivy: 2.3.0
Device: cuda:0
```

### 2.6 Launch the Application

```bash
# Windows
.\venv_win\Scripts\python.exe Programma_CS2_RENAN/main.py

# Linux
./venv_linux/bin/python Programma_CS2_RENAN/main.py
```

The window opens at 1280x720. On **first launch**, you will see the Setup Wizard.

---

## 3. First Launch & Setup Wizard

When you run main.py for the first time, the app shows a **3-step setup wizard**.

### Step 1: Welcome Screen

You see a welcome message explaining the app. Click **START** to begin configuration.

### Step 2: Brain Data Root

The app asks: **"Where should the AI store its training data?"**

This is the folder where the neural network models, knowledge base, and training datasets will be saved. It can be on any drive.

**How to set it:**
1. Click **Select Folder** — a file picker opens
2. Navigate to your desired location (e.g., `D:\CS2_Coach_Data` or `C:\Users\YourName\Documents\CS2Coach`)
3. Select the folder and confirm
4. The app creates three subdirectories inside it: `knowledge/`, `models/`, `datasets/`

**Or** paste a path manually into the text field.

> **Tip:** Choose a location with at least 2 GB of free space. An SSD is recommended for faster training.

> **If you see "Permission denied":** Choose a folder inside your user directory, like `C:\Users\YourName\Documents\MacenaData`.

Click **NEXT** when done.

### Step 3: Setup Complete

Click **LAUNCH** to enter the app. The wizard will not appear again on future launches.

> **To re-run the wizard:** Delete the file `Programma_CS2_RENAN/user_settings.json` and restart the app.

---

## 4. Configuring API Keys (Steam & FaceIT)

API keys enable the app to fetch your match history and player statistics. They are **optional** — the app works without them, but some features (automatic match import, player profile sync) will be unavailable.

### 4.1 Steam API Key

1. From the **Home Screen**, find the **Personalization** card
2. Click the **Steam** button
3. You see two fields:

**Steam ID (SteamID64):**
- This is your 17-digit Steam identifier (e.g., `76561198012345678`)
- Click the link **"Find Your Steam ID"** to open [steamid.io](https://steamid.io) in your browser
- Enter your Steam profile URL and copy the **SteamID64** number

**Steam Web API Key:**
- Click the link **"Get Steam API Key"** to open [Steam Developer](https://steamcommunity.com/dev/apikey) in your browser
- Log in with your Steam account
- When asked for a domain name, type `localhost`
- Copy the generated key

4. Paste both values and click **Save Config**

> **Security:** Your API key is stored in **Windows Credential Manager** (or the system keyring on Linux), not in plain text. The settings file shows `"PROTECTED_BY_WINDOWS_VAULT"` instead of the actual key.

### 4.2 FaceIT API Key

1. From the **Home Screen** > **Personalization** card, click **FaceIT**
2. Click the link **"Get FaceIT API Key"** to open [FaceIT Developers](https://developers.faceit.com/)
3. Create a developer account and generate an API key
4. Paste the key and click **Save**

> **Note:** The app validates keys at usage time, not at save time. If a key is invalid, you will see an error when the app tries to fetch data.

---

## 5. Home Screen

After setup, this is your main dashboard. It has a **top navigation bar** and **scrollable cards**.

### Top Navigation Bar

| Icon | Action |
|------|--------|
| Gear (left) | Opens **Settings** |
| Question mark (left) | Opens **Help** — searchable documentation topics |
| Clipboard (right) | Opens **Match History** |
| Chart (right) | Opens **Performance Dashboard** |
| Graduation cap (right) | Opens **Coach Screen** |
| Person (right) | Opens **User Profile** |

### Dashboard Cards

**1. Training Progress**
Shows real-time ML training status: current epoch, train/validation loss, estimated time remaining. When training is idle, this shows the last completed training metrics.

**2. Pro Ingestion Hub**
- **Set Folder**: Pick the folder containing your personal `.dem` demo files
- **Pro Folder**: Pick the folder containing professional player `.dem` files
- **Speed selector**: Eco (slow, low CPU), Standard (balanced), Turbo (fast, high CPU)
- **Play/Stop button**: Start or stop the demo ingestion process

**3. Personalization**
- **Profile**: Set your in-game player name
- **Steam**: Configure Steam ID and API key ([see Section 4.1](#41-steam-api-key))
- **FaceIT**: Configure FaceIT API key ([see Section 4.2](#42-faceit-api-key))

**4. Tactical Analysis**
Click **Launch Viewer** to open the 2D tactical map viewer ([see Section 11](#11-tactical-viewer-2d-map-widget)).

**5. Dynamic Insights**
Auto-populated coaching cards from the AI. Each card has:
- A **severity color** (blue = info, orange = warning, red = critical)
- A **title** and **message** explaining the insight
- A **focus area** (e.g., "Positioning", "Utility Usage")

### ML Status Bar

At the top of the dashboard, a colored bar shows the coaching service status:
- **Blue**: Service is active and running
- **Red**: Service is offline — click **RESTART SERVICE** to recover

---

## 6. Settings Page

Access from the gear icon on the Home Screen. All changes are saved immediately.

### Visual Theme

Three theme presets that change the app's color scheme and wallpaper:
- **CS2** (orange tones)
- **CS:GO** (blue-gray tones)
- **CS 1.6** (green tones)

Click **Cycle Wallpaper** to rotate through available background images for the current theme.

### Analysis Paths

- **Default Demo Folder**: Where your personal `.dem` files are stored. Click **Change** to pick a new folder.
- **Pro Demo Folder**: Where professional player `.dem` files are stored. Click **Change** to pick a new folder.

> **Important:** When you change the Pro Demo Folder, the app automatically migrates the match database files (`match_data/`) to the new location.

### Appearance

- **Font Size**: Small (12pt), Medium (16pt), or Large (20pt)
- **Font Type**: Choose from Roboto, Arial, JetBrains Mono, New Hope, CS Regular, or YUPIX

### Data Ingestion Control

- **Mode Toggle**: Switch between **Manual** (one-shot scan) and **Auto** (continuous scanning at intervals)
- **Scan Interval**: How often (in minutes) auto-mode checks for new demos. Minimum: 1 minute.
- **Start/Stop Ingestion**: Manually trigger or stop the ingestion process

### Language

Switch between English, Italiano, and Portugues. The entire UI updates immediately.

---

## 7. Coach Screen & AI Chat

Access from the graduation cap icon on the Home Screen.

### Dashboard

- **Belief State**: Shows the AI coach's inference confidence (0-100%). Green when above 70%.
- **Trend Graph**: Line chart of your Rating and ADR over the last 20 matches.
- **Skill Radar**: Spider chart showing 5 skill dimensions (Aim, Utility, Positioning, Map Sense, Clutch) compared to professional baselines.
- **Causal Audit**: Click **Show Advantage Audit** to view causal analysis of your decisions.
- **Knowledge Engine**: Shows how many experience ticks the AI has processed and current parsing progress.
- **Coaching Cards**: AI-generated insights with severity levels.

### Chat Panel

Click the **chat toggle** button (bottom of screen) to expand the chat panel.

- **Quick Action Buttons**: Pre-built questions — "Positioning", "Utility", "What to improve?"
- **Text Input**: Type any question about your gameplay
- **Coach Replies**: The AI analyzes your match data and provides personalized advice

> **Note:** The coach's quality improves with more ingested demos. Minimum 10 demos recommended for meaningful insights.

---

## 8. Match History

Access from the clipboard icon on the Home Screen.

Shows a scrollable list of your **last 50 non-pro matches**. Each match card displays:

- **Rating badge** (left side, color-coded):
  - Green: Rating > 1.10 (above average)
  - Yellow: Rating 0.90 - 1.10 (average)
  - Red: Rating < 0.90 (below average)
- **Map name** and **date**
- **Stats**: K/D ratio, ADR, Kills, Deaths

**Click any match** to open the [Match Detail](#9-match-detail) screen.

---

## 9. Match Detail

Shows in-depth analysis of a single match, organized in 4 sections:

### Overview
Map name, date, overall rating (color-coded), and a stats grid: Kills, Deaths, ADR, KAST%, HS%, K:D ratio, KPR (Kills Per Round), DPR (Deaths Per Round).

### Round Timeline
A list of every round played, showing:
- Round number and side (CT/T)
- Kills, Deaths, Damage dealt
- Opening kill badge (if applicable)
- Round result (Win/Loss)

### Economy Graph
A bar chart showing your equipment value per round. Blue bars = CT side, Yellow bars = T side. Helps identify eco/force-buy patterns.

### Highlights & Momentum
- **Momentum Graph**: Line chart of your cumulative Kill-Death delta across rounds. Green fill = positive momentum, Red fill = negative.
- **Coaching Insights**: AI-generated analysis specific to this match.

---

## 10. Performance Dashboard

Access from the chart icon on the Home Screen. Shows your long-term performance trends.

### Rating Trend
Sparkline chart of your rating over the last 50 matches. Reference lines at:
- 1.10 (green) — top performance
- 1.00 (white) — average
- 0.90 (red) — below average

### Per-Map Performance
Horizontally scrollable cards, one per map (de_dust2, de_mirage, etc.). Each shows:
- Average rating (color-coded)
- Average ADR and K:D ratio
- Number of matches played

### Strengths & Weaknesses
Two-column comparison against professional player baselines using Z-scores:
- **Left (Green)**: Your strongest metrics
- **Right (Red)**: Areas needing improvement

### Utility Panel
Bar chart comparing your utility usage to professional baselines across 6 metrics:
- HE Grenades, Molotovs, Smoke Grenades
- Flash Blind Time, Flash Assists, Unused Utility

---

## 11. Tactical Viewer (2D Map Widget)

Access from **Launch Viewer** on the Home Screen.

This is the real-time 2D replay viewer. It renders demo files as an interactive map visualization.

### What You See
- **2D Map**: Top-down view of the CS2 map with player positions as colored circles
- **Player Labels**: Name, role, and health bars for each player
- **Event Markers**: Kill icons, bomb plant/defuse indicators
- **AI Overlay**: Ghost predictions showing AI-suggested positions (when enabled)

### Controls
- **Play/Pause**: Start or stop playback
- **Speed**: Toggle between 0.5x, 1x, 2x speed
- **Timeline Scrubber**: Click anywhere on the horizontal bar to jump to a specific tick
- **Map Selector**: Switch between maps (for multi-map demos)
- **Round Selector**: Jump to a specific round or view the full match
- **Ghost AI Toggle**: Enable/disable AI position predictions

### Loading a Demo
On first enter, a file picker opens automatically. Select a `.dem` file to load. The viewer parses and renders the demo data.

---

## 12. User Profile

Access from the person icon on the Home Screen.

Shows your player avatar, name, role, and bio. Click the **pencil icon** to edit your bio and role. Click **SYNC WITH STEAM** to pull your profile data from Steam (requires Steam API key).

---

## 13. Feeding the Coach: Demo Acquisition & Storage Guide

The AI coach ships with **no pre-trained knowledge**. It learns exclusively from professional CS2 match demo files (`.dem`). The quality and depth of coaching you receive is directly proportional to the quality and quantity of demos you ingest. Without demos, the coaching screens will display "Calibrating" and most coaching features remain inactive.

This section explains how to acquire demo files, how many you need, and how to plan your storage.

### 13.1 Why Your Coach Starts Empty

Unlike traditional coaching tools that ship with static tips, Macena CS2 Analyzer builds its intelligence from **real professional gameplay**. At first launch:

- The neural networks (RAP Coach, JEPA, Belief Model) have random weights with zero tactical knowledge
- The coaching pipeline has no professional baseline to compare your gameplay against
- The experience bank and RAG knowledge system are empty

This is by design. The coach learns from real professional match data, not synthetic or pre-fabricated advice. The more high-quality demos you feed it, the more nuanced and accurate its coaching becomes.

### 13.2 How to Download Pro Demos from HLTV.org

Follow these steps to build your professional demo library:

1. Go to [hltv.org](https://www.hltv.org) and navigate to **Results**
2. Filter by **top-tier events**: Major Championships, IEM Katowice/Cologne, BLAST Premier, ESL Pro League, PGL Major
3. Select matches involving **top-20 ranked teams** (e.g., Navi, FaZe, Vitality, G2, Spirit, Heroic)
4. Prefer **BO3 or BO5 series** — more rounds per download means more training data per file
5. On the match page, click **"Watch Demo"** (or "GOTV Demo") to download the `.dem` file
6. **Diversify maps** — cover all Active Duty maps (Mirage, Inferno, Nuke, Ancient, Anubis, Dust2, Vertigo). Downloading 50 demos of one map will create a biased coach
7. **Choose carefully** — pick the best matches: tournament finals, playoff elimination matches, and Grand Finals. These contain the highest tactical depth

**What to avoid:**
- Showmatches and exhibition games (low tactical intensity)
- Qualifiers with unknown/amateur teams (inconsistent quality)
- Charity events or content creator matches
- Very old demos (meta changes make them less relevant)

**Recommended events (highest quality):**
- CS2 Major Championships (any year)
- IEM Katowice, IEM Cologne
- BLAST World Final, BLAST Premier
- ESL Pro League Finals
- PGL Major series

### 13.3 How Many Demos to Download

The more demos you ingest, the better your coach becomes. Here are the coaching tiers:

| Pro Demos Ingested | Coaching Tier | Confidence | Coach Behavior |
|-------------------|---------------|-----------|----------------|
| **0 - 9** | Not ready | 0% | Coach inactive. Minimum 10 pro demos required to start the first training cycle. |
| **10 - 49** | CALIBRATING | 50% | Basic coaching active. Advice is marked as provisional. |
| **50 - 199** | LEARNING | 80% | Intermediate coaching. Growing confidence, increasingly reliable. |
| **200+** | MATURE | 100% | Full confidence. Production-ready coaching with maximum accuracy. |

**Key thresholds:**
- **10 pro demos**: First training cycle triggers automatically. This is the absolute minimum.
- **10% growth**: After the first cycle, retraining auto-triggers every time your pro demo count grows by 10% (e.g., 10 → 11, 50 → 55, 100 → 110).
- **50 demos**: Recommended minimum for meaningful, actionable coaching.
- **200+ demos**: Target for mature, high-confidence coaching across all maps and scenarios.

**The golden rule: more demos = better coach.** Download as many high-quality pro demos as you can. There is no upper limit — the system continuously improves with more data.

### 13.4 Maturity Gates Explained

Two maturity systems operate in parallel:

**A. Demo-Count Tiers** (primary, visible in the app)

These tiers are based on the raw number of ingested pro demos (see table in section 13.3). They directly control the confidence multiplier applied to all coaching advice.

**B. Conviction Index** (advanced, visible via TensorBoard)

During training, the AI tracks a composite "conviction index" (0.0 to 1.0) computed from five neural signals: belief entropy, gate specialization, concept focus, value accuracy, and role stability.

| State | Conviction Index | What It Means |
|-------|-----------------|---------------|
| **DOUBT** | < 0.30 | Model uncertain. Beliefs noisy, experts not specializing. |
| **LEARNING** | 0.30 - 0.60 | Actively forming beliefs. Experts beginning to differentiate. |
| **CONVICTION** | > 0.60 (stable for 10+ epochs) | Strong, consistent beliefs across training batches. |
| **MATURE** | > 0.75 (stable for 20+ epochs) | Converged model. Production-ready inference. |
| **CRISIS** | Sharp drop > 20% | Anomaly detected (overfitting or data distribution shift). Investigation needed. |

The conviction index provides deeper insight into the AI's internal state beyond just demo count. You can monitor it in real-time via TensorBoard (see section 13.6).

### 13.5 Storage Planning

`.dem` files are **large** — typically 300 to 850 MB each. As you build your demo library, storage requirements grow significantly. Plan ahead.

**Space Estimates:**

| Pro Demos | Raw .dem Files | Match Databases | Total Estimate |
|-----------|---------------|-----------------|----------------|
| 10 | ~5 GB | ~1 GB | **~6 GB** |
| 50 | ~30 GB | ~5 GB | **~35 GB** |
| 100 | ~60 GB | ~10 GB | **~70 GB** |
| 200 | ~120 GB | ~20 GB | **~140 GB** |

**Recommendations:**

- **Use a separate drive** with plenty of free space for your Pro Demo Folder. An HDD is perfectly fine for demo storage; SSD is preferred for the Brain Data Root (AI models and training)
- **Create a dedicated folder** (e.g., `D:\CS2_Pro_Demos\`) BEFORE you start downloading demos
- Configure this path in **Settings > Analysis Paths > Pro Demo Folder**
- If you store demos on the **same drive** as the program, ensure you have at least **50 GB of free space** beyond your OS and application needs
- The `match_data/` folder (per-match SQLite databases) is automatically created alongside your Pro Demo Folder
- The system does **NOT** auto-delete old demos — monitor your drive space periodically

**Why three separate storage locations?**

| Location | What It Stores | Where to Place It |
|----------|---------------|-------------------|
| **Core Database** (program folder) | Player stats, coaching state, HLTV metadata | Always stays in the program folder. Portable. |
| **Brain Data Root** (Setup Wizard) | AI model weights, logs, knowledge base, cache | SSD recommended for faster training. |
| **Pro Demo Folder** (Settings) | Raw .dem files + per-match SQLite databases | Needs the most space. HDD is acceptable. |

### 13.6 TensorBoard Monitoring

You can monitor the coach's training progress and maturity in real-time using TensorBoard.

**Launch TensorBoard:**
```bash
tensorboard --logdir runs/coach_training
```

Then open [http://localhost:6006](http://localhost:6006) in your browser.

**Key metrics to watch:**
- **`maturity/conviction_index`** (Scalars): Should trend upward over training epochs
- **`maturity/state`** (Text): Tracks transitions through doubt → learning → conviction → mature
- **`maturity/gate_specialization`** (Scalars): Higher values mean the expert network is becoming more specialized
- **`loss/train`** and **`loss/val`** (Scalars): Training and validation loss curves — both should decrease
- **`gates/mean_activation`** (Scalars): Gate routing in the mixture-of-experts layer

TensorBoard is optional but highly recommended for users who want to understand how their coach is evolving.

### 13.7 First Coaching Cycle: Step-by-Step Checklist

Follow this checklist from installation to your first coaching advice:

1. **Install** the application and complete the **Setup Wizard** (configure your Brain Data Root)
2. Go to **Settings > Analysis Paths** and set your **Pro Demo Folder** to a dedicated drive/folder with ample space
3. **Download at least 10 pro demos** from HLTV.org (diverse maps!)
4. **Place the `.dem` files** in your configured Pro Demo Folder
5. **Launch the app** — the Hunter daemon automatically discovers new demo files
6. **Wait for ingestion** — each demo takes approximately 5-10 minutes to process. Monitor progress on the Home Screen
7. After **10 pro demos are ingested**, the Teacher daemon automatically starts the **first training cycle**
8. *(Optional)* **Monitor maturity** via TensorBoard to see the conviction index rise
9. **Connect your Steam account** (Home > Personalization > Steam ID)
10. **Play 10+ competitive matches** — your personal demos are auto-located via Steam integration
11. Once you have **10+ personal demos AND 10+ pro demos**, the full coaching pipeline activates!

### 13.8 Troubleshooting: Disk Space

- **Drive full?** Move your Pro Demo Folder to a larger drive via Settings. The `match_data/` directory migrates automatically.
- **Database growing too fast?** The per-match SQLite files in `match_data/` can be individually deleted for old matches you no longer need to review in detail.
- **Want to save space but keep coaching?** The `.dem` files can be deleted after ingestion — all necessary data is extracted into the match databases during processing. However, keeping the original `.dem` files allows future re-ingestion if the demo parser is upgraded.
- **Cache taking space?** The ingestion cache in `ingestion/cache/` can be safely cleared. Demos will be re-parsed from the original `.dem` files on next access.

---

## 14. Troubleshooting

### "ModuleNotFoundError: No module named 'kivy'"

Kivy dependencies are not installed. On Windows:
```bash
pip install kivy-deps.glew==0.3.1 kivy-deps.sdl2==0.7.0 kivy-deps.angle==0.4.0
pip install Kivy==2.3.0 KivyMD==1.2.0
```
On Linux, skip the `kivy-deps` packages — they are Windows-only.

### "No module named 'watchdog'"

```bash
pip install watchdog
```
This is needed for automatic demo file detection. Without it, use manual ingestion from Settings.

### "CUDA not available" / GPU not detected

Verify your NVIDIA driver is installed:
```bash
nvidia-smi
```
Then reinstall PyTorch with CUDA:
```bash
pip install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```
Verify:
```bash
python -c "import torch; print(torch.cuda.is_available())"  # Should print True
```

> **No NVIDIA GPU?** The app works on CPU. Training is slower but everything functions.

### "sentence-transformers not installed" warning

This is **normal** and non-blocking. The app falls back to TF-IDF embeddings. To install:
```bash
pip install sentence-transformers
```
First run downloads a ~80MB model — this is expected.

### App crashes on launch with Kivy GL error

On Windows, try:
```bash
set KIVY_GL_BACKEND=angle_sdl2
python Programma_CS2_RENAN/main.py
```
On Linux:
```bash
export KIVY_GL_BACKEND=sdl2
python Programma_CS2_RENAN/main.py
```

### Database lock error ("database is locked")

Another process has the database open. Close all Python processes:
```bash
# Windows
taskkill /F /IM python.exe
# Linux
pkill -f python
```
Then restart the app.

### Permission denied when selecting folders

Choose a folder inside your user directory:
- Windows: `C:\Users\YourName\Documents\MacenaData`
- Linux: `~/MacenaData`

Avoid system-protected paths like `C:\Program Files\` or `/usr/`.

### "Integrity mismatch detected" warning

This is a development-mode warning from the RASP security audit. It means source files have been modified since the last integrity manifest was generated. **It does not block the app** — it only blocks frozen/production builds.

### App opens but shows a blank/white screen

The KV layout file failed to load. Check:
1. You are running from the project root (not from inside `Programma_CS2_RENAN/`)
2. The file `Programma_CS2_RENAN/apps/desktop_app/layout.kv` exists
3. Run: `python Programma_CS2_RENAN/main.py` (not `python main.py`)

### How to reset the app to factory state

Delete `user_settings.json` and restart:
```bash
# Windows
del Programma_CS2_RENAN\user_settings.json
# Linux
rm Programma_CS2_RENAN/user_settings.json
```
The setup wizard will appear again on next launch.

### Where are my databases stored?

| Database | Location | Content |
|----------|----------|---------|
| Main DB | `Programma_CS2_RENAN/backend/storage/database.db` | Player stats, coaching state, training data |
| HLTV DB | `Programma_CS2_RENAN/backend/storage/hltv_metadata.db` | Professional player metadata (separate from training) |
| Knowledge DB | `Programma_CS2_RENAN/data/knowledge_base.db` | RAG knowledge base |
| Match DBs | `{PRO_DEMO_PATH}/match_data/match_*.db` | Per-match tick-level data |

---

## Quick Reference

| Action | How |
|--------|-----|
| Launch app | `python Programma_CS2_RENAN/main.py` |
| Re-run wizard | Delete `user_settings.json`, restart |
| Change demo folder | Settings > Analysis Paths > Change |
| Add Steam key | Home > Personalization > Steam |
| Add FaceIT key | Home > Personalization > FaceIT |
| Start ingestion | Home > Pro Ingestion Hub > Play button |
| View match replay | Home > Launch Viewer |
| Ask the AI coach | Coach Screen > Chat toggle > Type question |
| Change theme | Settings > Visual Theme |
| Change language | Settings > Language |
