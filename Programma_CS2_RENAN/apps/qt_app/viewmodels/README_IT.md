# `apps/qt_app/viewmodels/` -- ViewModel MVVM

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** Regola 3 (Frontend & UX), Regola 1 (Correttezza)
> **Skill:** `/frontend-ux-review`, `/state-audit`

## Scopo

I ViewModel nel pattern Model-View-ViewModel (MVVM). Ogni schermata data-driven ha almeno un ViewModel che possiede:

1. **Caricamento dati** dal backend (servizi, analytics, storage).
2. **Lavoro in background** (query lunghe, inferenza ML) tramite `core/worker.Worker` (un `QRunnable` su `QThreadPool`).
3. **Broadcast di stato** alla schermata tramite `Signal` PySide6.
4. **Guard di stanchezza** -- gate di rientro `_is_loading` sulla maggior parte dei VM, piu `cancel()` esplicito (Match History) e `cancel_response()` (chat) dove il lavoro in volo deve essere abbandonato alla navigazione.

Non tutte le schermate passano per questo pacchetto: le schermate config / help non hanno VM, e le schermate profile / wizard (piu il lookup match-id del tactical viewer) eseguono i loro pochi tocchi DB diretti su un `core/worker.Worker` (vedi `screens/README.md`, F-0038).

Le schermate restano sottili e visuali; i ViewModel restano spessi e headless. La logica di business e progettata per essere testabile a livello ViewModel -- nessun event loop Qt richiesto (`QSignalSpy` di Qt o semplici mock bastano); la copertura automatizzata attuale e a livello import (`tools/headless_validator.py`).

## Inventario File

| File | ViewModel | Schermata Supportata | Responsabilita |
|------|-----------|----------------------|----------------|
| `__init__.py` | -- | -- | Marcatore di pacchetto. |
| `coach_vm.py` | `CoachViewModel` | Coach | Carica le righe `CoachingInsight` piu recenti per il giocatore attivo (`insights_loaded` / `is_loading_changed` / `error_changed`). |
| `coaching_chat_vm.py` | `CoachingChatViewModel` | Coach (pannello chat) | Dialogo multi-turno con `CoachingDialogueEngine` (Ollama). Lista messaggi thread-safe; streaming token tramite `streaming_changed`; `cancel_response()` interrompe una risposta in volo. |
| `focus_insight_vm.py` | `FocusInsightViewModel` | Home (focus card) | Stub: controlla se esistono match analizzati e emette un hint di navigazione onesto (nessun delta-vs-pro misurato ancora). |
| `match_detail_vm.py` | `MatchDetailViewModel` | Match Detail | Carica `PlayerMatchStats`, `RoundStats`, coaching insight, breakdown HLTV 2.0. |
| `match_history_vm.py` | `MatchHistoryViewModel` | Match History, Home (lista recenti) | Carica la lista match utente + pro (massimo 50 righe); i chip filtro sono applicati lato schermata. `cancel()` scarta risultati stantii all'uscita dalla schermata. |
| `performance_vm.py` | `PerformanceViewModel` | Performance | Trend di rating, statistiche per-mappa, punti di forza / debolezza, breakdown utility. |
| `pro_comparison_vm.py` | `ProComparisonViewModel` | Pro Comparison | Confronto stat utente-vs-pro con baseline role-aware. |
| `pro_player_detail_vm.py` | `ProPlayerDetailViewModel` | Pro Player Detail | Dati profilo pro player, match recenti, contesto percentile. |
| `tactical_vm.py` | `TacticalPlaybackVM`, `TacticalGhostVM`, `TacticalChronovisorVM` | Tactical Viewer | Tre VM coordinati: playback, overlay ghost AI, highlight chronovisor. |
| `user_profile_vm.py` | `UserProfileViewModel` | User Profile | Carica e salva i campi `PlayerProfile` (bio, ruolo). |

## Convenzioni

### Threading

Tutto l'I/O avviene fuori dal thread UI. I ViewModel usano `core/worker.Worker` sul `QThreadPool` globale:

```python
def load_matches(self):
    self._cancel.clear()                  # threading.Event
    self.is_loading_changed.emit(True)
    worker = Worker(self._bg_load)
    worker.signals.result.connect(self._on_loaded)
    worker.signals.error.connect(self._on_error)
    QThreadPool.globalInstance().start(worker)

def cancel(self):
    self._cancel.set()
```

`cancel()` (chiamato da `on_leave` della schermata) imposta il `threading.Event` cosi il caricamento in background si interrompe pulitamente senza toccare widget che potrebbero essere stati distrutti.

### Segnali

Lo stato pubblico e esposto tramite `Signal` (PySide6) -- mai attributi mutabili. Le schermate sottoscrivono; i ViewModel emettono:

```python
matches_changed = Signal(list)        # payload: lista di righe match
error_changed = Signal(str)           # payload: motivo leggibile dall'utente
is_loading_changed = Signal(bool)     # payload: True mentre un fetch e in corso
```

### Politica singleton

I ViewModel sono **per-istanza-di-schermata**, non singleton. Ogni schermata costruisce il proprio ViewModel al suo avvio dell'app (le schermate vivono nel `QStackedWidget` per la durata dell'applicazione). I singleton causerebbero leak di stato tra le schermate.

### Nessun widget Qt in questo livello

Importare da `PySide6.QtWidgets` qui e un code smell -- i ViewModel devono essere testabili senza una QApplication attiva. Import limitati a `PySide6.QtCore` (signal, QObject, QThreadPool).

## Pitfall comuni

| Errore | Conseguenza | Fix |
|--------|-------------|-----|
| Fetch sincrono in `__init__` | Blocca il thread UI all'ingresso della schermata | Rinvia alla prima chiamata `refresh()` |
| Dimenticare `cancel()` | Un fetch stantio termina su una schermata distrutta -> segfault | Implementa `cancel()` su ogni VM con worker |
| Condividere una singola sessione `DatabaseManager` tra thread | Contesa SQLite WAL | Usa `get_db_manager().get_session()` per worker |
| Emettere segnali da thread worker a slot non thread-safe | Crash su chiamata cross-thread | Usa connessioni queued (default Qt per `Signal` cross-thread) |

## Integrazione

```
Schermata (apps/qt_app/screens/*)
    +-- ViewModel (questo pacchetto)
            +-- backend/services/*           (logica di business)
            +-- backend/reporting/analytics  (matematica della dashboard)
            +-- backend/storage/database     (singleton di persistenza)
            +-- core/worker.Worker           (esecuzione in background)
```

## Correlati

- Schermate: `apps/qt_app/screens/README.md`
- Worker / threading: `apps/qt_app/core/worker.py`
- Servizi backend: `Programma_CS2_RENAN/backend/services/README.md`
- App parent: `apps/qt_app/README.md`
