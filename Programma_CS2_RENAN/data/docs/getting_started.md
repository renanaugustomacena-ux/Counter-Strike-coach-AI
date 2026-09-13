# Getting Started with Macena CS2 Analyzer

## 1. Who you are in the data

The analyzer identifies you by your **in-game name** — the nickname CS2 shows on the scoreboard. Set it in the setup wizard or later on the **Profile** screen (Dashboard → Connectivity → Profile). Matching is exact but not case-sensitive, and it has to be the same name that appears inside your demo files. No account linking is needed: the Steam Config screen is an optional extra for Steam profile stats and plays no part in telling your rounds apart from the other nine players.

## 2. Two folders, two kinds of demos

- **Demo folder** (wizard, or Settings → Analysis & Paths): your own matches. Everything ingested from here is *yours* and feeds Match History, Advanced Analytics and the coach.
- **Pro demo folder** (Settings → Analysis & Paths): professional matches you downloaded. They build the reference library the analyzer compares you against and are never shown as your performance.

CS2 saves your own demos in Steam's replay folder — `...\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\replays\` on Windows, `~/.steam/steam/steamapps/common/Counter-Strike Global Offensive/game/csgo/replays/` on Linux. Files under 10 MB are skipped as incomplete.

## 3. Analyze

On the Dashboard press **Analyze Demos** (your folder) or **Analyze Pro Demos** (the pro folder). Every new `.dem` is parsed tick by tick and its per-match stats, rounds and positions are written to the local database; a full match takes a few minutes. The caption under each button reports how many demos are analyzed. Once the background service is online (the **Service** chip), it also watches both folders and queues new files on its own.

## 4. What unlocks when

- **Match History** lists your matches and, separately, the pro matches in your library.
- **Advanced Analytics** and the **AI Coach** use your own demos only. With none analyzed they show an honest empty state; Advanced Analytics adds a clearly labelled *Pro reference* block built from other players' matches.
- **Coach chat** needs [Ollama](https://ollama.com/download) running on this machine with the `gemma4:e2b` model pulled; the Coach screen shows whether it is online.
- **Belief confidence** grows with your analyzed demos: 50% up to 49 demos, 80% from 50, 100% from 200.

## 5. Training the coach

The neural coach learns from the analyzed matches in the database — yours and the pro library. On the Dashboard, the **Training Status** card offers **Train coach**: pick a step preset (200 for a quick check, 2 000 standard, 20 000 for the full run, which takes hours on a CPU) and press the button. The same button sits in Settings next to Start Ingestion.

Training never runs inside the window: the request goes to the background service (the **Service** chip must be *Online*), which assigns the train/validation split, exports the episode shards under your data folder, trains the JEPA v2 encoder and records the run. The card shows the step progress, the losses and an ETA; **Stop** ends the run at a resumable checkpoint. When it finishes, the card names the active model with its step count, date and number of demos. With too few analyzed demos the run is skipped and the card says why.

What training does not do yet: the coach's advice text does not use the trained encoder until the next steps of the neural-core plan land, so the wording of the insights does not change after a run.

From a source checkout the command line still works:

```bash
python run_full_training_cycle.py --model-type jepa_v2
```
