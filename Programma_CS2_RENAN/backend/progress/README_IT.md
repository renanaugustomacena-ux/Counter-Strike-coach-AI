# Progress -- Tracciamento Longitudinale delle Prestazioni

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

> **Autorita:** Regola 1 (Correttezza), Regola 4 (Persistenza dei Dati)

## Introduzione

Questo modulo fornisce l'analisi temporale delle tendenze prestazionali del giocatore
su piu sessioni. Risponde alla domanda fondamentale del coaching: "Questo giocatore
sta migliorando, peggiorando o rimane stabile in ciascuna metrica nel tempo?" Il modulo
e intenzionalmente minimale -- due file, una dataclass, una funzione -- perche il
calcolo delle tendenze deve rimanere un'utilita matematica pura senza effetti
collaterali, senza stato e senza accesso al database.

L'output di questo modulo alimenta direttamente la pipeline di coaching: quando una
tendenza raggiunge una confidenza sufficiente, `CoachingService` puo emettere insight
di "Miglioramento" o "Regressione" al giocatore, trasformando numeri grezzi in
indicazioni attuabili.

## Inventario File

| File | Righe | Scopo | Export Principali |
|------|-------|-------|-------------------|
| `__init__.py` | 0 | Marcatore di pacchetto | -- |
| `longitudinal.py` | 9 | Struttura dati dei trend | `FeatureTrend` (dataclass) |
| `trend_analysis.py` | 19 | Calcolo statistico dei trend | `compute_trend(values)`, `TREND_CONFIDENCE_SAMPLE_SIZE` |

## Architettura e Concetti

### `FeatureTrend` -- Struttura Dati

```python
@dataclass
class FeatureTrend:
    feature: str        # es. "avg_adr", "kd_ratio"
    slope: float        # Pendenza regressione lineare (positivo = miglioramento)
    volatility: float   # Deviazione standard (misura di consistenza)
    confidence: float   # min(1.0, sample_count / 30)
```

Ogni campo ha un'interpretazione precisa:

- **feature**: Il nome della metrica prestazionale tracciata. Deve corrispondere alle
  chiavi di `PlayerMatchStats` (es. `avg_adr`, `kd_ratio`, `avg_hs`).
- **slope**: Il coefficiente di regressione lineare calcolato da
  `numpy.polyfit(x, y, 1)`. Una pendenza positiva indica miglioramento; negativa
  indica regressione. Le unita dipendono dalla feature in input.
- **volatility**: La deviazione standard della serie di valori. Misura la consistenza
  -- un giocatore con slope alto ma volatilita alta sta migliorando in modo erratico.
- **confidence**: Un punteggio normalizzato da 0.0 a 1.0 che rappresenta
  l'affidabilita del trend, calcolato come
  `min(1.0, len(values) / TREND_CONFIDENCE_SAMPLE_SIZE)`.

### `compute_trend()` -- Calcolo Statistico

```python
def compute_trend(values: List[float]) -> Tuple[float, float, float]:
    """Restituisce (slope, volatility, confidence)."""
```

- **Slope**: Regressione lineare sulla serie di valori tramite `numpy.polyfit` con
  grado 1. L'asse x e semplicemente l'indice (0, 1, 2, ...), che rappresenta
  partite sequenziali.
- **Volatility**: Deviazione standard dei valori tramite `numpy.ndarray.std()`.
- **Confidence**: `min(1.0, len(values) / TREND_CONFIDENCE_SAMPLE_SIZE)` dove la
  costante soglia e 30 campioni.
- **Guardia (AC-39-01)**: Restituisce `(0.0, 0.0, 0.0)` quando vengono forniti
  meno di 2 punti dati. Questo impedisce a `numpy.polyfit` di sollevare un
  `LinAlgError` su input degeneri.

### Scala di Confidenza

| Campioni | Confidenza | Interpretazione |
|----------|------------|-----------------|
| < 2 | 0.0 | Nessun trend (dati insufficienti) |
| 2--9 | 0.07--0.30 | Fase iniziale, inaffidabile |
| 10--19 | 0.33--0.63 | Trend emergente |
| 20--29 | 0.67--0.97 | Trend affidabile |
| 30+ | 1.0 | Confidenza piena |

La soglia di 30 corrisponde al requisito classico dell'intervallo di confidenza
bootstrap, producendo un errore campionario inferiore all'8% al livello di
confidenza del 95%.

## Integrazione

```
PlayerMatchStats (record storici in database.db)
        |
        +-- coaching_service.py chiama compute_trend() per ogni feature
                |
                +-- slope < 0 + confidence >= 0.6 --> Insight "Regressione"
                +-- slope > 0 + confidence >= 0.6 --> Insight "Miglioramento"
                +-- confidence < 0.6 --> Soppresso (dati insufficienti)
                        |
                        +-- coaching/longitudinal_engine.py genera testo di coaching
```

### Consumatori a Valle

| Consumatore | Modulo | Come Utilizza i Trend |
|-------------|--------|-----------------------|
| Coaching Service | `services/coaching_service.py` | Genera insight di coaching longitudinale da slope/confidence |
| Longitudinal Engine | `coaching/longitudinal_engine.py` | Produce narrative di coaching basate sui trend |
| Analytics Engine | `reporting/analytics.py` | Alimenta i grafici di tendenza della dashboard |
| Explanation Generator | `coaching/explainability.py` | Include dati di trend nelle spiegazioni di coaching |

### Flusso dei Dati

1. L'ingestione demo popola le righe `PlayerMatchStats` in `database.db`.
2. `CoachingService.generate_new_insights()` recupera lo storico delle partite del
   giocatore.
3. Per ogni feature tracciata, `compute_trend(values)` viene chiamata con la serie
   storica.
4. La tripla restituita `(slope, volatility, confidence)` viene incapsulata in una
   dataclass `FeatureTrend`.
5. I trend con `confidence >= 0.6` vengono passati a
   `generate_longitudinal_coaching()` per produrre insight di coaching leggibili.
6. Questi insight vengono persistiti come righe `CoachingInsight` nel database.

## Note di Sviluppo

- **Utilita matematica pura**: Nessuno stato, nessun effetto collaterale, nessun
  accesso al database, nessun logging. Questo e intenzionale -- il modulo e una
  dipendenza foglia.
- **TREND_CONFIDENCE_SAMPLE_SIZE = 30**: Questa costante e definita in
  `trend_analysis.py` e non dovrebbe essere modificata senza rivalutare la base
  statistica delle soglie di confidenza.
- **Unita dello slope**: Le unita dipendono dalla feature in input. Per l'ADR, lo
  slope e "punti ADR per partita." Per il rapporto K/D, e "K/D per partita."
  Confronti tra feature richiedono normalizzazione (non fatta qui -- gestita dal
  livello di coaching).
- **La volatilita e assoluta**: Deviazione standard, non coefficiente di variazione.
  Confrontare solo all'interno della stessa feature.
- **Nessun caching**: I risultati vengono calcolati freschi ogni volta. Il servizio
  di coaching decide quando chiamare e come fare caching.
- **Thread safety**: Sia `FeatureTrend` (dataclass immutabile) che `compute_trend()`
  (funzione pura) sono intrinsecamente thread-safe.
