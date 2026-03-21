# Reporting -- Motore Analitico per Dashboard

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

> **Autorita:** Regola 1 (Correttezza), Regola 2 (Sovranita Backend)
> **Skill:** `/correctness-check`

## Introduzione

Questo modulo fornisce il livello di calcolo matematico e aggregazione dati per
l'interfaccia dashboard. Calcola tendenze dei giocatori, dati radar delle abilita,
metriche di addestramento, storico dei rating, statistiche per mappa, analisi dei
punti di forza/debolezza, scomposizioni di utilita e decomposizione dei componenti
del rating HLTV 2.0. Tutti i metodi sono query in sola lettura senza mutazioni.

**Distinzione importante:** Questo e `backend/reporting/`, che si concentra sul
calcolo dei dati per la dashboard Qt. E separato dalla directory di primo livello
`Programma_CS2_RENAN/reporting/`, che gestisce la generazione PDF e i file di output
di visualizzazione.

## Inventario File

| File | Righe | Scopo | Export Principali |
|------|-------|-------|-------------------|
| `__init__.py` | 0 | Marcatore di pacchetto | -- |
| `analytics.py` | 353 | Motore matematico per dashboard | `AnalyticsEngine`, `analytics` (singleton) |

## Architettura e Concetti

### `AnalyticsEngine` -- Provider Centrale dei Dati Dashboard

La classe `AnalyticsEngine` e il punto di ingresso unico per tutta l'aggregazione
dei dati della dashboard. Possiede un riferimento al database manager (ottenuto
tramite `get_db_manager()`) ed espone sette metodi pubblici, ciascuno che restituisce
una forma dati specifica per un widget dell'interfaccia.

#### `get_player_trends(player_name, limit=20)` -> DataFrame

Recupera le metriche di prestazione storica per il widget del grafico delle tendenze:

- Interroga `PlayerMatchStats` dove `player_name` corrisponde e `is_pro == False`
- Ordina per `processed_at DESC`, limita a `limit` record (default 20)
- Converte i risultati in un DataFrame pandas in ordine cronologico (invertito)
- Restituisce un DataFrame vuoto se non esistono dati

#### `get_skill_radar(player_name)` -> Dict

Calcola gli attributi di abilita normalizzati (0--100) per il widget del grafico radar:

| Asse Abilita | Formula | Tetto |
|-------------|---------|-------|
| **Aim** | `(accuracy * 100 * 0.5) + (HS% * 100 * 0.5)` | 100 |
| **Utility** | `(blind_enemies / 2.0 * 100 * 0.6) + (flash_assists / 1.0 * 100 * 0.4)` | 100 |
| **Positioning** | `min(100, (KAST / 0.75) * 100)` | 100 |
| **Map Sense** | `min(100, (ADR / 100.0) * 100)` | 100 |
| **Clutch** | `min(100, clutch_win_pct * 100)` | 100 |

Restituisce dict vuoto `{}` se i dati sono insufficienti.

#### `get_training_metrics()` -> Dict

Recupera la telemetria di addestramento piu recente dalla tabella `CoachState` nel
contesto della sessione knowledge. Restituisce epoch, total_epochs, loss di
addestramento/validazione e confidence del belief.

#### `get_rating_history(player_name, limit=50)` -> List

Restituisce una lista ordinata cronologicamente di dict
`{rating, match_date, demo_name}` per il widget della timeline del rating.
Filtra le partite pro (`is_pro == False`).

#### `get_per_map_stats(player_name)` -> Dict

Aggrega le prestazioni per mappa in `{map_name: {rating, adr, kd, matches}}`:

- Estrae i nomi delle mappe da `demo_name` usando il pattern regex
  `(de_\w+|cs_\w+|ar_\w+)`
- Raggruppa le partite per mappa e calcola media di rating, ADR e K/D per mappa
- Le mappe non identificabili sono raggruppate sotto `"unknown"`

#### `get_strength_weakness(player_name)` -> Dict

Calcola le deviazioni Z-score rispetto alla baseline professionale per le metriche
chiave. Z-score > 0.5 qualifica come punto di forza; Z-score < -0.5 qualifica come
debolezza. Restituisce i primi 5 punti di forza e le prime 5 debolezze.

#### `get_utility_breakdown(player_name)` -> Dict

Confronto per tipo di utilita tra medie utente e medie pro per 6 metriche:
`he_damage`, `molotov_damage`, `smokes_per_round`, `flash_blind_time`,
`flash_assists`, `unused_utility`. La baseline pro viene interrogata da dati reali
del DB (`is_pro == True`). Se non esistono dati pro, il dict pro viene restituito
vuoto (Regola Anti-Fabbricazione).

#### `get_hltv2_breakdown(player_name)` -> Dict

Decompone il rating HLTV 2.0 del giocatore nei suoi cinque componenti: Kill,
Survival, KAST, Impact e Damage. Ogni componente e normalizzato rispetto alle
costanti baseline HLTV importate da `rating.py`.

### Singleton a Livello di Modulo

```python
analytics = AnalyticsEngine()
```

Il modulo espone un singleton pre-costruito `analytics` per l'importazione diretta
da parte dei ViewModel. Questo evita chiamate ripetute a `get_db_manager()` pur
mantenendo la classe testabile tramite istanziazione diretta.

## Integrazione

```
Dashboard UI (Qt MVVM)
    |
    +-- PerformanceViewModel
    |       +-- analytics.get_player_trends()    --> grafico tendenze
    |       +-- analytics.get_skill_radar()      --> grafico radar
    |       +-- analytics.get_rating_history()   --> timeline rating
    |       +-- analytics.get_per_map_stats()    --> scomposizione per mappa
    |
    +-- StrengthWeaknessWidget
    |       +-- analytics.get_strength_weakness() --> card Z-score
    |
    +-- UtilityWidget
    |       +-- analytics.get_utility_breakdown() --> barre utente vs pro
    |
    +-- TrainingStatusWidget
            +-- analytics.get_training_metrics()  --> display epoch/loss
```

### Dipendenze

| Dipendenza | Modulo | Scopo |
|------------|--------|-------|
| `get_db_manager()` | `backend/storage/database.py` | Accesso alle sessioni DB |
| `PlayerMatchStats` | `backend/storage/db_models.py` | Modello ORM per dati partita |
| `CoachState` | `backend/storage/db_models.py` | Modello ORM per stato addestramento |
| `get_pro_baseline()` | `backend/processing/baselines/pro_baseline.py` | Baseline pro per Z-score |
| `calculate_deviations()` | `backend/processing/baselines/pro_baseline.py` | Calcolo Z-score |
| Baseline HLTV 2.0 | `backend/processing/feature_engineering/rating.py` | Decomposizione rating |

## Note di Sviluppo

- **Contratto di sola lettura**: Tutti i metodi usano `get_db_manager().get_session()`
  per letture atomiche. Nessun metodo muta il database.
- **Controllo null difensivo**: Ogni metodo restituisce un default sicuro (dict vuoto,
  lista vuota, DataFrame vuoto) se i dati sottostanti mancano o sono insufficienti.
- **Tutte le query usano SQLModel ORM**: Nessun SQL grezzo.
- **La normalizzazione radar e basata su euristiche**: I pesi sono parametri di
  regolazione, non output ML. Regolarli nel corpo del metodo.
- **Baseline pro da dati reali**: Nessun valore fabbricato come fallback.
- **Nessun caching in questa classe**: I ViewModel gestiscono il caching.
- **Logging**: Utilizza `get_logger("cs2analyzer.analytics")` per logging strutturato.
