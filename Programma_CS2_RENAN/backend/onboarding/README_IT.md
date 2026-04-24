> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Onboarding -- Gestione del Flusso Nuovo Utente

> **Autorità:** Regola 3 (Frontend & UX), Regola 4 (Persistenza dei Dati)

Questo modulo gestisce il flusso di onboarding per i nuovi utenti
dell'applicazione CS2 Coach AI. Tiene traccia di quante demo un utente ha
importato, mappa quel conteggio su una fase di prontezza e controlla
l'accesso alle funzionalità di coaching in base alla disponibilità dei
dati. Il sistema è progettato per essere leggero, stateless per chiamata
e compatibile con la cache, così che la UI possa interrogarlo senza
effettuare ripetuti round-trip al database.

## Inventario File

| File | Righe | Scopo | Export Principali |
|------|-------|-------|-------------------|
| `__init__.py` | 1 | Marcatore di package | -- |
| `new_user_flow.py` | ~136 | Gestione fasi di onboarding e cache conteggio demo | `UserOnboardingManager`, `OnboardingStatus`, `OnboardingStage`, `get_onboarding_manager()` |

## Architettura e Concetti

### OnboardingStage

`OnboardingStage` è una classe semplice con tre costanti stringa che
denominano le possibili fasi in cui un utente può trovarsi:

| Costante | Valore | Significato |
|----------|--------|-------------|
| `AWAITING_FIRST_DEMO` | `"awaiting_first_demo"` | Nessuna demo importata. Il coach non può operare. |
| `BUILDING_BASELINE` | `"building_baseline"` | Tra 1 e `RECOMMENDED_DEMOS - 1` demo. Il coaching è attivo ma la baseline non è stabile. |
| `COACH_READY` | `"coach_ready"` | Almeno `RECOMMENDED_DEMOS` demo. Piena capacità di coaching. |

### OnboardingStatus

Un'istantanea immutabile restituita da `get_status()`. È un `@dataclass`
con i seguenti campi:

```
OnboardingStatus
  stage: str               # Una delle costanti OnboardingStage
  demos_uploaded: int       # Totale demo non-pro per l'utente
  demos_required: int       # MIN_INITIAL_DEMOS (attualmente 1)
  demos_recommended: int    # RECOMMENDED_DEMOS (attualmente 3)
  coach_ready: bool         # True quando demos_uploaded >= MIN_INITIAL_DEMOS
  baseline_stable: bool     # True quando demos_uploaded >= RECOMMENDED_DEMOS
  message: str              # Descrizione della fase leggibile dall'utente
```

### Soglie

| Costante | Valore | Scopo |
|----------|--------|-------|
| `MIN_INITIAL_DEMOS` | 1 | Minimo per sbloccare il coaching base |
| `RECOMMENDED_DEMOS` | 3 | Obiettivo per una baseline personale stabile |
| `_CACHE_TTL_SECONDS` | 60 | TTL per la cache in memoria del conteggio demo |

### Cache Conteggio Demo (TASK 2.16.1)

`UserOnboardingManager` mantiene una cache in memoria per utente
(`_demo_count_cache`) che mappa `user_id` su una tupla `(count, timestamp)`.
Quando viene chiamato `get_status()`, il manager verifica prima se il
conteggio in cache è ancora entro `_CACHE_TTL_SECONDS` dal tempo monotonico
corrente. In tal caso, il valore in cache viene restituito senza interrogare
il database.

Dopo l'importazione di una nuova demo, il chiamante dovrebbe invocare
`invalidate_cache(user_id)` per garantire che la prossima chiamata a
`get_status()` rifletta immediatamente il conteggio aggiornato. Chiamare
`invalidate_cache()` senza argomenti svuota l'intera cache.

### Query al Database

Il manager interroga `PlayerMatchStats` per contare le demo non-pro:

```python
select(func.count(PlayerMatchStats.id)).where(
    PlayerMatchStats.player_name == user_id,
    PlayerMatchStats.is_pro == False,
)
```

Solo le demo caricate dall'utente contano per il progresso dell'onboarding.
Le demo professionali importate per la baseline di addestramento sono
escluse (DA-16-01).

### Flusso di Determinazione della Fase

```
demos_uploaded == 0  -->  AWAITING_FIRST_DEMO
0 < demos_uploaded < RECOMMENDED_DEMOS  -->  BUILDING_BASELINE
demos_uploaded >= RECOMMENDED_DEMOS  -->  COACH_READY
```

## Integrazione

- **UI (Qt):** `HomeScreen` e la procedura guidata di onboarding interrogano
  `get_status()` per visualizzare indicatori di progresso, messaggi di
  benvenuto e dialoghi di gating.
- **CoachingService:** Verifica `coach_ready` prima di generare insight di
  coaching ad alta confidenza. Quando `coach_ready` è `False`, gli insight
  vengono comunque generati ma annotati con un avviso di bassa confidenza.
- **Pipeline di Ingestione:** Dopo l'importazione di una demo, la pipeline
  chiama `invalidate_cache()` affinché il prossimo polling della UI veda
  il conteggio aggiornato.
- **Database:** Il modulo legge da `PlayerMatchStats` in `database.db`.
  Non esegue scritture né mutazioni.

## Note di Sviluppo

- `UserOnboardingManager` ricalcola la fase ad ogni chiamata a
  `get_status()`. È stateless a parte la cache TTL.
- La factory `get_onboarding_manager()` è un singleton a livello di
  modulo (`new_user_flow.py:133-140`): la prima chiamata costruisce
  l'istanza e le chiamate successive restituiscono il riferimento
  memorizzato, quindi tutti i chiamanti condividono la stessa cache TTL.
- Le soglie delle fasi sono costanti a livello di classe. Se devono
  diventare configurabili, promuoverle in `core/config.py` come
  impostazioni utente.
- Non bloccare mai completamente le funzionalità in base alla fase.
  Consentire sempre l'output di coaching, ma annotarlo con il livello
  di confidenza derivato dalla fase.
- Il campo `message` in `OnboardingStatus` è una stringa rivolta
  all'utente. Mantenerla concisa e incoraggiante. Le traduzioni sono
  gestite a livello di UI, non in questo modulo.
- Il modulo utilizza il logging strutturato tramite
  `get_logger("cs2analyzer.onboarding")`.
- La cache usa `time.monotonic()` anziché il tempo reale per evitare
  problemi con aggiustamenti dell'orologio di sistema.
