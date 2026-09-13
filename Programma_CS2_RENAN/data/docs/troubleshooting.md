# Troubleshooting Guide

## "No personal demos analyzed yet"

- Your in-game name must match the name inside the demo (case does not matter). Check it on the Profile screen.
- The demo folder must be set and contain complete `.dem` files (10 MB or more).
- Press **Analyze Demos** on the Dashboard and watch the caption under the button.
- Pro matches never count as personal, even when a pro uses your nickname.

## Service: Offline

The background Session Engine is not running or has not sent a heartbeat in the last five minutes. Restart the application; if it stays offline, read `cs2_analyzer_daemon.log` in the logs folder. Automatic folder watching needs the service; the Analyze buttons work without it.

## "Backend Startup Error"

The console failed to initialize (database or paths). The window stays usable; check `cs2_analyzer.log` in the logs folder for the cause — a demo folder that no longer exists is the usual one.

## Coach chat offline

Chat needs Ollama running on this machine with the selected model pulled: `ollama pull gemma4:e2b`, then `ollama serve`. The model combo on the Coach screen lists what Ollama has.

## "AI language model" download

The coach's knowledge search uses a small language model (about 90 MB) downloaded once, in the background, after the window opens. Without it the coach falls back to a simpler similarity search; nothing else is blocked.

## Database is locked

Do not open `database.db` in an external SQLite tool while the app runs. Heavy ingestion can cause short retries; they resolve on their own.

## HLTV sync / Docker

Live HLTV scraping is optional and needs Docker. When Docker is unavailable the app uses the cached pro baselines and continues; the `ENABLE_HLTV_SYNC` setting turns the sync off entirely.

## Where the logs are

`cs2_analyzer.log` (application) and `cs2_analyzer_daemon.log` (background service) live in the `logs` folder of your data location — the project folder in a source install, or the brain folder chosen in the wizard.
