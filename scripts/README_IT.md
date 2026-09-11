> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Script di Build e Setup

> **Autorità:** Regola 7 (CI/CD & Release Engineering)

Script di build e setup per creare eseguibili pronti per la produzione dell'applicazione desktop Macena CS2 Analyzer. Questi script automatizzano il processo di build PyInstaller per la distribuzione su Windows.

## Inventario File

| File | Scopo | Piattaforma |
|------|-------|-------------|
| `build_exe.bat` | Wrapper di compatibilità — delega a `build_production.bat` (la vecchia invocazione inline di Kivy è stata sostituita) | Windows |
| `build_production.bat` | Automazione build di produzione — validazione, migrazione, manifest, build, audit, installer | Windows |
| `Setup_Macena_CS2.ps1` | Setup PowerShell — si riposiziona alla root del repository, crea `venv_win`, installa CPU torch + requirements, inizializza il database, installa Playwright Chromium | Windows |
| `reaggregate.sh` | Pipeline di ri-aggregazione — ripopola le statistiche round, arricchisce le statistiche match, estrae esperienze di coaching, ricostruisce la knowledge base + indici FAISS | Linux (bash) — eseguito sulla macchina separata per dati/training |

## Architettura di Build

Il processo di build utilizza PyInstaller per impacchettare l'intera applicazione Python, le sue dipendenze e tutti gli asset runtime in un eseguibile Windows standalone. Non è necessaria alcuna installazione di Python sulla macchina di destinazione.

```
Codice Sorgente + Dipendenze + Asset
        │
        ▼
    PyInstaller (packaging/cs2_analyzer_win.spec, guidato da build_production.bat)
        │
        ├── Fase di analisi (rileva import, raccoglie file dati)
        ├── Fase di bundle (crea archivio)
        └── Fase di output (genera eseguibile)
        │
        ▼
    dist/Macena_CS2_Analyzer/
        ├── Macena_CS2_Analyzer.exe   # Eseguibile principale
        ├── _internal/                # Python + dipendenze impacchettate
        └── (asset runtime)           # Mappe, font, temi, knowledge base
```

## `build_exe.bat` — Wrapper di Compatibilità

In precedenza un'invocazione inline di PyInstaller rivolta al punto di ingresso Kivy rimosso (`Programma_CS2_RENAN/main.py`). È stato sostituito (non eliminato, così le istruzioni più vecchie che lo invocano continuano a funzionare): lo script ora stampa un avviso e delega a `build_production.bat`, inoltrando tutti gli argomenti, in modo da produrre il build PySide6 attuale da `packaging/cs2_analyzer_win.spec`.

## `build_production.bat` — Automazione Build di Produzione

La pipeline di rilascio completa per Windows (utilizza `venv_win`; eseguire prima `Setup_Macena_CS2.ps1`):

1. **Pre-flight** — verifica la presenza di `venv_win`, `Programma_CS2_RENAN/tools/sync_integrity_manifest.py`, `tools/audit_binaries.py`, `packaging/cs2_analyzer_win.spec` e delle dipendenze core (keyring, kivymd, sqlmodel, alembic)
2. **Pulizia** — rimuove `build/` e `dist/`
3. **Sync dello schema** — `alembic upgrade head` (si interrompe in caso di errore)
4. **Manifest di integrità (RASP)** — rigenera `integrity_manifest.json` tramite `sync_integrity_manifest.py`
5. **Build** — `python Programma_CS2_RENAN/tools/build_tools.py build` (controlli di formato/import, pytest, `alembic upgrade head`, PyInstaller tramite `packaging/cs2_analyzer_win.spec`, SHA-256 `build_manifest.json` in `dist/`)
6. **Audit dei binari** — `python tools/audit_binaries.py` (si interrompe se l'audit di sicurezza fallisce)
7. **Installer (opzionale)** — compila `packaging/windows_installer.iss` con Inno Setup 6 se `ISCC.exe` è presente, producendo `dist\Macena_CS2_Installer.exe`

## Relazione con `packaging/`

La definizione del build risiede in `packaging/cs2_analyzer_win.spec` (punto di ingresso Qt/PySide6 `apps/qt_app/app.py`, 35 hidden import espliciti + `collect_submodules`). Entrambi gli script batch convergono su di essa:

- `build_production.bat` esegue la pipeline completa e costruisce la spec tramite `Programma_CS2_RENAN/tools/build_tools.py build`
- `build_exe.bat` delega semplicemente a `build_production.bat`
- L'installer opzionale è compilato da `packaging/windows_installer.iss` (Inno Setup, `Macena_CS2_Installer.exe`)

Lo stage di distribuzione CI (job `build-distribution` in `.github/workflows/build.yml`) costruisce la stessa spec su `windows-latest` (solo push su `main`) con Python 3.12, `requirements-lock-cpu.txt` e un `pyinstaller==6.17.0` fissato.

## Utilizzo

```bat
REM Setup una tantum dell'ambiente (crea venv_win)
powershell -ExecutionPolicy Bypass -File scripts\Setup_Macena_CS2.ps1

REM Build di produzione (validazione + build + audit + installer)
scripts\build_production.bat
```

```bash
# Pipeline di ri-aggregazione dati (macchina Linux separata, venv attivato)
bash scripts/reaggregate.sh
```

> **Nota:** `reaggregate.sh` viene eseguito sulla macchina Linux separata che ospita il corpus `.dem` (`PRO_DEMO_PATH` in `user_settings.json`) — come il training AI su larga scala, questo carico di lavoro pesante sui dati non viene eseguito sulla macchina di sviluppo Windows. Tempo di esecuzione previsto: 30-90 minuti a seconda del numero di demo.

`Setup_Macena_CS2.ps1` può essere invocato da qualsiasi directory (si sposta prima alla root del repository) e stampa il comando di avvio al completamento: `.\venv_win\Scripts\python.exe -m Programma_CS2_RENAN.apps.qt_app.app`.

## Prerequisiti

- Python 3.11+ con ambiente virtuale attivato
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
| Errori modulo mancante | PyInstaller non rileva import dinamici | Aggiungere a `hiddenimports` in `packaging/cs2_analyzer_win.spec` |
| Asset non trovato a runtime | File dati non impacchettati | Aggiungere il percorso mancante a `datas` nella spec |
| Eseguibile si blocca all'avvio | DLL o file runtime mancanti | Controllare avvisi PyInstaller durante il build |
| Build troppo grande (>3 GB) | PyTorch GPU incluso | Usare torch solo CPU per la distribuzione |

## Note di Sviluppo

- Eseguire sempre `python tools/headless_validator.py` prima del build
- Il build di produzione è circa 1.5 GB (PyTorch solo CPU; vedere `packaging/BUILD_CHECKLIST.md`)
- Il supporto GPU è auto-rilevato a runtime tramite `backend/nn/config.py:get_device()`
- Tutti i percorsi di build (entrambi gli script `.bat` e CI) utilizzano `packaging/cs2_analyzer_win.spec`
