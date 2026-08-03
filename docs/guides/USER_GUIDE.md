# Macena CS2 Analyzer — User Guide

Complete guide to install, configure, and use the Macena CS2 Analyzer on Windows or Linux.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Installation](#2-installation)
3. [First Launch & Setup Wizard](#3-first-launch--setup-wizard)
4. [Configuring API Keys (Steam & FaceIT)](#4-configuring-api-keys-steam--faceit)
5. [Home Screen (Dashboard)](#5-home-screen-dashboard)
6. [Settings Page](#6-settings-page)
7. [Coach Panel & AI Chat](#7-coach-panel--ai-chat)
8. [Match History](#8-match-history)
9. [Match Detail](#9-match-detail)
10. [Performance Dashboard](#10-performance-dashboard)
11. [Tactical Viewer (2D Map Widget)](#11-tactical-viewer-2d-map-widget)
12. [User Profile](#12-user-profile)
13. [AI Coaching Best Practices](#13-ai-coaching-best-practices)
14. [Advanced Configuration (Expert Mode)](#14-advanced-configuration-expert-mode)
15. [Performance Optimization](#15-performance-optimization)
16. [Community & Support](#16-community--support)
17. [Troubleshooting](#17-troubleshooting)

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
git clone https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI.git
cd Counter-Strike-coach-AI
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
- Install Playwright (Chromium browser used by the scraping tooling)

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

# Install all other dependencies (requirements.txt is at the repo root)
pip install -r requirements.txt

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
sudo apt install -y build-essential

# Create virtual environment
python3.10 -m venv venv_linux
source venv_linux/bin/activate

# Install PyTorch (choose ONE):
# CPU only:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
# NVIDIA GPU (CUDA 12.1):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install dependencies (requirements.txt is at the repo root; includes PySide6)
pip install -r requirements.txt

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
python -c "import PySide6; print(f'PySide6: {PySide6.__version__}')"
python -c "from Programma_CS2_RENAN.backend.nn.config import get_device; print(f'Device: {get_device()}')"
```

Expected output (GPU example — the pinned PySide6 version is 6.11.0; the PyTorch version depends on the build you installed):
```
PyTorch: 2.x.y+cu121
PySide6: 6.11.0
Device: cuda:0
```

### 2.6 Launch the Application

```bash
# Windows
.\venv_win\Scripts\python.exe -m Programma_CS2_RENAN.apps.qt_app.app

# Linux
./venv_linux/bin/python -m Programma_CS2_RENAN.apps.qt_app.app
```

The window opens at 1280x720. On **first launch**, you will see the Setup Wizard.

---

## 3. First Launch & Setup Wizard

When you launch the app for the first time, it shows a **5-step setup wizard**:
Intro → Player Name → Brain Path → Demo Path → Finish.

### Step 1: Welcome Screen

You see a welcome message explaining the app. Click **Get Started** to begin configuration.

### Step 2: Player Name

Enter your **CS2 in-game name**. It must match the player name inside your demo files, otherwise the analyzer cannot identify which player is you.

### Step 3: Brain Data Root

The app asks where the AI should store its data (models, knowledge base, datasets).

This is the folder where the neural network models, knowledge base, and training datasets will be saved. It can be on any drive.

**How to set it:**
1. Click the folder picker — a file dialog opens
2. Navigate to your desired location (e.g., `D:\CS2_Coach_Data` or `C:\Users\YourName\Documents\CS2Coach`)
3. Select the folder and confirm
4. The app creates three subdirectories inside it: `knowledge/`, `models/`, `datasets/`

**Or** paste a path manually into the text field.

> **Tip:** Choose a location with plenty of free space (the wizard recommends >50 GB for AI training data). An SSD is recommended for faster training.

> **If you see "Permission denied":** Choose a folder inside your user directory, like `C:\Users\YourName\Documents\MacenaData`.

Click **Next** when done.

### Step 4: Demo Path

Optionally point the app at the folder containing your `.dem` files. You can skip this and set it later from the Home dashboard or Settings.

### Step 5: Setup Complete

Click **Launch App** to enter the app. The wizard will not appear again on future launches.

> **To re-run the wizard:** Delete the file `Programma_CS2_RENAN/user_settings.json` and restart the app.

---

## 4. Configuring API Keys (Steam & FaceIT)

API keys enable the app to fetch your match history and player statistics. They are **optional** — the app works without them, but some features (automatic match import, player profile sync) will be unavailable.

> **Note:** The app contains dedicated **Steam Config** and **FaceIT Config** screens, but the redesigned sidebar navigation does not currently include a button that opens them — a known gap of the dashboard redesign. The instructions below describe those screens; the same values (`STEAM_ID`, API keys) can also be set by editing `user_settings.json` (see Section 14).

### 4.1 Steam API Key

On the **Steam Config** screen you see two fields:

**Steam ID (SteamID64):**
- This is your 17-digit Steam identifier (e.g., `76561198012345678`)
- Click the link **"Find Your Steam ID"** to open [steamid.io](https://steamid.io) in your browser
- Enter your Steam profile URL and copy the **SteamID64** number

**Steam Web API Key:**
- Click the link **"Get Steam API Key"** to open [Steam Developer](https://steamcommunity.com/dev/apikey) in your browser
- Log in with your Steam account
- When asked for a domain name, type `localhost`
- Copy the generated key

Paste both values and click **Save Config**.

> **Security:** When the `keyring` package is available, your API key is stored in **Windows Credential Manager** (or the system keyring on Linux), not in plain text — the settings file shows `"PROTECTED_BY_WINDOWS_VAULT"` instead of the actual key. If no system keyring is available, the screen warns you that keys will be stored on disk in plaintext.

### 4.2 FaceIT API Key

On the **FaceIT Config** screen:

1. Click the link **"Get FaceIT API Key"** to open [FaceIT Developers](https://developers.faceit.com/)
2. Create a developer account and generate an API key
3. Paste the key and click **Save**

> **Note:** The app validates keys at usage time, not at save time. If a key is invalid, you will see an error when the app tries to fetch data.

---

## 5. Home Screen (Dashboard)

After setup, this is your main dashboard. Navigation is via a **collapsible sidebar** on the left; the dashboard itself is composed of a title rail, a hero pair, a recent-matches strip, and a utility row.

### Sidebar Navigation

| Item | Shortcut | Opens |
|------|----------|-------|
| Dashboard | `Ctrl+1` | Home screen |
| Coach | `Ctrl+2` | Toggles the dockable AI coach panel |
| Match History | `Ctrl+3` | List of analyzed demos |
| Advanced Analytics | `Ctrl+4` | Performance Dashboard |
| Tactical Analyzer | `Ctrl+5` | 2D replay viewer |
| Settings | `Ctrl+,` | Settings page |
| Help Center | `F1` | Searchable documentation topics |

The hamburger button at the top collapses the sidebar to icons only.

### Dashboard Composition

**Title rail** — "Dashboard" title plus status chips, including a match counter ("N yours · M pro demos").

**Hero pair**
- **Last Match**: your most recent analyzed match with a mini rating trend; buttons to re-analyze or open the match detail.
- **Focus This Week**: the AI's current top improvement area, with a shortcut to the relevant screen.

**Recent Matches strip** — horizontally scrolling mini-cards for your latest matches (click one to open Match Detail; "View all" opens Match History).

**Utility row**
- **Ingest card**: two rows — **PERSONAL** (your demo folder + **Analyze** button) and **PRO BASELINE** (professional demo folder + **Analyze pro** button). Each row has a **Change** button to pick the folder and shows ingestion progress/status underneath.
- **Training card**: appears only while ML training is active — current epoch, loss, and ETA.
- **Tactical card**: **Open viewer** (2D replay viewer, [see Section 11](#11-tactical-viewer-2d-map-widget)) and **Compare pros** (pro comparison screen).

**Cold start** — before your first analyzed match, the hero pair is replaced by a single onboarding card pointing you at the Ingest card.

---

## 6. Settings Page

Access from the sidebar (**Settings**, or `Ctrl+,`). Settings are organized into **3 tabs** and all changes are saved immediately.

### Tab 1: Appearance

**Visual Theme** — three presets that change the app's color scheme and wallpaper:
- **CS2** (orange tones)
- **CS:GO** (blue-gray tones)
- **CS 1.6** (green tones)

**Wallpaper** — toggle buttons to pick among the background images available for the current theme.

**Font Size** — Small (11pt), Medium (13pt), or Large (16pt)

**Font Type** — Choose from Roboto, Arial, JetBrains Mono, New Hope, CS Regular, or YUPIX

### Tab 2: Paths & Data

**Analysis Paths**
- **Demo Path**: Where your personal `.dem` files are stored. Click **Change** to pick a new folder.
- **Pro Path**: Where professional player `.dem` files are stored. Click **Change** to pick a new folder.

> **Note:** Per-match databases live in a `match_data/` subfolder of the Pro Demo Path. Changing the path only updates the setting — move the `match_data/` folder yourself if you relocate an existing library.

**Data Ingestion Control**
- **Mode Toggle**: Switch between **Manual** (one-shot scan) and **Auto** (continuous scanning at intervals)
- **Scan Interval (min)**: How often auto-mode checks for new demos (default 30; minimum 1 minute — click **Set** to apply)
- **Start/Stop Ingestion**: Manually trigger or stop the ingestion process

### Tab 3: General

**Language** — Switch between English, Italiano, and Portugues. The entire UI updates immediately.

**Flagship Features** — opt-in polish toggles (UI sounds, frameless window, pyqtgraph heatmap). All default off; some require a restart.

---

## 7. Coach Panel & AI Chat

Click **Coach** in the sidebar (`Ctrl+2`). The coach is a **dockable panel**: it opens pinned to the right side (or bottom), can be floated as its own window, and the sidebar button toggles it on/off. Its position and visibility are remembered between launches.

### Panel Contents

- **Belief State**: A ring showing the AI coach's inference confidence (0-100%).
- **Recent Insights**: AI-generated coaching insights from your analyzed matches.
- **Status chip**: Shows whether the chat backend (local LLM) is available.

### Chat Composer

Click **Open chat** in the panel's title rail to slide the chat composer up.

- **Quick Action Buttons**: Pre-built questions — "How can I improve positioning?", "Analyze utility usage", "What should I focus on improving?"
- **Text Input**: Type any question about your gameplay
- **Coach Replies**: The AI analyzes your match data and provides personalized advice

> **Note:** The coach's quality improves with more ingested demos. Minimum 10 demos recommended for meaningful insights.

---

## 8. Match History

Access from the sidebar (**Match History**, `Ctrl+3`).

Shows a filterable list of the **last 50 analyzed matches** (yours and pro demos together):

- **Source filters**: chips for **All / Personal / Pro**
- **Map filters**: chips for **All maps** plus each map found in your history
- Each match row displays:
  - **Rating** (color-coded): green above 1.10, yellow between 0.90 and 1.10, red below 0.90 — with a text label (e.g., "Good") for color-blind accessibility
  - **Map name** and **date**
  - **Stats**: K/D, ADR, kill/death counts, and a "pro" marker for pro-baseline rows

**Click any match** to open the [Match Detail](#9-match-detail) screen.

---

## 9. Match Detail

Shows in-depth analysis of a single match, organized in 4 tabs (**Overview · Rounds · Economy · Highlights**), with a Back button returning to Match History:

### Overview
Map name, date, overall rating (color-coded), a stats grid (kills, deaths, ADR, KAST%, HS%, and derived ratios), a color-coded per-round win/loss strip, and HLTV-style rating details.

### Rounds
A list of every round played, showing:
- Round number and side (CT/T)
- Kills, Deaths, Damage dealt
- Round result (Win/Loss)

### Economy
A bar chart showing your equipment value per round. Helps identify eco/force-buy patterns.

### Highlights
- **Momentum Graph**: Chart of your cumulative kill-death delta across rounds.
- **Coaching Insights**: AI-generated analysis specific to this match.

---

## 10. Performance Dashboard

Access from the sidebar (**Advanced Analytics**, `Ctrl+4`). Shows your long-term performance trends in sectioned cards, headed by a hero stats strip.

### Trend
Summary of your rating history — average, range, and recent form.

### Per-Map Performance
A grid of map mini-cards (de_dust2, de_mirage, etc.). Each shows:
- Average rating (color-coded)
- Key averages and number of matches played

### Strengths & Weaknesses
Two-column comparison against professional player baselines:
- **Left**: Your strongest metrics
- **Right**: Areas needing improvement

### Utility
Comparison of your utility numbers per round against the professional baseline.

> If you have not analyzed any personal demos yet, the screen shows an empty state pointing you back to the Home dashboard.

---

## 11. Tactical Viewer (2D Map Widget)

Access from the sidebar (**Tactical Analyzer**, `Ctrl+5`) or from the Home dashboard's Tactical card (**Open viewer**).

This is the 2D replay viewer. It renders demo files as an interactive map visualization.

### What You See
- **2D Map**: Top-down view of the CS2 map with player positions as colored markers
- **Player Sidebar**: Per-player details for the current frame
- **Grenade/Event Rendering**: Utility and key events on the map
- **AI Overlay**: Ghost predictions showing AI-suggested positions (when enabled)

### Controls
- **Play/Pause**: Start or stop playback
- **Speed**: 0.5x, 1x, 2x, or 4x playback speed
- **Timeline**: Click the timeline to jump to a specific tick
- **Map Selector** and **Round Selector**: Jump to a specific map/round
- **Ghost AI checkbox**: Enable/disable AI position predictions
- **Next critical moment**: Skips to Chronovisor-detected key moments (enabled after a scan)

### Loading a Demo
Click **Open Demo** — a file picker opens (starting in your configured demo folder). Select a `.dem` file; the viewer parses it in passes and then renders it.

> An optional WebEngine-based viewer (React) exists behind the Flagship toggle and requires building the web assets with `tools/build_web.py`; otherwise the Qt-native viewer is used.

---

## 12. User Profile

The app includes a User Profile screen showing your player name, role, and bio, with an **Edit Profile** dialog and a **Sync with Steam** button to pull profile data from Steam (requires Steam API key).

> **Note:** Like the Steam/FaceIT config screens (Section 4), this screen is not currently linked from the sidebar navigation after the dashboard redesign. Your in-game player name is set in the setup wizard and stored as `CS2_PLAYER_NAME` in `user_settings.json`.

---

## 13. AI Coaching Best Practices

To get the most out of the AI coach, follow these guidelines:

- **Be Specific in Chat**: Instead of asking "How am I doing?", try "How was my positioning on de_mirage A-site?" or "What utility should I use for B-split on Anubis?". The more context you provide, the better the retrieval engine can surface relevant match data.
- **The "10-Demo Rule"**: The AI's "Belief State" and the performance analytics require a baseline of data to be accurate. We recommend ingesting at least **10 recent demos** before trusting the long-term trend analysis.
- **Strengths & Weaknesses**: A weak area flagged on the Performance Dashboard (e.g., "Utility") is a direct hint to watch the corresponding section and ask the coach about it.
- **The Belief State**: This percentage (0-100%) indicates how confident the AI is in its current assessment. If it's below 50%, ingest more demos to reduce the "variance" in your profile.

---

## 14. Advanced Configuration (Expert Mode)

For power users and server admins, the app can be fine-tuned via the `user_settings.json` file located in the `Programma_CS2_RENAN/` directory (for frozen/installed builds: `%LOCALAPPDATA%\MacenaCS2Analyzer\`).

### Manual Settings Editing
You can manually edit `user_settings.json`. Keys used by the app include:
- `CS2_PLAYER_NAME`: your in-game name (must match the demos)
- `DEFAULT_DEMO_PATH` / `PRO_DEMO_PATH`: personal and pro demo folders
- `BRAIN_DATA_ROOT`: the AI data root chosen in the wizard
- `STEAM_ID`: your SteamID64 (API keys go to the system keyring, not this file)
- `ACTIVE_THEME`, `FONT_SIZE`, `FONT_TYPE`, `LANGUAGE`: UI preferences
- `INGEST_INTERVAL_MINUTES`: auto-ingestion scan interval
- `COACH_DOCK_AREA` / `COACH_DOCK_FLOATING` / `COACH_DOCK_VISIBLE`: coach panel layout

### Headless & Server Setups
If running on a headless Linux server:
- Use the auto-ingestion mode and `INGEST_INTERVAL_MINUTES` to keep the database synced with a folder being populated by an external `ftp` or `rsync` script.
- Run the ingestion worker without the Qt GUI:
  ```bash
  python -m Programma_CS2_RENAN.run_worker
  ```

---

## 15. Performance Optimization

### Low-End PC Tips
- **Avoid analyzing during play**: Run demo ingestion while you are not in-game — parsing is CPU-heavy.
- **Font Quality**: In Settings, choose "Roboto" or "Arial" for better rendering performance on integrated GPUs.
- **Reduce UI Scale**: Use the "Small" font size to reduce the memory footprint of the Qt window.

### Storage: SSD vs HDD
The **Brain Data Root** contains thousands of small `.json` and `.pt` files.
- **SSD (Highly Recommended)**: Up to 10x faster model loading and knowledge base retrieval.
- **HDD**: Expect significant delays when opening the "Coach Screen" or switching between match details.

### CUDA Stability
If the app crashes frequently on NVIDIA cards, reinstall the CPU-only PyTorch build to bypass the CUDA toolkit and run the neural network on your processor:
```bash
pip install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

---

## 16. Community & Support

- **Contributing**: We welcome contributions! Please read `CONTRIBUTING.md` in the root directory for coding standards and pull request workflows.
- **Reporting Bugs**: Found a bug? Open an issue on GitHub using the **Bug Report** template. Include your `logs/app.log` and system specs.
- **Feature Requests**: Use the GitHub **Discussions** or **Feature Request** template to suggest new AI models or UI widgets.

---

## 17. Troubleshooting

### "Antivirus blocking the ingestion script"
Some antivirus software (like Windows Defender or Bitdefender) may flag the demo parser as a "Trojan" because it reads memory-like structures from binary files.
- **Fix**: Add the project folder to your antivirus **Exclusion List**.

### "ModuleNotFoundError: No module named 'PySide6'"

PySide6 (the Qt UI framework) is not installed:
```bash
pip install PySide6
```

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

This is **normal** and non-blocking. The app falls back to simple hash-based embeddings. To install:
```bash
pip install sentence-transformers
```
First run downloads a ~80MB model — this is expected.

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

Ensure you are running from the project root directory (not from inside `Programma_CS2_RENAN/`). Try: `python -m Programma_CS2_RENAN.apps.qt_app.app`

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
| Knowledge DB | `Programma_CS2_RENAN/data/knowledge_base.db` (under your Brain Data Root's `data/` folder if one is configured) | RAG knowledge base |
| Match DBs | `{PRO_DEMO_PATH}/match_data/match_*.db` | Per-match tick-level data |

---

## Quick Reference

| Action | How |
|--------|-----|
| Launch app | `python -m Programma_CS2_RENAN.apps.qt_app.app` |
| Re-run wizard | Delete `user_settings.json`, restart |
| Change demo folder | Settings > Paths & Data > Change (or Home > Ingest card > Change) |
| Add Steam / FaceIT keys | See Section 4 (config screens / `user_settings.json`) |
| Start ingestion | Home > Ingest card > Analyze / Analyze pro |
| View match replay | Sidebar > Tactical Analyzer (`Ctrl+5`) |
| Ask the AI coach | Sidebar > Coach (`Ctrl+2`) > Open chat > Type question |
| Change theme | Settings > Appearance > Visual Theme |
| Change language | Settings > General > Language |
