> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Analysis — Motores de Teoria dos Jogos e Estatística

Este diretório contém 11 motores analíticos implementando teoria dos jogos, modelagem probabilística e análise tática para Counter-Strike 2.

## Módulos Principais

### Modelos Probabilísticos
- **belief_model.py** — `DeathProbabilityEstimator`, `BeliefState` — Estimativa bayesiana de probabilidade de morte com calibração online
- **win_probability.py** — `WinProbabilityPredictor`, `WinProbabilityNN` — Previsão neural de vitória do round a partir do estado do jogo

### Análise Tática
- **blind_spots.py** — `BlindSpotDetector` — Identifica ângulos não verificados e vulnerabilidades táticas
- **engagement_range.py** — `EngagementRangeAnalyzer` — Análise de distância ótima de engajamento por classe de arma
- **entropy_analysis.py** — `EntropyAnalyzer` — Entropia de Shannon para medição de previsibilidade posicional
- **deception_index.py** — `DeceptionAnalyzer` — Quantifica imprevisibilidade do jogo e variação de padrões

### Otimização de Decisões
- **game_tree.py** — `ExpectiminimaxSearch` — Árvore de decisão adversarial com resultados probabilísticos
- **role_classifier.py** — `RoleClassifier`, `PlayerRole` — Classificação neural de função (Entry/Lurk/Support/AWP/IGL)

### Economia e Recursos
- **utility_economy.py** — `UtilityAnalyzer`, `EconomyOptimizer` — Eficiência de granadas e análise de decisões econômicas
- **momentum.py** — `MomentumTracker`, `MomentumState` — Rastreamento de momentum do round com multiplicadores

## Integração
Todos os módulos exportam funções factory via `__init__.py` para orquestração em `backend/services/coaching_service.py`.

## Dependências
PyTorch, NumPy, SQLModel (para persistência de estado).
