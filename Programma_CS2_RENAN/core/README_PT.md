# Sistemas Core

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autoridade:** `Programma_CS2_RENAN/core/`
Fundação de runtime que fornece orquestração de daemons, gerenciamento de
configuração, inteligência espacial e controle do ciclo de vida da aplicação.

## Introdução

O pacote `core/` é o coração do Macena CS2 Analyzer. Ele hospeda o Quad-Daemon
session engine que mantém o pipeline de análise em execução, o sistema de
configuração em três níveis que resolve as configurações do usuário em runtime,
a camada de dados espaciais que mapeia todos os nove mapas competitivos do CS2
no espaço de coordenadas, e o lifecycle manager que garante a execução em
instância única. Cada outro pacote no projeto depende de pelo menos um módulo
do `core/`.

## Inventário de Arquivos

| Arquivo | Propósito |
|---------|-----------|
| `session_engine.py` | Quad-Daemon Engine: Hunter, Digester, Teacher, Pulse |
| `config.py` | Resolução de config em três níveis (defaults, JSON, keyring) |
| `spatial_data.py` | `MapMetadata` para 9 mapas, suporte a níveis Z, transformações de coordenadas |
| `spatial_engine.py` | `SpatialEngine`: conversões world-to-pixel e pixel-to-world |
| `map_manager.py` | `MapManager`: carregamento de assets para UI com suporte assíncrono Kivy |
| `lifecycle.py` | `AppLifecycleManager`: mutex de instância única, lançamento/parada de daemon |
| `constants.py` | Constantes globais: tick rate, FOV, durações de utilitários, janela de trade |
| `demo_frame.py` | Tipos de dados core: `PlayerState`, `GhostState`, `NadeState`, `DemoFrame` |
| `asset_manager.py` | `SmartAsset` (lazy loading), `AssetAuthority` (registro centralizado) |
| `playback.py` | `TimelineController`: controlador centralizado Kivy para playback de partida |
| `playback_engine.py` | `PlaybackEngine`: replay de demo interpolado com blending de frames |
| `localization.py` | `LocalizationManager`: tabelas de strings em Inglês, Italiano, Português |
| `platform_utils.py` | Detecção de drives cross-platform (Windows, Linux, macOS) |
| `registry.py` | `ScreenRegistry` para gerenciamento de ciclo de vida de telas Kivy |
| `logger.py` | Setup de logging estruturado com loggers em nível de módulo |
| `app_types.py` | Aliases de tipo e enums compartilhados em toda a aplicação |
| `frozen_hook.py` | Hook de runtime PyInstaller para correção de caminhos em build congelada |
| `integrity_manifest.json` | Manifesto de hash de arquivos para verificação de integridade RASP |

## Quad-Daemon Engine (`session_engine.py`)

O session engine lança quatro threads daemon mais um `IngestionWatcher`,
coordenados por sinais `threading.Event` e uma linha central `CoachState`
no banco de dados monólito.

```
+----------------------------------------------------+
|              run_session_loop()                     |
|                                                    |
|  1. init_database()                                |
|  2. BackupManager.create_checkpoint("startup")     |
|  3. Init base de conhecimento (se vazia)           |
|  4. _monitor_stdin (detecção de morte do parent)   |
|  5. Lançamento dos daemons:                        |
|                                                    |
|     +----------+  +-----------+  +---------+       |
|     |  Hunter  |  | Digester  |  | Teacher |       |
|     | (Scanner)|  | (Worker)  |  | (ML)    |       |
|     +----------+  +-----------+  +---------+       |
|          |              |              |            |
|     Scan de arq.   Consumo da fila Verificação     |
|     ciclo 10s      Event-driven    retreino 5min   |
|                                                    |
|     +----------+                                   |
|     |  Pulse   |  Heartbeat a cada 5 segundos      |
|     +----------+                                   |
+----------------------------------------------------+
```

### Responsabilidades dos Daemons

- **Hunter (_scanner_daemon_loop):** Escaneia os diretórios de demos do usuário e pro
  a cada 10 segundos quando ativo. Chama `process_new_demos()` para enfileirar novos
  arquivos. Executa verificações periódicas de espaço em disco a cada 5 minutos.

- **Digester (_digester_daemon_loop):** Consome a fila de ingestão um task por vez.
  Usa `_work_available_event` para despertar eficiente (evita polling).
  Processa demos pro com prioridade mais alta.

- **Teacher (_teacher_daemon_loop):** Verifica se os novos samples pro ultrapassam o
  limiar de crescimento de 10%, então aciona `CoachTrainingManager.run_full_cycle()`.
  Também executa calibração de beliefs e detecção de meta-shift após cada retreino.
  Respeita o `_TRAINING_LOCK` em nível de módulo para prevenir treino concorrente.

- **Pulse (_pulse_daemon_loop):** Atualiza o timestamp `last_heartbeat` no
  `CoachState` a cada 5 segundos para provar a vivacidade do daemon para a UI.

### Protocolo de Shutdown

A morte do parent é detectada via fechamento da pipe stdin (`_monitor_stdin`).
O `_shutdown_event` é ativado, todos os daemons saem de seus loops, e os threads
são joinados com um timeout de 5 segundos cada.

## Sistema de Configuração (`config.py`)

Resolução em três níveis: defaults hardcoded, `user_settings.json` em disco, e
keyring do SO para segredos (chave API Steam, chave API Faceit).

```
  Defaults hardcoded (load_user_settings)
            |
            v
  user_settings.json  (SETTINGS_PATH)
            |
            v
  Keyring do SO (keyring.get_password)
            |
            v
  Globais em nível de módulo (CS2_PLAYER_NAME, STEAM_API_KEY, ...)
```

### Thread Safety

- `get_setting(key)` / `get_credential(key)` -- adquirem `_settings_lock`, sempre atualizados
- Globais em nível de módulo (`CS2_PLAYER_NAME`, etc.) -- snapshot no import, **defasados em
  threads daemon**; use `get_setting()` ao invés
- `save_user_setting(key, value)` -- escrita atômica via arquivo tmp + `os.replace()`
- `refresh_settings()` -- recarrega do disco sob lock, atualiza os globais

### Arquitetura de Caminhos

```
CORE_DB_DIR    = BASE_DIR/backend/storage/     (database.db SEMPRE aqui)
USER_DATA_ROOT = BRAIN_DATA_ROOT ou BASE_DIR   (modelos, logs, cache)
MATCH_DATA_PATH = PRO_DEMO_PATH/match_data/    (ou fallback in-project)
```

O banco de dados core permanece na pasta do projeto para portabilidade.
`BRAIN_DATA_ROOT` afeta apenas artefatos regeneráveis (modelos, logs, cache).

## Inteligência Espacial

### spatial_data.py

Define `MapMetadata` (dataclass imutável) para todos os nove mapas competitivos do CS2
com suporte a mapas multi-nível (Nuke, Vertigo) via limiares de cutoff no eixo Z.

Funções principais:
- `get_map_metadata(map_name)` -- busca fuzzy com matching parcial e avisos de ambiguidade
- `get_map_metadata_for_z(map_name, z)` -- seleção automática de nível baseada na coordenada Z
- `compute_z_penalty(z_position, map_name)` -- penalidade normalizada [0, 1] para o vetor 25-dim
- `classify_vertical_level(z, map_name)` -- retorna "upper", "lower", "transition" ou "default"

A configuração é carregada de `data/map_config.json` com fallbacks hardcoded em
`_FALLBACK_REGISTRY` (derivados dos arquivos overview de radar da Valve).

### spatial_engine.py

`SpatialEngine` fornece transformação de coordenadas entre coordenadas de mundo
Source 2 e espaço de pixels da UI:

- `world_to_normalized()` -- coordenadas de mundo para espaço radar [0, 1]
- `normalized_to_pixel()` / `pixel_to_normalized()` -- escalonamento de viewport
- `world_to_pixel()` / `pixel_to_world()` -- atalhos de conversão direta

### constants.py

Constantes temporais globais derivadas de `TICK_RATE = 64`:

| Constante | Segundos | Ticks |
|-----------|----------|-------|
| `SMOKE_DURATION` | 18.0 | 1152 |
| `MOLOTOV_DURATION` | 7.0 | 448 |
| `FLASH_DURATION` | 2.0 | 128 |
| `MEMORY_DECAY_TAU` | 2.5 | 160 |
| `MEMORY_CUTOFF` | 7.5 | 480 |
| `TRADE_WINDOW` | 3.0 | 192 |

## Ciclo de Vida da Aplicação (`lifecycle.py`)

`AppLifecycleManager` garante execução em instância única (mutex nomeado Windows)
e gerencia o subprocesso do session engine:

- `ensure_single_instance()` -- retorna False se outra instância detém o mutex
- `launch_daemon()` -- spawna `session_engine.py` como subprocesso com pipe stdin para IPC
- `shutdown()` -- terminação gradual com timeout de 3 segundos, depois force kill

Registrado como handler `atexit` para garantir limpeza na saída do processo.

## Pontos de Integração

```
main.py ──> lifecycle.launch_daemon() ──> session_engine.run_session_loop()
                                              |
                                              +──> config.DATABASE_URL
                                              +──> config.get_setting()
                                              +──> spatial_data.get_map_metadata()
                                              +──> constants.TICK_RATE
```

## Notas de Desenvolvimento

- **Globais de config são defasados em threads daemon.** Sempre use `get_setting()` ou
  `get_credential()` em threads de background. Imports em nível de módulo capturam um
  snapshot que nunca é atualizado a menos que `refresh_settings()` execute.
- **Nunca faça hardcode de caminhos de match data.** Use `config.MATCH_DATA_PATH` que se
  resolve dinamicamente baseado na disponibilidade de `PRO_DEMO_PATH`.
- **Os dados espaciais suportam hot reload.** Chame `reload_spatial_config()` para forçar
  a releitura de `map_config.json` sem reiniciar a aplicação.
- **O eixo Z importa.** Mapas multi-nível (Nuke, Vertigo) requerem
  `get_map_metadata_for_z()` ao invés do simples `get_map_metadata()` para seleção
  correta do nível.
- **O session engine monitora stdin.** Se o processo parent morre (pipe fecha),
  todos os daemons desligam automaticamente. Enviar "STOP" no stdin aciona saída gradual.
