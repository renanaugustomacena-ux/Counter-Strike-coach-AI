> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Progress — Tracciamento Longitudinale delle Prestazioni

> **Autorita:** Regola 1 (Correttezza), Regola 4 (Persistenza dei Dati)

Questo modulo fornisce l'analisi temporale delle tendenze prestazionali del giocatore su piu sessioni. Risponde alla domanda: "Questo giocatore sta migliorando, peggiorando o rimane stabile in ciascuna metrica?"

## File

| File | Righe | Scopo |
|------|-------|-------|
| `longitudinal.py` | 9 | Struttura dati dei trend: `FeatureTrend` (dataclass) |
| `trend_analysis.py` | 19 | Calcolo dei trend statistici: `compute_trend(values)` |

## FeatureTrend — Struttura Dati

Campi: feature (str), slope (float, positivo = miglioramento), volatility (float, misura di consistenza), confidence (float, min(1.0, sample_count / 30))

## compute_trend() — Calcolo Statistico

Restituisce (slope, volatility, confidence):
- Slope: Regressione lineare (numpy polyfit grado 1)
- Volatility: Deviazione standard
- Confidence: min(1.0, len(values) / 30)
- Guardia: Restituisce (0.0, 0.0, 0.0) se ci sono meno di 2 valori

### Scala di Confidenza

| Campioni | Confidenza | Interpretazione |
|----------|------------|-----------------|
| < 2 | 0.0 | Nessun trend (dati insufficienti) |
| 2-9 | 0.07-0.30 | Fase iniziale, inaffidabile |
| 10-19 | 0.33-0.63 | Trend emergente |
| 20-29 | 0.67-0.97 | Trend affidabile |
| 30+ | 1.0 | Confidenza piena |

## Integrazione

CoachingService chiama compute_trend() per ogni feature:
- slope < 0 + confidence >= 0.6 → Insight "Regressione"
- slope > 0 + confidence >= 0.6 → Insight "Miglioramento"
- confidence < 0.6 → Soppresso

## Note di Sviluppo

- Utilita matematica pura — nessuno stato, nessun effetto collaterale
- TREND_CONFIDENCE_SAMPLE_SIZE = 30 corrisponde ai requisiti del bootstrap CI
- Le unita dello slope dipendono dalle unita della feature in input
