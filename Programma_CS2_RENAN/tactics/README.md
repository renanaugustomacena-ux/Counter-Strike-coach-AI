> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Tactics Configuration

This directory serves as the centralized repository for map-specific tactical metadata used by the Counter-Strike AI coach. It stores foundational strategic knowledge in structured JSON format, enabling the AI to provide context-aware coaching based on established professional standards.

## Technical Overview

The tactical engine relies on these configuration files to validate player actions, suggest improvements, and understand the state of a round. By decoupling tactical data from the core logic, the system allows for easy updates to the "meta" without requiring code changes. The AI coach parses these files to compare real-time game data against predefined "perfect" execution parameters.

## Key Components

- **`mirage_defaults.json`**: This is the primary reference file for the map de_mirage. It contains comprehensive data points including:
    - **Smoke Lineups**: Precise coordinates and view angles for essential smoke grenades (e.g., Jungle, Stairs, Nest).
    - **Flash Timings**: Optimal delay and pop-flash durations to maximize enemy blindness.
    - **Default Setups**: Standard CT-side distributions (e.g., 2-1-2) and T-side default executions.
    - **Strategic Metadata**: Thresholds for utility efficiency and positioning heatmaps.

## Directory Structure

```text
Programma_CS2_RENAN/tactics/
├── mirage_defaults.json  # Strategic reference for de_mirage
├── README.md             # This documentation
├── README_IT.md          # Italian version
└── README_PT.md          # Portuguese version
```

## Usage

The AI coach utilizes these files during both the ingestion and analysis phases:
1. **Reference Loading**: At startup, the `tactics/` directory is scanned, and all JSON configurations are cached into memory.
2. **Comparison Engine**: During match analysis, the engine cross-references player utility usage against the coordinates defined in `mirage_defaults.json`.
3. **Feedback Generation**: If a player's timing or positioning deviates significantly from the "default," the coach generates specific corrective advice.
