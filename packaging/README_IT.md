# Packaging — Build e Distribuzione

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Autorità:** Regola 7 (CI/CD & Release Engineering)

Questa directory contiene tutto il necessario per compilare il Macena CS2 Analyzer in un'applicazione Windows distribuibile.

## Inventario File

| File | Scopo |
|------|-------|
| `cs2_analyzer_win.spec` | Specifica PyInstaller (172 righe) |
| `windows_installer.iss` | Script Inno Setup per l'installer EXE di Windows (78 righe) |
| `BUILD_CHECKLIST.md` | Protocollo di verifica pre-rilascio (75 righe) |

## Build Rapido

```bat
REM Prerequisiti (Windows): venv_win creato da scripts\Setup_Macena_CS2.ps1, PyInstaller installato
call venv_win\Scripts\activate

REM 1. Validare (deve passare prima del build)
python tools/headless_validator.py

REM 2. Compilare
python -m PyInstaller --noconfirm packaging/cs2_analyzer_win.spec --log-level WARN

REM 3. Output
dir dist\Macena_CS2_Analyzer
```

## `cs2_analyzer_win.spec` — Configurazione PyInstaller

### Punto di Ingresso

```python
# Punto di ingresso principale (frontend Qt6)
a = Analysis(['Programma_CS2_RENAN/apps/qt_app/app.py'], ...)
```

### Dati Inclusi (12 voci)

Lo spec include tutti i file necessari a runtime (i percorsi mancanti vengono filtrati con gestione sicura per gli ambienti CI):

| Categoria | File | Scopo |
|-----------|------|-------|
| Asset tematici | `PHOTO_GUI/` (font, sfondi) | Temi visivi |
| Configurazione mappe | `data/map_config.json` | Dati spaziali |
| Dataset | `data/dataset.csv`, `data/external/` | Statistiche di riferimento |
| Integrità | `core/integrity_manifest.json` | Manifesto sorgente RASP |
| Conoscenza | `backend/knowledge/tactical_knowledge.json` | Dati coaching RAG |
| Migrazioni | `alembic/` (radice del repo) | Aggiornamenti schema database |
| Traduzioni | `assets/i18n/` | Localizzazione |
| Documentazione | `data/docs/` | Guida in-app |
| Temi Qt | `apps/qt_app/themes/` | Fogli di stile QSS |
| Font | `assets/fonts/` | Stack tipografico del design atlas |
| Zone mappe | `assets/map_zones/` | Overlay zone con nome per la mappa tattica |

### Hidden Imports (35 espliciti + auto-collection)

Pacchetti critici che PyInstaller non riesce a rilevare automaticamente:
- **Qt:** PySide6 (QtCore, QtGui, QtWidgets)
- **ML:** torch, torch.nn, torch.optim
- **Database:** sqlmodel, sqlalchemy (incluso dialetto sqlite), alembic
- **Parsing:** demoparser2, pandas, numpy
- **Moduli del progetto:** 21 moduli interni con import differiti (app_state, jepa_model, coaching_service, ecc.)
- Più `collect_submodules("Programma_CS2_RENAN")` che rileva automaticamente il resto del pacchetto.

### Pacchetti Esclusi

```python
excludes = ['pytest', 'coverage', 'pre_commit', 'black', 'isort',
            'IPython', 'notebook', 'jupyterlab',
            'shap', 'playwright',
            'kivy', 'kivymd',      # migrati a Qt
            'ncps', 'hflayers']    # dipendenze opzionali RAP, non necessarie a runtime
```

### Dimensioni del Bundle

| Variante | Dimensione | Note |
|----------|-----------|------|
| PyTorch solo CPU | ~1.5 GB | Default, funziona ovunque |
| PyTorch GPU (CUDA) | ~2.5 GB | Rilevato automaticamente a runtime |

## `windows_installer.iss` — Inno Setup

Crea un eseguibile di setup per Windows (`dist/Macena_CS2_Installer.exe`) con:
- **Percorso di installazione:** `Program Files\Macena_CS2_Analyzer`
- **Lingue:** Inglese, Italiano, Portoghese Brasiliano
- **Compressione:** LZMA (compressione solida)
- **Scorciatoie:** Gruppo nel Menu Start + icona Desktop opzionale
- **Runtime MSVC:** installa silenziosamente `vc_redist.x64.exe` se mancante (posizionarlo in `packaging/` prima della compilazione)
- **Post-installazione:** Avvia opzionalmente l'applicazione

Richiede [Inno Setup](https://jrsoftware.org/isinfo.php) per la compilazione.

## `BUILD_CHECKLIST.md` — Protocollo di Rilascio

Verifica passo per passo prima della distribuzione:

1. **Pre-build:** Tutti i 14 hook pre-commit passano, copertura test >= 50%, il validatore esce con 0
2. **Sincronizzazione versione:** La versione in `pyproject.toml` corrisponde a AppVersion in `windows_installer.iss`
3. **Build:** PyInstaller con `--noconfirm`
4. **Post-build:** L'exe si avvia, la UI si renderizza, le mappe si caricano, i grafici si generano, `audit_binaries.py` passa
5. **Opzionale:** Compilare l'installer Inno Setup per la distribuzione

## Driver di Build e CI

Tre percorsi consumano lo spec — tutti terminano in `dist/Macena_CS2_Analyzer/`:

| Driver | Invocazione | Note |
|--------|-------------|------|
| Diretto | `python -m PyInstaller --noconfirm packaging/cs2_analyzer_win.spec --log-level WARN` | Build Rapido sopra |
| Pipeline batch | `scripts/build_production.bat` → `Programma_CS2_RENAN/tools/build_tools.py build` | Controlli pre-volo, migrazione alembic, manifesto RASP, PyInstaller, audit binari, Inno Setup opzionale (`scripts/build_exe.bat` delega qui) |
| Fase dist CI | Job `build-distribution` in `.github/workflows/build.yml` | Solo push su `main` |

La fase dist CI (rielaborata 14-08-2026) gira su `windows-latest` e:

- fissa **Python 3.12** — `requirements-lock-cpu.txt` è stato congelato su Python 3.12.10, e il lock viene installato sull'interprete per cui è stato congelato
- installa il set di dipendenze CPU bloccato (`requirements-lock-cpu.txt`) più un `pyinstaller==6.17.0` fissato (deliberatamente assente dal lock runtime)
- imposta `PYTHONUTF8=1` a livello di job (un `setup.py` di una dipendenza git-sdist fallisce con il cp1252 predefinito del runner)
- usa un comando nativo per step, così un'installazione fallita non può più essere mascherata dall'exit code di un comando successivo
- valida 10 file dati critici prima del build, poi esegue PyInstaller su questo spec
- verifica il risultato con `tools/audit_binaries.py` e carica `dist/` come artefatto `cs2-analyzer-windows` (retention 30 giorni)

> `tools/build_pipeline.py` (la vecchia pipeline "industrial" a 5 stadi) precede lo spostamento in `packaging/` e cerca ancora lo spec nella radice del repo; i driver mantenuti sono i tre sopra.

## Note di Sviluppo

- Il file `.spec` gestisce i percorsi mancanti in modo sicuro (per ambienti CI)
- `collect_submodules("Programma_CS2_RENAN")` rileva automaticamente i moduli del progetto
- Il rilevamento GPU avviene a runtime tramite `backend/nn/config.py:get_device()`
- **matplotlib è NECESSARIO** a runtime (per visualization_service.py)
- **sentence_transformers è NECESSARIO** (per gli embedding SBERT nel RAG)
- **ncps/hflayers NON sono necessari a runtime** (il modello RAP è sperimentale)
- Numeri di versione: controllare sia `pyproject.toml` che `windows_installer.iss` prima del rilascio
