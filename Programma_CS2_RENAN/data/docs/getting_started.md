# Getting Started with Macena CS2 Analyzer

## 1. Initial Setup & Requirements
The setup wizard guides you through the core configuration. For the analyzer to function at peak precision, ensure:
- **Default Demo Path**: Points to your CS2 demo folder (e.g., `...\game\csgo\demos`).
- **Profile Connection**: You MUST link your **Steam ID** and **FACEIT ID**. The system uses these to isolate your specific performance data from the other 9 players in a demo.
- **Game Nickname**: Enter your exact in-game name (case-sensitive) to assist the legacy identification system.

## 2. The "10/10 Rule"
The AI Coach (RAP) requires a baseline before it can provide reliable advice:
- **10 Professional Demos**: Ingest at least 10 HLTV pro demos to establish the "Gold Standard".
- **10 Personal Demos**: Ingest 10 of your own matches to allow the AI to identify your patterns.
- *Note: The coach will remain in "Idle" or "Calibrating" status until these thresholds are met.*

## 3. Ingestion & Training Service
The **Coach Dashboard** is your command center.
- **Start Service (Play Button)**: This launches the background worker which handles both **Ingestion** (parsing raw demos) and **Neural Training** (learning from the data).
- **Ingestion Speeds**:
    - **Eco**: Low CPU impact, suitable for background use.
    - **Standard**: Balanced performance.
    - **Turbo**: Maximum speed, recommended only for initial bulk ingestion.
- **Temporal Split**: The system automatically splits your data (70% Train, 15% Val, 15% Test) chronologically to ensure the AI learns from your growth over time without "cheating" by seeing future matches.

## 4. Understanding Data Maturity
As you add more demos, the AI's confidence increases:
- **CALIBRATING (0-49 demos)**: 50% confidence. Insights are experimental.
- **LEARNING (50-199 demos)**: 80% confidence. Professional corrections become available in the 2D Viewer.
- **MATURE (200+ demos)**: 100% confidence. Full tactical optimization and role-specific coaching.
