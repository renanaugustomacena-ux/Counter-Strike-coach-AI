> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Apps — Livello Interfaccia Utente

> **Autorita:** Rule 3 (Frontend & UX), pattern architetturale MVVM

La directory `apps/` contiene tutto il codice dell'interfaccia utente del Macena CS2 Analyzer. Due framework UI coesistono durante il periodo di migrazione:

| Sottodirectory | Framework | Stato | Scopo |
|----------------|-----------|-------|-------|
| `desktop_app/` | Kivy + KivyMD | Legacy (Fase 0) | UI desktop originale, in fase di sostituzione |
| `qt_app/` | PySide6 (Qt6) | **Attivo** (Fase 2+) | UI desktop di produzione |

## Architettura

Entrambe le UI seguono il pattern **MVVM (Model-View-ViewModel)**:

View (Screen/Widget) ──signals──> ViewModel (QObject) ──queries──> Model (SQLModel/DB)

Principi chiave:
- Le View non accedono mai direttamente al database
- I ViewModel eseguono le query al database su thread in background (Worker/QRunnable)
- I risultati vengono inoltrati al thread principale tramite Qt Signals
- Gli Screen non si importano tra loro (accoppiamento debole)

## Punto di Ingresso

python -m Programma_CS2_RENAN.apps.qt_app.app

## Linee Guida per lo Sviluppo

1. Tutto il nuovo lavoro UI va in `qt_app/` — non aggiungere funzionalita a `desktop_app/`
2. Nessun import Kivy nel codice Qt
3. Il threading in background e obbligatorio — non bloccare mai il thread principale
4. Usare `Worker` da `qt_app/core/worker.py` per tutte le operazioni in background
5. I grafici usano QtCharts (non matplotlib)
6. Localizzazione — tutte le stringhe visibili all'utente devono passare per `i18n_bridge.get_text(key)`
7. Temi — usare `ThemeEngine` per colori/font

## Conteggio File

- `desktop_app/`: 13 file Python (legacy)
- `qt_app/`: 50+ file Python distribuiti in `core/`, `viewmodels/`, `widgets/`, `screens/`
