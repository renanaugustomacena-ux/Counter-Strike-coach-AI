> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Packaging — Build e Distribuzione

> **Autorità:** Rule 7 (CI/CD & Release Engineering)

Questa directory contiene tutto il necessario per compilare il Macena CS2 Analyzer in un'applicazione Windows distribuibile.

## Inventario File

| File | Scopo |
|------|-------|
| `cs2_analyzer_win.spec` | Specifica PyInstaller (168 righe) |
| `windows_installer.iss` | Script Inno Setup per installer MSI (42 righe) |
| `BUILD_CHECKLIST.md` | Protocollo di verifica pre-rilascio (76 righe) |

## Build Rapido

```bash
# Prerequisiti: Python 3.10+, venv attivato, tutte le dipendenze installate
source /home/renan/.venvs/cs2analyzer/bin/activate

# 1. Validare (deve passare prima del build)
python tools/headless_validator.py

# 2. Compilare
python -m PyInstaller --noconfirm packaging/cs2_analyzer_win.spec --log-level WARN

# 3. Output
ls dist/Macena_CS2_Analyzer/
```

## `cs2_analyzer_win.spec` — Configurazione PyInstaller

### Punto di Ingresso

```python
# Punto di ingresso principale (frontend Qt6)
a = Analysis(['Programma_CS2_RENAN/apps/qt_app/app.py'], ...)
```

### Dati Inclusi (43 voci)

Lo spec include tutti i file necessari a runtime:

| Categoria | File | Scopo |
|-----------|------|-------|
| Asset tematici | `PHOTO_GUI/` (font, sfondi) | Temi visivi |
| Configurazione mappe | `map_config.json`, `map_tensors.json` | Dati spaziali |
| Dati esterni | `data/external/*.csv` | Statistiche di riferimento |
| Conoscenza | `data/knowledge/`, `tactical_knowledge.json` | Dati coaching RAG |
| Migrazioni | `alembic/` | Aggiornamenti schema database |
| Traduzioni | `assets/i18n/` | Localizzazione |
| Documentazione | `data/docs/` | Guida in-app |
| Temi Qt | `apps/qt_app/themes/` | Fogli di stile QSS |

### Hidden Imports (92 totali)

Pacchetti critici che PyInstaller non riesce a rilevare automaticamente:
- **Qt:** PySide6 (QtCore, QtGui, QtWidgets, QtCharts)
- **ML:** torch, torch.nn, torch.optim
- **Database:** sqlmodel, sqlalchemy, alembic
- **Parsing:** demoparser2, pandas, numpy
- **Moduli del progetto:** 30+ moduli interni (app_state, jepa_model, coaching_service, ecc.)

### Pacchetti Esclusi

```python
excludes = ['pytest', 'coverage', 'pre_commit', 'black', 'isort',
            'IPython', 'notebook', 'jupyterlab', 'kivy', 'kivymd',
            'shap', 'playwright']
```

### Dimensioni del Bundle

| Variante | Dimensione | Note |
|----------|-----------|------|
| PyTorch solo CPU | ~1.5 GB | Default, funziona ovunque |
| PyTorch GPU (CUDA) | ~2.5 GB | Rilevato automaticamente a runtime |

## `windows_installer.iss` — Inno Setup

Crea un installer MSI per Windows con:
- **Percorso di installazione:** `Program Files\Macena_CS2_Analyzer`
- **Lingue:** Inglese, Italiano, Portoghese Brasiliano
- **Compressione:** LZMA (compressione solida)
- **Scorciatoie:** Gruppo nel Menu Start + icona Desktop opzionale
- **Post-installazione:** Avvia automaticamente l'applicazione

Richiede [Inno Setup](https://jrsoftware.org/isinfo.php) per la compilazione.

## `BUILD_CHECKLIST.md` — Protocollo di Rilascio

Verifica passo per passo prima della distribuzione:

1. **Pre-build:** Tutti i 13 hook pre-commit passano, copertura test >= 30%, il validatore esce con 0
2. **Sincronizzazione versione:** La versione in `pyproject.toml` corrisponde a AppVersion in `windows_installer.iss`
3. **Build:** PyInstaller con `--noconfirm`
4. **Post-build:** L'exe si avvia, la UI si renderizza, le mappe si caricano, i grafici si generano, `audit_binaries.py` passa
5. **Opzionale:** Compilare l'installer Inno Setup per la distribuzione MSI

## Note di Sviluppo

- Il file `.spec` gestisce i percorsi mancanti in modo sicuro (per ambienti CI)
- `collect_submodules("Programma_CS2_RENAN")` rileva automaticamente i moduli del progetto
- Il rilevamento GPU avviene a runtime tramite `backend/nn/config.py:get_device()`
- **matplotlib è NECESSARIO** a runtime (per visualization_service.py)
- **sentence_transformers è NECESSARIO** (per gli embedding SBERT nel RAG)
- **ncps/hflayers NON sono necessari a runtime** (il modello RAP è sperimentale)
- La pipeline CI/CD (`/.github/workflows/build.yml`) automatizza tutto questo sui push verso main
- Numeri di versione: controllare sia `pyproject.toml` che `windows_installer.iss` prima del rilascio
