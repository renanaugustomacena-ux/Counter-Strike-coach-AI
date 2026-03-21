# Progress -- Rastreamento Longitudinal de Desempenho

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

> **Autoridade:** Regra 1 (Corretude), Regra 4 (Persistencia de Dados)

## Introducao

Este modulo fornece analise temporal das tendencias de desempenho do jogador ao longo
de multiplas sessoes. Ele responde a pergunta fundamental do coaching: "Este jogador
esta melhorando, piorando ou estavel em cada metrica ao longo do tempo?" O modulo e
intencionalmente minimalista -- dois arquivos, uma dataclass, uma funcao -- porque o
calculo de tendencias deve permanecer como uma utilidade matematica pura, sem efeitos
colaterais, sem estado e sem acesso ao banco de dados.

A saida deste modulo alimenta diretamente a pipeline de coaching: quando uma tendencia
atinge confianca suficiente, `CoachingService` pode emitir insights de "Melhoria" ou
"Regressao" para o jogador, transformando numeros brutos em orientacoes acionaveis.

## Inventario de Arquivos

| Arquivo | Linhas | Finalidade | Exports Principais |
|---------|--------|------------|--------------------|
| `__init__.py` | 0 | Marcador de pacote | -- |
| `longitudinal.py` | 9 | Estrutura de dados de tendencia | `FeatureTrend` (dataclass) |
| `trend_analysis.py` | 19 | Calculo estatistico de tendencias | `compute_trend(values)`, `TREND_CONFIDENCE_SAMPLE_SIZE` |

## Arquitetura e Conceitos

### `FeatureTrend` -- Estrutura de Dados

```python
@dataclass
class FeatureTrend:
    feature: str        # ex. "avg_adr", "kd_ratio"
    slope: float        # Inclinacao da regressao linear (positivo = melhoria)
    volatility: float   # Desvio padrao (medida de consistencia)
    confidence: float   # min(1.0, sample_count / 30)
```

Cada campo tem uma interpretacao precisa:

- **feature**: O nome da metrica de desempenho rastreada. Deve corresponder as
  chaves de `PlayerMatchStats` (ex. `avg_adr`, `kd_ratio`, `avg_hs`).
- **slope**: O coeficiente de regressao linear calculado por
  `numpy.polyfit(x, y, 1)`. Uma inclinacao positiva indica melhoria; negativa indica
  regressao. As unidades dependem da feature de entrada.
- **volatility**: O desvio padrao da serie de valores. Mede a consistencia -- um
  jogador com slope alto mas volatilidade alta esta melhorando de forma erratica.
- **confidence**: Uma pontuacao normalizada de 0.0 a 1.0 que representa a
  confiabilidade da tendencia, calculada como
  `min(1.0, len(values) / TREND_CONFIDENCE_SAMPLE_SIZE)`.

### `compute_trend()` -- Calculo Estatistico

```python
def compute_trend(values: List[float]) -> Tuple[float, float, float]:
    """Retorna (slope, volatility, confidence)."""
```

- **Slope**: Regressao linear sobre a serie de valores usando `numpy.polyfit` com
  grau 1. O eixo x e simplesmente o indice (0, 1, 2, ...), representando partidas
  sequenciais.
- **Volatility**: Desvio padrao dos valores via `numpy.ndarray.std()`.
- **Confidence**: `min(1.0, len(values) / TREND_CONFIDENCE_SAMPLE_SIZE)` onde a
  constante limiar e 30 amostras.
- **Guarda (AC-39-01)**: Retorna `(0.0, 0.0, 0.0)` quando menos de 2 pontos de
  dados sao fornecidos. Isso impede que `numpy.polyfit` lance um `LinAlgError` em
  entradas degeneradas.

### Escala de Confianca

| Amostras | Confianca | Interpretacao |
|----------|-----------|---------------|
| < 2 | 0.0 | Sem tendencia (dados insuficientes) |
| 2--9 | 0.07--0.30 | Fase inicial, nao confiavel |
| 10--19 | 0.33--0.63 | Tendencia emergente |
| 20--29 | 0.67--0.97 | Tendencia confiavel |
| 30+ | 1.0 | Confianca plena |

O limiar de 30 corresponde ao requisito classico do intervalo de confianca bootstrap,
produzindo erro amostral inferior a 8% no nivel de confianca de 95%.

## Integracao

```
PlayerMatchStats (registros historicos em database.db)
        |
        +-- coaching_service.py chama compute_trend() por feature
                |
                +-- slope < 0 + confidence >= 0.6 --> Insight "Regressao"
                +-- slope > 0 + confidence >= 0.6 --> Insight "Melhoria"
                +-- confidence < 0.6 --> Suprimido (dados insuficientes)
                        |
                        +-- coaching/longitudinal_engine.py gera texto de coaching
```

### Consumidores a Jusante

| Consumidor | Modulo | Como Usa as Tendencias |
|------------|--------|------------------------|
| Coaching Service | `services/coaching_service.py` | Gera insights de coaching longitudinal a partir de slope/confidence |
| Longitudinal Engine | `coaching/longitudinal_engine.py` | Produz narrativas de coaching baseadas em tendencias |
| Analytics Engine | `reporting/analytics.py` | Alimenta graficos de tendencia do dashboard |
| Explanation Generator | `coaching/explainability.py` | Inclui dados de tendencia nas explicacoes de coaching |

### Fluxo de Dados

1. A ingestao de demo popula as linhas `PlayerMatchStats` em `database.db`.
2. `CoachingService.generate_new_insights()` busca o historico de partidas do
   jogador.
3. Para cada feature rastreada, `compute_trend(values)` e chamada com a serie
   historica.
4. A tripla retornada `(slope, volatility, confidence)` e encapsulada em uma
   dataclass `FeatureTrend`.
5. Tendencias com `confidence >= 0.6` sao passadas para
   `generate_longitudinal_coaching()` para produzir insights de coaching legiveis.
6. Esses insights sao persistidos como linhas `CoachingInsight` no banco de dados.

## Notas de Desenvolvimento

- **Utilidade matematica pura**: Sem estado, sem efeitos colaterais, sem acesso ao
  banco de dados, sem logging. Isso e intencional -- o modulo e uma dependencia folha.
- **TREND_CONFIDENCE_SAMPLE_SIZE = 30**: Esta constante e definida em
  `trend_analysis.py` e nao deve ser alterada sem reavaliar a base estatistica dos
  limiares de confianca.
- **Unidades do slope**: As unidades dependem da feature de entrada. Para ADR, o
  slope e "pontos de ADR por partida." Para a razao K/D, e "K/D por partida."
  Comparacoes entre features requerem normalizacao (nao feita aqui -- tratada pela
  camada de coaching).
- **A volatilidade e absoluta**: Desvio padrao, nao coeficiente de variacao. Compare
  apenas dentro da mesma feature.
- **Sem caching**: Os resultados sao calculados do zero a cada chamada. O servico de
  coaching decide quando chamar e como fazer caching.
- **Thread safety**: Tanto `FeatureTrend` (dataclass imutavel) quanto
  `compute_trend()` (funcao pura) sao inerentemente thread-safe.
