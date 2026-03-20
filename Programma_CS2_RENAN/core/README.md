> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Core Systems

Runtime foundation providing daemon orchestration, asset management, spatial intelligence, and application lifecycle.

## Key Components

### Session Engine (`session_engine.py`)
**Quad-Daemon Engine** (historically Tri-Daemon) orchestrating four concurrent worker threads:
- **Hunter** — File system scanner detecting new demo files
- **Digester** — Demo processor extracting tactical data and persisting to database
- **Teacher** — Model retrainer with temporal baseline tracking and meta-shift detection
- **Pulse** — Heartbeat thread monitoring daemon health

Temporal baseline management:
- `_get_current_baseline_snapshot()` — Captures model performance snapshot
- `_check_meta_shift()` — Detects significant performance degradation requiring intervention

### Asset Management
- `asset_manager.py` — SmartAsset (lazy loading), AssetAuthority (centralized registry), MapAssetManager
- `map_manager.py` — MapManager wrapper for UI asset loading (recommended interface over direct AssetAuthority access)

### Spatial Intelligence
- `spatial_data.py` — MapMetadata for 9 CS2 maps with coordinate systems, Z-cutoffs for multi-level maps (Nuke, Vertigo)
- `spatial_engine.py` — SpatialEngine providing pixel-accurate coordinate mapping and zone classification

### Demo Playback
- `playback_engine.py` — InterpolatedPlayerState, InterpolatedFrame, PlaybackEngine for smooth demo replay with frame interpolation

### Configuration & Persistence
- `config.py` — Configuration management with path resolution, MATCH_DATA_PATH, get_setting/save_user_setting API
- `lifecycle.py` — AppLifecycleManager for graceful startup/shutdown sequencing
- `integrity_manifest.json` — File integrity manifest for RASP runtime integrity checks

### Data Structures
- `demo_frame.py` — Core data types: PlayerState, GhostState, NadeState, BombState, KillEvent, DemoFrame

### Infrastructure
- `localization.py` — LocalizationManager supporting English, Italian, Portuguese
- `registry.py` — ScreenRegistry for Kivy screen lifecycle management
- `logger.py` — Structured logging setup with module-level loggers

## Critical Patterns

### Match Data Path Resolution
Always use `config.MATCH_DATA_PATH` for match database location. Default is `PRO_DEMO_PATH/match_data/` with fallback to in-project directory. Never hardcode paths.

### Singleton Access
```python
from backend.storage.match_data_manager import get_match_data_manager

manager = get_match_data_manager()  # Singleton instance
```

After path changes, reset singleton:
```python
from backend.storage.match_data_manager import reset_match_data_manager

reset_match_data_manager()
manager = get_match_data_manager()  # New instance with updated path
```

### Asset Loading (UI)
```python
from core.map_manager import MapManager

map_manager = MapManager()
radar_path = map_manager.get_radar_image("de_dust2")
```

### Spatial Queries
```python
from core.spatial_engine import SpatialEngine

engine = SpatialEngine("de_dust2")
pixel_x, pixel_y = engine.world_to_pixel(world_x, world_y, world_z)
zone_name = engine.get_zone_at_position(world_x, world_y, world_z)
```
