# Reporting -- Motore Analitico per Dashboard

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

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
`Programma_CS2_RENAN/reporting/`, che genera report di partita in Markdown e file
immagine di heatmap/visualizzazione.

## Inventario File

| File | Righe | Scopo | Export Principali |
|------|-------|-------|-------------------|
| `__init__.py` | 0 | Marcatore di pacchetto | -- |
| `analytics.py` | 418 | Motore matematico per dashboard | `AnalyticsEngine`, `analytics` (singleton) |

## Architettura e Concetti

### `AnalyticsEngine` -- Provider Centrale dei Dati Dashboard

La classe `AnalyticsEngine` e il punto di ingresso unico per tutta l'aggregazione
dei dati della dashboard. Possiede un riferimento al database manager (ottenuto
tramite `get_db_manager()`) ed espone otto metodi pubblici, ciascuno che restituisce
una forma dati specifica per un widget dell'interfaccia.

Le query con ambito giocatore condividono un helper `_player_filter()`: se il
giocatore ha almeno una partita personale (`is_pro == False`), i risultati sono
limitati a quelle righe; altrimenti il filtro ricade su TUTTE le righe (incluse le
partite pro) cosi che la schermata Performance mostri una panoramica pro invece di
uno stato vuoto. `get_skill_radar()` e l'eccezione -- filtra solo per
`player_name`.

#### `get_player_trends(player_name, limit=20)` -> DataFrame

Recupera le metriche di prestazione storica per il widget del grafico delle tendenze:

- Interroga `PlayerMatchStats` tramite il fallback `_player_filter()` descritto sopra
- Ordina per `processed_at DESC`, limita a `limit` record (default 20)
- Converte i risultati in un DataFrame pandas in ordine cronologico (invertito)
- Restituisce un DataFrame vuoto se non esistono dati

#### `get_skill_radar(player_name)` -> Dict

Calcola gli attributi di abilita normalizzati (0--100) per il widget del grafico radar:

| Asse Abilita | Formula | Tetto |
|-------------|---------|-------|
| **Aim** | `(accuracy * 100 * 0.5) + (HS% * 100 * 0.5)` | non limitato |
| **Utility** | `min(100, blind_enemies / 2.0 * 100) * 0.6 + min(100, flash_assists / 1.0 * 100) * 0.4` | 100 |
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
`{rating, match_date, demo_name, kd_ratio, avg_adr, avg_kast}` per il widget della
timeline del rating, usando il fallback `_player_filter()`. I campi statistici extra
alimentano il contesto dei percentili pro in `performance_vm.py` (fix R4 HIGH,
2026-07-16).

#### `get_per_map_stats(player_name)` -> Dict

Aggrega le prestazioni per mappa in `{map_name: {rating, adr, kd, matches}}`:

- Estrae i nomi delle mappe da `demo_name` usando il pattern regex
  `(de_\w+|cs_\w+|ar_\w+)`
- Ricade su una lista di nomi mappe conosciuti (mirage, inferno, dust2, ...) per
  nomi di file demo come `furia-vs-navi-m1-mirage.dem`, normalizzati a `de_<nome>`
- Raggruppa le partite per mappa e calcola media di rating, ADR e K/D per mappa
- Le mappe non identificabili sono raggruppate sotto `"unknown"`

#### `get_strength_weakness(player_name)` -> Dict

Calcola le deviazioni Z-score rispetto alla baseline professionale per le metriche
chiave:

- Recupera le medie del giocatore per rating, K/D, ADR, KAST, HS%, precisione,
  clutch% e opening duel%
- Chiama `calculate_deviations()` da `pro_baseline.py` per ottenere gli Z-score
- Z-score > 0.5 qualifica come punto di forza; Z-score < -0.5 qualifica come
  debolezza
- Restituisce i primi 5 punti di forza e le prime 5 debolezze, ordinati per
  grandezza

#### `get_utility_breakdown(player_name)` -> Dict

Confronto per tipo di utilita tra medie utente e medie pro per 6 metriche:
`he_damage`, `molotov_damage`, `smokes_per_round`, `flash_blind_time`,
`flash_assists`, `unused_utility`. La baseline pro viene interrogata da dati reali
del DB (`is_pro == True`) e porta un marcatore `"_provenance": "db"`. Se non
esistono dati pro, il dict pro viene restituito vuoto (Regola Anti-Fabbricazione).

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
    +-- PerformanceViewModel (performance_vm.py)
    |       +-- analytics.get_rating_history()     --> timeline rating
    |       +-- analytics.get_per_map_stats()      --> scomposizione per mappa
    |       +-- analytics.get_strength_weakness()  --> card Z-score
    |       +-- analytics.get_utility_breakdown()  --> barre utente vs pro
    |
    +-- MatchDetailViewModel (match_detail_vm.py)
            +-- analytics.get_hltv2_breakdown()    --> componenti HLTV 2.0
```

`get_player_trends()`, `get_skill_radar()` e `get_training_metrics()` attualmente
non hanno consumatori collegati nella UI.

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
  per letture atomiche. Nessun metodo muta il database. Questo e garantito dal design,
  non da guardie nel codice.
- **Controllo null difensivo**: Ogni metodo restituisce un default sicuro (dict vuoto,
  lista vuota, DataFrame vuoto) se i dati sottostanti mancano o sono insufficienti.
- **Tutte le query usano SQLModel ORM**: Nessun SQL grezzo. Questo garantisce type
  safety e compatibilita con la configurazione SQLite WAL.
- **La normalizzazione radar e basata su euristiche**: I pesi (0.5/0.5 per Aim,
  0.6/0.4 per Utility, ecc.) sono parametri di regolazione, non output ML. Regolarli
  nel corpo del metodo man mano che il modello di coaching evolve.
- **Baseline pro da dati reali**: `get_utility_breakdown()` e
  `get_strength_weakness()` usano entrambi dati pro reali dal database. Nessun
  valore fabbricato come fallback (Regola Anti-Fabbricazione).
- **Nessun caching in questa classe**: I ViewModel gestiscono il caching e
  l'invalidazione. `AnalyticsEngine` ricalcola ad ogni chiamata.
- **Logging**: Utilizza `get_logger("cs2analyzer.analytics")` per logging strutturato
  degli errori. Tutti i percorsi di errore registrano l'eccezione e restituiscono
  default sicuri.
- **Il limite di 20 partite per default** per `get_player_trends()` previene letture
  DB eccessive fornendo al contempo linee di tendenza significative.
