# Macena CS2 Analyzer — Guida Utente

Guida completa per installare, configurare e utilizzare il Macena CS2 Analyzer su Windows o Linux.

---

## Indice

1. [Requisiti di Sistema](#1-requisiti-di-sistema)
2. [Installazione](#2-installazione)
3. [Primo Avvio e Procedura Guidata di Configurazione](#3-primo-avvio-e-procedura-guidata-di-configurazione)
4. [Configurazione delle API Key (Steam e FaceIT)](#4-configurazione-delle-api-key-steam-e-faceit)
5. [Schermata Principale](#5-schermata-principale)
6. [Pagina Impostazioni](#6-pagina-impostazioni)
7. [Schermata Coach e Chat AI](#7-schermata-coach-e-chat-ai)
8. [Cronologia Partite](#8-cronologia-partite)
9. [Dettaglio Partita](#9-dettaglio-partita)
10. [Dashboard Prestazioni](#10-dashboard-prestazioni)
11. [Visualizzatore Tattico (Widget Mappa 2D)](#11-visualizzatore-tattico-widget-mappa-2d)
12. [Profilo Utente](#12-profilo-utente)
13. [Risoluzione dei Problemi](#13-risoluzione-dei-problemi)

---

## 1. Requisiti di Sistema

| Componente | Minimo | Consigliato |
|------------|--------|-------------|
| Sistema Operativo | Windows 10 / Ubuntu 22.04 | Windows 10/11 |
| Python | 3.10 | 3.10 o 3.12 |
| RAM | 8 GB | 16 GB |
| GPU | Nessuna (modalita' CPU) | NVIDIA GTX 1650+ (CUDA 12.1) |
| Disco | 3 GB liberi | 5 GB liberi |
| Display | 1280x720 | 1920x1080 |

---

## 2. Installazione

### 2.1 Clonare il Repository

```bash
git clone https://github.com/renanaugustomacena-ux/Macena_cs2_analyzer.git
cd Macena_cs2_analyzer
```

### 2.2 Windows (Configurazione Automatica)

Apri **PowerShell** nella directory principale del progetto ed esegui:

```powershell
.\scripts\Setup_Macena_CS2.ps1
```

Questo script:
- Verifica che Python 3.10+ sia installato
- Crea un ambiente virtuale (`venv_win/`)
- Installa PyTorch (versione CPU) e tutte le dipendenze
- Inizializza il database
- Installa Playwright (browser Chromium per lo scraping di HLTV)

**Per il supporto GPU** (solo NVIDIA), dopo il completamento dello script:

```powershell
.\venv_win\Scripts\pip.exe install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 2.3 Windows (Configurazione Manuale)

Se lo script PowerShell fallisce o preferisci l'installazione manuale:

```powershell
# Crea l'ambiente virtuale
python -m venv venv_win
.\venv_win\Scripts\activate

# Installa PyTorch (scegli UNO):
# Solo CPU:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
# NVIDIA GPU (CUDA 12.1):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Installa tutte le altre dipendenze
pip install -r Programma_CS2_RENAN/requirements.txt

# Inizializza il database
python -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database()"

# Installa il browser Playwright
pip install playwright
python -m playwright install chromium
```

### 2.4 Linux (Ubuntu/Debian)

```bash
# Dipendenze di sistema
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev
sudo apt install -y libsdl2-dev libglew-dev build-essential

# Crea l'ambiente virtuale
python3.10 -m venv venv_linux
source venv_linux/bin/activate

# Installa PyTorch (scegli UNO):
# Solo CPU:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
# NVIDIA GPU (CUDA 12.1):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Installa le dipendenze (ignora kivy-deps specifici per Windows se pip si lamenta)
pip install -r Programma_CS2_RENAN/requirements.txt
pip install Kivy==2.3.0 KivyMD==1.2.0

# Inizializza il database
python -c "import sys; sys.path.append('.'); from Programma_CS2_RENAN.backend.storage.database import init_database; init_database()"

# Installa il browser Playwright
pip install playwright
python -m playwright install chromium
```

### 2.5 Verifica dell'Installazione

```bash
# Attiva prima il tuo venv, poi:
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import kivy; print(f'Kivy: {kivy.__version__}')"
python -c "from Programma_CS2_RENAN.backend.nn.config import get_device; print(f'Device: {get_device()}')"
```

Output atteso (esempio con GPU):
```
PyTorch: 2.5.1+cu121
Kivy: 2.3.0
Device: cuda:0
```

### 2.6 Avvio dell'Applicazione

```bash
# Windows
.\venv_win\Scripts\python.exe Programma_CS2_RENAN/main.py

# Linux
./venv_linux/bin/python Programma_CS2_RENAN/main.py
```

La finestra si apre a 1280x720. Al **primo avvio**, vedrai la Procedura Guidata di Configurazione (Setup Wizard).

---

## 3. Primo Avvio e Procedura Guidata di Configurazione

Quando esegui main.py per la prima volta, l'app mostra una **procedura guidata di configurazione in 3 passaggi**.

### Passaggio 1: Schermata di Benvenuto

Vedrai un messaggio di benvenuto che spiega l'app. Clicca **START** per iniziare la configurazione.

### Passaggio 2: Directory Root dei Dati AI

L'app chiede: **"Dove deve salvare l'AI i suoi dati di addestramento?"**

Questa e' la cartella dove verranno salvati i modelli della rete neurale, la base di conoscenza e i dataset di addestramento. Puo' trovarsi su qualsiasi unita'.

**Come impostarla:**
1. Clicca **Seleziona Cartella (Select Folder)** — si apre un selettore di file
2. Naviga fino alla posizione desiderata (es., `D:\CS2_Coach_Data` o `C:\Users\TuoNome\Documents\CS2Coach`)
3. Seleziona la cartella e conferma
4. L'app crea tre sottodirectory al suo interno: `knowledge/`, `models/`, `datasets/`

**Oppure** incolla manualmente un percorso nel campo di testo.

> **Suggerimento:** Scegli una posizione con almeno 2 GB di spazio libero. Si consiglia un SSD per un addestramento piu' veloce.

> **Se vedi "Permission denied":** Scegli una cartella all'interno della tua directory utente, come `C:\Users\TuoNome\Documents\MacenaData`.

Clicca **AVANTI (NEXT)** quando hai finito.

### Passaggio 3: Configurazione Completata

Clicca **AVVIA (LAUNCH)** per entrare nell'app. La procedura guidata non apparira' piu' nei futuri avvii.

> **Per rieseguire la procedura guidata:** Elimina il file `Programma_CS2_RENAN/user_settings.json` e riavvia l'app.

---

## 4. Configurazione delle API Key (Steam e FaceIT)

Le API key permettono all'app di recuperare la cronologia delle tue partite e le statistiche dei giocatori. Sono **opzionali** — l'app funziona anche senza, ma alcune funzionalita' (importazione automatica delle partite, sincronizzazione del profilo giocatore) non saranno disponibili.

### 4.1 API Key di Steam

1. Dalla **Schermata Principale (Home Screen)**, trova la scheda **Personalizzazione (Personalization)**
2. Clicca il pulsante **Steam**
3. Vedrai due campi:

**Steam ID (SteamID64):**
- Questo e' il tuo identificatore Steam a 17 cifre (es., `76561198012345678`)
- Clicca il link **"Trova il tuo Steam ID" ("Find Your Steam ID")** per aprire [steamid.io](https://steamid.io) nel browser
- Inserisci l'URL del tuo profilo Steam e copia il numero **SteamID64**

**Steam Web API Key:**
- Clicca il link **"Ottieni API Key di Steam" ("Get Steam API Key")** per aprire [Steam Developer](https://steamcommunity.com/dev/apikey) nel browser
- Accedi con il tuo account Steam
- Quando ti viene chiesto un nome di dominio, digita `localhost`
- Copia la chiave generata

4. Incolla entrambi i valori e clicca **Salva Configurazione (Save Config)**

> **Sicurezza:** La tua API key e' memorizzata nel **Gestore Credenziali di Windows** (Windows Credential Manager) (o nel portachiavi di sistema su Linux), non in testo semplice. Il file delle impostazioni mostra `"PROTECTED_BY_WINDOWS_VAULT"` al posto della chiave effettiva.

### 4.2 API Key di FaceIT

1. Dalla **Schermata Principale (Home Screen)** > scheda **Personalizzazione (Personalization)**, clicca **FaceIT**
2. Clicca il link **"Ottieni API Key di FaceIT" ("Get FaceIT API Key")** per aprire [FaceIT Developers](https://developers.faceit.com/)
3. Crea un account sviluppatore e genera un'API key
4. Incolla la chiave e clicca **Salva (Save)**

> **Nota:** L'app valida le chiavi al momento dell'utilizzo, non al momento del salvataggio. Se una chiave non e' valida, vedrai un errore quando l'app prova a recuperare i dati.

---

## 5. Schermata Principale

Dopo la configurazione, questa e' la tua dashboard principale. Ha una **barra di navigazione superiore** e **schede scorrevoli**.

### Barra di Navigazione Superiore

| Icona | Azione |
|-------|--------|
| Ingranaggio (sinistra) | Apre le **Impostazioni (Settings)** |
| Punto interrogativo (sinistra) | Apre la **Guida (Help)** — argomenti di documentazione ricercabili |
| Appunti (destra) | Apre la **Cronologia Partite (Match History)** |
| Grafico (destra) | Apre la **Dashboard Prestazioni (Performance Dashboard)** |
| Tocco di laurea (destra) | Apre la **Schermata Coach (Coach Screen)** |
| Persona (destra) | Apre il **Profilo Utente (User Profile)** |

### Schede della Dashboard

**1. Progresso dell'Addestramento (Training Progress)**
Mostra lo stato in tempo reale dell'addestramento ML: epoca attuale, perdita di addestramento/validazione, tempo rimanente stimato. Quando l'addestramento e' inattivo, mostra le ultime metriche di addestramento completate.

**2. Hub di Importazione Pro (Pro Ingestion Hub)**
- **Imposta Cartella (Set Folder)**: Seleziona la cartella contenente i tuoi file demo `.dem` personali
- **Cartella Pro (Pro Folder)**: Seleziona la cartella contenente i file demo `.dem` dei giocatori professionisti
- **Selettore velocita'**: Eco (lento, basso utilizzo CPU), Standard (bilanciato), Turbo (veloce, alto utilizzo CPU)
- **Pulsante Play/Stop**: Avvia o ferma il processo di importazione demo

**3. Personalizzazione (Personalization)**
- **Profilo (Profile)**: Imposta il tuo nome giocatore in-game
- **Steam**: Configura Steam ID e API key ([vedi Sezione 4.1](#41-api-key-di-steam))
- **FaceIT**: Configura API key di FaceIT ([vedi Sezione 4.2](#42-api-key-di-faceit))

**4. Analisi Tattica (Tactical Analysis)**
Clicca **Avvia Visualizzatore (Launch Viewer)** per aprire il visualizzatore tattico della mappa 2D ([vedi Sezione 11](#11-visualizzatore-tattico-widget-mappa-2d)).

**5. Approfondimenti Dinamici (Dynamic Insights)**
Schede di coaching generate automaticamente dall'AI. Ogni scheda ha:
- Un **colore di gravita'** (blu = informazione, arancione = avviso, rosso = critico)
- Un **titolo** e un **messaggio** che spiegano l'analisi
- Un'**area di interesse** (es., "Posizionamento", "Uso delle Utility")

### Barra di Stato ML

In cima alla dashboard, una barra colorata mostra lo stato del servizio di coaching:
- **Blu**: Il servizio e' attivo e in esecuzione
- **Rosso**: Il servizio e' offline — clicca **RIAVVIA SERVIZIO (RESTART SERVICE)** per ripristinarlo

---

## 6. Pagina Impostazioni

Accessibile dall'icona dell'ingranaggio nella Schermata Principale (Home Screen). Tutte le modifiche vengono salvate immediatamente.

### Tema Visivo (Visual Theme)

Tre preset di tema che cambiano la combinazione di colori e lo sfondo dell'app:
- **CS2** (toni arancioni)
- **CS:GO** (toni blu-grigi)
- **CS 1.6** (toni verdi)

Clicca **Cambia Sfondo (Cycle Wallpaper)** per ruotare tra le immagini di sfondo disponibili per il tema corrente.

### Percorsi di Analisi (Analysis Paths)

- **Cartella Demo Predefinita (Default Demo Folder)**: Dove sono memorizzati i tuoi file `.dem` personali. Clicca **Cambia (Change)** per selezionare una nuova cartella.
- **Cartella Demo Pro (Pro Demo Folder)**: Dove sono memorizzati i file `.dem` dei giocatori professionisti. Clicca **Cambia (Change)** per selezionare una nuova cartella.

> **Importante:** Quando cambi la Cartella Demo Pro, l'app migra automaticamente i file del database delle partite (`match_data/`) nella nuova posizione.

### Aspetto (Appearance)

- **Dimensione Carattere (Font Size)**: Piccolo (12pt), Medio (16pt), o Grande (20pt)
- **Tipo di Carattere (Font Type)**: Scegli tra Roboto, Arial, JetBrains Mono, New Hope, CS Regular, o YUPIX

### Controllo Importazione Dati (Data Ingestion Control)

- **Interruttore Modalita' (Mode Toggle)**: Alterna tra **Manuale (Manual)** (scansione singola) e **Automatico (Auto)** (scansione continua a intervalli)
- **Intervallo di Scansione (Scan Interval)**: Con quale frequenza (in minuti) la modalita' automatica controlla la presenza di nuovi demo. Minimo: 1 minuto.
- **Avvia/Ferma Importazione (Start/Stop Ingestion)**: Attiva o ferma manualmente il processo di importazione

### Lingua (Language)

Cambia tra English, Italiano e Portugues. L'intera interfaccia utente si aggiorna immediatamente.

---

## 7. Schermata Coach e Chat AI

Accessibile dall'icona del tocco di laurea nella Schermata Principale (Home Screen).

### Dashboard

- **Stato delle Credenze (Belief State)**: Mostra la fiducia dell'inferenza del coach AI (0-100%). Verde quando sopra il 70%.
- **Grafico delle Tendenze (Trend Graph)**: Grafico a linee del tuo Rating e ADR nelle ultime 20 partite.
- **Radar delle Abilita' (Skill Radar)**: Grafico a ragno che mostra 5 dimensioni di abilita' (Mira, Utility, Posizionamento, Senso della Mappa, Clutch) confrontate con i parametri di riferimento dei professionisti.
- **Audit Causale (Causal Audit)**: Clicca **Mostra Audit Vantaggio (Show Advantage Audit)** per visualizzare l'analisi causale delle tue decisioni.
- **Motore di Conoscenza (Knowledge Engine)**: Mostra quanti tick di esperienza l'AI ha elaborato e il progresso corrente dell'analisi.
- **Schede di Coaching (Coaching Cards)**: Analisi generate dall'AI con livelli di gravita'.

### Pannello Chat (Chat Panel)

Clicca il pulsante **attiva/disattiva chat (chat toggle)** (in fondo allo schermo) per espandere il pannello chat.

- **Pulsanti di Azione Rapida (Quick Action Buttons)**: Domande predefinite — "Posizionamento", "Utility", "Cosa migliorare?"
- **Campo di Testo (Text Input)**: Digita qualsiasi domanda sul tuo gameplay
- **Risposte del Coach (Coach Replies)**: L'AI analizza i dati delle tue partite e fornisce consigli personalizzati

> **Nota:** La qualita' del coach migliora con piu' demo importati. Si raccomandano almeno 10 demo per analisi significative.

---

## 8. Cronologia Partite

Accessibile dall'icona degli appunti nella Schermata Principale (Home Screen).

Mostra una lista scorrevole delle tue **ultime 50 partite non professionistiche**. Ogni scheda partita visualizza:

- **Badge del Rating** (lato sinistro, codificato per colore):
  - Verde: Rating > 1.10 (sopra la media)
  - Giallo: Rating 0.90 - 1.10 (nella media)
  - Rosso: Rating < 0.90 (sotto la media)
- **Nome mappa** e **data**
- **Statistiche**: Rapporto K/D, ADR, Uccisioni, Morti

**Clicca su qualsiasi partita** per aprire la schermata [Dettaglio Partita](#9-dettaglio-partita).

---

## 9. Dettaglio Partita

Mostra un'analisi approfondita di una singola partita, organizzata in 4 sezioni:

### Panoramica (Overview)
Nome mappa, data, rating complessivo (codificato per colore) e una griglia di statistiche: Uccisioni, Morti, ADR, KAST%, HS%, Rapporto K:D, KPR (Uccisioni Per Round), DPR (Morti Per Round).

### Cronologia dei Round (Round Timeline)
Una lista di ogni round giocato, che mostra:
- Numero del round e fazione (CT/T)
- Uccisioni, Morti, Danni inflitti
- Badge apertura uccisione (se applicabile)
- Risultato del round (Vittoria/Sconfitta)

### Grafico dell'Economia (Economy Graph)
Un grafico a barre che mostra il valore del tuo equipaggiamento per round. Barre blu = lato CT, Barre gialle = lato T. Aiuta a identificare i pattern di eco/force-buy.

### Momenti Salienti e Momentum (Highlights & Momentum)
- **Grafico del Momentum (Momentum Graph)**: Grafico a linee del tuo delta cumulativo Uccisioni-Morti attraverso i round. Riempimento verde = momentum positivo, Riempimento rosso = negativo.
- **Analisi del Coaching (Coaching Insights)**: Analisi generate dall'AI specifiche per questa partita.

---

## 10. Dashboard Prestazioni

Accessibile dall'icona del grafico nella Schermata Principale (Home Screen). Mostra le tendenze delle tue prestazioni a lungo termine.

### Tendenza del Rating (Rating Trend)
Grafico sparkline del tuo rating nelle ultime 50 partite. Linee di riferimento a:
- 1.10 (verde) — prestazione eccellente
- 1.00 (bianco) — media
- 0.90 (rosso) — sotto la media

### Prestazioni Per Mappa (Per-Map Performance)
Schede scorrevoli orizzontalmente, una per mappa (de_dust2, de_mirage, ecc.). Ciascuna mostra:
- Rating medio (codificato per colore)
- ADR medio e rapporto K:D
- Numero di partite giocate

### Punti di Forza e Debolezze (Strengths & Weaknesses)
Confronto a due colonne rispetto ai parametri di riferimento dei giocatori professionisti usando i punteggi Z:
- **Sinistra (Verde)**: Le tue metriche migliori
- **Destra (Rosso)**: Aree che necessitano di miglioramento

### Pannello Utility (Utility Panel)
Grafico a barre che confronta il tuo utilizzo delle utility con i parametri di riferimento dei professionisti su 6 metriche:
- Granate HE, Molotov, Granate Fumogene
- Tempo di Accecamento Flash, Assist Flash, Utility Non Utilizzate

---

## 11. Visualizzatore Tattico (Widget Mappa 2D)

Accessibile tramite **Avvia Visualizzatore (Launch Viewer)** nella Schermata Principale (Home Screen).

Questo e' il visualizzatore di replay 2D in tempo reale. Renderizza i file demo come una visualizzazione interattiva della mappa.

### Cosa Vedrai

- **Mappa 2D**: Vista dall'alto della mappa CS2 con le posizioni dei giocatori come cerchi colorati
- **Etichette Giocatori**: Nome, ruolo e barre della salute per ogni giocatore
- **Marcatori Eventi**: Icone delle uccisioni, indicatori di piazzamento/disinnesco bomba
- **Overlay AI**: Previsioni fantasma che mostrano le posizioni suggerite dall'AI (quando abilitato)

### Controlli

- **Play/Pausa**: Avvia o ferma la riproduzione
- **Velocita'**: Alterna tra 0.5x, 1x, 2x
- **Barra di Scorrimento Timeline (Timeline Scrubber)**: Clicca ovunque sulla barra orizzontale per saltare a un tick specifico
- **Selettore Mappa (Map Selector)**: Cambia mappa (per demo multi-mappa)
- **Selettore Round (Round Selector)**: Salta a un round specifico o visualizza l'intera partita
- **Interruttore AI Fantasma (Ghost AI Toggle)**: Abilita/disabilita le previsioni di posizione dell'AI

### Caricamento di un Demo

Al primo accesso, si apre automaticamente un selettore di file. Seleziona un file `.dem` da caricare. Il visualizzatore analizza e renderizza i dati del demo.

---

## 12. Profilo Utente

Accessibile dall'icona della persona nella Schermata Principale (Home Screen).

Mostra il tuo avatar, nome, ruolo e biografia. Clicca l'**icona della matita** per modificare la tua biografia e il tuo ruolo. Clicca **SINCRONIZZA CON STEAM (SYNC WITH STEAM)** per recuperare i dati del tuo profilo da Steam (richiede API key di Steam).

---

## 13. Risoluzione dei Problemi

### "ModuleNotFoundError: No module named 'kivy'"

Le dipendenze di Kivy non sono installate. Su Windows:
```bash
pip install kivy-deps.glew==0.3.1 kivy-deps.sdl2==0.7.0 kivy-deps.angle==0.4.0
pip install Kivy==2.3.0 KivyMD==1.2.0
```
Su Linux, salta i pacchetti `kivy-deps` — sono specifici per Windows.

### "No module named 'watchdog'"

```bash
pip install watchdog
```
Questo e' necessario per il rilevamento automatico dei file demo. Senza di esso, usa l'importazione manuale dalle Impostazioni (Settings).

### "CUDA not available" / GPU non rilevata

Verifica che il driver NVIDIA sia installato:
```bash
nvidia-smi
```
Poi reinstalla PyTorch con CUDA:
```bash
pip install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```
Verifica:
```bash
python -c "import torch; print(torch.cuda.is_available())"  # Dovrebbe stampare True
```

> **Nessuna GPU NVIDIA?** L'app funziona su CPU. L'addestramento e' piu' lento ma tutto funziona.

### Avviso "sentence-transformers not installed"

Questo e' **normale** e non bloccante. L'app ricorre agli embedding TF-IDF. Per installarlo:
```bash
pip install sentence-transformers
```
La prima esecuzione scarica un modello di ~80MB — questo e' previsto.

### L'app si blocca all'avvio con errore Kivy GL

Su Windows, prova:
```bash
set KIVY_GL_BACKEND=angle_sdl2
python Programma_CS2_RENAN/main.py
```
Su Linux:
```bash
export KIVY_GL_BACKEND=sdl2
python Programma_CS2_RENAN/main.py
```

### Errore di blocco database ("database is locked")

Un altro processo ha il database aperto. Chiudi tutti i processi Python:
```bash
# Windows
taskkill /F /IM python.exe
# Linux
pkill -f python
```
Poi riavvia l'app.

### Permesso negato nella selezione delle cartelle

Scegli una cartella all'interno della tua directory utente:
- Windows: `C:\Users\TuoNome\Documents\MacenaData`
- Linux: `~/MacenaData`

Evita percorsi protetti dal sistema come `C:\Program Files\` o `/usr/`.

### Avviso "Integrity mismatch detected"

Questo e' un avviso in modalita' sviluppo proveniente dall'audit di sicurezza RASP. Significa che i file sorgente sono stati modificati dall'ultima generazione del manifesto di integrita'. **Non blocca l'app** — blocca solo le build congelate/di produzione.

### L'app si apre ma mostra una schermata bianca/vuota

Il file di layout KV non e' riuscito a caricarsi. Controlla:
1. Stai eseguendo dalla directory principale del progetto (non dall'interno di `Programma_CS2_RENAN/`)
2. Il file `Programma_CS2_RENAN/apps/desktop_app/layout.kv` esiste
3. Esegui: `python Programma_CS2_RENAN/main.py` (non `python main.py`)

### Come ripristinare l'app allo stato di fabbrica

Elimina `user_settings.json` e riavvia:
```bash
# Windows
del Programma_CS2_RENAN\user_settings.json
# Linux
rm Programma_CS2_RENAN/user_settings.json
```
La procedura guidata di configurazione apparira' di nuovo al prossimo avvio.

### Dove sono memorizzati i miei database?

| Database | Posizione | Contenuto |
|----------|-----------|-----------|
| DB Principale | `Programma_CS2_RENAN/backend/storage/database.db` | Statistiche giocatore, stato coaching, dati di addestramento |
| DB HLTV | `Programma_CS2_RENAN/backend/storage/hltv_metadata.db` | Metadati giocatori professionisti (separato dall'addestramento) |
| DB Conoscenza | `Programma_CS2_RENAN/data/knowledge_base.db` | Base di conoscenza RAG |
| DB Partite | `{PRO_DEMO_PATH}/match_data/match_*.db` | Dati tick-per-tick per partita |

---

## Riferimento Rapido

| Azione | Come |
|--------|------|
| Avvia l'app | `python Programma_CS2_RENAN/main.py` |
| Riesegui la procedura guidata | Elimina `user_settings.json`, riavvia |
| Cambia cartella demo | Impostazioni (Settings) > Percorsi di Analisi (Analysis Paths) > Cambia (Change) |
| Aggiungi chiave Steam | Schermata Principale (Home) > Personalizzazione (Personalization) > Steam |
| Aggiungi chiave FaceIT | Schermata Principale (Home) > Personalizzazione (Personalization) > FaceIT |
| Avvia importazione | Schermata Principale (Home) > Hub di Importazione Pro (Pro Ingestion Hub) > Pulsante Play |
| Visualizza replay partita | Schermata Principale (Home) > Avvia Visualizzatore (Launch Viewer) |
| Chiedi al coach AI | Schermata Coach (Coach Screen) > Attiva chat (Chat toggle) > Scrivi la domanda |
| Cambia tema | Impostazioni (Settings) > Tema Visivo (Visual Theme) |
| Cambia lingua | Impostazioni (Settings) > Lingua (Language) |
