# `backend/nn/inference/` -- Utilita neurali sola-inferenza

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorita:** `Programma_CS2_RENAN/backend/nn/inference/`
> **Skill:** `/ml-check`

## Scopo

Questo pacchetto contiene componenti di rete neurale usati **esclusivamente in inferenza** -- consumano checkpoint gia addestrati, non eseguono mai loop di training, e non possiedono mai stato lato training (optimizer, scheduler, EMA shadow, ecc.).

L'intento e tenere i percorsi di training e inferenza fisicamente separati nell'albero sorgente cosi che:

- Un deployment pure-inference (senza optimizer PyTorch, senza DataLoader) importa una superficie piu piccola.
- Invarianti solo-training (flusso del gradiente, cloning EMA, freezing del target encoder) non possano fluire in percorsi di inferenza.
- I test sul comportamento di inferenza possano essere scritti senza mettere in piedi un trainer.

## Inventario File

| File | Scopo |
|------|-------|
| `__init__.py` | Marcatore di pacchetto. |
| `ghost_engine.py` | `GhostEngine` -- proietta le posizioni predette dei giocatori sulla mappa tattica per l'overlay "ghost AI" nel Tactical Viewer. Carica il checkpoint JEPA / RAP attivo ed esegue inferenza forward-only su batch di tick. |

## Riassunto di `GhostEngine`

- Carica il modello tramite `ModelFactory.get_model(model_type).eval()` e disabilita il gradiente con `torch.no_grad()`.
- Accetta una finestra scorrevole di feature di tick recenti (25-dim `METADATA_DIM`) ed emette i delta di posizione proiettati.
- Cachea l'handle del modello cosi che chiamate ripetute riutilizzino gli stessi parametri; reset tramite l'helper pubblico `reset()` dopo uno swap di checkpoint.
- Ricade in un percorso a predizione zero quando nessun checkpoint esiste, cosi l'UI rimane utilizzabile su un'installazione fresca.

## Punti di integrazione

| Consumer | Uso |
|----------|-----|
| `apps/qt_app/screens/tactical_viewer_screen.py` | Renderizza le proiezioni ghost sull'overlay della mappa tattica |
| `apps/desktop_app/tactical_viewmodels.py` (`TacticalGhostViewModel`) | Carica l'engine in modo lazy on demand per evitare costo di startup |

## Note di sviluppo

- **Nessun import lato training.** I moduli qui non devono importare da `training_orchestrator.py`, trainer, helper EMA, o assemblaggi DataLoader.
- **Nessuna mutazione di file.** Le utilita di inferenza non scrivono mai checkpoint. Il salvataggio appartiene a `nn/persistence.py:save_nn()` invocato dai percorsi di training.
- **Determinismo.** L'inferenza viene invocata da thread UI -- proteggi qualsiasi operazione tensoriale non idempotente (es. dropout) con `model.eval()`.
- **Degradazione graziosa.** Checkpoint mancante -> fallback a predizione zero, log a `WARNING`. Mai sollevare nel thread UI.

## Correlati

- Checkpoint addestrati: `Programma_CS2_RENAN/models/global/`
- Helper di persistenza: `backend/nn/persistence.py`
- Orchestrazione di inferenza: `backend/services/coaching_service.py`
- Tactical viewer (consumer): `apps/qt_app/screens/tactical_viewer_screen.py`
