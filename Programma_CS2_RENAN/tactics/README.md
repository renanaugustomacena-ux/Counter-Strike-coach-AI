> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Tactics Configuration

This directory serves as the centralized repository for map-specific tactical metadata used by the Counter-Strike AI coach. It stores foundational strategic knowledge in structured JSON format, enabling the AI to provide context-aware coaching based on established professional standards.

## Technical Overview

By decoupling tactical data from the core logic, this directory allows updates to the "meta" without requiring code changes. Each JSON file carries a map identifier, a version string, and a list of role-based coaching rules keyed by an in-round trigger.

## Key Components

- **`mirage_defaults.json`**: A seed reference file for the map de_mirage (version 1.0). It currently contains two role-based advice rules:
    - **AWPer / `round_start`**: Check Mid Nest timing — professional standard is reaching window by 1:48.
    - **Entry Fragger / `t_side_exec`**: Prioritize clearing Sandwich and Firebox during A-site execution.

Each rule is a `{role, trigger, advice}` object; there are no coordinate lineups or utility timings in the current file.

## Directory Structure

```text
Programma_CS2_RENAN/tactics/
├── mirage_defaults.json  # Strategic reference for de_mirage
├── README.md             # This documentation
├── README_IT.md          # Italian version
└── README_PT.md          # Portuguese version
```

## Usage

**Status: not yet wired into the runtime.** No code currently loads files from `tactics/`; the coaching pipeline draws its tactical content from `backend/knowledge/` (RAG knowledge base and Coach Book) instead. This directory is the designated home for map-specific rule files should trigger-based tactical coaching be integrated:
1. **Reference Loading**: Scan the `tactics/` directory and cache JSON configurations in memory.
2. **Rule Matching**: Match a rule's `trigger` (e.g., `round_start`, `t_side_exec`) and `role` against the player's in-round context.
3. **Feedback Generation**: Surface the rule's `advice` text as corrective coaching.
