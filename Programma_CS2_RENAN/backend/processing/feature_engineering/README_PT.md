> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Feature Engineering — Extração de Características Unificada

Pipeline de extração de características unificada para treinamento e inferência com cálculo de rating HLTV 2.0 e características específicas de função.

## Módulos Principais

### Vetor de Características Unificado
- **vectorizer.py** — `FeatureExtractor` — Vetor de características unificado de 25 dimensões (METADATA_DIM=25) para todos os modelos ML. Garante representação consistente de características entre treinamento e inferência. Extrai características por tick: posição (x, y, z), velocidade, saúde, armadura, estatísticas de arma, contagens de utilitários, estado de economia, contexto de round.

### Rating HLTV 2.0
- **rating.py** — `compute_hltv2_rating()`, `compute_impact_rating()`, `compute_survival_rating()` — Implementação completa de rating HLTV 2.0 com três componentes:
  - Impact Rating: Kills/mortes/assists ponderados por multiplicadores de multi-kill
  - Survival Rating: Inverso de mortes por round com penalidades
  - Integração KAST: Contribuição de percentual Kill/Assist/Survive/Trade

### Cálculo KAST
- **kast.py** — `estimate_kast_from_stats()` — Cálculo de porcentagem KAST a partir de estatísticas de round. KAST = porcentagem de rounds com Kill OU Assist OU Sobreviveu OU Trocado.

### Características Base
- **base_features.py** — `HeuristicConfig`, `extract_match_stats()`, `load_learned_heuristics()` — Extração de características heurísticas com carregamento de parâmetros aprendidos do treinamento. Pesos de características e limites configuráveis.

### Características Específicas de Função
- **role_features.py** — Extração de características específicas de função para funções Entry Fragger, Lurker, Support, AWPer e IGL. Extrai métricas relevantes de função (first kills, backstabs, utility assists, AWP kills, decision outcomes).

## Integração

FeatureExtractor usado por:
- Treinamento RAP Coach (`backend/nn/rap_coach/trainer.py`)
- Treinamento JEPA (`backend/nn/jepa_trainer.py`)
- Serviço de coaching (`backend/services/coaching_service.py`)
- Orquestrador de análise (`backend/services/analysis_service.py`)

## Componentes do Vetor de Características (25-dim)
Posição (3), velocidade (3), saúde/armadura (2), arma (5), utilitários (4), economia (3), contexto de round (5).

## Dependências
NumPy, Pandas, SQLModel.
