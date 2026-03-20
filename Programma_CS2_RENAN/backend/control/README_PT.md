> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Control — Orquestracao da Aplicacao & Gerenciamento de Daemons

> **Autoridade:** Regra 2 (Soberania do Backend), Regra 6 (Governanca de Mudancas)

Este modulo contem o plano de controle central do Macena CS2 Analyzer. Gerencia o ciclo de vida de todos os daemons em background, saude do banco de dados, filas de ingestao e coordenacao de treinamento ML.

## Arquivos

| Arquivo | Finalidade | Classes Principais |
|---------|-----------|-------------------|
| `console.py` | Console de controle unificado — orquestrador singleton | `Console`, `ServiceSupervisor`, `SystemState` |
| `db_governor.py` | Auditoria de saude do banco de dados + auto-recuperacao | `DatabaseGovernor` |
| `ingest_manager.py` | Controlador de fila de ingestao (SINGLE/CONTINUOUS/TIMED) | `IngestionManager`, `IngestMode` |
| `ml_controller.py` | Ciclo de vida de treinamento ML com locks de seguranca cross-processo | `MLControlContext`, `TrainingStopRequested` |

## Estados do Sistema

IDLE ──> BOOTING ──> BUSY ──> IDLE
                       │
                       ├──> MAINTENANCE
                       └──> ERROR → SHUTTING_DOWN

## Arquitetura Tri-Daemon

| Daemon | Controller | Finalidade |
|--------|-----------|-----------|
| Hunter | ServiceSupervisor | Scraping de estatisticas profissionais HLTV (subprocesso) |
| Digester | IngestionManager | Parsing de demo + extracao de features (thread) |
| Teacher | MLController | Treinamento de rede neural (thread com file lock) |

## Funcionalidades Principais

- Console singleton: thread-safe, gerencia sequencias de inicializacao/encerramento
- DatabaseGovernor: audita armazenamento Tier 1/2/3, auto-recuperacao do DB HLTV a partir de backup
- IngestionManager: 3 modos (SINGLE, CONTINUOUS, TIMED), thread-safe com encerramento gracioso
- MLController: file lock cross-processo (training.lock), suporte a pausa/retomada/throttle
- Ordem dos locks: Console._lock > ServiceSupervisor._lock (previne deadlock)

## Notas de Desenvolvimento

- Console e um singleton — seguro para chamar de qualquer thread
- A excecao TrainingStopRequested fornece uma interrupcao limpa para treinamentos longos
- O throttling de recursos esta em ingestion/resource_manager.py, nao aqui
