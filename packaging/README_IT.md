> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Packaging — Build e Distribuzione

> **Autorita:** Rule 7 (CI/CD & Release Engineering)

Questa directory contiene tutto il necessario per compilare il Macena CS2 Analyzer in un'applicazione Windows distribuibile.

## Inventario File

| File | Scopo |
|------|-------|
| `cs2_analyzer_win.spec` | Specifica PyInstaller (168 righe) |
| `windows_installer.iss` | Script Inno Setup per installer MSI (42 righe) |
| `BUILD_CHECKLIST.md` | Protocollo di verifica pre-rilascio (76 righe) |

## Build Rapido

Prerequisiti: Python 3.10+, venv attivato, tutte le dipendenze installate.
1. Validare (deve passare prima del build): python tools/headless_validator.py
2. Compilare: python -m PyInstaller --noconfirm packaging/cs2_analyzer_win.spec
3. Output: ls dist/Macena_CS2_Analyzer/

## Dettagli Chiave

- Punto di ingresso: Frontend Qt6 (qt_app/app.py)
- Dati inclusi: 43 voci (temi, mappe, dati esterni, conoscenza, migrazioni, traduzioni, documentazione, temi Qt)
- Hidden Imports: 92 totali (Qt, ML, Database, Parsing, moduli del progetto)
- Dimensione bundle: solo CPU ~1.5 GB, GPU (CUDA) ~2.5 GB
- Installer Windows: Inno Setup con lingue Inglese, Italiano, Portoghese Brasiliano
- Percorso di installazione: Program Files\Macena_CS2_Analyzer

## Note di Sviluppo

- Il file `.spec` gestisce i percorsi mancanti in modo sicuro (per ambienti CI)
- Il rilevamento GPU avviene a runtime tramite `backend/nn/config.py:get_device()`
- matplotlib e sentence_transformers sono NECESSARI a runtime
- Numeri di versione: controllare sia `pyproject.toml` che `windows_installer.iss` prima del rilascio
