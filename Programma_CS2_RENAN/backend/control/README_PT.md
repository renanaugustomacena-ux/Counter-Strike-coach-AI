> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Control — Orquestração da Aplicação & Gerenciamento de Daemons

> **Autoridade:** Rule 2 (Soberania do Backend), Rule 6 (Governança de Mudanças)
> **Skill:** `/state-audit`, `/resilience-check`

Este módulo contém o plano de controle central do Macena CS2 Analyzer. Gerencia o ciclo de vida de todos os daemons em background, a saúde do banco de dados, as filas de ingestão e a coordenação de treinamento ML.

## Inventário de Arquivos

| Arquivo | Finalidade | Classes Principais |
|---------|-----------|-------------------|
| `console.py` | Console de controle unificado — orquestrador singleton | `Console`, `ServiceSupervisor`, `SystemState`, `ServiceStatus` |
| `db_governor.py` | Auditoria de saúde do banco de dados + auto-recuperação | `DatabaseGovernor` |
| `ingest_manager.py` | Controlador de fila de ingestão (SINGLE/CONTINUOUS/TIMED) | `IngestionManager`, `IngestMode` |
| `ml_controller.py` | Ciclo de vida de treinamento ML com locks de segurança cross-processo | `MLControlContext`, `TrainingStopRequested` |

## Estados do Sistema

```
IDLE ──> BOOTING ──> BUSY ──> IDLE
                       │
                       ├──> MAINTENANCE
                       └──> ERROR
                             │
                             └──> SHUTTING_DOWN
```

## Sequência de Inicialização

O singleton `Console` orquestra a inicialização:

```
1. DatabaseGovernor.audit_storage()
   ├── Verificar Tier 1/2 (DB monolítico + WAL)
   ├── Verificar Tier 3 (DBs por partida)
   └── Auto-recuperar DB HLTV a partir de .bak se ausente
2. Inicialização do StateManager
3. Início do ServiceSupervisor
   └── Iniciar daemon Hunter (sincronização HLTV)
4. Início do IngestionManager
   └── Começar varredura de demos
5. Pronto para MLController (treinamento sob demanda)
```

## Sequência de Encerramento

```
1. Parar IngestionManager (drenar fila)
2. Parar MLController (salvar checkpoint)
3. Parar ServiceSupervisor
   └── terminate() com timeout de 5s → kill()
4. Salvar estado
```

## Arquitetura Tri-Daemon

O `Console` gerencia três tipos de daemons:

| Daemon | Controller | Finalidade |
|--------|-----------|-----------|
| **Hunter** | `ServiceSupervisor` | Scraping de estatísticas profissionais HLTV (subprocesso) |
| **Digester** | `IngestionManager` | Parsing de demo + extração de features (thread) |
| **Teacher** | `MLController` | Treinamento de rede neural (thread com file lock) |

### ServiceSupervisor (Hunter)

- Inicia o Hunter como subprocesso com configuração de `PYTHONPATH`
- Auto-restart: máximo de 3 tentativas com backoff exponencial
- Janela de reset de tentativas: 3600s (reseta o contador se nenhum crash em 1 hora)
- Thread de monitoramento observa a saída do subprocesso com timeout de 3600s
- Cancela timers de restart pendentes ao parar (previne spawns duplicados)

### IngestionManager (Digester)

Três modos operacionais:
- **SINGLE**: Processa uma demo, depois para
- **CONTINUOUS**: Processa todas as demos, depois aguarda e reescaneia
- **TIMED**: Reescaneia a cada N minutos (padrão 30)

Thread-safe com `threading.Event` para encerramento gracioso. Reporta status: contagens de enfileirados/em processamento/falhos.

### MLController (Teacher)

- `MLControlContext`: Token de controle passado para os loops de treinamento
  - `check_state()`: Chamado a cada batch — lança `TrainingStopRequested` ao parar
  - Suporte a pausa com `Event.wait()` (sem espera ativa)
  - Fator de throttle: 0.0 (velocidade máxima) a 1.0 (atraso máximo)
- **File lock cross-processo** (`training.lock`): Impede treinamento concorrente
  - Utiliza `fcntl` (Unix) / `msvcrt` (Windows)
  - Não-bloqueante: lança `RuntimeError` se o lock está mantido
  - Rastreamento baseado em PID para debugging

## Ordem dos Locks (Crítico)

```
Console._lock  >  ServiceSupervisor._lock
```

O Console nunca adquire o lock do ServiceSupervisor enquanto mantém o seu próprio, e vice-versa. Violar essa ordem arrisca um deadlock.

## Notas de Desenvolvimento

- `Console` é um singleton — seguro para chamar de qualquer thread
- Todos os métodos públicos do `Console` são thread-safe
- `DatabaseGovernor.audit_storage()` retorna uma lista de anomalias para logging
- O enum `IngestMode` previne strings de modo inválidas
- A exceção `TrainingStopRequested` fornece um mecanismo de interrupção limpa para treinamentos longos
- O throttling de recursos está em `ingestion/resource_manager.py`, não aqui
