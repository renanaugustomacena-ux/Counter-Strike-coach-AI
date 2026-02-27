# Registro de Arquivos de Demo & Gerenciamento de Ciclo de Vida

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Visão Geral

Rastreamento de registro de arquivos de demo e gerenciamento de estados de ciclo de vida. Previne ingestão duplicada, rastreia status de processamento e fornece trilha de auditoria para todas as operações de arquivos de demo.

## Componentes Principais

### `registry.py`
- **Registro de arquivos de demo** — Registra todos os arquivos de demo descobertos na tabela `DemoFileRecord`
- **Detecção de duplicatas** — Verificação de hash de arquivo previne processamento redundante
- **Rastreamento de metadados** — Tamanho de arquivo, timestamp de descoberta, tipo de fonte (user/pro/tournament)
- **Interface de consulta** — Recupera arquivos por status, fonte, intervalo de datas

### `lifecycle.py`
- **Implementação de máquina de estados** — Gerencia ciclo de vida de processamento de demo
- **Estados**: `discovered` → `queued` → `processing` → `completed` | `failed`
- **Transições de estado atômicas** — Transações de banco de dados garantem consistência
- **Tratamento de estado de erro** — Arquivos falhados marcados com código de erro e contador de retry

## Estados do Ciclo de Vida

1. **Discovered** — Arquivo encontrado durante varredura de diretório, ainda não validado
2. **Queued** — Validado e pronto para ingestão, aguardando slot de processamento
3. **Processing** — Atualmente sendo analisado e ingerido
4. **Completed** — Ingestão bem-sucedida, todos os dados derivados persistidos
5. **Failed** — Ingestão falhou, erro logado, marcado para revisão manual

## Integração

Usado por todas as pipelines de ingestão (`user_ingest.py`, `pro_ingest.py`, `json_tournament_ingestor.py`) para:
- Verificar se arquivo já foi processado antes de iniciar ingestão
- Atualizar status de processamento em tempo real
- Marcar conclusão ou falha com contexto de erro detalhado

## Consultas ao Registro

- `get_pending_files()` — Retorna todos os arquivos em estado `discovered` ou `queued`
- `get_failed_files()` — Retorna arquivos que falharam ingestão com detalhes de erro
- `get_completed_files(source_type, date_range)` — Recupera arquivos processados com sucesso por critérios de filtro

## Tratamento de Erros

Ingestões falhadas incrementam contador de retry. Após 3 falhas, arquivo é marcado como permanentemente falhado e requer intervenção manual. Todos os erros logados com IDs de correlação para rastreabilidade.

## Schema do Banco de Dados

Tabela `DemoFileRecord` inclui:
- `file_path`, `file_hash`, `file_size`, `source_type`
- `lifecycle_state`, `error_code`, `retry_count`
- `discovered_at`, `queued_at`, `processing_started_at`, `completed_at`
