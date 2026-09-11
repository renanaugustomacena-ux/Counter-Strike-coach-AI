# Sistemas Core

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autoridade:** `Programma_CS2_RENAN/core/`
Fundacao de runtime que fornece orquestracao de daemons, gerenciamento de
configuracao, inteligencia espacial e controle do ciclo de vida da aplicacao.

## Introducao

O pacote `core/` e o coracao do Macena CS2 Analyzer. Ele hospeda o Quad-Daemon
session engine que mantem o pipeline de analise em execucao, o sistema de
configuracao em tres niveis que resolve as configuracoes do usuario em runtime,
a camada de dados espaciais que mapeia todos os nove mapas competitivos do CS2
no espaco de coordenadas, e o lifecycle manager que garante a execucao em
instancia unica. Cada outro pacote no projeto depende de pelo menos um modulo
do `core/`. Nao confundir com `apps/qt_app/core/`, que hospeda os helpers
de UI do lado Qt (icones, geracao QSS, motor de temas) e tem seu proprio README.

## Inventario de Arquivos

| Arquivo | Proposito |
|---------|-----------|
| `session_engine.py` | Quad-Daemon Engine: Scanner, Digester, Teacher, Pulse |
| `config.py` | Resolucao de config em tres niveis (defaults, JSON, keyring) |
| `spatial_data.py` | `MapMetadata` para 9 mapas, suporte a niveis Z, transformacoes de coordenadas |
| `spatial_engine.py` | `SpatialEngine`: conversoes world-to-pixel e pixel-to-world |
| `known_maps.py` | SSOT de mapas conhecidos (CP0 #2): `KNOWN_MAP_NAMES`, `is_known_map()`, sniffing de nomes de arquivo |
| `tick_rate.py` | SSOT 26-NORM-01: `DEFAULT_TICK_RATE`, `resolve_tick_rate()` resolucao por-demo |
| `team_codes.py` | SSOT de normalizacao de lado de time (F-0025 / F-0016): `normalize_team()` mapeia vocabularios de time brutos (`'CT'`, `'TERRORIST'`, codigos numericos) para canonicos `'CT'` / `'T'` |
| `map_manager.py` | `MapManager`: carregamento de assets para UI com suporte assincrono Kivy (legacy) |
| `lifecycle.py` | `AppLifecycleManager`: lock de instancia unica (mutex Windows / lock nomeado POSIX), lancamento/parada de daemon |
| `constants.py` | Constantes globais (baseadas em segundos): FOV, duracoes de utilitarios, decaimento de memoria, janela de trade |
| `demo_frame.py` | Tipos de dados core: `PlayerState`, `GhostState`, `NadeState`, `DemoFrame` |
| `asset_manager.py` | `SmartAsset` (lazy loading), `AssetAuthority` (registro centralizado) |
| `playback_engine.py` | `PlaybackEngine`: replay de demo interpolado com blending de frames |
| `localization.py` | `LocalizationManager`: tabelas de strings em Ingles, Italiano, Portugues |
| `registry.py` | `ScreenRegistry` para registro de telas KivyMD (legacy; Qt e a UI ativa) |
| `lock_files.py` | Locks nomeados baseados em PID: concorrencia D-track / HLTV-track, instancia unica POSIX; liberacao ownership-aware (F-0009) |
| `map_callouts.py` | `NamedPositionRegistry`: traducao coordenadas-callout para mapas CS2 |
| `app_types.py` | Aliases de tipo e enums compartilhados em toda a aplicacao |
| `frozen_hook.py` | Hook de runtime PyInstaller para correcao de caminhos em build congelada |
| `integrity_manifest.json` | Manifesto de hash de arquivos para verificacao de integridade RASP |

## Quad-Daemon Engine (`session_engine.py`)

O session engine lanca quatro threads daemon mais um `IngestionWatcher`,
coordenados por sinais `threading.Event` e uma linha central `CoachState`
no banco de dados monolito.

```
+----------------------------------------------------+
|              run_session_loop()                     |
|                                                    |
|  1. init_database()                                |
|  2. BackupManager.create_checkpoint(               |
|         label="startup_auto")                      |
|  3. Init base de conhecimento (se vazia)           |
|  4. _monitor_stdin (deteccao de morte do parent)   |
|  5. Lancamento dos daemons:                        |
|                                                    |
|     +----------+  +-----------+  +---------+       |
|     | Scanner  |  | Digester  |  | Teacher |       |
|     | (Files)  |  | (Worker)  |  | (ML)    |       |
|     +----------+  +-----------+  +---------+       |
|          |              |              |            |
|     Scan de arq.   Consumo da fila Verificacao     |
|     ciclo 10s      Event-driven    retreino 5min   |
|                                                    |
|     +----------+                                   |
|     |  Pulse   |  Heartbeat a cada 5 segundos      |
|     +----------+                                   |
+----------------------------------------------------+
```

Um watchdog no loop keep-alive principal verifica a saude dos daemons a cada
30 segundos e reinicia qualquer thread daemon que morreu inesperadamente.

### Responsabilidades dos Daemons

- **Scanner (_scanner_daemon_loop):** Escaneia os diretorios de demos do usuario e pro
  a cada 10 segundos quando ativo. Chama `process_new_demos()` para enfileirar novos
  arquivos. Executa verificacoes periodicas de espaco em disco a cada 5 minutos.
  Reporta seu status sob a chave de estado `"hunter"`.

- **Digester (_digester_daemon_loop):** Consome a fila de ingestao um task por vez.
  Usa `_work_available_event` para despertar eficiente (evita polling).
  Processa demos pro com prioridade mais alta.

- **Teacher (_teacher_daemon_loop):** Verifica o gatilho de retreino a cada 300
  segundos -- pelo menos 10 samples pro na partida a frio, ou um crescimento de 10%
  sobre a ultima contagem treinada -- entao aciona `CoachTrainingManager.run_full_cycle()`.
  Tambem executa calibracao de beliefs e deteccao de meta-shift apos cada retreino.
  Respeita o `_TRAINING_LOCK` em nivel de modulo para prevenir treino concorrente.

- **Pulse (_pulse_daemon_loop):** Atualiza o timestamp `last_heartbeat` no
  `CoachState` a cada 5 segundos para provar a vivacidade do daemon para a UI.

### Protocolo de Shutdown

A morte do parent e detectada via fechamento da pipe stdin (`_monitor_stdin`).
O `_shutdown_event` e ativado, todos os daemons saem de seus loops, e os threads
sao joinados com um timeout de 5 segundos cada.

## Sistema de Configuracao (`config.py`)

Resolucao em tres niveis: defaults hardcoded, `user_settings.json` em disco, e
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
  Globais em nivel de modulo (CS2_PLAYER_NAME, STEAM_API_KEY, ...)
```

### Thread Safety

- `get_setting(key)` / `get_credential(key)` -- adquirem `_settings_lock`, sempre atualizados
- Globais em nivel de modulo (`CS2_PLAYER_NAME`, etc.) -- snapshot no import, **defasados em
  threads daemon**; use `get_setting()` ao inves
- `save_user_setting(key, value)` -- escrita atomica via arquivo tmp + `os.replace()`
- `set_secret(key, value)` -- retorna `False` ao inves de lancar excecao quando o keyring
  nao esta disponivel (F-0007); os chamadores recorrem ao armazenamento em disco
- `refresh_settings()` -- recarrega do disco sob lock, atualiza os globais

### Arquitetura de Caminhos

```
CORE_DB_DIR    = BASE_DIR/backend/storage/     (database.db SEMPRE aqui)
USER_DATA_ROOT = BRAIN_DATA_ROOT ou BASE_DIR   (modelos, logs, cache)
MATCH_DATA_PATH = PRO_DEMO_PATH/match_data/    (ou fallback in-project)
```

O banco de dados core permanece na pasta do projeto para portabilidade.
`BRAIN_DATA_ROOT` afeta apenas artefatos regeneraveis (modelos, logs, cache).

`get_pro_demo_base()` resolve o pool de demos pro: retorna o `PRO_DEMO_PATH`
configurado, auto-detecta montagens SSD realocadas sob `/media` quando o caminho
configurado esta ausente (DP-06), e caso contrario recorre ao diretorio
`backend/storage/` in-project -- nunca `$HOME` (F-0008). Um diretorio home nu
tambem e recusado como root shard de `MATCH_DATA_PATH`.

## Inteligencia Espacial

### spatial_data.py

Define `MapMetadata` (dataclass imutavel) para todos os nove mapas competitivos do CS2
com suporte a mapas multi-nivel (Nuke, Vertigo) via limiares de cutoff no eixo Z.

Funcoes principais:
- `get_map_metadata(map_name)` -- busca fuzzy com matching parcial e avisos de ambiguidade
- `get_map_metadata_for_z(map_name, z)` -- selecao automatica de nivel baseada na coordenada Z
- `compute_z_penalty(z_position, map_name)` -- penalidade normalizada [0, 1] para o vetor 25-dim
- `classify_vertical_level(z, map_name)` -- retorna "upper", "lower", "transition" ou "default"

A configuracao e carregada de `data/map_config.json` com fallbacks hardcoded em
`_FALLBACK_REGISTRY` (derivados dos arquivos overview de radar da Valve).

### spatial_engine.py

`SpatialEngine` fornece transformacao de coordenadas entre coordenadas de mundo
Source 2 e espaco de pixels da UI:

- `world_to_normalized()` -- coordenadas de mundo para espaco radar [0, 1]
- `normalized_to_pixel()` / `pixel_to_normalized()` -- escalonamento de viewport
- `world_to_pixel()` / `pixel_to_world()` -- atalhos de conversao direta

### known_maps.py

Autoridade unica para verificacoes "este e um mapa conhecido?" (map-SSOT, CP0 #2),
substituindo as listas divergentes por-ferramenta encontradas durante a auditoria:

- `KNOWN_MAP_NAMES` (11 nomes base) / `KNOWN_MAP_IDS` (com prefixo `de_`)
- `is_known_map(name)` -- aceita ambas as convencoes
- `sniff_map_from_text(text)` -- sniffing de nomes de arquivo longest-first via `MAP_NAME_RE`

O `SPATIAL_REGISTRY` de 9 mapas em `spatial_data.py` e um subconjunto deliberado
(mapas com geometria de radar calibrada), nao uma divergencia.

### constants.py

Constantes temporais globais, definidas **apenas em segundos**. As janelas em ticks sao
calculadas no ponto de uso a partir do tick rate por-demo (`resolve_tick_rate()` em
`tick_rate.py`) -- as antigas derivacoes de segundos-para-ticks no momento do import
foram removidas porque incorporavam `TICK_RATE = 64`. `TICK_RATE` permanece apenas como
alias legacy de `core.tick_rate.DEFAULT_TICK_RATE`.

| Constante | Segundos |
|-----------|----------|
| `SMOKE_DURATION_S` | 18.0 |
| `MOLOTOV_DURATION_S` | 7.0 |
| `FLASH_DURATION_S` | 2.0 |
| `MEMORY_DECAY_TAU_S` | 2.5 |
| `MEMORY_CUTOFF_S` | 7.5 |
| `TRADE_WINDOW_S` | 3.0 |

Tambem define `FOV_DEGREES = 90.0` e `Z_FLOOR_THRESHOLD = 200.0`.

## Ciclo de Vida da Aplicacao (`lifecycle.py`)

`AppLifecycleManager` garante execucao em instancia unica e gerencia o subprocesso
do session engine. No Windows a guarda e um mutex kernel nomeado; no POSIX e o lock
nomeado `lock_files` `app_single_instance` com recuperacao de PID morto, falhando em
modo fechado em qualquer erro de lock para proteger o banco de dados SQLite (F-0010):

- `ensure_single_instance()` -- retorna False se outra instancia detem o lock
- `launch_daemon()` -- spawna `session_engine.py` como subprocesso com pipe stdin para IPC
- `shutdown()` -- terminacao gradual com timeout de 3 segundos, depois force kill

Registrado como handler `atexit` para garantir limpeza na saida do processo.

## Pontos de Integracao

```
apps/qt_app/app.py ──> lifecycle.launch_daemon() ──> session_engine.run_session_loop()
                                              |
                                              +──> config.DATABASE_URL
                                              +──> config.get_setting()
                                              +──> spatial_data.get_map_metadata()
                                              +──> constants.TICK_RATE
```

## Notas de Desenvolvimento

- **Globais de config sao defasados em threads daemon.** Sempre use `get_setting()` ou
  `get_credential()` em threads de background. Imports em nivel de modulo capturam um
  snapshot que nunca e atualizado a menos que `refresh_settings()` execute.
- **Nunca faca hardcode de caminhos de match data.** Use `config.MATCH_DATA_PATH` que se
  resolve dinamicamente baseado na disponibilidade de `PRO_DEMO_PATH`.
- **Os dados espaciais suportam hot reload.** Chame `reload_spatial_config()` para forcar
  a releitura de `map_config.json` sem reiniciar a aplicacao.
- **O eixo Z importa.** Mapas multi-nivel (Nuke, Vertigo) requerem
  `get_map_metadata_for_z()` ao inves do simples `get_map_metadata()` para selecao
  correta do nivel.
- **O session engine monitora stdin.** Se o processo parent morre (pipe fecha),
  todos os daemons desligam automaticamente. Enviar "STOP" no stdin aciona saida gradual.
