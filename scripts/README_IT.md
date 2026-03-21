> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Script di Build e Setup

> **Autorità:** Regola 7 (CI/CD & Release Engineering)

Script di build e setup per creare eseguibili pronti per la produzione dell'applicazione desktop Macena CS2 Analyzer. Questi script automatizzano il processo di build PyInstaller per la distribuzione su Windows.

## Inventario File

| File | Scopo | Piattaforma |
|------|-------|-------------|
| `build_exe.bat` | Build di sviluppo — crea eseguibile standalone | Windows |
| `build_production.bat` | Build di produzione — ottimizzato e ridotto | Windows |

## Architettura di Build

Il processo di build utilizza PyInstaller per impacchettare l'intera applicazione Python, le sue dipendenze e tutti gli asset runtime in un eseguibile Windows standalone. Non è necessaria alcuna installazione di Python sulla macchina di destinazione.

```
Codice Sorgente + Dipendenze + Asset
        │
        ▼
    PyInstaller (build_exe.bat)
        │
        ├── Fase di analisi (rileva import, raccoglie file dati)
        ├── Fase di bundle (crea archivio)
        └── Fase di output (genera eseguibile)
        │
        ▼
    dist/Macena/
        ├── Macena.exe          # Eseguibile principale
        ├── _internal/          # Python + dipendenze impacchettate
        └── (asset runtime)     # Mappe, font, temi, knowledge base
```

## `build_exe.bat` — Build di Sviluppo

Questo script crea un bundle in modalità directory (non un singolo file) per facilitare il debug:

### Cosa Fa

1. **Pulisce** i vecchi artefatti di build (directory `dist/`, `build/`)
2. **Esegue PyInstaller** con la seguente configurazione:
   - `--noconsole` — nessuna finestra terminale (applicazione GUI)
   - `--name Macena` — eseguibile denominato `Macena.exe`
   - `--icon` — utilizza `Programma_CS2_RENAN/PHOTO_GUI/icon.ico`
3. **Impacchetta dati runtime:**
   - `PHOTO_GUI/` — font, sfondi, immagini tema
   - `apps/` — schermate applicazione e layout
   - `data/` — knowledge base, CSV esterni, configurazioni mappe
4. **Raccoglie** automaticamente tutti gli asset KivyMD e Kivy

### Punto di Ingresso

```python
# Il build parte dal punto di ingresso legacy Kivy
Programma_CS2_RENAN/main.py
```

### Output

```
dist/Macena/
├── Macena.exe
└── _internal/
    ├── PHOTO_GUI/
    ├── apps/
    ├── data/
    └── (runtime Python + tutte le dipendenze)
```

## `build_production.bat` — Build di Produzione

Estende il build di sviluppo con ottimizzazioni per la produzione:

| Ottimizzazione | Flag | Effetto |
|----------------|------|---------|
| Ottimizzazione Python | `-OO` | Rimuove docstring e istruzioni assert |
| Rimozione debug | (interno PyInstaller) | Rimuove simboli di debug |
| Minimizzazione dimensione | Escludi pacchetti dev | Rimuove pytest, coverage, IPython, ecc. |
| Validazione integrità | Controllo post-build | Verifica che l'eseguibile possa avviarsi |

## Relazione con `packaging/`

Questi script sono l'approccio di build **legacy**. Il sistema di build principale è stato spostato a `packaging/cs2_analyzer_win.spec`, che utilizza il punto di ingresso Qt (PySide6) invece di Kivy:

| Aspetto | `scripts/` (legacy) | `packaging/` (principale) |
|---------|---------------------|--------------------------|
| Punto di ingresso | `main.py` (Kivy) | `apps/qt_app/app.py` (Qt) |
| Framework UI | Kivy + KivyMD | PySide6/Qt |
| File spec | Inline nel .bat | `cs2_analyzer_win.spec` |
| Hidden import | Auto-rilevati | 92 voci esplicite |
| Installer | Nessuno | Inno Setup (MSI) |

## Utilizzo

```bat
REM Build di sviluppo
scripts\build_exe.bat

REM Build di produzione (ottimizzato)
scripts\build_production.bat
```

## Prerequisiti

- Python 3.10+ con ambiente virtuale attivato
- PyInstaller installato (`pip install pyinstaller`)
- Tutte le dipendenze del progetto installate
- Ambiente Windows (script batch)

## Artefatti di Build

| Directory | Contenuto | Tracciato da Git |
|-----------|-----------|------------------|
| `dist/` | Eseguibile finale e file impacchettati | No (.gitignore) |
| `build/` | Artefatti di build intermedi | No (.gitignore) |

Per un build pulito, eliminare entrambe le directory prima di ricostruire.

## Risoluzione Problemi

| Problema | Causa | Soluzione |
|----------|-------|-----------|
| Errori modulo mancante | PyInstaller non rileva import dinamici | Aggiungere ai flag `--hidden-import` |
| Asset non trovato a runtime | File dati non impacchettati | Aggiungere `--add-data` per il percorso mancante |
| Eseguibile si blocca all'avvio | DLL o file runtime mancanti | Controllare avvisi PyInstaller durante il build |
| Build troppo grande (>3 GB) | PyTorch GPU incluso | Usare torch solo CPU per la distribuzione |

## Note di Sviluppo

- Eseguire sempre `python tools/headless_validator.py` prima del build
- Il build di produzione è circa 1.5 GB (PyTorch solo CPU)
- Il supporto GPU è auto-rilevato a runtime tramite `backend/nn/config.py:get_device()`
- Per il build principale basato su Qt, utilizzare `packaging/cs2_analyzer_win.spec` invece
