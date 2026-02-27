> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Analysis — Motori di Teoria dei Giochi e Statistica

Questa directory contiene 11 motori analitici che implementano teoria dei giochi, modelli probabilistici e analisi tattica per Counter-Strike 2.

## Moduli Principali

### Modelli Probabilistici
- **belief_model.py** — `DeathProbabilityEstimator`, `BeliefState` — Stima bayesiana della probabilità di morte con calibrazione online
- **win_probability.py** — `WinProbabilityPredictor`, `WinProbabilityNN` — Predizione neurale della vittoria del round da stato di gioco

### Analisi Tattica
- **blind_spots.py** — `BlindSpotDetector` — Identifica angoli non controllati e vulnerabilità tattiche
- **engagement_range.py** — `EngagementRangeAnalyzer` — Analisi distanza ottimale di ingaggio per classe d'arma
- **entropy_analysis.py** — `EntropyAnalyzer` — Entropia di Shannon per misurare la prevedibilità posizionale
- **deception_index.py** — `DeceptionAnalyzer` — Quantifica l'imprevedibilità del gioco e la variazione dei pattern

### Ottimizzazione Decisionale
- **game_tree.py** — `ExpectiminimaxSearch` — Albero decisionale avversariale con esiti probabilistici
- **role_classifier.py** — `RoleClassifier`, `PlayerRole` — Classificazione neurale del ruolo (Entry/Lurk/Support/AWP/IGL)

### Economia e Risorse
- **utility_economy.py** — `UtilityAnalyzer`, `EconomyOptimizer` — Efficienza granate e analisi decisioni economiche
- **momentum.py** — `MomentumTracker`, `MomentumState` — Tracciamento momentum del round con moltiplicatori

## Integrazione
Tutti i moduli esportano funzioni factory via `__init__.py` per orchestrazione in `backend/services/coaching_service.py`.

## Dipendenze
PyTorch, NumPy, SQLModel (per persistenza dello stato).
