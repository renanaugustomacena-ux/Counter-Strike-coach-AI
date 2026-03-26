# Pipelines de Ingestão de Demos

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Infraestrutura de ingestão de demos para demos CS2 profissionais e de usuário com integração Steam, validação de integridade e enriquecimento estatístico em nível de round.

## Estrutura de Diretório

```
ingestion/
├── __init__.py
├── demo_loader.py          # Orquestrador principal de carregamento de demos
├── integrity.py            # Validação de integridade de arquivo demo
├── steam_locator.py        # Descoberta de instalação Steam
├── cache/                  # Cache de demos processadas (arquivos .mcn)
├── pipelines/              # Implementações de pipeline de ingestão
│   ├── user_ingest.py      # Pipeline de ingestão de demo de usuário
│   └── json_tournament_ingestor.py  # Importação em lote de JSON de torneio
└── registry/               # Rastreamento e ciclo de vida de arquivo demo
    ├── lifecycle.py         # Máquina de estados do ciclo de vida demo
    ├── registry.py          # Registro de arquivo demo
    └── schema.sql           # Schema de banco de dados do registro
```

## Componentes Principais

### Orquestradores Principais

**`demo_loader.py`** — Orquestrador principal de carregamento de demos
- Coordena parsing de arquivo demo com demoparser2
- Validação de integridade via `integrity.py`
- Delega para implementações de pipeline com base na fonte da demo
- Rastreamento de progresso e recuperação de erros

**`steam_locator.py`** — Descoberta de instalação Steam
- Detecção de instalação CS2 multiplataforma (Windows, Linux, macOS)
- Parsing de registro (Windows) e varredura de sistema de arquivos
- Auto-detecção de pasta de demos

**`integrity.py`** — Validação de integridade de arquivo demo
- Verificação de formato de arquivo (magic bytes PBDEMS2)
- Parsing de cabeçalho e validação de tamanho
- Detecção de corrupção

## Sub-Pacotes

### `pipelines/`

**`user_ingest.py`** — Pipeline de ingestão de demo de usuário
- Parsing de demos de usuário via demoparser2
- Extração de estatísticas de round com `round_stats_builder.py`
- Enriquecimento com `enrich_from_demo()` (kills noscope/blind, flash assists, uso de utilitários)
- Persistência em tabelas RoundStats + PlayerMatchStats

**`json_tournament_ingestor.py`** — Ingestão em lote de JSON de torneio
- Importação em massa de exportações de dados de torneio
- Validação de schema
- Resolução de conflitos

### `registry/`

Registro de arquivo demo e gerenciamento de ciclo de vida.

**`registry.py`** — Rastreamento de arquivo demo
- Rastreia estado de processamento demo (pending, processing, completed, failed)
- Detecção de duplicatas via hash de arquivo
- Interface de consulta para status de demo

**`lifecycle.py`** — Máquina de estados do ciclo de vida demo
- Transições de estado para processamento demo
- Aplicação de políticas de retenção
- Automação de limpeza

**`schema.sql`** — Definição de schema de banco de dados do registro

### `cache/`

Diretório de cache de demos processadas. Armazena arquivos intermediários `.mcn` para evitar re-parsing de demos previamente processadas.

## Notas Importantes

- O **scraping HLTV** reside em `backend/data_sources/hltv/`, NÃO neste pacote
- A função principal de orquestração de ingestão `_ingest_single_demo()` reside em `run_ingestion.py` na raiz do pacote
- A ingestão de demo profissional usa o mesmo pipeline central das demos de usuário, com enriquecimento estatístico adicional
- A descoberta de demos e processamento em lote são gerenciados por `batch_ingest.py` na raiz do projeto
