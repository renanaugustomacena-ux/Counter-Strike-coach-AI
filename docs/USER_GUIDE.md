# Macena CS2 Analyzer — User Guide

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
13. [Troubleshooting](#13-troubleshooting)

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

## 13. Troubleshooting

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
