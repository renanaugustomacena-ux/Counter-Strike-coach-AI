# `apps/qt_app/viewmodels/` -- ViewModel MVVM

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** Regola 3 (Frontend & UX), Regola 1 (Correttezza)
> **Skill:** `/frontend-ux-review`, `/state-audit`

## Scopo

I ViewModel nel pattern Model-View-ViewModel (MVVM). Ogni schermata ha almeno un ViewModel che possiede:

1. **Caricamento dati** dal backend (servizi, analytics, storage).
2. **Lavoro in background** (query lunghe, inferenza ML) tramite `core/worker.QThread`.
3. **Broadcast di stato** alla schermata tramite `pyqtSignal` / `Signal`.
4. **Semantica di cancellazione** cosi che l'utente non aspetti mai del lavoro stantio dopo la navigazione.

Le schermate restano sottili e visuali; i ViewModel restano spessi e headless. I test per la logica di business avvengono a livello ViewModel -- nessun event loop Qt richiesto (usiamo `QSignalSpy` di Qt o semplici mock).

## Inventario File

| File | ViewModel | Schermata Supportata | Responsabilita |
|------|-----------|----------------------|----------------|
| `__init__.py` | -- | -- | Marcatore di pacchetto. |
| `coach_vm.py` | `CoachViewModel` | Coach | Stato della schermata Coach -- model picker, LLM disponibili (`Ollama /api/tags`), ciclo di vita della sessione. |
| `coaching_chat_vm.py` | `CoachingChatViewModel` | Coach (pannello chat) | Dialogo multi-turno con `CoachingDialogueEngine`. Lista messaggi thread-safe. |
| `focus_insight_vm.py` | `FocusInsightViewModel` | Home (focus card) | Carosello a singolo insight per la focus card della home page. |
| `match_detail_vm.py` | `MatchDetailViewModel` | Match Detail | Carica `PlayerMatchStats`, `RoundStats`, coaching insight, breakdown HLTV 2.0. |
| `match_history_vm.py` | `MatchHistoryViewModel` | Match History | Lista filtrabile dei match utente. Cancellazione al cambio di filtro. |
| `performance_vm.py` | `PerformanceViewModel` | Performance | Trend di rating, statistiche per-mappa, punti di forza / debolezza, breakdown utility. |
| `pro_comparison_vm.py` | `ProComparisonViewModel` | Pro Comparison | Confronto stat utente-vs-pro con baseline role-aware. |
| `pro_player_detail_vm.py` | `ProPlayerDetailViewModel` | Pro Player Detail | Dati profilo pro player, match recenti, contesto percentile. |
| `tactical_vm.py` | `TacticalPlaybackViewModel`, `TacticalGhostViewModel`, `TacticalChronovisorViewModel` | Tactical Viewer | Tre VM coordinati: playback, overlay ghost AI, highlight chronovisor. |
| `user_profile_vm.py` | `UserProfileViewModel` | User Profile | Stato di sync Steam / FaceIT, campi del profilo. |

## Convenzioni

### Threading

Tutto l'I/O avviene fuori dal thread UI. I ViewModel usano `core/worker.QThread`:

```python
def refresh(self):
    self._cancel_token = CancelToken()
    self._worker = run_in_thread(
        self._fetch_match_history,
        cancel_token=self._cancel_token,
    )
    self._worker.finished.connect(self._on_loaded)
    self._worker.failed.connect(self._on_load_failed)
```

`cancel_loads()` (chiamato da `on_leave` della schermata) ribalta il cancel token cosi il worker abbandona pulitamente senza toccare widget che potrebbero essere stati distrutti.

### Segnali

Lo stato pubblico e esposto tramite `Signal` (PySide6) -- mai attributi mutabili. Le schermate sottoscrivono; i ViewModel emettono:

```python
matches_loaded = Signal(list)         # payload: List[MatchSummary]
load_failed = Signal(str)             # payload: motivo leggibile dall'utente
loading_changed = Signal(bool)        # payload: True mentre un fetch e in corso
```

### Politica singleton

I ViewModel sono **per-istanza-di-schermata**, non singleton. Il router costruisce un nuovo ViewModel ogni volta che una schermata viene istanziata. I singleton causerebbero leak di stato tra le navigazioni.

### Nessun widget Qt in questo livello

Importare da `PySide6.QtWidgets` qui e un code smell -- i ViewModel devono essere testabili senza una QApplication attiva. Import limitati a `PySide6.QtCore` (signal, QObject, QThread).

## Pitfall comuni

| Errore | Conseguenza | Fix |
|--------|-------------|-----|
| Fetch sincrono in `__init__` | Blocca il thread UI all'ingresso della schermata | Rinvia alla prima chiamata `refresh()` |
| Dimenticare `cancel_loads()` | Un fetch stantio termina su una schermata distrutta -> segfault | Implementa `cancel_loads()` su ogni VM con worker |
| Condividere una singola sessione `DatabaseManager` tra thread | Contesa SQLite WAL | Usa `get_db_manager().get_session()` per worker |
| Emettere segnali da thread worker a slot non thread-safe | Crash su chiamata cross-thread | Usa connessioni queued (default Qt per `Signal` cross-thread) |

## Integrazione

```
Schermata (apps/qt_app/screens/*)
    +-- ViewModel (questo pacchetto)
            +-- backend/services/*           (logica di business)
            +-- backend/reporting/analytics  (matematica della dashboard)
            +-- backend/storage/database     (singleton di persistenza)
            +-- core/worker.QThread          (esecuzione in background)
```

## Correlati

- Schermate: `apps/qt_app/screens/README.md`
- Worker / threading: `apps/qt_app/core/worker.py`
- Servizi backend: `Programma_CS2_RENAN/backend/services/README.md`
- App parent: `apps/qt_app/README.md`
