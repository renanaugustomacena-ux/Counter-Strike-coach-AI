> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Sistemi Core

Fondazione runtime che fornisce orchestrazione dei daemon, gestione asset, intelligenza spaziale e ciclo di vita dell'applicazione.

## Componenti Chiave

### Session Engine (`session_engine.py`)
**Quad-Daemon Engine** (storicamente Tri-Daemon) che orchestra quattro thread worker concorrenti:
- **Hunter** — Scanner del file system che rileva nuovi file demo
- **Digester** — Processore demo che estrae dati tattici e persiste nel database
- **Teacher** — Retrainer del modello con tracciamento baseline temporale e rilevamento meta-shift
- **Pulse** — Thread heartbeat che monitora la salute dei daemon

Gestione baseline temporale:
- `_get_current_baseline_snapshot()` — Cattura snapshot delle performance del modello
- `_check_meta_shift()` — Rileva degrado significativo delle performance che richiede intervento

### Gestione Asset
- `asset_manager.py` — SmartAsset (lazy loading), AssetAuthority (registro centralizzato), MapAssetManager
- `map_manager.py` — Wrapper MapManager per caricamento asset UI (interfaccia consigliata rispetto all'accesso diretto ad AssetAuthority)

### Intelligenza Spaziale
- `spatial_data.py` — MapMetadata per 9 mappe CS2 con sistemi di coordinate, Z-cutoff per mappe multi-livello (Nuke, Vertigo)
- `spatial_engine.py` — SpatialEngine che fornisce mappatura coordinate pixel-accurate e classificazione zone

### Riproduzione Demo
- `playback_engine.py` — InterpolatedPlayerState, InterpolatedFrame, PlaybackEngine per riproduzione demo fluida con interpolazione frame

### Configurazione & Persistenza
- `config.py` — Gestione configurazione con risoluzione percorsi, MATCH_DATA_PATH, API get_setting/save_user_setting
- `lifecycle.py` — AppLifecycleManager per sequenziamento avvio/arresto graduale
- `integrity_manifest.json` — Manifest integrità file per controlli integrità runtime RASP

### Strutture Dati
- `demo_frame.py` — Tipi dati core: PlayerState, GhostState, NadeState, BombState, KillEvent, DemoFrame

### Infrastruttura
- `localization.py` — LocalizationManager con supporto per Inglese, Italiano, Portoghese
- `registry.py` — ScreenRegistry per gestione ciclo di vita schermate Kivy
- `logger.py` — Setup logging strutturato con logger a livello modulo

## Pattern Critici

### Risoluzione Percorso Match Data
Usare sempre `config.MATCH_DATA_PATH` per la posizione del database match. Default è `PRO_DEMO_PATH/match_data/` con fallback alla directory in-project. Mai hardcodare i percorsi.

### Accesso Singleton
```python
from backend.storage.match_data_manager import get_match_data_manager

manager = get_match_data_manager()  # Istanza singleton
```

Dopo modifiche al percorso, resettare il singleton:
```python
from backend.storage.match_data_manager import reset_match_data_manager

reset_match_data_manager()
manager = get_match_data_manager()  # Nuova istanza con percorso aggiornato
```

### Caricamento Asset (UI)
```python
from core.map_manager import MapManager

map_manager = MapManager()
radar_path = map_manager.get_radar_image("de_dust2")
```

### Query Spaziali
```python
from core.spatial_engine import SpatialEngine

engine = SpatialEngine("de_dust2")
pixel_x, pixel_y = engine.world_to_pixel(world_x, world_y, world_z)
zone_name = engine.get_zone_at_position(world_x, world_y, world_z)
```
