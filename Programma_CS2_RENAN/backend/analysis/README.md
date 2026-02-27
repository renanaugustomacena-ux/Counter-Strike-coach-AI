> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Analysis — Game Theory & Statistical Engines

This directory contains 11 analytical engines implementing game theory, probabilistic modeling, and tactical analysis for Counter-Strike 2.

## Core Modules

### Probabilistic Models
- **belief_model.py** — `DeathProbabilityEstimator`, `BeliefState` — Bayesian death probability estimation with online calibration
- **win_probability.py** — `WinProbabilityPredictor`, `WinProbabilityNN` — Neural round win prediction from game state

### Tactical Analysis
- **blind_spots.py** — `BlindSpotDetector` — Identifies unchecked angles and tactical vulnerabilities
- **engagement_range.py** — `EngagementRangeAnalyzer` — Optimal engagement distance analysis per weapon class
- **entropy_analysis.py** — `EntropyAnalyzer` — Shannon entropy for positional predictability measurement
- **deception_index.py** — `DeceptionAnalyzer` — Quantifies play unpredictability and pattern variation

### Decision Optimization
- **game_tree.py** — `ExpectiminimaxSearch` — Adversarial decision tree with probabilistic outcomes
- **role_classifier.py** — `RoleClassifier`, `PlayerRole` — Neural role classification (Entry/Lurk/Support/AWP/IGL)

### Economy & Resources
- **utility_economy.py** — `UtilityAnalyzer`, `EconomyOptimizer` — Grenade efficiency and economy decision analysis
- **momentum.py** — `MomentumTracker`, `MomentumState` — Round momentum tracking with multipliers

## Integration
All modules export factory functions via `__init__.py` for orchestration in `backend/services/coaching_service.py`.

## Dependencies
PyTorch, NumPy, SQLModel (for state persistence).
