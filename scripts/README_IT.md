> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Script di Build e Setup

Script di build e setup per creare eseguibili pronti per la produzione e configurazione ambiente di sviluppo.

## Script di Build

- `build_exe.bat` — Script build eseguibile PyInstaller per Windows
- `build_production.bat` — Script build produzione con ottimizzazioni

## Processo di Build

Gli script di build usano PyInstaller per creare un eseguibile standalone dell'applicazione desktop Macena CS2 Analyzer.

### build_exe.bat

- Crea un eseguibile single-file (`--onefile`) o bundle directory
- Include tutte le dipendenze necessarie (Kivy, KivyMD, PyTorch, ncps, hflayers)
- Bundla asset (mappe, immagini, font) da `apps/desktop_app/assets/`
- Configura icona e metadata eseguibile
- Output: `dist/MacenaCS2Analyzer.exe`

### build_production.bat

- Estende `build_exe.bat` con ottimizzazioni produzione
- Abilita flag ottimizzazione Python (`-OO`)
- Rimuove simboli debug e bytecode
- Minimizza dimensione eseguibile
- Valida integrità build

## Utilizzo

```bat
# Build sviluppo
scripts\build_exe.bat

# Build produzione (ottimizzato)
scripts\build_production.bat
```

## Requisiti

- PyInstaller installato (`pip install pyinstaller`)
- Tutte le dipendenze progetto installate
- Ambiente Windows (script batch)

## Note

Gli artefatti di build sono generati nelle directory `dist/` e `build/`. Build pulita: eliminare queste directory prima di ricostruire.
