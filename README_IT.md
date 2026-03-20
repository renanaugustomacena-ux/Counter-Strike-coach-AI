# Macena CS2 Analyzer

[![CI Pipeline](https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI/actions/workflows/build.yml/badge.svg)](https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI/actions/workflows/build.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Proprietary%20%7C%20Apache--2.0-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-1523%20passed-brightgreen.svg)]()

**Coach Tattico basato su IA per Counter-Strike 2**

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

---

## Cos'e?

Macena CS2 Analyzer e un'applicazione desktop che funge da coach IA personale per Counter-Strike 2. Analizza file demo professionali e dell'utente, addestra molteplici modelli di reti neurali e fornisce coaching tattico personalizzato confrontando il tuo gameplay con gli standard professionali.

Il sistema impara dalle migliori partite professionali mai giocate e adatta il suo coaching al tuo stile di gioco individuale -- che tu sia un AWPer, entry fragger, support o qualsiasi altro ruolo. La pipeline di coaching fonde previsioni di machine learning con conoscenze tattiche recuperate, analisi basata su teoria dei giochi e modellazione bayesiana delle credenze per produrre consigli azionabili e context-aware.

A differenza degli strumenti di coaching statici con suggerimenti pre-scritti, questo sistema costruisce la sua intelligenza da dati reali di gameplay professionistico. Al primo avvio le reti neurali hanno pesi casuali e zero conoscenza tattica. Ogni demo che gli fornisci rende il coach piu intelligente, piu sfumato e piu personalizzato.

---

## Indice

- [Funzionalita Principali](#funzionalita-principali)
- [Requisiti di Sistema](#requisiti-di-sistema)
- [Avvio Rapido](#avvio-rapido)
- [Panoramica Architetturale](#panoramica-architetturale)
- [Mappe Supportate](#mappe-supportate)
- [Stack Tecnologico](#stack-tecnologico)
- [Struttura del Progetto](#struttura-del-progetto)
- [Punti di Ingresso](#punti-di-ingresso)
- [Validazione e Qualita](#validazione-e-qualita)
- [Supporto Multi-Lingua](#supporto-multi-lingua)
- [Funzionalita di Sicurezza](#funzionalita-di-sicurezza)
- [Maturita del Sistema](#maturita-del-sistema)
- [Documentazione](#documentazione)
- [Alimentare il Coach](#alimentare-il-coach)
- [Risoluzione dei Problemi](#risoluzione-dei-problemi)
- [Indice Completo della Documentazione](#indice-completo-della-documentazione)
- [Licenza](#licenza)
- [Autore](#autore)

---

## Funzionalita Principali

### Pipeline di Coaching IA

- **Catena di Fallback a 4 Livelli** -- COPER > Ibrido > RAG > Base, garantendo che il sistema produca sempre consigli utili indipendentemente dalla maturita del modello
- **COPER Experience Bank** -- Memorizza e recupera esperienze di coaching passate pesate per recenza, efficacia e similarita di contesto
- **Base di Conoscenza RAG** -- Retrieval-Augmented Generation con pattern di riferimento professionali e conoscenza tattica
- **Integrazione Ollama** -- LLM locale opzionale per la rifinitura in linguaggio naturale degli insight di coaching
- **Attribuzione Causale** -- Ogni raccomandazione di coaching include una spiegazione "perche" tracciabile a specifiche decisioni di gameplay

### Sottosistemi di Reti Neurali

- **RAP Coach** -- Architettura a 7 livelli che combina percezione, memoria (LTC-Hopfield), strategia (Mixture-of-Experts con superposizione), pedagogia (value function), predizione posizione, attribuzione causale e aggregazione output
- **Encoder JEPA** -- Joint-Embedding Predictive Architecture per pre-training auto-supervisionato con loss contrastiva InfoNCE e target encoder EMA
- **VL-JEPA** -- Estensione Vision-Language con allineamento di 16 concetti tattici (posizionamento, utility, economia, engagement, decisione, psicologia)
- **AdvancedCoachNN** -- Architettura LSTM + Mixture-of-Experts per la predizione dei pesi di coaching
- **Neural Role Head** -- Classificatore MLP a 5 ruoli (entry, support, lurk, AWP, anchor) con KL-divergence e consensus gating
- **Modelli Bayesiani delle Credenze** -- Tracking dello stato mentale dell'avversario con calibrazione adattiva dai dati della partita

### Analisi Demo

- **Parsing a Livello di Tick** -- Ogni tick dei file `.dem` e analizzato tramite demoparser2, preservando tutto lo stato di gioco (nessuna decimazione di tick)
- **Rating HLTV 2.0** -- Calcolato per partita usando la formula ufficiale HLTV 2.0 (uccisioni, morti, ADR, KAST%, sopravvivenza, assist flash)
- **Breakdown Round per Round** -- Timeline dell'economia, analisi degli engagement, uso delle utility, tracking del momentum
- **Decadimento Temporale della Baseline** -- Traccia l'evoluzione delle abilita del giocatore nel tempo con pesi a decadimento esponenziale

### Analisi basata su Teoria dei Giochi

- **Alberi Expectiminimax** -- Valutazione decisionale game-theoretic per scenari strategici
- **Probabilita di Morte Bayesiana** -- Stima la probabilita di sopravvivenza basata su posizione, equipaggiamento e stato nemico
- **Indice di Inganno** -- Quantifica l'imprevedibilita posizionale rispetto alle baseline professionali
- **Analisi del Raggio di Engagement** -- Mappa la selezione delle armi contro le distribuzioni di distanza di engagement
- **Probabilita di Vittoria** -- Calcolo della probabilita di vittoria in tempo reale
- **Tracking del Momentum** -- Traiettoria di confidenza e prestazione round per round

### Applicazione Desktop

- **Architettura Dual UI** -- Frontend PySide6/Qt (primario) con fallback legacy Kivy/KivyMD, entrambi con pattern MVVM
- **Visualizzatore Tattico 2D** -- Replay demo in tempo reale con posizioni giocatori, eventi uccisione, indicatori bomba e predizioni AI ghost
- **Cronologia Partite** -- Lista scorrevole delle partite recenti con rating codificati per colore
- **Dashboard Prestazioni** -- Tendenze del rating, statistiche per mappa, analisi punti di forza/debolezza, breakdown utility
- **Chat con il Coach** -- Conversazione AI interattiva con pulsanti quick-action e domande in testo libero
- **Profilo Utente** -- Integrazione Steam con importazione automatica delle partite
- **3 Temi Visivi** -- CS2 (arancione), CS:GO (blu-grigio), CS 1.6 (verde) con wallpaper a rotazione

### Training e Automazione

- **4-Daemon Session Engine** -- Scanner (scoperta file), Digester (elaborazione demo), Teacher (training modelli), Pulse (monitoraggio salute)
- **Gating di Maturita a 3 Stadi** -- CALIBRATING (0-49 demo, 0.5x confidenza) > LEARNING (50-199, 0.8x) > MATURE (200+, piena)
- **Conviction Index** -- Composito a 5 segnali che traccia entropia delle credenze, specializzazione gate, focus concettuale, accuratezza valore e stabilita ruolo
- **Auto-Retraining** -- Il training si attiva automaticamente al 10% di crescita del conteggio demo
- **Rilevamento Drift** -- Monitoraggio drift delle feature basato su Z-score con flag automatico di retraining
- **Coach Introspection Observatory** -- Integrazione TensorBoard con macchina a stati di maturita, proiettore embedding e tracking della convinzione

---

## Requisiti di Sistema

| Componente | Minimo | Consigliato |
|------------|--------|-------------|
| OS | Windows 10 / Ubuntu 22.04 | Windows 10/11 |
| Python | 3.10 | 3.10 o 3.12 |
| RAM | 8 GB | 16 GB |
| GPU | Nessuna (modalita CPU) | NVIDIA GTX 1650+ (CUDA 12.1) |
| Disco | 3 GB liberi | 5 GB liberi |
| Display | 1280x720 | 1920x1080 |

---

## Avvio Rapido

### 1. Clona

```bash
git clone https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI.git
cd Counter-Strike-coach-AI
```

### 2. Setup Automatizzato (Windows)

```powershell
.\scripts\Setup_Macena_CS2.ps1
```

Crea un ambiente virtuale, installa tutte le dipendenze, inizializza il database e configura Playwright per lo scraping HLTV.

**Per il supporto GPU NVIDIA**, dopo il completamento dello script:

```powershell
.\venv_win\Scripts\pip.exe install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 3. Setup Manuale (Windows)

```powershell
python -m venv venv_win
.\venv_win\Scripts\activate

# PyTorch (scegli UNO):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu       # Solo CPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121     # GPU NVIDIA

pip install -r requirements.txt
python -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database()"
pip install playwright && python -m playwright install chromium
```

### 4. Setup Manuale (Linux)

```bash
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev libsdl2-dev libglew-dev build-essential

python3.10 -m venv venv_linux
source venv_linux/bin/activate

# PyTorch (scegli UNO):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu       # Solo CPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121     # GPU NVIDIA

pip install -r requirements.txt
python -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database()"
pip install playwright && python -m playwright install chromium
```

### 5. Verifica Installazione

```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import PySide6; print(f'PySide6: {PySide6.__version__}')"
python -c "from Programma_CS2_RENAN.backend.nn.config import get_device; print(f'Device: {get_device()}')"
```

### 6. Avvia

```bash
# Applicazione desktop (GUI Qt -- primaria)
python -m Programma_CS2_RENAN.apps.qt_app.app

# Applicazione desktop (GUI Kivy -- fallback legacy)
python Programma_CS2_RENAN/main.py

# Console interattiva (TUI live con pannelli in tempo reale)
python console.py

# CLI one-shot (build, test, audit, hospital, sanitize)
python goliath.py
```

> Per la guida completa con configurazione API, walkthrough delle funzionalita e troubleshooting, consulta la [Guida Utente](docs/USER_GUIDE_IT.md).

---

## Panoramica Architetturale

### Pipeline GUARDA > IMPARA > PENSA > PARLA

Il sistema e organizzato come una pipeline a 4 stadi che trasforma file demo grezzi in coaching personalizzato:

```
GUARDA (Ingestione)    IMPARA (Training)      PENSA (Inferenza)       PARLA (Dialogo)
  Daemon Scanner         Daemon Teacher         Pipeline COPER          Template + Ollama
  Parsing demo           Maturita a 3 stadi     Conoscenza RAG          Attribuzione causale
  Estrazione feature     Training multi-modello  Teoria dei giochi       Confronti con i pro
  Archiviazione tick     Rilevamento drift       Modellazione credenze   Scoring di gravita
```

**GUARDA** -- Il daemon Scanner monitora continuamente le cartelle demo configurate per nuovi file `.dem`. Quando trovati, il daemon Digester analizza ogni tick usando demoparser2, estrae il vettore canonico di feature a 25 dimensioni, calcola i rating HLTV 2.0 e archivia tutto in database SQLite per-match.

**IMPARA** -- Il daemon Teacher addestra automaticamente i modelli neurali quando si accumulano dati sufficienti. Il training procede attraverso 3 stadi di maturita (CALIBRATING > LEARNING > MATURE). Multiple architetture si addestrano in parallelo: JEPA per l'apprendimento auto-supervisionato delle rappresentazioni, RAP Coach per la modellazione delle decisioni tattiche, NeuralRoleHead per la classificazione del ruolo dei giocatori.

**PENSA** -- A tempo di inferenza, la pipeline COPER combina previsioni neurali con esperienze di coaching recuperate, conoscenza RAG e analisi di teoria dei giochi. Una catena di fallback a 4 livelli (COPER > Ibrido > RAG > Base) garantisce che i consigli siano sempre disponibili indipendentemente dalla maturita del modello.

**PARLA** -- L'output finale del coaching e formattato con livelli di gravita, attribuzione causale ("perche questo consiglio") e opzionalmente rifinito attraverso un LLM locale Ollama per la qualita del linguaggio naturale.

### 4-Daemon Session Engine

| Daemon | Ruolo | Trigger |
|--------|-------|---------|
| **Scanner (Hunter)** | Scopre nuovi file `.dem` nelle cartelle configurate | Scansione periodica o file watcher |
| **Digester** | Analizza le demo, estrae feature, calcola rating | Nuovo file rilevato dallo Scanner |
| **Teacher** | Addestra i modelli neurali sui dati accumulati | Soglia di crescita 10% nel conteggio demo |
| **Pulse** | Monitoraggio salute, rilevamento drift, stato sistema | Continuo in background |

### Pipeline di Coaching COPER

COPER (Coaching via Organized Pattern Experience Retrieval) e il motore di coaching principale. Opera una catena di fallback a 4 livelli:

1. **Modalita COPER** -- Pipeline completa: recupero Experience Bank + conoscenza RAG + previsioni modello neurale + confronti professionali. Richiede modelli addestrati.
2. **Modalita Ibrida** -- Combina previsioni neurali con consigli basati su template quando alcuni modelli sono ancora in calibrazione.
3. **Modalita RAG** -- Puro recupero: cerca pattern di coaching rilevanti nella knowledge base senza inferenza neurale. Funziona con le sole demo ingerite.
4. **Modalita Base** -- Consigli basati su template dall'analisi statistica (deviazioni media/std dalle baseline professionali). Funziona immediatamente.

---

## Mappe Supportate

Il sistema supporta tutte le 9 mappe competitive Active Duty con mappatura coordinate pixel-accurate:

| Mappa | Tipo | Calibrazione |
|-------|------|--------------|
| de_mirage | Singolo livello | pos (-3230, 1713), scala 5.0 |
| de_inferno | Singolo livello | pos (-2087, 3870), scala 4.9 |
| de_dust2 | Singolo livello | pos (-2476, 3239), scala 4.4 |
| de_overpass | Singolo livello | pos (-4831, 1781), scala 5.2 |
| de_ancient | Singolo livello | pos (-2953, 2164), scala 5.0 |
| de_anubis | Singolo livello | pos (-2796, 3328), scala 5.22 |
| de_train | Singolo livello | pos (-2477, 2392), scala 4.7 |
| de_nuke | **Multi-livello** | pos (-3453, 2887), scala 7.0, Z-cutoff -495 |
| de_vertigo | **Multi-livello** | pos (-3168, 1762), scala 4.0, Z-cutoff 11700 |

Le mappe multi-livello (Nuke, Vertigo) usano cutoff sull'asse Z per separare livello superiore e inferiore per un rendering 2D accurato.

---

## Stack Tecnologico

| Categoria | Pacchetto | Scopo |
|-----------|-----------|-------|
| **ML Framework** | PyTorch | Training e inferenza reti neurali |
| **Reti Ricorrenti** | ncps | Reti Liquid Time-Constant (LTC) |
| **Memoria Associativa** | hopfield-layers | Layer rete Hopfield per la memoria |
| **Parsing Demo** | demoparser2 | Parsing a livello di tick dei file demo CS2 |
| **Framework UI (primario)** | PySide6 | GUI desktop cross-platform basata su Qt |
| **Framework UI (legacy)** | Kivy + KivyMD | GUI di fallback legacy |
| **ORM Database** | SQLAlchemy + SQLModel | Modelli e query database |
| **Migrazioni** | Alembic | Migrazioni schema database |
| **Web Scraping** | Playwright | Browser headless per HLTV |
| **Data Science** | NumPy, Pandas, SciPy, scikit-learn | Calcolo numerico e analisi |
| **Sicurezza** | cryptography | Cifratura credenziali |
| **TUI** | Rich | UI terminale per modalita console |
| **Testing** | pytest + pytest-cov | Framework di test e copertura |
| **Packaging** | PyInstaller | Distribuzione binaria |

---

## Punti di Ingresso

### Applicazione Desktop (GUI Qt -- Primaria)

```bash
python -m Programma_CS2_RENAN.apps.qt_app.app
```

Interfaccia grafica completa con visualizzatore tattico, cronologia partite, dashboard prestazioni, chat con il coach e impostazioni. Si apre a 1280x720. Al primo avvio, una procedura guidata in 4 passaggi configura la directory Brain Data Root.

### Applicazione Desktop (GUI Kivy -- Legacy)

```bash
python Programma_CS2_RENAN/main.py
```

Interfaccia Kivy/KivyMD originale. Mantenuta come fallback per ambienti dove Qt non e disponibile.

### Console Interattiva (TUI)

```bash
python console.py
```

UI terminale con pannelli in tempo reale per sviluppo e controllo runtime.

### CLI di Produzione (Goliath)

```bash
python goliath.py <comando>
```

Orchestratore master per build di produzione, release e diagnostica.

### Runner Ciclo di Training

```bash
python run_full_training_cycle.py
```

Script standalone che esegue un ciclo di training completo fuori dal daemon engine.

---

## Validazione e Qualita

| Strumento | Ambito | Comando | Check |
|-----------|--------|---------|-------|
| Headless Validator | Gate di regressione primario | `python tools/headless_validator.py` | 291+ check |
| Suite Pytest | Test logici e integrazione | `python -m pytest Programma_CS2_RENAN/tests/ -x -q` | 1,515+ test |
| Feature Audit | Integrita feature engineering | `python tools/Feature_Audit.py` | Dimensioni vettore, range |
| Portability Test | Compatibilita cross-platform | `python tools/portability_test.py` | Check importazione, percorsi |
| Safety Verifier | Check di sicurezza | `python tools/verify_all_safe.py` | RASP, scansione segreti |
| DB Health | Diagnostica database | `python tools/db_health_diagnostic.py` | Schema, modalita WAL, integrita |

**Gate CI/CD:** L'headless validator deve restituire exit code 0 prima che qualsiasi commit sia considerato valido. La pipeline CI gira su Ubuntu e Windows con GitHub Actions SHA-pinned.

---

## Supporto Multi-Lingua

| Lingua | UI | Guida Utente | README |
|--------|----|-------------|--------|
| English | Completa | [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | [README.md](README.md) |
| Italiano | Completa | [docs/USER_GUIDE_IT.md](docs/USER_GUIDE_IT.md) | [README_IT.md](README_IT.md) |
| Portugues | Completa | [docs/USER_GUIDE_PT.md](docs/USER_GUIDE_PT.md) | [README_PT.md](README_PT.md) |

La lingua puo essere cambiata a runtime dalle Impostazioni senza riavviare l'applicazione.

---

## Funzionalita di Sicurezza

- **Manifesto di Integrita RASP** -- Hash SHA-256 di tutti i file sorgente critici, verificati all'avvio
- **Integrazione OS Keyring** -- API key memorizzate nel Windows Credential Manager / keyring Linux, mai in testo semplice
- **SQLite WAL Mode** -- Write-Ahead Logging per accesso concorrente sicuro su tutti i database
- **Validazione Input** -- Modelli Pydantic al confine di ingestione, query SQL parametrizzate
- **Logging Strutturato** -- Namespace `get_logger("cs2analyzer.<modulo>")`, nessun PII nei log

---

## Maturita del Sistema

| Sottosistema | Stato | Punteggio | Note |
|-------------|-------|-----------|------|
| Coaching COPER | OPERATIVO | 8/10 | Experience bank + RAG + riferimenti pro. Funziona immediatamente. |
| Motore Analitico | OPERATIVO | 6/10 | Rating HLTV 2.0, breakdown round, timeline economia. |
| JEPA Base (InfoNCE) | OPERATIVO | 7/10 | Pre-training auto-supervisionato, target encoder EMA. |
| Neural Role Head | OPERATIVO | 7/10 | MLP a 5 ruoli con KL-divergence, consensus gating. |
| RAP Coach (7 livelli) | LIMITATO | 3/10 | Architettura completa (LTC+Hopfield), necessita 200+ demo. |
| VL-JEPA (16 concetti) | LIMITATO | 2/10 | Allineamento concettuale implementato, qualita etichette in miglioramento. |

---

## Documentazione

| Documento | Descrizione |
|-----------|-------------|
| [Guida Utente (IT)](docs/USER_GUIDE_IT.md) | Installazione, setup wizard, API key, tutte le schermate, troubleshooting |
| [User Guide (EN)](docs/USER_GUIDE.md) | Guida utente completa in inglese |
| [Guia do Usuario (PT)](docs/USER_GUIDE_PT.md) | Guida utente in portoghese |
| [Architettura Parte 1](docs/AI-cs2-coach-part1.md) | Design del sistema e architettura core |
| [Architettura Parte 2](docs/AI-cs2-coach-part2.md) | Sottosistemi reti neurali |
| [Architettura Parte 3](docs/AI-cs2-coach-part3.md) | Pipeline di coaching e gestione della conoscenza |

La cartella `docs/Studies/` contiene 17 paper di ricerca sulle fondamenta teoriche di ogni sottosistema.

---

## Alimentare il Coach

Il coach IA viene fornito senza conoscenza pre-addestrata. Apprende esclusivamente da file demo professionali CS2.

| Demo Pro | Livello | Confidenza | Cosa Succede |
|----------|---------|------------|--------------|
| 0-9 | Non pronto | 0% | Minimo 10 demo pro richieste per il primo ciclo di training |
| 10-49 | CALIBRATING | 50% | Coaching base attivo, consigli marcati come provvisori |
| 50-199 | LEARNING | 80% | Affidabilita crescente, sempre piu personalizzato |
| 200+ | MATURE | 100% | Piena confidenza, massima accuratezza |

### Dove Trovare Demo Pro

1. Vai su [hltv.org](https://www.hltv.org) > Results
2. Filtra per eventi top-tier: Major Championship, IEM Katowice/Cologne, BLAST Premier, ESL Pro League
3. Seleziona partite di team nella top-20 (Navi, FaZe, Vitality, G2, Spirit, Heroic)
4. Preferisci serie BO3/BO5 per massimizzare i dati di training per download
5. Diversifica su tutte le mappe Active Duty

---

## Risoluzione dei Problemi

| Problema | Soluzione |
|----------|----------|
| `ModuleNotFoundError: No module named 'PySide6'` | Installa le dipendenze Qt: `pip install PySide6` |
| `ModuleNotFoundError: No module named 'kivy'` | Per la UI legacy: `pip install Kivy==2.3.0 KivyMD==1.2.0` (piu kivy-deps su Windows) |
| `CUDA not available` | Verifica il driver con `nvidia-smi`, reinstalla PyTorch con `--index-url https://download.pytorch.org/whl/cu121` |
| `database is locked` | Chiudi tutti i processi Python e riavvia |
| Reset allo stato di fabbrica | Elimina `Programma_CS2_RENAN/user_settings.json` e riavvia |

---

## Indice Completo della Documentazione

Tutti i README e documenti tecnici del progetto. Clicca su qualsiasi link per aprire il documento.

### Serie Book Coach (PDF)

- [Ultimate CS2 Coach — Sistema AI](docs/Book-Coach-1.pdf)
- [Ultimate CS2 Coach — Parte 1A — Il Cervello](docs/Book-Coach-1A.pdf)
- [Ultimate CS2 Coach — Parte 1B — I Sensi e lo Specialista](docs/Book-Coach-1B.pdf)
- [Ultimate CS2 Coach — Parte 2 — Servizi, Analisi e Database](docs/Book-Coach-2.pdf)
- [Ultimate CS2 Coach — Parte 3 — Programma, UI, Tools e Build](docs/Book-Coach-3.pdf)

### Radice

- [README (EN)](README.md) — [Italiano](README_IT.md) — [Portugues](README_PT.md)

### Infrastruttura

- [CI/CD Pipeline & Configurazione GitHub](.github/README.md) — [Italiano](.github/README_IT.md) — [Portugues](.github/README_PT.md)
- [Sistema di Migrazione Database — Alembic](alembic/README.md) — [Italiano](alembic/README_IT.md) — [Portugues](alembic/README_PT.md)
- [Indice Documentazione](docs/README.md) — [Italiano](docs/README_IT.md) — [Portugues](docs/README_PT.md)
- [Gli Studi — Bibliotheca](docs/Studies/README.md) — [Italiano](docs/Studies/README_IT.md) — [Portugues](docs/Studies/README_PT.md)
- [Script di Build e Setup](scripts/README.md) — [Italiano](scripts/README_IT.md) — [Portugues](scripts/README_PT.md)
- [Test di Verifica e Forensi](tests/README.md) — [Italiano](tests/README_IT.md) — [Portugues](tests/README_PT.md)
- [Strumenti di Progetto](tools/README.md) — [Italiano](tools/README_IT.md) — [Portugues](tools/README_PT.md)
- [Packaging — Build & Distribuzione](packaging/README.md) — [Italiano](packaging/README_IT.md) — [Portugues](packaging/README_PT.md)

### Pacchetto Principale

- [Programma_CS2_RENAN](Programma_CS2_RENAN/README.md) — [Italiano](Programma_CS2_RENAN/README_IT.md) — [Portugues](Programma_CS2_RENAN/README_PT.md)
- [Sistemi Core](Programma_CS2_RENAN/core/README.md) — [Italiano](Programma_CS2_RENAN/core/README_IT.md) — [Portugues](Programma_CS2_RENAN/core/README_PT.md)
- [Dati — Dati Applicativi & Configurazione](Programma_CS2_RENAN/data/README.md) — [Italiano](Programma_CS2_RENAN/data/README_IT.md) — [Portugues](Programma_CS2_RENAN/data/README_PT.md)
- [Assets — Risorse Statiche](Programma_CS2_RENAN/assets/README.md) — [Italiano](Programma_CS2_RENAN/assets/README_IT.md) — [Portugues](Programma_CS2_RENAN/assets/README_PT.md)
- [Modelli — Storage Checkpoint Reti Neurali](Programma_CS2_RENAN/models/README.md) — [Italiano](Programma_CS2_RENAN/models/README_IT.md) — [Portugues](Programma_CS2_RENAN/models/README_PT.md)
- [Strumenti di Validazione e Diagnostica](Programma_CS2_RENAN/tools/README.md) — [Italiano](Programma_CS2_RENAN/tools/README_IT.md) — [Portugues](Programma_CS2_RENAN/tools/README_PT.md)
- [Suite di Test](Programma_CS2_RENAN/tests/README.md) — [Italiano](Programma_CS2_RENAN/tests/README_IT.md) — [Portugues](Programma_CS2_RENAN/tests/README_PT.md)

### Apps — Interfaccia Utente

- [Apps — Livello Interfaccia Utente](Programma_CS2_RENAN/apps/README.md) — [Italiano](Programma_CS2_RENAN/apps/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/README_PT.md)
- [Applicazione Desktop Qt (Primaria)](Programma_CS2_RENAN/apps/qt_app/README.md) — [Italiano](Programma_CS2_RENAN/apps/qt_app/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/qt_app/README_PT.md)
- [Applicazione Desktop (Legacy Kivy/KivyMD)](Programma_CS2_RENAN/apps/desktop_app/README.md) — [Italiano](Programma_CS2_RENAN/apps/desktop_app/README_IT.md) — [Portugues](Programma_CS2_RENAN/apps/desktop_app/README_PT.md)

### Backend

- [Backend](Programma_CS2_RENAN/backend/README.md) — [Italiano](Programma_CS2_RENAN/backend/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/README_PT.md)
- [Analisi — Teoria dei Giochi & Motori Statistici](Programma_CS2_RENAN/backend/analysis/README.md) — [Italiano](Programma_CS2_RENAN/backend/analysis/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/analysis/README_PT.md)
- [Coaching — Pipeline Multi-Modalita](Programma_CS2_RENAN/backend/coaching/README.md) — [Italiano](Programma_CS2_RENAN/backend/coaching/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/coaching/README_PT.md)
- [Controllo — Orchestrazione & Gestione Daemon](Programma_CS2_RENAN/backend/control/README.md) — [Italiano](Programma_CS2_RENAN/backend/control/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/control/README_PT.md)
- [Sorgenti Dati — Integrazioni Esterne](Programma_CS2_RENAN/backend/data_sources/README.md) — [Italiano](Programma_CS2_RENAN/backend/data_sources/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/data_sources/README_PT.md)
- [Scraping Dati Professionali HLTV](Programma_CS2_RENAN/backend/data_sources/hltv/README.md) — [Italiano](Programma_CS2_RENAN/backend/data_sources/hltv/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/data_sources/hltv/README_PT.md)
- [Ingestione Backend — File Watching & Governance Risorse](Programma_CS2_RENAN/backend/ingestion/README.md) — [Italiano](Programma_CS2_RENAN/backend/ingestion/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/ingestion/README_PT.md)
- [Conoscenza — RAG & Experience Bank](Programma_CS2_RENAN/backend/knowledge/README.md) — [Italiano](Programma_CS2_RENAN/backend/knowledge/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/knowledge/README_PT.md)
- [Knowledge Base — Sistema di Aiuto In-App](Programma_CS2_RENAN/backend/knowledge_base/README.md) — [Italiano](Programma_CS2_RENAN/backend/knowledge_base/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/knowledge_base/README_PT.md)
- [Onboarding — Gestione Flusso Nuovo Utente](Programma_CS2_RENAN/backend/onboarding/README.md) — [Italiano](Programma_CS2_RENAN/backend/onboarding/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/onboarding/README_PT.md)
- [Progresso — Tracking Prestazioni Longitudinale](Programma_CS2_RENAN/backend/progress/README.md) — [Italiano](Programma_CS2_RENAN/backend/progress/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/progress/README_PT.md)
- [Reporting — Motore Analytics Dashboard](Programma_CS2_RENAN/backend/reporting/README.md) — [Italiano](Programma_CS2_RENAN/backend/reporting/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/reporting/README_PT.md)
- [Livello Servizi Applicativi](Programma_CS2_RENAN/backend/services/README.md) — [Italiano](Programma_CS2_RENAN/backend/services/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/services/README_PT.md)
- [Livello Storage Database](Programma_CS2_RENAN/backend/storage/README.md) — [Italiano](Programma_CS2_RENAN/backend/storage/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/storage/README_PT.md)

### Reti Neurali

- [Sottosistema Reti Neurali](Programma_CS2_RENAN/backend/nn/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/README_PT.md)
- [RAP Coach — Architettura Ricorrente a 7 Livelli](Programma_CS2_RENAN/backend/nn/rap_coach/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/rap_coach/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/rap_coach/README_PT.md)
- [Advanced — Modulo Sperimentale](Programma_CS2_RENAN/backend/nn/advanced/README.md) — [Italiano](Programma_CS2_RENAN/backend/nn/advanced/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/nn/advanced/README_PT.md)

### Elaborazione & Feature Engineering

- [Elaborazione — Pipeline Dati & Feature Engineering](Programma_CS2_RENAN/backend/processing/README.md) — [Italiano](Programma_CS2_RENAN/backend/processing/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/processing/README_PT.md)
- [Baseline Professionali & Rilevamento Meta Drift](Programma_CS2_RENAN/backend/processing/baselines/README.md) — [Italiano](Programma_CS2_RENAN/backend/processing/baselines/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/processing/baselines/README_PT.md)
- [Feature Engineering — Estrazione Unificata delle Feature](Programma_CS2_RENAN/backend/processing/feature_engineering/README.md) — [Italiano](Programma_CS2_RENAN/backend/processing/feature_engineering/README_IT.md) — [Portugues](Programma_CS2_RENAN/backend/processing/feature_engineering/README_PT.md)

### Pipeline di Ingestione

- [Pipeline di Ingestione Demo](Programma_CS2_RENAN/ingestion/README.md) — [Italiano](Programma_CS2_RENAN/ingestion/README_IT.md) — [Portugues](Programma_CS2_RENAN/ingestion/README_PT.md)
- [Implementazioni Pipeline di Ingestione](Programma_CS2_RENAN/ingestion/pipelines/README.md) — [Italiano](Programma_CS2_RENAN/ingestion/pipelines/README_IT.md) — [Portugues](Programma_CS2_RENAN/ingestion/pipelines/README_PT.md)
- [Registro File Demo & Gestione Ciclo di Vita](Programma_CS2_RENAN/ingestion/registry/README.md) — [Italiano](Programma_CS2_RENAN/ingestion/registry/README_IT.md) — [Portugues](Programma_CS2_RENAN/ingestion/registry/README_PT.md)

### Osservabilita & Reporting

- [Osservabilita & Protezione Runtime](Programma_CS2_RENAN/observability/README.md) — [Italiano](Programma_CS2_RENAN/observability/README_IT.md) — [Portugues](Programma_CS2_RENAN/observability/README_PT.md)
- [Visualizzazione & Generazione Report](Programma_CS2_RENAN/reporting/README.md) — [Italiano](Programma_CS2_RENAN/reporting/README_IT.md) — [Portugues](Programma_CS2_RENAN/reporting/README_PT.md)

---

## Licenza

Questo progetto e a doppia licenza. Copyright (c) 2025-2026 Renan Augusto Macena.

- **Licenza Proprietaria** -- Tutti i Diritti Riservati (default). Visualizzazione per scopi educativi consentita.
- **Apache License 2.0** -- Open source permissiva con protezione brevetti.

Consulta [LICENSE](LICENSE) per i termini completi.

---

## Autore

**Renan Augusto Macena**

Costruito con passione da un giocatore di Counter-Strike con oltre 10.000 ore dal 2004, combinando una profonda conoscenza del gioco con l'ingegneria IA per creare il sistema di coaching definitivo.

> *"Ho sempre desiderato una guida professionale -- come quella dei veri giocatori professionisti -- per capire come appare realmente quando qualcuno si allena nel modo giusto e gioca nel modo giusto."*
