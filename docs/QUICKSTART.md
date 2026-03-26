# Quickstart

Get AI coaching feedback from your CS2 demos in under 5 minutes.

## Prerequisites

- Python 3.10+
- A CS2 `.dem` replay file

## Install

```bash
git clone https://github.com/your-repo/macena-cs2-analyzer.git
cd macena-cs2-analyzer
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows
pip install -e .
```

## Run

```bash
python -m Programma_CS2_RENAN.apps.qt_app.app
```

## First-time Setup

1. The setup wizard launches automatically on first run.
2. Enter your **CS2 in-game name** (must match the name in your demo files).
3. Choose a folder for AI brain data (models, knowledge base).
4. Optionally point to your CS2 demo folder.
5. Click **Launch App**.

## Analyze a Demo

1. On the Home screen, set your demo folder if you didn't during setup.
2. Click **Analyze Demos**.
3. Wait for the progress indicator to finish.
4. Go to **Match History** to see ingested demos.
5. Click a match to view coaching insights, stats, and highlights.

## Validate Installation

```bash
python tools/headless_validator.py
```

Should report `319/319 passed` and `VERDICT: PASS`.

## Run Tests

```bash
python -m pytest Programma_CS2_RENAN/tests/ -q
```

## Troubleshoot

- **"Set a demo folder first"**: Go to Settings or Home screen and select a folder containing `.dem` files.
- **No coaching insights**: Make sure your in-game name exactly matches the player name in the demo file.
- **Import errors**: Verify you installed with `pip install -e .` inside the activated venv.
