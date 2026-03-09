> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Sistemas Core

Fundação de runtime fornecendo orquestração de daemons, gerenciamento de assets, inteligência espacial e ciclo de vida da aplicação.

## Componentes Principais

### Session Engine (`session_engine.py`)
**Tri-Daemon Engine** orquestrando três threads worker concorrentes:
- **Hunter** — Scanner do sistema de arquivos detectando novos arquivos demo
- **Digester** — Processador de demo extraindo dados táticos e persistindo no banco de dados
- **Teacher** — Re-treinador do modelo com rastreamento de baseline temporal e detecção de meta-shift
- **Pulse** — Thread de heartbeat monitorando saúde dos daemons

Gerenciamento de baseline temporal:
- `_get_current_baseline_snapshot()` — Captura snapshot de performance do modelo
- `_check_meta_shift()` — Detecta degradação significativa de performance requerendo intervenção

### Gerenciamento de Assets
- `asset_manager.py` — SmartAsset (lazy loading), AssetAuthority (registro centralizado), MapAssetManager
- `map_manager.py` — Wrapper MapManager para carregamento de assets UI (interface recomendada sobre acesso direto ao AssetAuthority)

### Inteligência Espacial
- `spatial_data.py` — MapMetadata para 9 mapas CS2 com sistemas de coordenadas, Z-cutoffs para mapas multi-nível (Nuke, Vertigo)
- `spatial_engine.py` — SpatialEngine fornecendo mapeamento de coordenadas pixel-accurate e classificação de zona

### Reprodução de Demo
- `playback_engine.py` — InterpolatedPlayerState, InterpolatedFrame, PlaybackEngine para reprodução suave de demo com interpolação de frames

### Configuração & Persistência
- `config.py` — Gerenciamento de configuração com resolução de caminhos, MATCH_DATA_PATH, API get_setting/save_user_setting
- `lifecycle.py` — AppLifecycleManager para sequenciamento gradual de inicialização/desligamento
- `integrity_manifest.json` — Manifesto de integridade de arquivos para verificações de integridade runtime RASP

### Estruturas de Dados
- `demo_frame.py` — Tipos de dados core: PlayerState, GhostState, NadeState, BombState, KillEvent, DemoFrame

### Infraestrutura
- `localization.py` — LocalizationManager com suporte para Inglês, Italiano, Português
- `registry.py` — ScreenRegistry para gerenciamento de ciclo de vida de telas Kivy
- `logger.py` — Configuração de logging estruturado com loggers em nível de módulo

## Padrões Críticos

### Resolução de Caminho Match Data
Sempre use `config.MATCH_DATA_PATH` para localização do banco de dados de partidas. Padrão é `PRO_DEMO_PATH/match_data/` com fallback para diretório in-project. Nunca faça hardcode de caminhos.

### Acesso Singleton
```python
from backend.storage.match_data_manager import get_match_data_manager

manager = get_match_data_manager()  # Instância singleton
```

Após mudanças de caminho, resete o singleton:
```python
from backend.storage.match_data_manager import reset_match_data_manager

reset_match_data_manager()
manager = get_match_data_manager()  # Nova instância com caminho atualizado
```

### Carregamento de Assets (UI)
```python
from core.map_manager import MapManager

map_manager = MapManager()
radar_path = map_manager.get_radar_image("de_dust2")
```

### Consultas Espaciais
```python
from core.spatial_engine import SpatialEngine

engine = SpatialEngine("de_dust2")
pixel_x, pixel_y = engine.world_to_pixel(world_x, world_y, world_z)
zone_name = engine.get_zone_at_position(world_x, world_y, world_z)
```
