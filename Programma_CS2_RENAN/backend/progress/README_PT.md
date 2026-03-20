> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Progress — Rastreamento Longitudinal de Desempenho

> **Autoridade:** Regra 1 (Corretude), Regra 4 (Persistencia de Dados)

Este modulo fornece analise temporal das tendencias de desempenho do jogador ao longo de multiplas sessoes. Ele responde: "Este jogador esta melhorando, piorando ou estavel em cada metrica?"

## Arquivos

| Arquivo | Linhas | Finalidade |
|---------|--------|------------|
| `longitudinal.py` | 9 | Estrutura de dados de tendencia: `FeatureTrend` (dataclass) |
| `trend_analysis.py` | 19 | Calculo de tendencias estatisticas: `compute_trend(values)` |

## FeatureTrend — Estrutura de Dados

Campos: feature (str), slope (float, positivo = melhoria), volatility (float, medida de consistencia), confidence (float, min(1.0, sample_count / 30))

## compute_trend() — Calculo Estatistico

Retorna (slope, volatility, confidence):
- Slope: Regressao linear (numpy polyfit grau 1)
- Volatility: Desvio padrao
- Confidence: min(1.0, len(values) / 30)
- Guarda: Retorna (0.0, 0.0, 0.0) se houver menos de 2 valores

### Escala de Confianca

| Amostras | Confianca | Interpretacao |
|----------|-----------|---------------|
| < 2 | 0.0 | Sem tendencia (dados insuficientes) |
| 2-9 | 0.07-0.30 | Fase inicial, nao confiavel |
| 10-19 | 0.33-0.63 | Tendencia emergente |
| 20-29 | 0.67-0.97 | Tendencia confiavel |
| 30+ | 1.0 | Confianca plena |

## Integracao

CoachingService chama compute_trend() por feature:
- slope < 0 + confidence >= 0.6 → Insight "Regressao"
- slope > 0 + confidence >= 0.6 → Insight "Melhoria"
- confidence < 0.6 → Suprimido

## Notas de Desenvolvimento

- Utilidade matematica pura — sem estado, sem efeitos colaterais
- TREND_CONFIDENCE_SAMPLE_SIZE = 30 corresponde aos requisitos do bootstrap CI
- As unidades do slope dependem das unidades da feature de entrada
