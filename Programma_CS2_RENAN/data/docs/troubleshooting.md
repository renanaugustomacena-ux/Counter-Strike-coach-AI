# Troubleshooting Guide

## Neural & Data Issues

### 1. "Neural Stall: Connect IDs"
- **Cause**: You have ingested demos, but the AI doesn't know which player is YOU.
- **Solution**: Go to **Profile** and ensure both **Steam ID** and **FACEIT ID** are connected and saved. The AI requires these IDs to filter your specific "Tick States" from the match.

### 2. "Coach is Idle" / No Insights
- **The 10/10 Rule**: Ensure you have at least 10 Professional demos and 10 Personal demos processed.
- **Maturity Gate**: If you have fewer than 50 demos, the Coach is in "Calibrating" mode. Insights will be sparse and a watermark will appear over the analytics.
- **Nickname Sync**: If your IDs are connected but the system still fails, verify your **Game Nickname** exactly matches your in-game name (casing matters).

### 3. "No Demos Found"
- **Path Validation**: Double-check the **Default Demo Path** in Settings. Use the "Test Path" button if available.
- **Integrity Check**: The scanner ignores corrupted demos or those without a valid header. Ensure your files are complete `.dem` files.
- **Processing Queue**: If you just added 50+ demos, the scanner may take a few minutes to index them before they appear in the history.

## UI & Launch Issues

### 6. "ModuleNotFoundError: No module named 'PySide6'"
- **Cause**: The Qt UI framework is not installed.
- **Solution**: Run `pip install PySide6` in your virtual environment.

### 7. App Opens but Shows Blank Screen
- **Qt UI**: Ensure you are running from the project root directory. Launch with: `python -m Programma_CS2_RENAN.apps.qt_app.app`
- **Legacy Kivy UI**: Verify the layout file exists at `Programma_CS2_RENAN/apps/desktop_app/layout.kv` and run with `python Programma_CS2_RENAN/main.py`.

## Performance & System

### 4. Application Lag / High CPU
- **Turbo Mode**: If "Turbo Mode" is ON, the ingestion process will consume significant CPU resources, potentially lagging the UI or your game. Switch to **Standard** or **Eco** for background processing.
- **Database Locks**: If you see "Database Locked" errors, avoid opening the `database.db` file in external SQLite browsers while the app is running. The system will auto-retry, but heavy ingestion can cause temporary contention.

### 5. Scraper / HLTV Sync Issues
- **Playwright Dependency**: HLTV synchronization requires the Playwright browser. If sync fails, run `playwright install chromium` in your terminal or use the "Fix Dependencies" button in the Wizard.
- **Network Blocks**: Ensure the application has access to `hltv.org`. Some VPNs or Firewalls may block the scraper.
