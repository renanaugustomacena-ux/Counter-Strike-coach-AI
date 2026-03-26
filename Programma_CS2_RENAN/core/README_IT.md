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
di `core/`.

## Inventario File

| File | Scopo |
|------|-------|
| `session_engine.py` | Quad-Daemon Engine: Hunter, Digester, Teacher, Pulse |
| `config.py` | Risoluzione config a tre livelli (default, JSON, keyring) |
| `spatial_data.py` | `MapMetadata` per 9 mappe, supporto livelli Z, trasformazioni coordinate |
| `spatial_engine.py` | `SpatialEngine`: conversioni world-to-pixel e pixel-to-world |
| `map_manager.py` | `MapManager`: caricamento asset per UI con supporto asincrono Kivy |
| `lifecycle.py` | `AppLifecycleManager`: mutex istanza singola, lancio/arresto daemon |
| `constants.py` | Costanti globali: tick rate, FOV, durate utility, finestra trade |
| `demo_frame.py` | Tipi dati core: `PlayerState`, `GhostState`, `NadeState`, `DemoFrame` |
| `asset_manager.py` | `SmartAsset` (lazy loading), `AssetAuthority` (registro centralizzato) |
| `playback.py` | `TimelineController`: controller centralizzato Kivy per playback partita |
| `playback_engine.py` | `PlaybackEngine`: replay demo interpolato con blending dei frame |
| `localization.py` | `LocalizationManager`: tabelle stringhe Inglese, Italiano, Portoghese |
| `platform_utils.py` | Rilevamento drive cross-platform (Windows, Linux, macOS) |
| `registry.py` | `ScreenRegistry` per gestione ciclo di vita schermate Kivy |
| `logger.py` | Setup logging strutturato con logger a livello modulo |
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
|  2. BackupManager.create_checkpoint("startup")     |
|  3. Init base di conoscenza (se vuota)             |
|  4. _monitor_stdin (rilevamento morte parent)      |
|  5. Lancio daemon:                                 |
|                                                    |
|     +----------+  +-----------+  +---------+       |
|     |  Hunter  |  | Digester  |  | Teacher |       |
|     | (Scanner)|  | (Worker)  |  | (ML)    |       |
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

### Responsabilità dei Daemon

- **Hunter (_scanner_daemon_loop):** Scansiona le directory demo utente e pro ogni
  10 secondi quando attivo. Chiama `process_new_demos()` per accodare nuovi file.
  Esegue controlli periodici dello spazio disco ogni 5 minuti.

- **Digester (_digester_daemon_loop):** Consuma la coda di ingestion un task alla
  volta. Usa `_work_available_event` per risveglio efficiente (evita il polling).
  Processa le demo pro con priorità più alta.

- **Teacher (_teacher_daemon_loop):** Verifica se i nuovi sample pro superano la
  soglia di crescita del 10%, quindi attiva `CoachTrainingManager.run_full_cycle()`.
  Esegue anche la calibrazione dei belief e il rilevamento meta-shift dopo ogni
  riaddestramnto. Rispetta il `_TRAINING_LOCK` a livello modulo per prevenire
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
- `refresh_settings()` -- ricarica da disco sotto lock, aggiorna i globali

### Architettura dei Percorsi

```
CORE_DB_DIR    = BASE_DIR/backend/storage/     (database.db SEMPRE qui)
USER_DATA_ROOT = BRAIN_DATA_ROOT o BASE_DIR    (modelli, log, cache)
MATCH_DATA_PATH = PRO_DEMO_PATH/match_data/    (o fallback in-project)
```

Il database core resta nella cartella progetto per portabilità. `BRAIN_DATA_ROOT`
influenza solo artefatti rigenerabili (modelli, log, cache).

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

### constants.py

Costanti temporali globali derivate da `TICK_RATE = 64`:

| Costante | Secondi | Tick |
|----------|---------|------|
| `SMOKE_DURATION` | 18.0 | 1152 |
| `MOLOTOV_DURATION` | 7.0 | 448 |
| `FLASH_DURATION` | 2.0 | 128 |
| `MEMORY_DECAY_TAU` | 2.5 | 160 |
| `MEMORY_CUTOFF` | 7.5 | 480 |
| `TRADE_WINDOW` | 3.0 | 192 |

## Ciclo di Vita dell'Applicazione (`lifecycle.py`)

`AppLifecycleManager` garantisce l'esecuzione a istanza singola (mutex nominato Windows)
e gestisce il sottoprocesso del session engine:

- `ensure_single_instance()` -- restituisce False se un'altra istanza detiene il mutex
- `launch_daemon()` -- genera `session_engine.py` come sottoprocesso con pipe stdin per IPC
- `shutdown()` -- terminazione graduale con timeout 3 secondi, poi force kill

Registrato come handler `atexit` per garantire la pulizia all'uscita del processo.

## Punti di Integrazione

```
main.py ──> lifecycle.launch_daemon() ──> session_engine.run_session_loop()
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
