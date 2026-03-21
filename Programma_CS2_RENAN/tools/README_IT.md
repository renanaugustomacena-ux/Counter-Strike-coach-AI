> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Strumenti di Validazione e Diagnostica

**Autorita:** `Programma_CS2_RENAN/tools/` -- Utilita di validazione, diagnostica e sviluppo a livello di package per il Macena CS2 Analyzer.

Questa directory contiene strumenti interni specifici per il package `Programma_CS2_RENAN`. Sono
distinti dalla directory `tools/` a livello root (che contiene entry point a livello progetto come
`headless_validator.py` invocato dagli hook pre-commit). Gli strumenti qui formano una gerarchia
di validazione a 4 livelli che garantisce la salute del sistema dai controlli rapidi fino alla
diagnostica clinica approfondita. Ogni strumento eredita dalla ABC condivisa `BaseValidator`
definita in `_infra.py`, producendo oggetti strutturati `ToolResult` / `ToolReport` con livelli
di severita.

## Gerarchia di Validazione

I quattro livelli sono progettati per essere eseguiti in ordine crescente di profondita e costo temporale:

| Livello | Strumento | Controlli | Tempo | Scopo |
|---------|-----------|-----------|-------|-------|
| 1 | `headless_validator.py` | 291+ in 7 fasi | <20s | Gate di regressione rapido (obbligatorio prima del completamento task) |
| 2 | Suite pytest | 1.515+ test in 79 file | ~2min | Validazione logica, asserzioni di contratto |
| 3 | `backend_validator.py` | 40 in 7 sezioni | ~30s | Salute build, zoo modelli, pipeline coaching |
| 4 | `Goliath_Hospital.py` | 10 reparti | ~60s | Diagnostica clinica completa |

## Inventario File

| File | Categoria | Descrizione |
|------|-----------|-------------|
| `_infra.py` | Infrastruttura | Infrastruttura condivisa: stabilizzazione percorsi, ABC `BaseValidator`, `Console`, `ToolResult`, `ToolReport`, guardia venv |
| `__init__.py` | Infrastruttura | Marcatore package |
| `headless_validator.py` | Validazione | Gate di regressione rapido a 7 fasi (ambiente, import core, import backend, schema database, caricamento config, smoke ML, osservabilita) |
| `backend_validator.py` | Validazione | Gate di salute backend con 7 sezioni (ambiente, database, zoo modelli, analisi, coaching, integrita risorse, salute servizi) |
| `Goliath_Hospital.py` | Diagnostica | Suite diagnostica in stile ospedaliero con 10 reparti (ER, Radiologia, Laboratorio Patologia, Cardiologia, Neurologia, Oncologia, Pediatria, ICU, Farmacia, Clinica Strumenti) |
| `ui_diagnostic.py` | Diagnostica | Validazione UI headless (risorse, localizzazione, asset, validazione KV, coordinate spaziali) |
| `Ultimate_ML_Coach_Debugger.py` | Diagnostica | Strumento di falsificazione degli stati di credenza neurali e logica decisionale; verifica soglie di fedelta, sonde di stabilita, tracciabilita insight |
| `build_tools.py` | Build | Pipeline di build consolidata (lint, test, PyInstaller, verifica hash, manifest di integrita) |
| `context_gatherer.py` | Sviluppo | Raccoglitore di contesto relazionale per un dato file (import, dipendenti, test, superficie API, cronologia git) |
| `db_inspector.py` | Sviluppo | CLI di ispezione database per stato DB completo senza query manuali |
| `dead_code_detector.py` | Pre-commit | Rilevamento moduli orfani, import test obsoleti, package vuoti |
| `dev_health.py` | Pre-commit | Controllo salute sviluppo con modalita `--quick` (pre-commit, <10s) e `--full` (headless + backend) |
| `demo_inspector.py` | Sviluppo | Ispezione unificata file demo (eventi, campi, tracking entita); unisce 7 script probe legacy |
| `project_snapshot.py` | Sviluppo | Snapshot compatto dello stato progetto (dipendenze, stato git, statistiche DB, ambiente) |
| `seed_hltv_top20.py` | Dati | Popola il database metadati HLTV con top-20 team, giocatori e schede statistiche |
| `sync_integrity_manifest.py` | Pre-commit | Rigenera `core/integrity_manifest.json` dagli hash SHA-256 dei file `.py` di produzione |
| `user_tools.py` | Utente | Utilita interattive consolidate (personalize, customize, manual-entry, weights, heartbeat) |
| `logs/` | Infrastruttura | Log di esecuzione degli strumenti |

## Infrastruttura Condivisa (`_infra.py`)

Tutti gli strumenti in questa directory si basano sul modulo di infrastruttura condivisa `_infra.py`, che fornisce:

- **`path_stabilize()`** -- Configurazione canonica dei percorsi; aggiunge `PROJECT_ROOT` a
  `sys.path`, imposta `KIVY_NO_ARGS=1`, configura la codifica UTF-8. Restituisce
  `(PROJECT_ROOT, SOURCE_ROOT)`.
- **`require_venv()`** -- Guardia venv che esce se non nell'ambiente virtuale `cs2analyzer`
  (bypassata quando `CI` e impostato).
- **`BaseValidator`** -- Classe base astratta con `define_checks()`, `check()`, `run()`,
  integrazione `Console` e generazione report JSON.
- **`ToolResult`** / **`ToolReport`** -- Dataclass strutturate per risultati dei controlli con
  livelli `Severity` (CRITICAL, WARNING, INFO, OK).
- **`Console`** -- Output terminale in stile Rich con intestazioni di sezione, indicatori
  pass/fail e tabelle riepilogative.

## Reparti Goliath Hospital

La suite diagnostica `Goliath_Hospital.py` organizza i controlli in reparti a tema medico:

| Reparto | Focus |
|---------|-------|
| Emergency Room (ER) | Problemi critici di sintassi e import |
| Radiology | Scansioni di integrita asset visivi |
| Pathology Lab | Qualita dati, rilevamento mock vs dati reali |
| Cardiology | Salute moduli core (DB, config, modelli) |
| Neurology | Integrita sistemi ML/AI |
| Oncology | Codice morto, pattern deprecati, debito tecnico |
| Pediatrics | File nuovi e modificati di recente |
| ICU | Test di integrazione, flussi end-to-end |
| Pharmacy | Salute dipendenze e controlli versioni |
| Tool Clinic | Valida tutti gli script strumenti del progetto |

## Integrazione Pre-commit

Tre strumenti in questa directory vengono invocati come hook pre-commit:

1. **`dev_health.py --quick`** -- Smoke test import, controllo DB attivo, validazione config (<10s)
2. **`dead_code_detector.py`** -- Scansione moduli orfani e import test obsoleti
3. **`sync_integrity_manifest.py`** -- Rigenera il manifest di integrita RASP; esce con 1 se il
   manifest su disco diverge dagli hash calcolati quando eseguito con `--verify-only`

`headless_validator.py` viene invocato post-task (non come hook git) e deve uscire con 0 prima
che qualsiasi task di sviluppo sia considerato completato.

## Utilizzo

```bash
# Attivare prima l'ambiente virtuale
source ~/.venvs/cs2analyzer/bin/activate

# Validazione headless (gate post-task obbligatorio)
python Programma_CS2_RENAN/tools/headless_validator.py

# Validazione backend (zoo modelli, pipeline coaching, servizi)
python Programma_CS2_RENAN/tools/backend_validator.py

# Diagnostica completa Goliath Hospital
python Programma_CS2_RENAN/tools/Goliath_Hospital.py

# Controllo salute sviluppo rapido (pre-commit)
python Programma_CS2_RENAN/tools/dev_health.py --quick

# Controllo salute sviluppo completo
python Programma_CS2_RENAN/tools/dev_health.py --full

# Ispezione database
python Programma_CS2_RENAN/tools/db_inspector.py

# Ispezione file demo
python Programma_CS2_RENAN/tools/demo_inspector.py all --demo percorso/al/file.dem

# Pipeline di build
python Programma_CS2_RENAN/tools/build_tools.py build

# Snapshot stato progetto
python Programma_CS2_RENAN/tools/project_snapshot.py

# Popolamento dati HLTV top-20
python -m Programma_CS2_RENAN.tools.seed_hltv_top20
```

## Note di Sviluppo

- Tutti gli strumenti usano `_infra.path_stabilize()` per la risoluzione coerente dei percorsi.
  Non manipolare mai `sys.path` direttamente negli script degli strumenti.
- I codici di uscita sono standardizzati: `0 = PASS`, `1 = FAIL`. Gli hook pre-commit si basano
  su questo contratto.
- Il pattern `BaseValidator` garantisce che ogni strumento produca sia output console leggibile
  dall'uomo che report JSON leggibili dalla macchina salvati in `tools/logs/`.
- `Goliath_Hospital.py` usa `print()` per l'output console piuttosto che logging strutturato.
  Come strumento diagnostico (non servizio di produzione), questo e accettabile -- tutti i
  risultati sono catturati in oggetti `DiagnosticFinding` con livelli di severita.
- `demo_inspector.py` consolida 7 script probe legacy (`probe_demo_data`, `probe_entity_track`,
  `probe_events_advanced`, `probe_inventory`, `probe_stats_fields`, `probe_trajectories`,
  `probe_inv_direct`) in un singolo strumento unificato.
- `user_tools.py` consolida 7 strumenti interattivi legacy (`Manual_Data_v2`, `Personalize_v2`,
  `GUI_Master_Customizer`, `ML_Coach_Control_Panel`, `manage_sync`, `Seed_Pro_Data`,
  `Heartbeat_Monitor`) in sottocomandi di un singolo entry point.
