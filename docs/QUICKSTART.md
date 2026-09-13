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
3. Choose a data folder (models, logs, knowledge base, training data; the installed app keeps its database there too).
4. Optionally point to your CS2 demo folder and to a folder of downloaded pro demos.
5. Click **Launch App**.

## Analyze a Demo

1. On the Dashboard, the **Demo Analysis** card shows your demo folder — **Select Demo Folder** changes it.
2. Click **Analyze Demos** (or **Analyze Pro Demos** on the **Pro Demo Ingestion** card for a downloaded pro pool — reference material, never counted as your matches).
3. Wait for the progress indicator to finish.
4. Open **Match History** from the sidebar to see analyzed demos.
5. Click a match to view its stats, rounds and highlights.

## Train the Coach

1. The **Service** chip on the Dashboard must read *Online* (the background service does the training).
2. In the **Training Status** card pick a step preset (200 quick check · 2 000 standard · 20 000 full, hours on CPU) and click **Train coach**.
3. The card shows step progress, losses and an ETA; **Stop** ends the run at a resumable checkpoint.
4. When done, the card names the active model (steps, date, demos). The coach's advice text does not use it until the next neural-core steps land.

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
