> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Advanced — Orquestração Multi-Modelo

Arquiteturas neurais avançadas para orquestração multi-modelo, redes inspiradas em quântica e engenharia de características em nível cerebral.

## Módulos Principais

### Orquestração Multi-Modelo
- **brain_bridge.py** — `BrainBridge` — Camada de orquestração multi-modelo coordenando RAP Coach, JEPA, VL-JEPA e NeuralRoleHead. Implementa análise CSI (Critical Situation Index) para seleção de modelos consciente do contexto e estratégias de ensemble.

### Arquitetura Inspirada em Quântica
- **superposition_net.py** — `SuperpositionLayer`, `AdaptiveSuperpositionMLP` — Rede de superposição inspirada em quântica com mistura probabilística de características. Implementa estados de superposição que colapsam para saídas determinísticas baseadas em atenção de contexto.

### Engenharia de Características
- **feature_engineering.py** — `BrainFeatureEngineer` — Engenharia de características em nível cerebral para entradas multi-modelo. Extrai e normaliza características através de dimensões visuais, temporais e estratégicas para consumo unificado de modelo.

## Integração

BrainBridge coordena saídas de modelos via estratégias de ensemble ponderadas:
1. **Avaliação de Situação**: Análise CSI determina criticidade do contexto (rotina/tático/crítico)
2. **Seleção de Modelo**: Ativa modelos apropriados baseados na situação (JEPA para percepção, RAP para coaching, Role para classificação)
3. **Síntese de Saída**: Combinação ponderada com gating baseado em confiança

## Análise CSI

Critical Situation Index calculado a partir de:
- Pressão de tempo (temporizador de bomba, tempo restante do round)
- Estado econômico (buy round, eco, force buy)
- Vantagem/desvantagem numérica
- Zonas de controle de mapa contestadas

## Dependências
PyTorch, NumPy.
