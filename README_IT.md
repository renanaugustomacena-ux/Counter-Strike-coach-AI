# Macena CS2 Analyzer

[![CI Pipeline](https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI/actions/workflows/build.yml/badge.svg)](https://github.com/renanaugustomacena-ux/Counter-Strike-coach-AI/actions/workflows/build.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Proprietary%20%7C%20Apache--2.0-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-313%20validator%20%7C%201794%20pytest-brightgreen.svg)]()

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
- [Ottimizzazione delle Prestazioni](#ottimizzazione-delle-prestazioni)
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

- **Applicazione Desktop Qt** -- Frontend PySide6/Qt (primario) con pattern MVVM. Kivy/KivyMD legacy mantenuto solo come riferimento
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

### 5. Configura l'Ambiente

```bash
cp .env.example .env
# Modifica .env con la tua API key Steam e le preferenze (vedi commenti nel file)
```

### 6. Verifica Installazione

```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import PySide6; print(f'PySide6: {PySide6.__version__}')"
python -c "from Programma_CS2_RENAN.backend.nn.config import get_device; print(f'Device: {get_device()}')"
```

### 7. Opzionale: Baseline Coaching Professionistico

Per costruire baseline di coaching da dati di partite professionali, sono necessari due componenti aggiuntivi:

**Docker + FlareSolverr** (per scraping automatizzato delle statistiche HLTV dei professionisti):

```bash
# Installa Docker Desktop: https://docs.docker.com/desktop/
# Poi avvia FlareSolverr:
docker compose up -d
```

FlareSolverr bypassa la protezione Cloudflare su hltv.org. Senza di esso, il daemon Hunter non puo effettuare lo scraping delle statistiche dei giocatori professionisti. Puoi comunque usare il coach con i tuoi file demo -- le baseline professionistiche migliorano la qualita del coaching ma non sono obbligatorie.

**Dipendenze RAP Coach** (architettura sperimentale opzionale):

```bash
pip install -r requirements-rap.txt
```

Necessario solo se abiliti `USE_RAP_MODEL=True` nelle impostazioni. Il modello JEPA predefinito funziona senza queste.

### 8. Avvia

```bash
# Applicazione desktop (GUI Qt -- consigliata)
./launch.sh

# Oppure manualmente:
python -m Programma_CS2_RENAN.apps.qt_app.app

# Console interattiva (TUI live con pannelli in tempo reale)
python console.py

# CLI one-shot (build, test, audit, hospital, sanitize)
python goliath.py
```

> Per la guida completa con configurazione API, walkthrough delle funzionalita e troubleshooting, consulta la [Guida Utente](docs/guides/USER_GUIDE_IT.md).

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

### Architetture di Reti Neurali

**RAP Coach (Architettura a 7 Livelli)**

Il RAP (Reasoning, Attribution, Prediction) Coach e il modello neurale principale. I suoi 7 livelli elaborano dati di gameplay attraverso una pipeline cognitiva:

| Livello | Funzione | Dettagli |
|---------|----------|----------|
| 1. Percezione | Encoding visivo + spaziale | Layer Conv per frame visivo (64d), stato mappa (32d), diff movimento (32d) -> 128d |
| 2. Memoria | Tracking ricorrente delle credenze | LSTM + rete Hopfield per memoria associativa. Input: 153d (128 percezione + 25 metadata) -> 256d stato nascosto |
| 3. Strategia | Ottimizzazione decisionale | Mixture-of-Experts con superposizione per decisioni context-dependent. 10 pesi azione |
| 4. Pedagogia | Stima del valore | Stima V-function con integrazione vettore abilita |
| 5. Posizione | Piazzamento ottimale | Predice (dx, dy, dz) delta alla posizione ottimale (scala: 500 unita mondo) |
| 6. Attribuzione | Diagnosi causale | Attribuzione a 5 dimensioni che spiega i driver decisionali |
| 7. Output | Aggregazione | advice_probs, belief_state, value_estimate, gate_weights, optimal_pos, attribution |

**JEPA (Joint-Embedding Predictive Architecture)**

Pre-training auto-supervisionato con:
- Context encoder + predictor -> predice l'embedding target
- Target encoder aggiornato tramite EMA (momentum 0.996)
- Loss contrastiva InfoNCE con negativi in-batch
- Dimensione latente: 128

**VL-JEPA (Estensione Vision-Language)**

Estende JEPA con allineamento di 16 concetti tattici:
- Concetti: posizionamento (3), utility (2), economia (2), engagement (4), decisione (2), psicologia (3)
- Concept alignment loss + diversity regularization
- Etichettatura basata su outcome da RoundStats (uccisioni, morti, equipaggiamento, risultato round)

**Altri Modelli:**
- **AdvancedCoachNN** -- LSTM (hidden=128) + Mixture-of-Experts (4 esperti, top-k=2) per predizione pesi di coaching
- **NeuralRoleHead** -- Classificatore MLP a 5 ruoli con KL-divergence gating e consensus voting
- **RoleClassifier** -- Rilevamento leggero del ruolo dalle feature dei tick

### Vettore di Feature a 25 Dimensioni

Ogni tick di gioco e rappresentato come un vettore canonico a 25 dimensioni (`METADATA_DIM=25`):

| Indice | Feature | Range | Descrizione |
|--------|---------|-------|-------------|
| 0 | health | [0, 1] | HP / 100 |
| 1 | armor | [0, 1] | Armatura / 100 |
| 2 | has_helmet | {0, 1} | Elmetto equipaggiato |
| 3 | has_defuser | {0, 1} | Kit disinnesco |
| 4 | equipment_value | [0, 1] | Costo equipaggiamento normalizzato |
| 5 | is_crouching | {0, 1} | Posizione accovacciata |
| 6 | is_scoped | {0, 1} | Arma con mirino attiva |
| 7 | is_blinded | {0, 1} | Effetto flash |
| 8 | enemies_visible | [0, 1] | Conteggio nemici visibili (normalizzato) |
| 9-11 | pos_x, pos_y, pos_z | [-1, 1] | Coordinate mondo (normalizzate per mappa) |
| 12-13 | view_yaw_sin, view_yaw_cos | [-1, 1] | Angolo di visuale (encoding ciclico) |
| 14 | view_pitch | [-1, 1] | Angolo visuale verticale |
| 15 | z_penalty | [0, 1] | Distinzione verticale (mappe multi-livello) |
| 16 | kast_estimate | [0, 1] | Rapporto Kill/Assist/Survive/Trade |
| 17 | map_id | [0, 1] | Hash deterministico della mappa (basato su MD5) |
| 18 | round_phase | {0, .33, .66, 1} | Pistol / Eco / Force / Full buy |
| 19 | weapon_class | [0, 1] | Knife=0, Pistol=.2, SMG=.4, Rifle=.6, Sniper=.8, Heavy=1 |
| 20 | time_in_round | [0, 1] | Secondi / 115 |
| 21 | bomb_planted | {0, 1} | Flag bomba piazzata |
| 22 | teammates_alive | [0, 1] | Conteggio / 4 |
| 23 | enemies_alive | [0, 1] | Conteggio / 5 |
| 24 | team_economy | [0, 1] | Media soldi del team / 16000 |

### Gating di Maturita a 3 Stadi

I modelli progrediscono attraverso gate di maturita basati sul conteggio delle demo ingerite:

| Stadio | Conteggio Demo | Confidenza | Comportamento |
|--------|---------------|------------|---------------|
| **CALIBRATING** | 0-49 | 0.5x | Coaching base, consigli marcati come provvisori |
| **LEARNING** | 50-199 | 0.8x | Intermedio, affidabilita crescente |
| **MATURE** | 200+ | 1.0x | Piena confidenza, tutti i sottosistemi contribuiscono |

Un parallelo **Conviction Index** (0.0-1.0) traccia 5 segnali neurali: entropia delle credenze, specializzazione gate, focus concettuale, accuratezza valore e stabilita ruolo. Stati: DOUBT (<0.30) > LEARNING (0.30-0.60) > CONVICTION (>0.60 stabile per 10+ epoche) > MATURE (>0.75 stabile per 20+ epoche). Un calo brusco >20% attiva lo stato CRISIS.

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

Le mappe multi-livello (Nuke, Vertigo) usano cutoff sull'asse Z per separare livello superiore e inferiore per un rendering 2D accurato. La feature z_penalty (indice 15) nel vettore di feature cattura la distinzione verticale per queste mappe.

---

## Stack Tecnologico

### Dipendenze Principali

| Categoria | Pacchetto | Versione | Scopo |
|-----------|-----------|----------|-------|
| **ML Framework** | PyTorch | Latest | Training e inferenza reti neurali |
| **Reti Ricorrenti** | ncps | Latest | Reti Liquid Time-Constant (LTC) |
| **Memoria Associativa** | hopfield-layers | Latest | Layer rete Hopfield per la memoria |
| **Parsing Demo** | demoparser2 | 0.40.2 | Parsing a livello di tick dei file demo CS2 |
| **Framework UI (primario)** | PySide6 | 6.8+ | GUI desktop cross-platform basata su Qt |
| **Framework UI (legacy)** | Kivy + KivyMD | 2.3.0 / 1.2.0 | Riferimento legacy |
| **ORM Database** | SQLAlchemy + SQLModel | Latest | Modelli e query database |
| **Migrazioni** | Alembic | Latest | Migrazioni schema database |
| **Web Scraping** | Playwright | 1.57.0 | Browser headless per HLTV |
| **Client HTTP** | HTTPX | 0.28.1 | Richieste HTTP asincrone |
| **Data Science** | NumPy, Pandas, SciPy, scikit-learn | Latest | Calcolo numerico e analisi |
| **Visualizzazione** | Matplotlib | Latest | Generazione grafici |
| **Grafi** | NetworkX | Latest | Analisi basata su grafi |
| **Sicurezza** | cryptography | 46.0.3 | Cifratura credenziali |
| **TUI** | Rich | 14.2.0 | UI terminale per modalita console |
| **API** | FastAPI + Uvicorn | 0.40.0 | Server API interno |
| **Validazione** | Pydantic | Latest | Validazione dati e impostazioni |
| **Testing** | pytest + pytest-cov + pytest-mock | 9.0.2 | Framework di test e copertura |
| **Packaging** | PyInstaller | 6.17.0 | Distribuzione binaria |
| **Templating** | Jinja2 | 3.1.6 | Rendering template per report |
| **Parsing HTML** | BeautifulSoup4 + lxml | 4.12.3 | Estrazione contenuti web |
| **Configurazione** | PyYAML | 6.0.3 | File di configurazione YAML |
| **Immagini** | Pillow | 12.0.0 | Elaborazione immagini |
| **Keyring** | keyring | 25.6.0 | Archiviazione sicura credenziali |

---

## Struttura del Progetto

```
Counter-Strike-coach-AI/
|
+-- Programma_CS2_RENAN/                Pacchetto applicazione principale
|   +-- apps/
|   |   +-- qt_app/                     GUI PySide6/Qt (primaria, MVVM + Segnali)
|   |   |   +-- app.py                  Punto di ingresso Qt
|   |   |   +-- main_window.py          QMainWindow con navigazione laterale
|   |   |   +-- core/                   Singleton AppState, ThemeEngine, pattern Worker
|   |   |   +-- screens/               13 schermate (home, visualizzatore tattico, cronologia
|   |   |   |                           partite, dettaglio partita, prestazioni, coach,
|   |   |   |                           impostazioni, wizard, aiuto, profilo, config steam/faceit)
|   |   |   +-- viewmodels/            ViewModel signal-driven (QObject + Signal/Slot)
|   |   |   +-- widgets/               Grafici (radar, momentum, economia, sparkline),
|   |   |                               tattici (widget mappa, sidebar giocatore, timeline)
|   |   +-- desktop_app/               GUI Kivy/KivyMD (fallback legacy)
|   |       +-- main.py                 Punto di ingresso Kivy
|   |       +-- layout.kv               Definizione layout KivyMD
|   |       +-- screens/                Classi schermata Kivy
|   |       +-- widgets/                Componenti widget Kivy
|   |       +-- viewmodels/             ViewModel stile Kivy
|   |       +-- assets/                 Temi (CS2, CSGO, CS1.6), font, immagini radar mappa
|   |       +-- i18n/                   Traduzioni (EN, IT, PT)
|   |
|   +-- backend/
|   |   +-- analysis/                   Teoria dei giochi e analisi statistica
|   |   |   +-- belief_model.py         Tracking bayesiano stato mentale avversario
|   |   |   +-- game_tree.py            Alberi decisionali Expectiminimax
|   |   |   +-- momentum.py             Momentum round e tendenze di confidenza
|   |   |   +-- role_classifier.py      Rilevamento ruolo giocatore (entry, support, lurk, AWP, anchor)
|   |   |   +-- blind_spots.py          Consapevolezza mappa e debolezze posizionali
|   |   |   +-- deception_index.py      Metrica di imprevedibilita posizionale
|   |   |   +-- entropy_analysis.py     Quantificazione casualita decisionale
|   |   |   +-- engagement_range.py     Analisi distribuzione distanza arma
|   |   |   +-- utility_economy.py      Efficienza spesa granate
|   |   |   +-- win_probability.py      Calcolo probabilita vittoria in tempo reale
|   |   |
|   |   +-- data_sources/              Integrazione dati esterni
|   |   |   +-- demo_parser.py          Wrapper demoparser2 (estrazione a livello di tick)
|   |   |   +-- hltv_scraper.py         Scraping metadati professionali HLTV
|   |   |   +-- steam_api.py            Profilo Steam e dati partita
|   |   |   +-- faceit_api.py           Integrazione dati partita FaceIT
|   |   |
|   |   +-- nn/                         Sottosistemi reti neurali
|   |   |   +-- config.py               Config globale NN (dimensioni, lr, batch size, device)
|   |   |   +-- jepa_model.py           Encoder JEPA + VL-JEPA + ConceptLabeler
|   |   |   +-- jepa_trainer.py         Loop training JEPA con monitoraggio drift
|   |   |   +-- training_orchestrator.py Orchestrazione training multi-modello
|   |   |   +-- rap_coach/              Modello RAP Coach
|   |   |   |   +-- model.py            Architettura a 7 livelli
|   |   |   |   +-- trainer.py          Loop training specifico RAP
|   |   |   |   +-- memory.py           Modulo memoria LTC + Hopfield
|   |   |   +-- layers/                 Componenti neurali condivisi
|   |   |       +-- superposition.py    Layer superposizione context-dependent
|   |   |       +-- moe.py             Gating Mixture-of-Experts
|   |   |
|   |   +-- processing/                Feature engineering ed elaborazione dati
|   |   |   +-- feature_engineering/
|   |   |   |   +-- vectorizer.py       Estrazione feature canonica a 25 dim (METADATA_DIM=25)
|   |   |   |   +-- tensor_factory.py   Costruzione tensori vista/mappa per RAP Coach
|   |   |   +-- heatmap/               Generazione heatmap spaziali
|   |   |   +-- validation/            Rilevamento drift, controlli qualita dati
|   |   |
|   |   +-- knowledge/                 Gestione conoscenza
|   |   |   +-- rag_knowledge.py        Recupero RAG per pattern di coaching
|   |   |   +-- experience_bank.py      Archiviazione e recupero esperienze COPER
|   |   |
|   |   +-- services/                  Servizi applicativi
|   |   |   +-- coaching_service.py     Pipeline coaching a 4 livelli (COPER/Ibrido/RAG/Base)
|   |   |   +-- ollama_service.py       Integrazione LLM locale per rifinitura linguaggio
|   |   |
|   |   +-- storage/                   Layer database
|   |       +-- database.py            Gestione connessioni SQLite WAL-mode
|   |       +-- db_models.py           Definizioni ORM SQLAlchemy/SQLModel
|   |       +-- backup_manager.py      Backup database automatizzato
|   |       +-- match_data_manager.py  Gestione database SQLite per-match
|   |
|   +-- core/                          Servizi core dell'applicazione
|   |   +-- session_engine.py           Engine a 4 daemon (Scanner, Digester, Teacher, Pulse)
|   |   +-- map_manager.py             Caricamento mappe, calibrazione coordinate, Z-cutoff
|   |   +-- asset_manager.py           Risoluzione temi e asset
|   |   +-- spatial_data.py            Sistemi di coordinate spaziali
|   |
|   +-- ingestion/                     Pipeline di ingestione demo
|   |   +-- steam_locator.py           Auto-scoperta percorsi demo CS2 da Steam
|   |   +-- integrity_check.py         Validazione file demo
|   |
|   +-- observability/                 Monitoraggio e sicurezza
|   |   +-- rasp.py                    Runtime Application Self-Protection
|   |   +-- telemetry.py              Metriche TensorBoard e tracking convinzione
|   |   +-- logger_setup.py           Logging strutturato (namespace cs2analyzer.*)
|   |
|   +-- reporting/                     Generazione output
|   |   +-- visualizer.py             Rendering grafici e diagrammi
|   |   +-- pdf_generator.py          Generazione report PDF
|   |
|   +-- tests/                         Suite di test (1,794+ test)
|   +-- data/                          Dati statici (seed knowledge base, dataset esterni)
|
+-- docs/                              Documentazione
|   +-- USER_GUIDE.md                  Guida utente completa (EN)
|   +-- USER_GUIDE_IT.md               Guida utente (Italiano)
|   +-- USER_GUIDE_PT.md               Guida utente (Portoghese)
|   +-- Book-Coach-1A.md               Vision book -- Core neurale
|   +-- Book-Coach-1B.md               Vision book -- RAP Coach & sorgenti dati
|   +-- Book-Coach-2.md                Vision book -- Servizi & infrastruttura
|   +-- Book-Coach-3.md                Vision book -- Logica programma & UI
|   +-- cybersecurity.md               Analisi sicurezza
|   +-- Studies/                        17 paper di ricerca
|
+-- tools/                             Strumenti di validazione e diagnostica
|   +-- headless_validator.py          Gate di regressione primario (313 check, 24 fasi)
|   +-- Feature_Audit.py              Audit feature engineering
|   +-- portability_test.py           Controlli compatibilita cross-platform
|   +-- dead_code_detector.py         Scansione codice inutilizzato
|   +-- dev_health.py                 Salute ambiente di sviluppo
|   +-- verify_all_safe.py            Verifica di sicurezza
|   +-- db_health_diagnostic.py       Diagnostica salute database
|   +-- Sanitize_Project.py           Preparazione per distribuzione
|   +-- build_pipeline.py             Orchestrazione pipeline di build
|
+-- tests/                            Test di integrazione e verifica
+-- scripts/                          Script di setup e deploy
+-- alembic/                          Script di migrazione database
+-- .github/workflows/build.yml       Pipeline CI/CD cross-platform
+-- console.py                        Punto di ingresso TUI interattivo
+-- goliath.py                        Orchestratore CLI di produzione
+-- run_full_training_cycle.py        Runner standalone ciclo di training
```

---

## Punti di Ingresso

L'applicazione fornisce diversi punti di ingresso per differenti casi d'uso:

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

UI terminale con pannelli in tempo reale per sviluppo e controllo runtime. Comandi organizzati per sottosistema:

| Gruppo Comandi | Esempi |
|----------------|--------|
| **ML Pipeline** | `ml start`, `ml stop`, `ml pause`, `ml resume`, `ml throttle 0.5`, `ml status` |
| **Ingestione** | `ingest start`, `ingest stop`, `ingest mode continuous 5`, `ingest scan` |
| **Build & Test** | `build run`, `build verify`, `test all`, `test headless`, `test hospital` |
| **Sistema** | `sys status`, `sys audit`, `sys baseline`, `sys db`, `sys vacuum`, `sys resources` |
| **Config** | `set steam /percorso`, `set faceit KEY`, `set config chiave valore` |
| **Servizi** | `svc restart coaching` |

### CLI di Produzione (Goliath)

```bash
python goliath.py <comando>
```

Orchestratore master per build di produzione, release e diagnostica:

| Comando | Descrizione | Flag |
|---------|-------------|------|
| `build` | Pipeline di build industriale | `--test-only` |
| `sanitize` | Pulisci il progetto per distribuzione | `--force` |
| `integrity` | Genera manifesto di integrita | |
| `audit` | Verifica dati e feature | `--demo <percorso>` |
| `db` | Gestione schema database | `--force` |
| `doctor` | Diagnostica clinica | `--department <nome>` |
| `baseline` | Stato decadimento temporale baseline | |

### Runner Ciclo di Training

```bash
python run_full_training_cycle.py
```

Script standalone che esegue un ciclo di training completo fuori dal daemon engine. Utile per training manuale o debug.

### Ingestione Batch

```bash
python batch_ingest.py [--workers N] [--limit N]
```

Ingestione batch parallela di file demo professionali usando multiprocessing. Riprendibile -- salta le demo gia ingerite. Usa tutti i core CPU di default.

### Server API Interno

```bash
python -m uvicorn Programma_CS2_RENAN.backend.services.api:app --host 127.0.0.1 --port 8000
```

API interna basata su FastAPI per accesso programmatico a coaching, stato ingestione e stato modello. Non esposta esternamente di default. Vedi i README di `backend/services/` per la documentazione degli endpoint.

---

## Validazione e Qualita

Il progetto mantiene una gerarchia di validazione multi-livello:

| Strumento | Ambito | Comando | Check |
|-----------|--------|---------|-------|
| Headless Validator | Gate di regressione primario | `python tools/headless_validator.py` | 313 check, 24 fasi |
| Suite Pytest | Test logici e integrazione | `python -m pytest Programma_CS2_RENAN/tests/ -x -q` | 1,794+ test |
| Feature Audit | Integrita feature engineering | `python tools/Feature_Audit.py` | Dimensioni vettore, range |
| Portability Test | Compatibilita cross-platform | `python tools/portability_test.py` | Check importazione, percorsi |
| Dev Health | Ambiente di sviluppo | `python tools/dev_health.py` | Dipendenze, config |
| Dead Code Detector | Scansione codice inutilizzato | `python tools/dead_code_detector.py` | Analisi import |
| Safety Verifier | Check di sicurezza | `python tools/verify_all_safe.py` | RASP, scansione segreti |
| DB Health | Diagnostica database | `python tools/db_health_diagnostic.py` | Schema, modalita WAL, integrita |
| Goliath Hospital | Diagnostica completa | `python goliath.py doctor` | Salute completa del sistema |

**Gate CI/CD:** L'headless validator deve restituire exit code 0 prima che qualsiasi commit sia considerato valido. Gli hook pre-commit garantiscono gli standard di qualita del codice. La pipeline CI gira su Ubuntu e Windows con GitHub Actions SHA-pinned.

---

## Supporto Multi-Lingua

L'applicazione supporta 3 lingue su tutta l'interfaccia:

| Lingua | UI | Guida Utente | README |
|--------|----|-------------|--------|
| English | Completa | [docs/guides/USER_GUIDE.md](docs/guides/USER_GUIDE.md) | [README.md](README.md) |
| Italiano | Completa | [docs/guides/USER_GUIDE_IT.md](docs/guides/USER_GUIDE_IT.md) | [README_IT.md](README_IT.md) |
| Portugues | Completa | [docs/guides/USER_GUIDE_PT.md](docs/guides/USER_GUIDE_PT.md) | [README_PT.md](README_PT.md) |

La lingua puo essere cambiata a runtime dalle Impostazioni senza riavviare l'applicazione.

---

## Funzionalita di Sicurezza

### Runtime Application Self-Protection (RASP)

- **Manifesto di Integrita** -- Hash SHA-256 di tutti i file sorgente critici, verificati all'avvio
- **Rilevamento Manomissione** -- Avvisa quando i file sorgente sono stati modificati dall'ultima generazione del manifesto
- **Validazione Binary Frozen** -- Verifica struttura bundle PyInstaller e ambiente di esecuzione
- **Rilevamento Posizione Sospetta** -- Avvisa quando si esegue da percorsi del filesystem inattesi

### Sicurezza Credenziali

- **Integrazione OS Keyring** -- API key (Steam, FaceIT) memorizzate nel Windows Credential Manager / keyring Linux, mai in testo semplice
- **Nessun Segreto Hardcoded** -- Il file impostazioni mostra il placeholder `"PROTECTED_BY_WINDOWS_VAULT"`
- **Operazioni Crittografiche** -- Usa `cryptography==46.0.3` (libreria verificata, nessun crypto custom)

### Sicurezza Database

- **SQLite WAL Mode** -- Write-Ahead Logging per accesso concorrente sicuro su tutti i database
- **Validazione Input** -- Modelli Pydantic al confine di ingestione, query SQL parametrizzate
- **Sistema di Backup** -- Backup database automatizzati con verifica di integrita

### Logging Strutturato

- Tutto il logging attraverso il namespace `get_logger("cs2analyzer.<modulo>")`
- Nessun PII nell'output dei log
- Formato strutturato per integrazione di osservabilita

---

## Ottimizzazione delle Prestazioni

| Parametro | Default | Effetto |
|-----------|---------|---------|
| Device GPU | Auto-rilevato tramite `get_device()` | CUDA quando disponibile, altrimenti CPU. Override con `CUDA_VISIBLE_DEVICES` |
| Batch size training | 32 (`backend/nn/config.py`) | Aumentare per GPU con >6 GB VRAM. Diminuire se OOM |
| Worker ingestione | Conteggio CPU (`batch_ingest.py`) | `--workers N` per limitare il parsing demo parallelo |
| Momentum EMA | 0.996 base, schedulato con coseno fino a 1.0 (`backend/nn/jepa_train.py:353`) | Tracking del target encoder JEPA. Valori piu bassi tracciano piu velocemente ma con piu rumore. EMA del RAP Coach ha default 0.999 (`backend/nn/ema.py:39`) |
| TensorBoard | `runs/coach_training` | `tensorboard --logdir runs/coach_training` per metriche live |
| SQLite WAL mode | Abilitato di default | Lettura/scrittura concorrente. Nessun tuning necessario per utente singolo |
| Soglia rilevamento drift | Basata su Z-score (`backend/processing/validation/`) | Attiva automaticamente flag di retraining quando le distribuzioni delle feature cambiano |

Per utenti GPU: PyTorch CUDA 12.1 e la configurazione testata. La precisione mista non e attualmente abilitata -- tutto il training gira a FP32.

> Per indicazioni specifiche sull'hardware, vedi [Studio 15 -- Hardware and Scaling](docs/Studies/).

---

## Maturita del Sistema

Non tutti i sottosistemi sono ugualmente maturi. La modalita di coaching predefinita (COPER) e production-ready e **non** dipende dai modelli neurali. Il coaching neurale migliora man mano che piu demo vengono elaborate.

| Sottosistema | Stato | Punteggio | Note |
|-------------|-------|-----------|------|
| Coaching COPER | OPERATIVO | 8/10 | Experience bank + RAG + riferimenti pro. Funziona immediatamente. |
| Motore Analitico | OPERATIVO | 6/10 | Rating HLTV 2.0, breakdown round, timeline economia. |
| JEPA Base (InfoNCE) | OPERATIVO | 7/10 | Pre-training auto-supervisionato, target encoder EMA. |
| Neural Role Head | OPERATIVO | 7/10 | MLP a 5 ruoli con KL-divergence, consensus gating. |
| RAP Coach (7 livelli) | LIMITATO | 3/10 | Architettura completa (LTC+Hopfield), necessita 200+ demo. |
| VL-JEPA (16 concetti) | LIMITATO | 2/10 | Allineamento concettuale implementato, qualita etichette in miglioramento. |

**Livelli di maturita:**
- **CALIBRATING** (0-49 demo): confidenza 0.5x, coaching fortemente integrato da COPER
- **LEARNING** (50-199 demo): confidenza 0.8x, feature neurali gradualmente attivate
- **MATURE** (200+ demo): piena confidenza, tutti i sottosistemi contribuiscono

---

## Documentazione

### Guide Utente

| Documento | Descrizione |
|-----------|-------------|
| [Guida Utente (IT)](docs/guides/USER_GUIDE_IT.md) | Installazione completa, setup wizard, API key, tutte le schermate, acquisizione demo, troubleshooting |
| [User Guide (EN)](docs/guides/USER_GUIDE.md) | Guida utente completa in inglese |
| [Guia do Usuario (PT)](docs/guides/USER_GUIDE_PT.md) | Guida utente completa in portoghese |

### Documentazione Architetturale

| Documento | Descrizione |
|-----------|-------------|
| [Book-Coach-1A](docs/books/Book-Coach-1A.md) | Core neurale: JEPA, VL-JEPA, AdvancedCoachNN, MaturityObservatory |
| [Book-Coach-1B](docs/books/Book-Coach-1B.md) | RAP Coach (7 componenti), sorgenti dati (demo, HLTV, Steam, FACEIT) |
| [Book-Coach-2](docs/books/Book-Coach-2.md) | Servizi, motori analisi, knowledge/COPER, database, training |
| [Book-Coach-3](docs/books/Book-Coach-3.md) | Logica programma completa, UI Qt, ingestione, tools, test, build |
| [Analisi Cybersecurity](docs/archive/cybersecurity.md) | Postura di sicurezza e modello di minaccia |

### Paper di Ricerca (17 Studi)

La cartella `docs/Studies/` contiene 17 paper di ricerca approfonditi sulle fondamenta teoriche e le decisioni ingegneristiche dietro ogni sottosistema:

| # | Studio | Argomento |
|---|--------|-----------|
| 01 | Epistemic Foundations | Framework di rappresentazione e ragionamento della conoscenza |
| 02 | Ingestion Algebra | Modello matematico dell'elaborazione dati demo |
| 03 | Recurrent Networks | Teoria reti LTC e Hopfield |
| 04 | Reinforcement Learning | Fondamenti RL per decisioni di coaching |
| 05 | Perceptive Architecture | Design pipeline di elaborazione visiva |
| 06 | Cognitive Architecture | Modellazione credenze e sistemi decisionali |
| 07 | JEPA Architecture | Teoria Joint-Embedding Predictive Architecture |
| 08 | Forensic Engineering | Metodologia di debugging e diagnostica |
| 09 | Feature Engineering | Design e validazione del vettore a 25 dimensioni |
| 10 | Database and Storage | SQLite WAL, DB per-match, strategia di migrazione |
| 11 | Tri-Daemon Engine | Architettura multi-daemon e ciclo di vita |
| 12 | Evaluation and Falsification | Metodologia di test e validazione |
| 13 | Explainability and Coaching | Attribuzione causale e design UI coaching |
| 14 | Ethics, Privacy and Integrity | Protezione dati ed etica IA |
| 15 | Hardware and Scaling | Ottimizzazione per varie configurazioni hardware |
| 16 | Maps and GNN | Analisi spaziale e approcci con grafi neurali |
| 17 | Sociotechnical Impact | Direzioni future e implicazioni sociali |

---

## Alimentare il Coach

Il coach IA viene fornito senza conoscenza pre-addestrata. Apprende esclusivamente da file demo professionali CS2. La qualita del coaching e direttamente proporzionale alla qualita e quantita delle demo ingerite.

### Soglie di Conteggio Demo

| Demo Pro | Livello | Confidenza | Cosa Succede |
|----------|---------|------------|--------------|
| 0-9 | Non pronto | 0% | Minimo 10 demo pro richieste per il primo ciclo di training |
| 10-49 | CALIBRATING | 50% | Coaching base attivo, consigli marcati come provvisori |
| 50-199 | LEARNING | 80% | Affidabilita crescente, sempre piu personalizzato |
| 200+ | MATURE | 100% | Piena confidenza, massima accuratezza |

### Dove Trovare Demo Pro

1. Vai su [hltv.org](https://www.hltv.org) > Results
2. Filtra per eventi top-tier: Major Championship, IEM Katowice/Cologne, BLAST Premier, ESL Pro League, PGL Major
3. Seleziona partite di team nella top-20 (Navi, FaZe, Vitality, G2, Spirit, Heroic)
4. Preferisci serie BO3/BO5 per massimizzare i dati di training per download
5. Diversifica su tutte le mappe Active Duty -- una distribuzione sbilanciata crea un coach sbilanciato
6. Scarica il link "GOTV Demo" o "Watch Demo"

### Pianificazione dello Storage

I file `.dem` sono tipicamente 300-850 MB ciascuno. Pianifica lo storage di conseguenza:

| Demo | File Grezzi | DB Match | Totale |
|------|-------------|----------|--------|
| 10 | ~5 GB | ~1 GB | ~6 GB |
| 50 | ~30 GB | ~5 GB | ~35 GB |
| 100 | ~60 GB | ~10 GB | ~70 GB |
| 200 | ~120 GB | ~20 GB | ~140 GB |

Tre posizioni di storage separate:

| Posizione | Contenuto | Raccomandazione |
|-----------|-----------|-----------------|
| Database Core | Statistiche giocatore, stato coaching, metadati HLTV | Resta nella cartella del programma |
| Brain Data Root | Pesi modelli IA, log, knowledge base | SSD consigliato |
| Cartella Demo Pro | File .dem grezzi + database SQLite per-match | Piu grande, HDD accettabile |

### Monitoraggio TensorBoard

```bash
tensorboard --logdir runs/coach_training
```

Apri [http://localhost:6006](http://localhost:6006) per monitorare conviction index, transizioni stato di maturita, specializzazione gate e curve di loss del training.

> Per la checklist completa passo-passo del ciclo di coaching e la guida dettagliata allo storage, consulta la [Guida Utente](docs/guides/USER_GUIDE_IT.md).

---

## Risoluzione dei Problemi

### Problemi Comuni

| Problema | Soluzione |
|----------|----------|
| `ModuleNotFoundError: No module named 'PySide6'` | Installa le dipendenze Qt: `pip install PySide6` |
| `ModuleNotFoundError: No module named 'kivy'` | Per la UI legacy: `pip install Kivy==2.3.0 KivyMD==1.2.0` (piu kivy-deps su Windows) |
| `CUDA not available` | Verifica il driver con `nvidia-smi`, reinstalla PyTorch con `--index-url https://download.pytorch.org/whl/cu121` |
| `sentence-transformers not installed` | Avviso non bloccante. Installa con `pip install sentence-transformers` per embedding migliorati, o ignora (fallback TF-IDF funziona) |
| `database is locked` | Chiudi tutti i processi Python e riavvia |
| `RuntimeError: mat1 and mat2 shapes cannot be multiplied` | Checkpoint del modello da un METADATA_DIM diverso. Elimina i checkpoint obsoleti in `Programma_CS2_RENAN/models/` e riaddestra |
| Headless validator fallisce | Esegui `python tools/headless_validator.py` per la fase specifica che fallisce. Correggi prima di committare |
| Il parsing demo restituisce 0 round | Il file potrebbe essere corrotto o sotto `MIN_DEMO_SIZE` (10 MB). Prova con una demo diversa |
| TensorBoard non mostra dati | Verifica che `runs/coach_training/` esista e contenga file di eventi. Il training deve completare almeno un'epoca |
| Ollama non risponde | Assicurati che Ollama sia in esecuzione (`ollama serve`) e che il modello configurato sia scaricato (`ollama pull llama3.1:8b`) |
| FlareSolverr connessione rifiutata | Avvia Docker: `docker compose up -d`. Verifica che la porta 8191 sia accessibile |
| Reset allo stato di fabbrica | Elimina `Programma_CS2_RENAN/user_settings.json` e riavvia |

### Posizioni Database

| Database | Percorso | Contenuto |
|----------|----------|-----------|
| Principale | `Programma_CS2_RENAN/backend/storage/database.db` | Statistiche giocatore, stato coaching, dati training |
| HLTV | `Programma_CS2_RENAN/backend/storage/hltv_metadata.db` | Metadati giocatori professionisti |
| Knowledge | `Programma_CS2_RENAN/data/knowledge_base.db` | Knowledge base RAG |
| Per-match | `{PRO_DEMO_PATH}/match_data/match_*.db` | Dati partita a livello di tick |

> Per il troubleshooting completo, consulta la [Guida Utente](docs/guides/USER_GUIDE_IT.md).

---

## Indice Completo della Documentazione

Tutti i README e documenti tecnici del progetto. Clicca su qualsiasi link per aprire il documento.

### Serie Book Coach

Quattro libri di visione tri-lingui + un libro compagno di analogie canoniche. Ogni libro-coach è disponibile in Markdown (sorgente modificabile) e PDF.

**Italiano (sorgente canonica):**
- [Ultimate CS2 Coach — Sistema AI](docs/books/Book-Coach-1.pdf) — PDF ombrello
- [Parte 1A — Il Cervello](docs/books/Book-Coach-1A.md) ([PDF](docs/books/Book-Coach-1A.pdf))
- [Parte 1B — I Sensi e lo Specialista](docs/books/Book-Coach-1B.md) ([PDF](docs/books/Book-Coach-1B.pdf))
- [Parte 2 — Servizi, Analisi e Database](docs/books/Book-Coach-2.md) ([PDF](docs/books/Book-Coach-2.pdf))
- [Parte 3 — Programma, UI, Tools e Build](docs/books/Book-Coach-3.md) ([PDF](docs/books/Book-Coach-3.pdf))
- [Il Libro delle Analogie](docs/books/analogy-book.md) — 35 metafore pedagogiche canoniche

**Traduzioni inglesi:**
- [Part 1A — The Brain](docs/books/Book-Coach-1A-en.md)
- [Part 1B — The Senses and the Specialist](docs/books/Book-Coach-1B-en.md)
- [Part 2 — Services, Analysis, and Database](docs/books/Book-Coach-2-en.md)
- [Part 3 — Program, UI, Tools, and Build](docs/books/Book-Coach-3-en.md)
- [The Book of Analogies](docs/books/analogy-book-en.md)

**Traduzioni brasiliane:**
- [Parte 1A — O Cerebro](docs/books/Book-Coach-1A-pt.md)
- [Parte 1B — Os Sentidos e o Especialista](docs/books/Book-Coach-1B-pt.md)
- [Parte 2 — Servicos, Analise e Banco de Dados](docs/books/Book-Coach-2-pt.md)
- [Parte 3 — Programa, UI, Ferramentas e Build](docs/books/Book-Coach-3-pt.md)
- [O Livro das Analogias](docs/books/analogy-book-pt.md)

**Riferimento traduzioni:** [Glossario delle Traduzioni (IT → EN → PT-BR)](docs/books/TRANSLATION_GLOSSARY.md) — terminologia canonica usata in ogni edizione tradotta.

### Radice

- [README (EN)](README.md) — [Italiano](README_IT.md) — [Portugues](README_PT.md)

### Ingegneria

- [Engineering Handoff](docs/ENGINEERING_HANDOFF.md) — Riferimento master: audit completo codebase, 75 work item, piano di esecuzione, roadmap prodotto

### Infrastruttura

- [CI/CD Pipeline & Configurazione GitHub](.github/README.md) — [Italiano](.github/README_IT.md) — [Portugues](.github/README_PT.md)
- [Sistema di Migrazione Database — Alembic](alembic/README.md) — [Italiano](alembic/README_IT.md) — [Portugues](alembic/README_PT.md)
- [Indice Documentazione](docs/README.md) — [Italiano](docs/README_IT.md) — [Portugues](docs/README_PT.md)
- [Gli Studi — Bibliotheca](docs/Studies/README.md) — [Italiano](docs/Studies/README_IT.md) — [Portugues](docs/Studies/README_PT.md)
- [Script di Build e Setup](scripts/README.md) — [Italiano](scripts/README_IT.md) — [Portugues](scripts/README_PT.md)
- [Test di Verifica e Forensi a Livello Root](tests/README.md) — [Italiano](tests/README_IT.md) — [Portugues](tests/README_PT.md)
- [Strumenti di Progetto a Livello Root](tools/README.md) — [Italiano](tools/README_IT.md) — [Portugues](tools/README_PT.md)
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
