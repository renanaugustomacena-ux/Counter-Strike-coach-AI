> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Coaching — Pipeline de Coaching Multi-Modo

Orquestração de pipeline de coaching com quatro modos operacionais: COPER (Experience Bank + RAG + Referências Pro), Hybrid (síntese ML + RAG), RAG (apenas recuperação de conhecimento) e Neural Network (ML puro).

## Motores Principais

### Orquestração Primária
- **hybrid_engine.py** — `HybridCoachingEngine` — Sintetiza previsões de machine learning com recuperação de conhecimento RAG para insights de coaching equilibrados

### Correção e Refinamento
- **correction_engine.py** — `generate_corrections()` — Gera correções táticas a partir de desvios de desempenho contra linhas de base pro
- **nn_refinement.py** — `apply_nn_refinement()` — Camada de refinamento de rede neural para correções heurísticas com pontuação de confiança

### Análise Longitudinal
- **longitudinal_engine.py** — `generate_longitudinal_coaching()` — Rastreia tendências de desempenho ao longo do tempo com integração de decaimento temporal de linha de base

### Explicabilidade e Integração
- **explainability.py** — `ExplanationGenerator` — Converte previsões ML em explicações legíveis por humanos com atribuição causal
- **pro_bridge.py** — `PlayerCardAssimilator` — Conecta dados de jogadores profissionais a insights de coaching via comparação baseada em função
- **token_resolver.py** — `PlayerTokenResolver` — Canonicalização de nomes de jogadores com fuzzy matching e normalização leet-speak

## Modos de Coaching

1. **COPER** (Padrão) — Recuperação semântica Experience Bank + conhecimento RAG + Referências Pro
2. **Hybrid** — Previsões ML sintetizadas com contexto RAG
3. **RAG** — Recuperação pura de conhecimento de padrões de demos pro
4. **Neural** — Previsões ML puras sem aumento de conhecimento

## Integração
Usado por `backend/services/coaching_service.py` com contexto de linha de base temporal de `backend/processing/baselines/temporal_decay.py`.

## Dependências
PyTorch, sentence-transformers (embeddings), SQLModel (persistência de experiência).
