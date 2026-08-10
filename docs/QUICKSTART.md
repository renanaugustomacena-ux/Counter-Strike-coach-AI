# Quickstart

Get AI coaching feedback from your CS2 demos in under 5 minutes.

## Prerequisites

- Python 3.10+ (3.12 recommended)
- A CS2 `.dem` replay file

## Install

```bash
git clone https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI.git
cd Counter-Strike-coach-AI
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

## Run

```bash
python -m Programma_CS2_RENAN.apps.qt_app.app
```

(On Linux you can also use `./launch.sh`, which expects the `.venv` created above.)

## First-time Setup

1. The 5-step setup wizard launches automatically on first run.
2. Enter your **CS2 in-game name** (must match the name in your demo files).
3. Choose a folder for AI brain data (models, knowledge base, datasets).
4. Optionally point to your CS2 demo folder.
5. Click **Launch App**.

## Analyze a Demo

1. On the Home dashboard, find the **Ingest** card and click **Change** to set your demo folder if you didn't during setup.
2. Click **Analyze** (or **Analyze pro** for professional demos).
3. Wait for the progress indicator to finish.
4. Open **Match History** from the sidebar to see ingested demos.
5. Click a match to view coaching insights, stats, and highlights.

## Validate Installation

```bash
python tools/headless_validator.py
```

Should end with `VERDICT: PASS` (the `RESULT:` line reports how many checks passed; warnings for optional dependencies are allowed).

## Run Tests

```bash
python -m pytest Programma_CS2_RENAN/tests/ -q
```

## Troubleshoot

- **"Not configured" demo folder**: On the Home dashboard's Ingest card (or Settings > Analysis Paths), select a folder containing `.dem` files.
- **No coaching insights**: Make sure your in-game name exactly matches the player name in the demo file.
- **Import errors**: Verify you installed `requirements.txt` inside the activated venv.
