> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Backend Ingestion — Monitoramento de Arquivos, Governanca de Recursos & Migracao CSV

> **Autoridade:** Regra 2 (Soberania do Backend), Regra 4 (Persistencia de Dados)

Este modulo gerencia a camada de ingestao em tempo de execucao: monitoramento de novos arquivos demo em disco, governanca de recursos do sistema durante processamento em background e migracao de datasets CSV externos para o banco de dados.

Nota: Distinto do diretorio ingestion/ de nivel superior que lida com a orquestracao de pipeline multi-estagio. Este modulo fornece os componentes de baixo nivel.

## Arquivos

| Arquivo | Finalidade | Classes Principais |
|---------|-----------|-------------------|
| `watcher.py` | Monitor do filesystem para arquivos .dem | `DemoFileHandler` |
| `resource_manager.py` | Throttling de CPU/RAM para tarefas em background | `ResourceManager` |
| `csv_migrator.py` | Importacao de CSV externo em tabelas SQLModel | `CSVMigrator` |

## watcher.py — Monitor de Arquivos Demo

Utiliza watchdog para observar diretorios em busca de novos arquivos .dem. Debouncing de estabilidade previne a leitura de arquivos parcialmente escritos. Prevencao de duplicatas via verificacao na tabela IngestionTask.

## resource_manager.py — Throttling de Carga do Sistema

Throttling de CPU baseado em histerese: inicio em 85%, parada em 70%. Media movel de 10 segundos. HP_MODE=1 para desabilitar o throttling.

## csv_migrator.py — Importacao de Dados Externos

Migra arquivos CSV externos para tabelas do banco de dados SQLModel. Idempotente, tratamento de UTF-8 com BOM, parsing seguro.

## Notas de Desenvolvimento

- watcher.py requer o pacote watchdog
- ResourceManager e uma classe de utilidade estatica
- A variavel de ambiente HP_MODE e apenas para desenvolvimento
