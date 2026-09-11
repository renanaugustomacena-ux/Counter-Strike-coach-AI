# Sistemi Core

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autorità:** `Programma_CS2_RENAN/core/`
Fondazione runtime che fornisce orchestrazione dei daemon, gestione della
configurazione, intelligenza spaziale e controllo del ciclo di vita dell'applicazione.

## Introduzione

Il pacchetto `core/` è il cuore pulsante di Macena CS2 Analyzer. Ospita il
Quad-Daemon session engine che mantiene attiva la pipeline di analisi, il sistema
di configurazione a tre livelli che risolve le impostazioni utente a runtime, il
livello di dati spaziali che mappa tutte le nove mappe competitive CS2 nello
spazio delle coordinate, e il lifecycle manager che garantisce l'esecuzione a
istanza singola. Ogni altro pacchetto nel progetto dipende da almeno un modulo
di `core/`. Da non confondere con `apps/qt_app/core/`, che ospita gli helper
UI lato Qt (icone, generazione QSS, motore temi) e ha il proprio README.

## Inventario File

| File | Scopo |
|------|-------|
| `session_engine.py` | Quad-Daemon Engine: Scanner, Digester, Teacher, Pulse |
| `config.py` | Risoluzione config a tre livelli (default, JSON, keyring) |
| `spatial_data.py` | `MapMetadata` per 9 mappe, supporto livelli Z, trasformazioni coordinate |
| `spatial_engine.py` | `SpatialEngine`: conversioni world-to-pixel e pixel-to-world |
| `known_maps.py` | SSOT mappe conosciute (CP0 #2): `KNOWN_MAP_NAMES`, `is_known_map()`, sniffing nomi file |
| `tick_rate.py` | SSOT 26-NORM-01: `DEFAULT_TICK_RATE`, `resolve_tick_rate()` risoluzione per-demo |
| `team_codes.py` | SSOT normalizzazione lato team (F-0025 / F-0016): `normalize_team()` mappa vocabolari team grezzi (`'CT'`, `'TERRORIST'`, codici numerici) a canonici `'CT'` / `'T'` |
| `map_manager.py` | `MapManager`: caricamento asset per UI con supporto asincrono Kivy (legacy) |
| `lifecycle.py` | `AppLifecycleManager`: lock istanza singola (mutex Windows / lock nominato POSIX), lancio/arresto daemon |
| `constants.py` | Costanti globali (basate sui secondi): FOV, durate utility, decadimento memoria, finestra trade |
| `demo_frame.py` | Tipi dati core: `PlayerState`, `GhostState`, `NadeState`, `DemoFrame` |
| `asset_manager.py` | `SmartAsset` (lazy loading), `AssetAuthority` (registro centralizzato) |
| `playback_engine.py` | `PlaybackEngine`: replay demo interpolato con blending dei frame |
| `localization.py` | `LocalizationManager`: tabelle stringhe Inglese, Italiano, Portoghese |
| `registry.py` | `ScreenRegistry` per registrazione schermate KivyMD (legacy; Qt è la UI attiva) |
| `lock_files.py` | Lock nominati basati su PID: concorrenza D-track / HLTV-track, istanza singola POSIX; rilascio ownership-aware (F-0009) |
| `map_callouts.py` | `NamedPositionRegistry`: traduzione coordinate-callout per mappe CS2 |
| `app_types.py` | Alias di tipo ed enum condivisi in tutta l'applicazione |
| `frozen_hook.py` | Hook runtime PyInstaller per correzione percorsi in build congelata |
| `integrity_manifest.json` | Manifest hash file per verifica integrità runtime RASP |

## Quad-Daemon Engine (`session_engine.py`)

Il session engine lancia quattro thread daemon più un `IngestionWatcher`,
coordinati tramite segnali `threading.Event` e una riga centrale `CoachState`
nel database monolite.

```
+----------------------------------------------------+
|              run_session_loop()                     |
|                                                    |
|  1. init_database()                                |
|  2. BackupManager.create_checkpoint(               |
|         label="startup_auto")                      |
|  3. Init base di conoscenza (se vuota)             |
|  4. _monitor_stdin (rilevamento morte parent)      |
|  5. Lancio daemon:                                 |
|                                                    |
|     +----------+  +-----------+  +---------+       |
|     | Scanner  |  | Digester  |  | Teacher |       |
|     | (Files)  |  | (Worker)  |  | (ML)    |       |
|     +----------+  +-----------+  +---------+       |
|          |              |              |            |
|     File scan      Consumo coda   Verifica         |
|     ciclo 10s      Event-driven   retrain 5min     |
|                                                    |
|     +----------+                                   |
|     |  Pulse   |  Heartbeat ogni 5 secondi         |
|     +----------+                                   |
+----------------------------------------------------+
```

Un watchdog nel loop keep-alive principale controlla la salute dei daemon ogni
30 secondi e riavvia qualsiasi thread daemon morto inaspettatamente.

### Responsabilità dei Daemon

- **Scanner (_scanner_daemon_loop):** Scansiona le directory demo utente e pro ogni
  10 secondi quando attivo. Chiama `process_new_demos()` per accodare nuovi file.
  Esegue controlli periodici dello spazio disco ogni 5 minuti. Riporta il suo stato
  sotto la chiave di stato `"hunter"`.

- **Digester (_digester_daemon_loop):** Consuma la coda di ingestion un task alla
  volta. Usa `_work_available_event` per risveglio efficiente (evita il polling).
  Processa le demo pro con priorità più alta.

- **Teacher (_teacher_daemon_loop):** Verifica il trigger di riaddestramnto ogni 300
  secondi -- almeno 10 sample pro a freddo, o una crescita del 10% rispetto all'ultimo
  conteggio addestrato -- quindi attiva `CoachTrainingManager.run_full_cycle()`.
  Esegue anche la calibrazione dei belief e il rilevamento meta-shift dopo ogni
  riaddestramento. Rispetta il `_TRAINING_LOCK` a livello modulo per prevenire
  addestramento concorrente.

- **Pulse (_pulse_daemon_loop):** Aggiorna il timestamp `last_heartbeat` su
  `CoachState` ogni 5 secondi per dimostrare la vitalità del daemon alla UI.

### Protocollo di Shutdown

La morte del parent è rilevata tramite chiusura della pipe stdin (`_monitor_stdin`).
Il `_shutdown_event` viene impostato, tutti i daemon escono dai loro cicli, e i
thread vengono joinati con un timeout di 5 secondi ciascuno.

## Sistema di Configurazione (`config.py`)

Risoluzione a tre livelli: default hardcoded, `user_settings.json` su disco, e
keyring del SO per i segreti (chiave API Steam, chiave API Faceit).

```
  Default hardcoded (load_user_settings)
            |
            v
  user_settings.json  (SETTINGS_PATH)
            |
            v
  Keyring del SO (keyring.get_password)
            |
            v
  Globali a livello modulo (CS2_PLAYER_NAME, STEAM_API_KEY, ...)
```

### Thread Safety

- `get_setting(key)` / `get_credential(key)` -- acquisiscono `_settings_lock`, sempre aggiornati
- Globali a livello modulo (`CS2_PLAYER_NAME`, ecc.) -- snapshot all'import, **obsolete nei
  thread daemon**; usare `get_setting()` invece
- `save_user_setting(key, value)` -- scrittura atomica via file tmp + `os.replace()`
- `set_secret(key, value)` -- restituisce `False` invece di sollevare un'eccezione quando il
  keyring non è disponibile (F-0007); i chiamanti ricorrono allo storage su disco
- `refresh_settings()` -- ricarica da disco sotto lock, aggiorna i globali

### Architettura dei Percorsi

```
CORE_DB_DIR    = BASE_DIR/backend/storage/     (database.db SEMPRE qui)
USER_DATA_ROOT = BRAIN_DATA_ROOT o BASE_DIR    (modelli, log, cache)
MATCH_DATA_PATH = PRO_DEMO_PATH/match_data/    (o fallback in-project)
```

Il database core resta nella cartella progetto per portabilità. `BRAIN_DATA_ROOT`
influenza solo artefatti rigenerabili (modelli, log, cache).

`get_pro_demo_base()` risolve il pool demo pro: restituisce il `PRO_DEMO_PATH`
configurato, rileva automaticamente mount SSD spostati sotto `/media` quando il
percorso configurato è assente (DP-06), e altrimenti ricorre alla directory
`backend/storage/` in-project -- mai `$HOME` (F-0008). Una home directory nuda
viene altresì rifiutata come root shard di `MATCH_DATA_PATH`.

## Intelligenza Spaziale

### spatial_data.py

Definisce `MapMetadata` (dataclass immutabile) per tutte le nove mappe competitive CS2
con supporto per mappe multi-livello (Nuke, Vertigo) tramite soglie di cutoff asse Z.

Funzioni principali:
- `get_map_metadata(map_name)` -- lookup fuzzy con matching parziale e avvisi ambiguità
- `get_map_metadata_for_z(map_name, z)` -- selezione automatica livello basata su coordinata Z
- `compute_z_penalty(z_position, map_name)` -- penalità normalizzata [0, 1] per il vettore 25-dim
- `classify_vertical_level(z, map_name)` -- restituisce "upper", "lower", "transition" o "default"

La configurazione viene caricata da `data/map_config.json` con fallback hardcoded in
`_FALLBACK_REGISTRY` (derivati dai file overview radar di Valve).

### spatial_engine.py

`SpatialEngine` fornisce trasformazione di coordinate tra coordinate mondo Source 2
e spazio pixel della UI:

- `world_to_normalized()` -- coordinate mondo a spazio radar [0, 1]
- `normalized_to_pixel()` / `pixel_to_normalized()` -- scaling viewport
- `world_to_pixel()` / `pixel_to_world()` -- scorciatoie conversione diretta

### known_maps.py

Autorità unica per i controlli "è questa una mappa conosciuta?" (map-SSOT, CP0 #2),
sostituendo le liste divergenti per-strumento trovate durante l'audit:

- `KNOWN_MAP_NAMES` (11 nomi base) / `KNOWN_MAP_IDS` (con prefisso `de_`)
- `is_known_map(name)` -- accetta entrambe le convenzioni
- `sniff_map_from_text(text)` -- sniffing nomi file longest-first tramite `MAP_NAME_RE`

Il `SPATIAL_REGISTRY` a 9 mappe in `spatial_data.py` è un sottoinsieme deliberato
(mappe con geometria radar calibrata), non una divergenza.

### constants.py

Costanti temporali globali, definite **solo in secondi**. Le finestre in tick vengono
calcolate al punto di utilizzo dal tick rate per-demo (`resolve_tick_rate()` in
`tick_rate.py`) -- le vecchie derivazioni secondi-in-tick al momento dell'import sono
state rimosse perché incorporavano `TICK_RATE = 64`. `TICK_RATE` rimane solo come alias
legacy di `core.tick_rate.DEFAULT_TICK_RATE`.

| Costante | Secondi |
|----------|---------|
| `SMOKE_DURATION_S` | 18.0 |
| `MOLOTOV_DURATION_S` | 7.0 |
| `FLASH_DURATION_S` | 2.0 |
| `MEMORY_DECAY_TAU_S` | 2.5 |
| `MEMORY_CUTOFF_S` | 7.5 |
| `TRADE_WINDOW_S` | 3.0 |

Definisce inoltre `FOV_DEGREES = 90.0` e `Z_FLOOR_THRESHOLD = 200.0`.

## Ciclo di Vita dell'Applicazione (`lifecycle.py`)

`AppLifecycleManager` garantisce l'esecuzione a istanza singola e gestisce il
sottoprocesso del session engine. Su Windows la guardia è un mutex kernel nominato;
su POSIX è il lock nominato `lock_files` `app_single_instance` con recupero PID morti,
che fallisce in modalità chiusa su qualsiasi errore di lock per proteggere il database
SQLite (F-0010):

- `ensure_single_instance()` -- restituisce False se un'altra istanza detiene il lock
- `launch_daemon()` -- genera `session_engine.py` come sottoprocesso con pipe stdin per IPC
- `shutdown()` -- terminazione graduale con timeout 3 secondi, poi force kill

Registrato come handler `atexit` per garantire la pulizia all'uscita del processo.

## Punti di Integrazione

```
apps/qt_app/app.py ──> lifecycle.launch_daemon() ──> session_engine.run_session_loop()
                                              |
                                              +──> config.DATABASE_URL
                                              +──> config.get_setting()
                                              +──> spatial_data.get_map_metadata()
                                              +──> constants.TICK_RATE
```

## Note di Sviluppo

- **I globali config sono obsoleti nei thread daemon.** Usare sempre `get_setting()` o
  `get_credential()` nei thread in background. Gli import a livello modulo catturano uno
  snapshot che non viene mai aggiornato a meno che `refresh_settings()` non venga eseguito.
- **Mai hardcodare percorsi match data.** Usare `config.MATCH_DATA_PATH` che si risolve
  dinamicamente in base alla disponibilità di `PRO_DEMO_PATH`.
- **I dati spaziali supportano hot reload.** Chiamare `reload_spatial_config()` per forzare
  la ri-lettura di `map_config.json` senza riavviare l'applicazione.
- **L'asse Z conta.** Le mappe multi-livello (Nuke, Vertigo) richiedono
  `get_map_metadata_for_z()` invece del semplice `get_map_metadata()` per la corretta
  selezione del livello.
- **Il session engine monitora stdin.** Se il processo parent muore (pipe chiusa),
  tutti i daemon si arrestano automaticamente. Inviare "STOP" su stdin attiva l'uscita graduale.
