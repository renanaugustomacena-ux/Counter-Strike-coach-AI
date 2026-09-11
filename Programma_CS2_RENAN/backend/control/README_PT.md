> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Control — Orquestracao da Aplicacao & Gerenciamento de Daemons

> **Autoridade:** Rule 2 (Soberania do Backend), Rule 6 (Governanca de Mudancas)
> **Skill:** `/state-audit`, `/resilience-check`

Este modulo contem o plano de controle central do Macena CS2 Analyzer. Gerencia o ciclo de vida de todos os daemons em background, a saude do banco de dados, as filas de ingestao e a coordenacao de treinamento ML.

## Inventario de Arquivos

| Arquivo | Finalidade | Classes Principais |
|---------|-----------|-------------------|
| `console.py` | Console de controle unificado — orquestrador singleton | `Console`, `ServiceSupervisor`, `SystemState`, `ServiceStatus` |
| `db_governor.py` | Auditoria de saude do banco de dados + auto-recuperacao | `DatabaseGovernor` |
| `ingest_manager.py` | Controlador de fila de ingestao (SINGLE/CONTINUOUS/TIMED) | `IngestionManager`, `IngestMode` |
| `ml_controller.py` | Ciclo de vida de treinamento ML com locks de seguranca | `MLController`, `MLControlContext`, `TrainingStopRequested` |

## Estados do Sistema

`_compute_state()` avalia uma cascata de prioridade — a primeira condicao
correspondente vence:

1. **SHUTTING_DOWN** — flag `_shutting_down` definido
2. **BOOTING** — flag `_booting` definido
3. **ERROR** — falha de integridade do DB, um servico supervisionado crashou,
   ou um daemon CoachState tem status `"Error"`
4. **BUSY** — treinamento ML ou ingestao ativamente em execucao
5. **IDLE** — fallthrough padrao

MAINTENANCE e definido no enum `SystemState` mas atualmente nunca e
atribuido por `_compute_state()`.

## Sequencia de Inicializacao

O singleton `Console` orquestra a inicializacao (`boot()`):

```
1. Inicio do daemon Hunter (somente se ENABLE_HLTV_SYNC=true)
   |-- docker_manager.ensure_flaresolverr()
   +-- ServiceSupervisor.start_service("hunter")
       (pulado com notificacao ao usuario se Docker nao esta disponivel)
2. init_database() — cria tabelas/colunas ausentes
3. Auditoria DatabaseGovernor
   |-- audit_storage(): Tier 1/2 (DB monolitico + WAL), Tier 3 (DBs por partida)
   |-- Auto-restore hltv_metadata.db a partir de .bak se ausente
   +-- verify_integrity() — define estado ERROR em falha do monolito
4. Aplicacao de retencao de logs (OBS-06)
5. Confianca de belief calculada a partir da contagem de PlayerMatchStats
   (IngestionManager e MLController iniciam sob demanda, nao no boot)
```

## Sequencia de Encerramento

```
1. Parar MLController (solicitar parada do treinamento)
2. Parar IngestionManager (sinalizar evento de parada)
3. Parar Hunter via ServiceSupervisor
   +-- terminate() com timeout de 5s -> kill()
4. Parar container FlareSolverr (docker stop)
5. Espera de drenagem: ate 5s para ML/ingestao reportarem parada
6. Estado definido como Offline (idempotente — seguro chamar duas vezes)
```

## Arquitetura Tri-Daemon

O `Console` gerencia tres tipos de daemons:

| Daemon | Controller | Finalidade |
|--------|-----------|-----------|
| **Hunter** | `ServiceSupervisor` | Scraping de estatisticas profissionais HLTV (subprocesso) |
| **Digester** | `IngestionManager` | Parsing de demo + extracao de features (thread) |
| **Teacher** | `MLController` | Treinamento de rede neural (thread com lock in-process) |

### ServiceSupervisor (Hunter)

- Inicia o Hunter como subprocesso com configuracao de `PYTHONPATH`
- Auto-restart: maximo de 3 tentativas com atraso fixo de 5s para restart
- Janela de reset de tentativas: 3600s (reseta o contador se nenhum crash em 1 hora)
- Thread de monitoramento observa a saida do subprocesso com timeout de 3600s
- Cancela timers de restart pendentes ao parar (previne spawns duplicados)

### IngestionManager (Digester)

Tres modos operacionais:
- **SINGLE**: Processa uma demo, depois para
- **CONTINUOUS**: Processa todas as demos, depois aguarda e reescaneia
- **TIMED**: Reescaneia a cada N minutos (padrao 30)

Thread-safe com `threading.Event` para encerramento gracioso. Processa no maximo 10 demos por ciclo (WR-07, `_MAX_BATCH_SIZE`) para prevenir uso excessivo de CPU. Reporta status: contagens de enfileirados/em processamento/falhos.

### MLController (Teacher)

- `MLControlContext`: Token de controle passado para os loops de treinamento
  - `check_state()`: Chamado a cada batch — lanca `TrainingStopRequested` ao parar
  - Suporte a pausa com `Event.wait()` (sem espera ativa)
  - Fator de throttle: 0.0 (velocidade maxima) a 1.0 (atraso maximo)
- **Lock threading in-process** (`_TRAINING_LOCK`): `MLController.start_training()`
  adquire este `threading.Lock` a nivel de modulo para prevenir treinamento
  concorrente dentro do mesmo processo. Nao-bloqueante: retorna imediatamente
  se o lock esta mantido.
- **File lock cross-processo** (`training_file_lock()`): Context manager exportado
  que bloqueia `DATA_DIR/training.lock` via `fcntl`/`msvcrt` para seguranca
  cross-processo. Atualmente nao chamado pelo `MLController` em si — disponivel para
  chamadores externos que necessitam de coordenacao entre processos.

## Ordem dos Locks (Critico)

```
Console._lock  >  ServiceSupervisor._lock
```

O Console nunca adquire o lock do ServiceSupervisor enquanto mantem o seu proprio, e vice-versa. Violar essa ordem arrisca um deadlock.

## Notas de Desenvolvimento

- `Console` e um singleton — seguro para chamar de qualquer thread
- Todos os metodos publicos do `Console` sao thread-safe
- `DatabaseGovernor.audit_storage()` retorna uma lista de anomalias para logging
- O enum `IngestMode` previne strings de modo invalidas
- A excecao `TrainingStopRequested` fornece um mecanismo de interrupcao limpa para treinamentos longos
- O throttling de recursos esta em `backend/ingestion/resource_manager.py`, nao aqui
