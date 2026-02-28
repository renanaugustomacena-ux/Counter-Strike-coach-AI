# Baselines Profissionais & Detecção de Meta Drift

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Visão Geral

Este módulo fornece baselines de jogadores profissionais, limiares de classificação de papéis, detecção de drift do meta-jogo e resolução fuzzy de nicknames. Permite modelagem de decaimento temporal de estatísticas profissionais e limiares de papéis aprendidos e persistidos no banco de dados.

## Componentes Principais

### `pro_baseline.py`
- **`get_pro_baseline()`** — Recupera estatísticas de jogadores profissionais com ponderação de decaimento temporal
- **`calculate_deviations()`** — Calcula desvios de desempenho do usuário em relação ao baseline pro
- **`TemporalBaselineDecay`** — Modelo de decaimento exponencial para estatísticas profissionais envelhecidas (padrão λ=0.0001/dia)

### `role_thresholds.py`
- **`RoleThresholdStore`** — Armazenamento em memória para limiares de classificação de papéis aprendidos
- **`LearnedThreshold`** — Dataclass para limiares estatísticos por papel (entry, support, lurk, AWP, IGL)
- **`persist_to_db()` / `load_from_db()`** — Persistência em banco de dados para limiares aprendidos

### `meta_drift.py`
- **`MetaDriftEngine`** — Detecta mudanças nos padrões do meta-jogo profissional (uso de armas, meta de utilitários, tendências de controle de mapa)

### `nickname_resolver.py`
- **`NicknameResolver`** — Matching fuzzy para nicknames de jogadores profissionais (lida com leet-speak, abreviações, aliases)

## Integração

Usado por `CoachingService` para enriquecimento de baseline temporal, daemon `Teacher` para detecção de meta-shift após retreinamento e `NeuralRoleHead` para aprendizado de limiares de classificação de papéis.

## Fontes de Dados

Baselines profissionais originados das tabelas `ProPlayer` e `MatchResult` via pipeline de scraping HLTV.
