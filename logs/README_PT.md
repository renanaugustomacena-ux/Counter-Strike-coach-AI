> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Logs de Sistema Centralizados

Este diretorio coleta logs de runtime do tooling operador na raiz do repo (o operador Goliath, o console de desenvolvedor, ferramentas de manutencao) e serve como sink de fallback para a stack de logging do backend. A aplicacao em si resolve seu diretorio de log a partir da configuracao (`LOG_DIR = <USER_DATA_ROOT>/logs`, padrao `Programma_CS2_RENAN/logs`, sobreponivel via `BRAIN_DATA_ROOT` / `CUSTOM_STORAGE_PATH`), entao o `cs2_analyzer.log` primario normalmente vai para la, nao aqui.

## Visao Geral Tecnica

A arquitetura de logging e projetada para monitoramento de alta granularidade do backend do coach de Counter-Strike. O logging e configurado por `Programma_CS2_RENAN/observability/logger_setup.py`: todos os loggers compartilham um unico sink `cs2_analyzer.log` (saida JSON estruturada, parseavel por maquina), e execucoes standalone de tools adicionalmente gravam logs JSON com timestamp sob `tools/`. `core/config.py` conecta o `LOG_DIR` resolvido no `logger_setup` via `configure_log_dir()`; scripts que usam `logger_setup` sem essa conexao recaem no caminho relativo `logs/` — este diretorio, quando executados da raiz do repo. O objetivo principal e garantir que gargalos de desempenho, falhas de ingestao e desvios de modelo sejam identificados e resolvidos rapidamente.

## Componentes Chave

Todos os arquivos abaixo sao gerados em runtime e gitignored (apenas os READMEs sao rastreados):

- **`cs2_analyzer.log`**: Copia de fallback do log principal backend/analise (linhas JSON: erros com stack traces, eventos de parsing e ingestao por demo). A copia primaria reside em `<USER_DATA_ROOT>/logs/`.
- **`tools/`**: Logs JSON por-tool das execucoes (`<nome_tool>_<YYYYMMDD_HHMMSS>.json`) de `get_tool_logger()`, criados quando tools CLI (ex. `tools/build_pipeline.py`) sao executados da raiz do repo.
- **`goliath_master_<YYYYMMDD>.json`**: Log master diario do operador Goliath (`goliath.py`), concatenado entre execucoes.
- **`spawn_<tool>_<HHMMSS>.log`**: stderr de tools em background lancados via comando `svc spawn` do console (`console.py`).
- **`wipe_audit_<YYYYMMDD>.jsonl`**: Trilha de auditoria append-only escrita por `tools/wipe_for_reingest_safe.py` para cada operacao de wipe/restore.

## Estrutura do Diretorio

```text
logs/
├── cs2_analyzer.log              # Log fallback backend/analise (gerado em runtime)
├── tools/                        # Logs JSON com timestamp de execucoes de tools (gerados)
├── goliath_master_<date>.json    # Log master diario do operador Goliath (gerado)
├── spawn_<tool>_<time>.log       # stderr de tools em background lancados pelo console (gerados)
├── wipe_audit_<date>.jsonl       # Trilha de auditoria wipe/restore (gerado)
├── README.md                     # Esta documentacao
├── README_IT.md                  # Versao Italiana
└── README_PT.md                  # Versao Portuguesa
```

## Uso

### Monitoramento em Tempo Real
Para monitorar os logs do sistema em tempo real durante uma sessao de ingestao ou treinamento em larga escala:
```bash
tail -f logs/cs2_analyzer.log
```

### Rotacao de Log
Um `RotatingFileHandler` rotaciona `cs2_analyzer.log` a 5 MB, mantendo 3 versoes historicas (ex. `cs2_analyzer.log.1`) para evitar o esgotamento do espaco em disco. Se o handler nao pode ser criado (PermissionError), o setup recai em um `FileHandler` simples (sem rotacao). Cada processo grava seu proprio arquivo de log (indexado pela variavel de ambiente `CS2_LOG_ROLE`), entao cada rotating handler tem um unico writer. Os outros arquivos aqui (`goliath_master_*`, `spawn_*`, `wipe_audit_*`) nao sao rotacionados; `configure_retention()` em `logger_setup.py` pode eliminar arquivos `.log`/`.json` com mais de 30 dias.

### Filtragem por Erros
Para identificar rapidamente problemas criticos nos logs:
```bash
grep "ERROR" logs/cs2_analyzer.log
```
