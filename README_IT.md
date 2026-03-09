# Macena CS2 Analyzer

**Coach Tattico basato su IA per Counter-Strike 2**

> **[Portugues](README_PT.md)**

---

## Cos'è?

Macena CS2 Analyzer è un'applicazione desktop che funge da coach IA personale per Counter-Strike 2. Analizza file demo professionali e dell'utente, addestra molteplici modelli di reti neurali e fornisce coaching tattico personalizzato confrontando il tuo gameplay con gli standard professionali.

Il sistema impara dalle migliori partite professionali mai giocate e adatta il suo coaching al tuo stile di gioco individuale — che tu sia un AWPer, entry fragger, support o qualsiasi altro ruolo. La pipeline di coaching fonde previsioni di machine learning con conoscenze tattiche recuperate, analisi basata su teoria dei giochi e modellazione bayesiana delle credenze per produrre consigli azionabili e context-aware.

A differenza degli strumenti di coaching statici con suggerimenti pre-scritti, questo sistema costruisce la sua intelligenza da dati reali di gameplay professionistico. Al primo avvio le reti neurali hanno pesi casuali e zero conoscenza tattica. Ogni demo che gli fornisci rende il coach più intelligente, più sfumato e più personalizzato.

---

## Indice

- [Funzionalità Principali](#funzionalità-principali)
- [Requisiti di Sistema](#requisiti-di-sistema)
- [Avvio Rapido](#avvio-rapido)
- [Panoramica Architetturale](#panoramica-architetturale)
- [Mappe Supportate](#mappe-supportate)
- [Stack Tecnologico](#stack-tecnologico)
- [Struttura del Progetto](#struttura-del-progetto)
- [Punti di Ingresso](#punti-di-ingresso)
- [Validazione e Qualità](#validazione-e-qualità)
- [Supporto Multi-Lingua](#supporto-multi-lingua)
- [Funzionalità di Sicurezza](#funzionalità-di-sicurezza)
- [Maturità del Sistema](#maturità-del-sistema)
- [Documentazione](#documentazione)
- [Alimentare il Coach](#alimentare-il-coach)
- [Risoluzione dei Problemi](#risoluzione-dei-problemi)
- [Licenza](#licenza)
- [Autore](#autore)

---

## Funzionalità Principali

### Pipeline di Coaching IA

- **Catena di Fallback a 4 Livelli** — COPER > Ibrido > RAG > Base, garantendo che il sistema produca sempre consigli utili indipendentemente dalla maturità del modello
- **COPER Experience Bank** — Memorizza e recupera esperienze di coaching passate pesate per recenza, efficacia e similarità di contesto
- **Base di Conoscenza RAG** — Retrieval-Augmented Generation con pattern di riferimento professionali e conoscenza tattica
- **Integrazione Ollama** — LLM locale opzionale per la rifinitura in linguaggio naturale degli insight di coaching
- **Attribuzione Causale** — Ogni raccomandazione di coaching include una spiegazione "perché" tracciabile a specifiche decisioni di gameplay

### Sottosistemi di Reti Neurali

- **RAP Coach** — Architettura a 7 livelli che combina percezione, memoria (LTC-Hopfield), strategia (Mixture-of-Experts con superposizione), pedagogia (value function), predizione posizione, attribuzione causale e aggregazione output
- **Encoder JEPA** — Joint-Embedding Predictive Architecture per pre-training auto-supervisionato con loss contrastiva InfoNCE e target encoder EMA
- **VL-JEPA** — Estensione Vision-Language con allineamento di 16 concetti tattici (posizionamento, utility, economia, engagement, decisione, psicologia)
- **AdvancedCoachNN** — Architettura LSTM + Mixture-of-Experts per la predizione dei pesi di coaching
- **Neural Role Head** — Classificatore MLP a 5 ruoli (entry, support, lurk, AWP, anchor) con KL-divergence e consensus gating
- **Modelli Bayesiani delle Credenze** — Tracking dello stato mentale dell'avversario con calibrazione adattiva dai dati della partita

### Analisi Demo

- **Parsing a Livello di Tick** — Ogni tick dei file `.dem` è analizzato tramite demoparser2, preservando tutto lo stato di gioco (nessuna decimazione di tick)
- **Rating HLTV 2.0** — Calcolato per partita usando la formula ufficiale HLTV 2.0 (uccisioni, morti, ADR, KAST%, sopravvivenza, assist flash)
- **Breakdown Round per Round** — Timeline dell'economia, analisi degli engagement, uso delle utility, tracking del momentum
- **Decadimento Temporale della Baseline** — Traccia l'evoluzione delle abilità del giocatore nel tempo con pesi a decadimento esponenziale

### Analisi basata su Teoria dei Giochi

- **Alberi Expectiminimax** — Valutazione decisionale game-theoretic per scenari strategici
- **Probabilità di Morte Bayesiana** — Stima la probabilità di sopravvivenza basata su posizione, equipaggiamento e stato nemico
- **Indice di Inganno** — Quantifica l'imprevedibilità posizionale rispetto alle baseline professionali
- **Analisi del Raggio di Engagement** — Mappa la selezione delle armi contro le distribuzioni di distanza di engagement
- **Probabilità di Vittoria** — Calcolo della probabilità di vittoria in tempo reale
- **Tracking del Momentum** — Traiettoria di confidenza e prestazione round per round

### Applicazione Desktop

- **Interfaccia Kivy + KivyMD** — App desktop cross-platform con architettura MVVM
- **Visualizzatore Tattico 2D** — Replay demo in tempo reale con posizioni giocatori, eventi uccisione, indicatori bomba e predizioni AI ghost
- **Cronologia Partite** — Lista scorrevole delle partite recenti con rating codificati per colore
- **Dashboard Prestazioni** — Tendenze del rating, statistiche per mappa, analisi punti di forza/debolezza, breakdown utility
- **Chat con il Coach** — Conversazione AI interattiva con pulsanti quick-action e domande in testo libero
- **Profilo Utente** — Integrazione Steam con importazione automatica delle partite
- **3 Temi Visivi** — CS2 (arancione), CS:GO (blu-grigio), CS 1.6 (verde) con wallpaper a rotazione

### Training e Automazione

- **4-Daemon Session Engine** — Scanner (scoperta file), Digester (elaborazione demo), Teacher (training modelli), Pulse (monitoraggio salute)
- **Gating di Maturità a 3 Stadi** — CALIBRATING (0-49 demo, 0.5x confidenza) > LEARNING (50-199, 0.8x) > MATURE (200+, piena)
- **Conviction Index** — Composito a 5 segnali che traccia entropia delle credenze, specializzazione gate, focus concettuale, accuratezza valore e stabilità ruolo
- **Auto-Retraining** — Il training si attiva automaticamente al 10% di crescita del conteggio demo
- **Rilevamento Drift** — Monitoraggio drift delle feature basato su Z-score con flag automatico di retraining
- **Coach Introspection Observatory** — Integrazione TensorBoard con macchina a stati di maturità, proiettore embedding e tracking della convinzione

---

## Requisiti di Sistema

| Componente | Minimo | Consigliato |
|------------|--------|-------------|
| OS | Windows 10 / Ubuntu 22.04 | Windows 10/11 |
| Python | 3.10 | 3.10 o 3.12 |
| RAM | 8 GB | 16 GB |
| GPU | Nessuna (modalità CPU) | NVIDIA GTX 1650+ (CUDA 12.1) |
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

pip install -r Programma_CS2_RENAN/requirements.txt
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

pip install -r Programma_CS2_RENAN/requirements.txt
pip install Kivy==2.3.0 KivyMD==1.2.0
python -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database()"
pip install playwright && python -m playwright install chromium
```

### 5. Verifica Installazione

```bash
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import kivy; print(f'Kivy: {kivy.__version__}')"
python -c "from Programma_CS2_RENAN.backend.nn.config import get_device; print(f'Device: {get_device()}')"
```

### 6. Avvia

```bash
# Applicazione desktop (GUI Kivy)
python Programma_CS2_RENAN/main.py

# Console interattiva (TUI live con pannelli in tempo reale)
python console.py

# CLI one-shot (build, test, audit, hospital, sanitize)
python goliath.py
```

> Per la guida completa con configurazione API, walkthrough delle funzionalità e troubleshooting, consulta la [Guida Utente](docs/USER_GUIDE_IT.md).

---

## Panoramica Architetturale

### Pipeline GUARDA > IMPARA > PENSA > PARLA

Il sistema è organizzato come una pipeline a 4 stadi che trasforma file demo grezzi in coaching personalizzato:

```
GUARDA (Ingestione)    IMPARA (Training)      PENSA (Inferenza)       PARLA (Dialogo)
  Daemon Scanner         Daemon Teacher         Pipeline COPER          Template + Ollama
  Parsing demo           Maturità a 3 stadi     Conoscenza RAG          Attribuzione causale
  Estrazione feature     Training multi-modello  Teoria dei giochi       Confronti con i pro
  Archiviazione tick     Rilevamento drift       Modellazione credenze   Scoring di gravità
```

**GUARDA** — Il daemon Scanner monitora continuamente le cartelle demo configurate per nuovi file `.dem`. Quando trovati, il daemon Digester analizza ogni tick usando demoparser2, estrae il vettore canonico di feature a 25 dimensioni, calcola i rating HLTV 2.0 e archivia tutto in database SQLite per-match.

**IMPARA** — Il daemon Teacher addestra automaticamente i modelli neurali quando si accumulano dati sufficienti. Il training procede attraverso 3 stadi di maturità (CALIBRATING > LEARNING > MATURE). Multiple architetture si addestrano in parallelo: JEPA per l'apprendimento auto-supervisionato delle rappresentazioni, RAP Coach per la modellazione delle decisioni tattiche, NeuralRoleHead per la classificazione del ruolo dei giocatori.

**PENSA** — A tempo di inferenza, la pipeline COPER combina previsioni neurali con esperienze di coaching recuperate, conoscenza RAG e analisi di teoria dei giochi. Una catena di fallback a 4 livelli (COPER > Ibrido > RAG > Base) garantisce che i consigli siano sempre disponibili indipendentemente dalla maturità del modello.

**PARLA** — L'output finale del coaching è formattato con livelli di gravità, attribuzione causale ("perché questo consiglio") e opzionalmente rifinito attraverso un LLM locale Ollama per la qualità del linguaggio naturale.

### 4-Daemon Session Engine

| Daemon | Ruolo | Trigger |
|--------|-------|---------|
| **Scanner (Hunter)** | Scopre nuovi file `.dem` nelle cartelle configurate | Scansione periodica o file watcher |
| **Digester** | Analizza le demo, estrae feature, calcola rating | Nuovo file rilevato dallo Scanner |
| **Teacher** | Addestra i modelli neurali sui dati accumulati | Soglia di crescita 10% nel conteggio demo |
| **Pulse** | Monitoraggio salute, rilevamento drift, stato sistema | Continuo in background |

### Pipeline di Coaching COPER

COPER (Coaching via Organized Pattern Experience Retrieval) è il motore di coaching principale. Opera una catena di fallback a 4 livelli:

1. **Modalità COPER** — Pipeline completa: recupero Experience Bank + conoscenza RAG + previsioni modello neurale + confronti professionali. Richiede modelli addestrati.
2. **Modalità Ibrida** — Combina previsioni neurali con consigli basati su template quando alcuni modelli sono ancora in calibrazione.
3. **Modalità RAG** — Puro recupero: cerca pattern di coaching rilevanti nella knowledge base senza inferenza neurale. Funziona con le sole demo ingerite.
4. **Modalità Base** — Consigli basati su template dall'analisi statistica (deviazioni media/std dalle baseline professionali). Funziona immediatamente.

### Architetture di Reti Neurali

**RAP Coach (Architettura a 7 Livelli)**

Il RAP (Reasoning, Attribution, Prediction) Coach è il modello neurale principale. I suoi 7 livelli processano i dati di gameplay attraverso una pipeline cognitiva:

| Livello | Funzione | Dettagli |
|---------|----------|----------|
| 1. Percezione | Codifica visiva + spaziale | Layer conv per view frame (64d), stato mappa (32d), diff movimento (32d) → 128d |
| 2. Memoria | Tracking ricorrente delle credenze | LSTM + rete Hopfield per memoria associativa. Input: 153d (128 percezione + 25 metadati) → 256d stato nascosto |
| 3. Strategia | Ottimizzazione decisionale | Mixture-of-Experts con superposizione per decisioni context-dependent. 10 pesi azione |
| 4. Pedagogia | Stima del valore | Valutazione V-function con integrazione skill vector |
| 5. Posizione | Piazzamento ottimale | Predice (dx, dy, dz) delta alla posizione ottimale (scala: 500 unità mondo) |
| 6. Attribuzione | Diagnosi causale | Attribuzione a 5 dimensioni che spiega i driver delle decisioni |
| 7. Output | Aggregazione | advice_probs, belief_state, value_estimate, gate_weights, optimal_pos, attribution |

**JEPA (Joint-Embedding Predictive Architecture)**

Pre-training auto-supervisionato con:
- Context encoder + predictor → predice embedding target
- Target encoder aggiornato via EMA (momentum 0.996)
- Loss contrastiva InfoNCE con negativi in-batch
- Dimensione latente: 128

**VL-JEPA (Estensione Vision-Language)**

Estende JEPA con allineamento di 16 concetti tattici:
- Concetti: posizionamento (3), utility (2), economia (2), engagement (4), decisione (2), psicologia (3)
- Loss di allineamento concettuale + regolarizzazione diversità
- Etichettatura basata su outcome dai RoundStats (uccisioni, morti, equipaggiamento, risultato round)

**Altri Modelli:**
- **AdvancedCoachNN** — LSTM (hidden=128) + Mixture-of-Experts (4 esperti, top-k=2) per la predizione dei pesi di coaching
- **NeuralRoleHead** — Classificatore MLP a 5 ruoli con KL-divergence gating e consensus voting
- **RoleClassifier** — Rilevamento leggero dei ruoli dalle feature dei tick

### Vettore di Feature a 25 Dimensioni

Ogni tick di gioco è rappresentato come un vettore canonico a 25 dimensioni (`METADATA_DIM=25`):

| Indice | Feature | Range | Descrizione |
|--------|---------|-------|-------------|
| 0 | health | [0, 1] | HP / 100 |
| 1 | armor | [0, 1] | Armatura / 100 |
| 2 | has_helmet | {0, 1} | Elmetto equipaggiato |
| 3 | has_defuser | {0, 1} | Kit disinnesco |
| 4 | equipment_value | [0, 1] | Costo equipaggiamento normalizzato |
| 5 | is_crouching | {0, 1} | Posizione accovacciata |
| 6 | is_scoped | {0, 1} | Arma con scope attiva |
| 7 | is_blinded | {0, 1} | Effetto flash |
| 8 | enemies_visible | [0, 1] | Conteggio nemici visibili (normalizzato) |
| 9-11 | pos_x, pos_y, pos_z | [-1, 1] | Coordinate mondo (normalizzate per mappa) |
| 12-13 | view_yaw_sin, view_yaw_cos | [-1, 1] | Angolo di visione (codifica ciclica) |
| 14 | view_pitch | [-1, 1] | Angolo di visione verticale |
| 15 | z_penalty | [0, 1] | Distintività verticale (mappe multi-livello) |
| 16 | kast_estimate | [0, 1] | Rapporto Kill/Assist/Survive/Trade |
| 17 | map_id | [0, 1] | Hash deterministico della mappa (basato su MD5) |
| 18 | round_phase | {0, .33, .66, 1} | Pistol / Eco / Force / Full buy |
| 19 | weapon_class | [0, 1] | Coltello=0, Pistola=.2, SMG=.4, Fucile=.6, Sniper=.8, Pesante=1 |
| 20 | time_in_round | [0, 1] | Secondi / 115 |
| 21 | bomb_planted | {0, 1} | Flag bomba piazzata |
| 22 | teammates_alive | [0, 1] | Conteggio / 4 |
| 23 | enemies_alive | [0, 1] | Conteggio / 5 |
| 24 | team_economy | [0, 1] | Money medio del team / 16000 |

### Gating di Maturità a 3 Stadi

I modelli progrediscono attraverso gate di maturità basati sul conteggio di demo ingerite:

| Stadio | Conteggio Demo | Confidenza | Comportamento |
|--------|---------------|------------|---------------|
| **CALIBRATING** | 0-49 | 0.5x | Coaching base, consigli marcati come provvisori |
| **LEARNING** | 50-199 | 0.8x | Intermedio, affidabilità crescente |
| **MATURE** | 200+ | 1.0x | Piena confidenza, tutti i sottosistemi contribuiscono |

Un **Conviction Index** parallelo (0.0-1.0) traccia 5 segnali neurali: entropia delle credenze, specializzazione gate, focus concettuale, accuratezza valore e stabilità ruolo. Stati: DOUBT (<0.30) > LEARNING (0.30-0.60) > CONVICTION (>0.60 stabile per 10+ epoche) > MATURE (>0.75 stabile per 20+ epoche). Un calo brusco >20% attiva lo stato CRISIS.

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

Le mappe multi-livello (Nuke, Vertigo) usano cutoff sull'asse Z per separare livello superiore e inferiore per un rendering 2D accurato. La feature z_penalty (indice 15) nel vettore di feature cattura la distintività verticale per queste mappe.

---

## Stack Tecnologico

### Dipendenze Principali

| Categoria | Pacchetto | Versione | Scopo |
|-----------|-----------|----------|-------|
| **ML Framework** | PyTorch | Latest | Training e inferenza reti neurali |
| **Reti Ricorrenti** | ncps | Latest | Reti Liquid Time-Constant (LTC) |
| **Memoria Associativa** | hopfield-layers | Latest | Layer rete Hopfield per la memoria |
| **Parsing Demo** | demoparser2 | 0.40.2 | Parsing a livello di tick dei file demo CS2 |
| **Utility CS2** | awpy | 1.2.3 | Utility di analisi CS2 |
| **Framework UI** | Kivy | 2.3.0 | GUI desktop cross-platform |
| **Componenti UI** | KivyMD | 1.2.0 | Widget Material Design |
| **ORM Database** | SQLAlchemy + SQLModel | Latest | Modelli e query database |
| **Migrazioni** | Alembic | Latest | Migrazioni schema database |
| **Web Scraping** | Playwright | 1.57.0 | Browser headless per HLTV |
| **Client HTTP** | HTTPX | 0.28.1 | Richieste HTTP async |
| **Data Science** | NumPy, Pandas, SciPy, scikit-learn | Latest | Calcolo numerico e analisi |
| **Visualizzazione** | Matplotlib | Latest | Generazione grafici |
| **Geometria** | Shapely | 2.1.2 | Analisi spaziale |
| **Grafi** | NetworkX | Latest | Analisi basata su grafi |
| **Sicurezza** | cryptography | 46.0.3 | Cifratura credenziali |
| **TUI** | Rich | 14.2.0 | UI terminale per modalità console |
| **API** | FastAPI + Uvicorn | 0.40.0 | Server API interno |
| **Validazione** | Pydantic | Latest | Validazione dati e impostazioni |
| **Testing** | pytest + pytest-cov + pytest-mock | 9.0.2 | Framework di test e copertura |
| **Packaging** | PyInstaller | 6.17.0 | Distribuzione binaria |
| **Templating** | Jinja2 | 3.1.6 | Rendering template per report |
| **Parsing HTML** | BeautifulSoup4 + lxml | 4.12.3 | Estrazione contenuti web |
| **Config** | PyYAML | 6.0.3 | File di configurazione YAML |
| **Immagini** | Pillow | 12.0.0 | Elaborazione immagini |
| **Keyring** | keyring | 25.6.0 | Archiviazione credenziali sicura |

### Dipendenze Solo Windows

| Pacchetto | Versione | Scopo |
|-----------|----------|-------|
| kivy-deps.glew | 0.3.1 | OpenGL extension wrangler |
| kivy-deps.sdl2 | 0.7.0 | Libreria multimediale SDL2 |
| kivy-deps.angle | 0.4.0 | Backend ANGLE OpenGL ES |

---

## Struttura del Progetto

```
Counter-Strike-coach-AI/
|
+-- Programma_CS2_RENAN/                Pacchetto applicazione principale
|   +-- apps/desktop_app/               GUI Kivy (pattern MVVM)
|   |   +-- main.py                     Entry point dell'app
|   |   +-- layout.kv                   Definizione layout Kivy
|   |   +-- viewmodels/                 Layer ViewModel (playback, ghost, chronovisor)
|   |   +-- screens/                    Schermate UI (tactical viewer, match history, performance,
|   |   |                               match detail, wizard, help, coach, settings, profile)
|   |   +-- widgets/                    Componenti UI riutilizzabili (tactical map, player sidebar,
|   |   |                               timeline scrubber, ghost pixel renderer)
|   |   +-- assets/                     Temi (CS2, CSGO, CS1.6), font, immagini radar mappe
|   |   +-- i18n/                       Traduzioni (EN, IT, PT)
|   |
|   +-- backend/
|   |   +-- analysis/                   Teoria dei giochi e analisi statistica
|   |   |   +-- belief_model.py         Tracking bayesiano dello stato mentale dell'avversario
|   |   |   +-- game_tree.py            Alberi decisionali expectiminimax
|   |   |   +-- momentum.py             Momentum dei round e tendenze di confidenza
|   |   |   +-- role_classifier.py      Rilevamento ruolo giocatore (entry, support, lurk, AWP, anchor)
|   |   |   +-- blind_spots.py          Consapevolezza della mappa e debolezze posizionali
|   |   |   +-- deception_index.py      Metrica di imprevedibilità posizionale
|   |   |   +-- entropy_analysis.py     Quantificazione casualità decisionale
|   |   |   +-- engagement_range.py     Analisi distribuzione arma-distanza
|   |   |   +-- utility_economy.py      Efficienza spesa granate
|   |   |   +-- win_probability.py      Calcolo probabilità di vittoria in tempo reale
|   |   |
|   |   +-- data_sources/              Integrazione dati esterni
|   |   |   +-- demo_parser.py          Wrapper demoparser2 (estrazione a livello di tick)
|   |   |   +-- hltv_api_service.py     Scraping metadati professionali HLTV
|   |   |   +-- steam_api_service.py    Profilo Steam e dati partite
|   |   |   +-- faceit_api_service.py   Integrazione dati partite FaceIT
|   |   |
|   |   +-- nn/                         Sottosistemi reti neurali
|   |   |   +-- config.py               Configurazione globale NN (dimensioni, lr, batch size, device)
|   |   |   +-- jepa_model.py           Encoder JEPA + VL-JEPA + ConceptLabeler
|   |   |   +-- jepa_trainer.py         Loop di training JEPA con monitoraggio drift
|   |   |   +-- training_orchestrator.py Orchestrazione training multi-modello
|   |   |   +-- rap_coach/              Modello RAP Coach
|   |   |   |   +-- model.py            Architettura a 7 livelli (Percezione-Memoria-Strategia-
|   |   |   |   |                       Pedagogia-Posizione-Attribuzione-Output)
|   |   |   |   +-- trainer.py          Loop di training specifico RAP
|   |   |   |   +-- memory.py           Modulo memoria LTC + Hopfield
|   |   |   +-- layers/                 Componenti neurali condivisi
|   |   |       +-- superposition.py    Layer di superposizione context-dependent
|   |   |       +-- moe.py             Gating Mixture-of-Experts
|   |   |
|   |   +-- processing/                Feature engineering ed elaborazione dati
|   |   |   +-- feature_engineering/
|   |   |   |   +-- vectorizer.py       Estrazione feature canoniche a 25-dim (METADATA_DIM=25)
|   |   |   |   +-- tensor_factory.py   Costruzione tensori view/map per RAP Coach
|   |   |   +-- heatmap/               Generazione heatmap spaziali
|   |   |   +-- validation/            Rilevamento drift, controlli qualità dati
|   |   |
|   |   +-- knowledge/                 Gestione della conoscenza
|   |   |   +-- rag_knowledge.py        Recupero RAG per pattern di coaching
|   |   |   +-- experience_bank.py      Archiviazione e recupero esperienze COPER
|   |   |   +-- round_utils.py          Utility di rilevamento fase round
|   |   |
|   |   +-- services/                  Servizi applicativi
|   |   |   +-- coaching_service.py     Pipeline di coaching a 4 livelli (COPER/Ibrido/RAG/Base)
|   |   |   +-- ollama_service.py       Integrazione LLM locale per rifinitura linguaggio
|   |   |
|   |   +-- storage/                   Layer database
|   |       +-- database.py            Gestione connessioni SQLite WAL-mode
|   |       +-- models.py              Definizioni ORM SQLAlchemy/SQLModel
|   |       +-- backup.py              Backup automatizzato database
|   |       +-- match_data_manager.py  Gestione database SQLite per-match
|   |
|   +-- core/                          Servizi core dell'applicazione
|   |   +-- session_engine.py           Engine a 4 daemon (Scanner, Digester, Teacher, Pulse)
|   |   +-- map_manager.py             Caricamento mappe, calibrazione coordinate, Z-cutoff
|   |   +-- asset_manager.py           Risoluzione temi e asset
|   |   +-- spatial_data.py            Sistemi di coordinate spaziali
|   |
|   +-- ingestion/                     Pipeline di ingestione demo
|   |   +-- steam_locator.py           Auto-scoperta percorsi demo CS2 di Steam
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
|   +-- tests/                         Suite di test (390+ test)
|   +-- data/                          Dati statici (seed knowledge base, dataset esterni)
|
+-- docs/                              Documentazione
|   +-- USER_GUIDE.md                  Guida utente completa (EN)
|   +-- USER_GUIDE_IT.md               Guida utente (Italiano)
|   +-- USER_GUIDE_PT.md               Guida utente (Portoghese)
|   +-- AI-cs2-coach-part1.md          Documentazione architettura (Parte 1)
|   +-- AI-cs2-coach-part2.md          Documentazione architettura (Parte 2)
|   +-- AI-cs2-coach-part3.md          Documentazione architettura (Parte 3)
|   +-- cybersecurity.md               Analisi di sicurezza
|   +-- Studies/                        17 paper di ricerca su:
|       +-- Studio_01                   Fondamenti Epistemici
|       +-- Studio_02                   Algebra dell'Ingestione
|       +-- Studio_03                   Reti Ricorrenti
|       +-- Studio_04                   Apprendimento per Rinforzo
|       +-- Studio_05                   Architettura Percettiva
|       +-- Studio_06                   Architettura Cognitiva
|       +-- Studio_07                   Architettura JEPA
|       +-- Studio_08                   Ingegneria Forense
|       +-- Studio_09                   Feature Engineering
|       +-- Studio_10                   Database e Storage
|       +-- Studio_11                   Motore Tri-Daemon
|       +-- Studio_12                   Valutazione e Falsificazione
|       +-- Studio_13                   Spiegabilità e Interfaccia di Coaching
|       +-- Studio_14                   Etica, Privacy e Integrità
|       +-- Studio_15                   Ottimizzazione Hardware e Scaling
|       +-- Studio_16                   Mappe e GNN
|       +-- Studio_17                   Impatto Sociotecnico e Futuro
|
+-- tools/                             Strumenti di validazione e diagnostica
|   +-- headless_validator.py          Gate di regressione primario (245+ check)
|   +-- Feature_Audit.py              Audit feature engineering
|   +-- portability_test.py           Check di portabilità cross-platform
|   +-- dead_code_detector.py         Rilevamento codice inutilizzato
|   +-- dev_health.py                 Salute ambiente di sviluppo
|   +-- verify_all_safe.py            Verifica di sicurezza
|   +-- db_health_diagnostic.py       Diagnostica salute database
|   +-- generate_manifest.py          Generatore manifesto di integrità
|   +-- Sanitize_Project.py           Preparazione per la distribuzione
|   +-- build_pipeline.py             Orchestrazione pipeline di build
|
+-- tests/                            Test di integrazione e verifica
|   +-- forensics/                    Utility di debug e forensiche
|
+-- scripts/                          Script di setup e deployment
|   +-- Setup_Macena_CS2.ps1          Setup automatizzato Windows
|
+-- alembic/                          Script di migrazione database
+-- console.py                        Entry point TUI interattiva
+-- goliath.py                        Orchestratore CLI di produzione
+-- run_full_training_cycle.py        Runner standalone ciclo di training
```

---

## Punti di Ingresso

L'applicazione fornisce 4 punti di ingresso per diversi casi d'uso:

### Applicazione Desktop (GUI)

```bash
python Programma_CS2_RENAN/main.py
```

Interfaccia grafica completa con visualizzatore tattico, cronologia partite, dashboard prestazioni, chat con il coach e impostazioni. Si apre a 1280x720. Al primo avvio, una procedura guidata in 3 passaggi configura la directory Brain Data Root.

### Console Interattiva (TUI)

```bash
python console.py
```

UI terminale con pannelli in tempo reale per sviluppo e controllo runtime. Comandi organizzati per sottosistema:

| Gruppo Comandi | Esempi |
|----------------|--------|
| **Pipeline ML** | `ml start`, `ml stop`, `ml pause`, `ml resume`, `ml throttle 0.5`, `ml status` |
| **Ingestione** | `ingest start`, `ingest stop`, `ingest mode continuous 5`, `ingest scan` |
| **Build & Test** | `build run`, `build verify`, `test all`, `test headless`, `test hospital` |
| **Sistema** | `sys status`, `sys audit`, `sys baseline`, `sys db`, `sys vacuum`, `sys resources` |
| **Config** | `set steam /path`, `set faceit KEY`, `set config key value` |
| **Servizi** | `svc restart coaching` |

### CLI di Produzione (Goliath)

```bash
python goliath.py <comando>
```

Orchestratore master per build di produzione, release e diagnostica:

| Comando | Descrizione | Flag |
|---------|-------------|------|
| `build` | Pipeline di build industriale | `--test-only` |
| `sanitize` | Pulisci il progetto per la distribuzione | `--force` |
| `integrity` | Genera manifesto di integrità | |
| `audit` | Verifica dati e feature | `--demo <path>` |
| `db` | Gestione schema database | `--force` |
| `doctor` | Diagnostica clinica | `--department <name>` |
| `baseline` | Stato decadimento baseline temporale | |

### Runner Ciclo di Training

```bash
python run_full_training_cycle.py
```

Script standalone che esegue un ciclo di training completo fuori dal daemon engine. Utile per training manuale o debugging.

---

## Validazione e Qualità

Il progetto mantiene una gerarchia di validazione multi-livello:

| Strumento | Ambito | Comando | Check |
|-----------|--------|---------|-------|
| Headless Validator | Gate di regressione primario | `python tools/headless_validator.py` | 245+ check |
| Suite Pytest | Test logici e integrazione | `python -m pytest Programma_CS2_RENAN/tests/ -x -q` | 390+ test |
| Feature Audit | Integrità feature engineering | `python tools/Feature_Audit.py` | Dimensioni vettore, range |
| Portability Test | Compatibilità cross-platform | `python tools/portability_test.py` | Check importazione, percorsi |
| Dev Health | Ambiente di sviluppo | `python tools/dev_health.py` | Dipendenze, config |
| Dead Code Detector | Scansione codice inutilizzato | `python tools/dead_code_detector.py` | Analisi importazioni |
| Safety Verifier | Check di sicurezza | `python tools/verify_all_safe.py` | RASP, scansione segreti |
| DB Health | Diagnostica database | `python tools/db_health_diagnostic.py` | Schema, modalità WAL, integrità |
| Goliath Hospital | Diagnostica completa | `python goliath.py doctor` | Salute completa del sistema |

**Gate CI/CD:** L'headless validator deve restituire exit code 0 prima che qualsiasi commit sia considerato valido. I pre-commit hook applicano standard di qualità del codice.

---

## Supporto Multi-Lingua

L'applicazione supporta 3 lingue in tutta l'interfaccia utente:

| Lingua | UI | Guida Utente | README |
|--------|----|-------------|--------|
| English | Completa | [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | [README.md](README.md) |
| Italiano | Completa | [docs/USER_GUIDE_IT.md](docs/USER_GUIDE_IT.md) | [README_IT.md](README_IT.md) |
| Portugues | Completa | [docs/USER_GUIDE_PT.md](docs/USER_GUIDE_PT.md) | [README_PT.md](README_PT.md) |

La lingua può essere cambiata a runtime dalle Impostazioni senza riavviare l'applicazione.

---

## Funzionalità di Sicurezza

### Runtime Application Self-Protection (RASP)

- **Manifesto di Integrità** — Hash SHA-256 di tutti i file sorgente critici, verificati all'avvio
- **Rilevamento Manomissione** — Avvisa quando i file sorgente sono stati modificati dall'ultima generazione del manifesto
- **Validazione Binari Congelati** — Verifica la struttura del bundle PyInstaller e l'ambiente di esecuzione
- **Rilevamento Posizione Sospetta** — Avvisa quando eseguito da percorsi del filesystem inattesi

### Sicurezza delle Credenziali

- **Integrazione OS Keyring** — API key (Steam, FaceIT) memorizzate nel Windows Credential Manager / keyring Linux, mai in testo semplice
- **Nessun Segreto Hardcoded** — Il file impostazioni mostra il placeholder `"PROTECTED_BY_WINDOWS_VAULT"`
- **Operazioni Crittografiche** — Usa `cryptography==46.0.3` (libreria verificata, nessuna crypto personalizzata)

### Sicurezza Database

- **SQLite WAL Mode** — Write-Ahead Logging per accesso concorrente sicuro su tutti i database
- **Validazione Input** — Modelli Pydantic al confine di ingestione, query SQL parametrizzate
- **Sistema di Backup** — Backup automatizzati del database con verifica di integrità

### Logging Strutturato

- Tutto il logging attraverso il namespace `get_logger("cs2analyzer.<modulo>")`
- Nessun PII nell'output dei log
- Formato strutturato per integrazione osservabilità

---

## Maturità del Sistema

Non tutti i sottosistemi sono ugualmente maturi. La modalità di coaching predefinita (COPER) è production-ready e **non** dipende dai modelli neurali. Il coaching neurale migliora man mano che più demo vengono elaborate.

| Sottosistema | Stato | Punteggio | Note |
|-------------|-------|-----------|------|
| Coaching COPER | OPERATIVO | 8/10 | Experience bank + RAG + riferimenti pro. Funziona immediatamente. |
| Motore Analitico | OPERATIVO | 6/10 | Rating HLTV 2.0, breakdown round, timeline economia. |
| JEPA Base (InfoNCE) | OPERATIVO | 7/10 | Pre-training auto-supervisionato, target encoder EMA. |
| Neural Role Head | OPERATIVO | 7/10 | MLP a 5 ruoli con KL-divergence, consensus gating. |
| RAP Coach (7 livelli) | LIMITATO | 3/10 | Architettura completa (LTC+Hopfield), necessita 200+ demo. |
| VL-JEPA (16 concetti) | LIMITATO | 2/10 | Allineamento concettuale implementato, qualità etichette in miglioramento. |

**Livelli di maturità:**
- **CALIBRATING** (0-49 demo): 0.5x confidenza, coaching fortemente integrato da COPER
- **LEARNING** (50-199 demo): 0.8x confidenza, feature neurali gradualmente attivate
- **MATURE** (200+ demo): Piena confidenza, tutti i sottosistemi contribuiscono

---

## Documentazione

### Guide Utente

| Documento | Descrizione |
|-----------|-------------|
| [Guida Utente (IT)](docs/USER_GUIDE_IT.md) | Guida completa installazione, setup wizard, API key, tutte le schermate, acquisizione demo, troubleshooting |
| [User Guide (EN)](docs/USER_GUIDE.md) | Complete installation, setup wizard, API keys, all screens, demo acquisition, troubleshooting |
| [Guia do Usuário (PT)](docs/USER_GUIDE_PT.md) | Guia completo do usuário em português |

### Documentazione Architetturale

| Documento | Descrizione |
|-----------|-------------|
| [Architettura Parte 1](docs/AI-cs2-coach-part1.md) | Design del sistema e architettura core |
| [Architettura Parte 2](docs/AI-cs2-coach-part2.md) | Sottosistemi reti neurali |
| [Architettura Parte 3](docs/AI-cs2-coach-part3.md) | Pipeline di coaching e gestione della conoscenza |
| [Analisi Cybersecurity](docs/cybersecurity.md) | Postura di sicurezza e modello delle minacce |

### Paper di Ricerca (17 Studi)

La cartella `docs/Studies/` contiene 17 paper di ricerca approfonditi che coprono le fondamenta teoriche e le decisioni ingegneristiche dietro ogni sottosistema:

| # | Studio | Argomento |
|---|--------|-----------|
| 01 | Fondamenti Epistemici | Framework di rappresentazione e ragionamento della conoscenza |
| 02 | Algebra dell'Ingestione | Modello matematico dell'elaborazione dati demo |
| 03 | Reti Ricorrenti | Teoria delle reti LTC e Hopfield |
| 04 | Apprendimento per Rinforzo | Fondamenti RL per decisioni di coaching |
| 05 | Architettura Percettiva | Design della pipeline di elaborazione visiva |
| 06 | Architettura Cognitiva | Modellazione delle credenze e sistemi decisionali |
| 07 | Architettura JEPA | Teoria Joint-Embedding Predictive Architecture |
| 08 | Ingegneria Forense | Metodologia di debug e diagnostica |
| 09 | Feature Engineering | Design e validazione del vettore a 25 dimensioni |
| 10 | Database e Storage | SQLite WAL, DB per-match, strategia di migrazione |
| 11 | Motore Tri-Daemon | Architettura multi-daemon e ciclo di vita |
| 12 | Valutazione e Falsificazione | Metodologia di testing e validazione |
| 13 | Spiegabilità e Coaching | Attribuzione causale e design dell'interfaccia utente |
| 14 | Etica, Privacy e Integrità | Protezione dati e considerazioni etiche sull'IA |
| 15 | Hardware e Scaling | Ottimizzazione per varie configurazioni hardware |
| 16 | Mappe e GNN | Analisi spaziale e approcci con reti neurali su grafi |
| 17 | Impatto Sociotecnico | Direzioni future e implicazioni sociali |

---

## Alimentare il Coach

Il coach IA viene fornito senza conoscenza pre-addestrata. Apprende esclusivamente da file demo professionali CS2. La qualità del coaching è direttamente proporzionale alla qualità e quantità delle demo ingerite.

### Soglie di Conteggio Demo

| Demo Pro | Livello | Confidenza | Cosa Succede |
|----------|---------|------------|--------------|
| 0-9 | Non pronto | 0% | Minimo 10 demo pro richieste per il primo ciclo di training |
| 10-49 | CALIBRATING | 50% | Coaching base attivo, consigli marcati come provvisori |
| 50-199 | LEARNING | 80% | Affidabilità crescente, sempre più personalizzato |
| 200+ | MATURE | 100% | Piena confidenza, massima accuratezza |

### Dove Trovare Demo Pro

1. Vai su [hltv.org](https://www.hltv.org) > Results
2. Filtra per eventi top-tier: Major Championship, IEM Katowice/Cologne, BLAST Premier, ESL Pro League, PGL Major
3. Seleziona partite di team nella top-20 (Navi, FaZe, Vitality, G2, Spirit, Heroic)
4. Preferisci serie BO3/BO5 per massimizzare i dati di training per download
5. Diversifica su tutte le mappe Active Duty — una distribuzione sbilanciata crea un coach sbilanciato
6. Scarica il link "GOTV Demo" o "Watch Demo"

### Pianificazione Storage

I file `.dem` sono tipicamente 300-850 MB ciascuno. Pianifica il tuo storage di conseguenza:

| Demo | File Raw | DB Match | Totale |
|------|----------|----------|--------|
| 10 | ~5 GB | ~1 GB | ~6 GB |
| 50 | ~30 GB | ~5 GB | ~35 GB |
| 100 | ~60 GB | ~10 GB | ~70 GB |
| 200 | ~120 GB | ~20 GB | ~140 GB |

Tre posizioni di storage separate:

| Posizione | Contenuto | Raccomandazione |
|-----------|-----------|----------------|
| Core Database | Statistiche giocatore, stato coaching, metadati HLTV | Resta nella cartella programma |
| Brain Data Root | Pesi modelli AI, log, knowledge base | SSD consigliato |
| Pro Demo Folder | File .dem raw + database SQLite per-match | Il più grande, HDD accettabile |

### Monitoraggio TensorBoard

```bash
tensorboard --logdir runs/coach_training
```

Apri [http://localhost:6006](http://localhost:6006) per monitorare conviction index, transizioni stato di maturità, specializzazione gate e curve di loss del training.

> Per la checklist completa passo-passo del ciclo di coaching e la guida dettagliata allo storage, consulta la [Guida Utente](docs/USER_GUIDE_IT.md).

---

## Risoluzione dei Problemi

### Problemi Comuni

| Problema | Soluzione |
|----------|----------|
| `ModuleNotFoundError: No module named 'kivy'` | Installa le dipendenze Kivy: `pip install kivy-deps.glew==0.3.1 kivy-deps.sdl2==0.7.0 kivy-deps.angle==0.4.0 Kivy==2.3.0 KivyMD==1.2.0` (salta kivy-deps su Linux) |
| `CUDA not available` | Verifica il driver con `nvidia-smi`, reinstalla PyTorch con `--index-url https://download.pytorch.org/whl/cu121` |
| `sentence-transformers not installed` | Avviso non bloccante. Installa con `pip install sentence-transformers` per embedding migliorati, oppure ignora (fallback TF-IDF funziona) |
| L'app crasha con errore GL | Imposta `KIVY_GL_BACKEND=angle_sdl2` (Windows) o `KIVY_GL_BACKEND=sdl2` (Linux) |
| `database is locked` | Chiudi tutti i processi Python e riavvia |
| Schermo bianco/vuoto | Esegui dalla root del progetto: `python Programma_CS2_RENAN/main.py`, verifica che `layout.kv` esista |
| Reset allo stato di fabbrica | Elimina `Programma_CS2_RENAN/user_settings.json` e riavvia |

### Posizioni Database

| Database | Percorso | Contenuto |
|----------|---------|-----------|
| Principale | `Programma_CS2_RENAN/backend/storage/database.db` | Statistiche giocatore, stato coaching, dati training |
| HLTV | `Programma_CS2_RENAN/backend/storage/hltv_metadata.db` | Metadati giocatori professionisti |
| Conoscenza | `Programma_CS2_RENAN/data/knowledge_base.db` | Base di conoscenza RAG |
| Per-match | `{PRO_DEMO_PATH}/match_data/match_*.db` | Dati tick-level della partita |

> Per il troubleshooting completo, consulta la [Guida Utente](docs/USER_GUIDE_IT.md).

---

## Licenza

Questo progetto è a doppia licenza. Copyright (c) 2025-2026 Renan Augusto Macena.

Puoi scegliere tra:
- **Licenza Proprietaria** — Tutti i Diritti Riservati (default). La visualizzazione per scopi educativi è consentita.
- **Apache License 2.0** — Open source permissiva con protezione brevetti.

Consulta [LICENSE](LICENSE) per i termini completi.

---

## Autore

**Renan Augusto Macena**

Costruito con passione da un giocatore di Counter-Strike con oltre 10.000 ore dal 2004, combinando una profonda conoscenza del gioco con l'ingegneria IA per creare il sistema di coaching definitivo.

> *"Ho sempre desiderato una guida professionale — come quella dei veri giocatori professionisti — per capire come appare realmente quando qualcuno si allena nel modo giusto e gioca nel modo giusto."*
