# Pipelines de Ingestao de Demos

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Infraestrutura de ingestao de demos para demos CS2 profissionais e de usuario com integracao Steam, validacao de integridade e enriquecimento estatistico em nivel de round.

## Estrutura de Diretorio

```
ingestion/
├── __init__.py
├── .validated_cache.json   # Artefato runtime legado; resetado apenas por tools/reset_pro_data.py (raiz do repo), nao escrito por este pacote
├── demo_loader.py          # Parser de demo em tres passadas com cache assinado
├── integrity.py            # Validacao de integridade de arquivo demo
├── steam_locator.py        # Descoberta de instalacao Steam
├── pipelines/              # Implementacoes de pipeline de ingestao
│   ├── user_ingest.py      # Pipeline de ingestao de demo de usuario
│   └── json_tournament_ingestor.py  # Importacao em lote de JSON de torneio
└── registry/               # Rastreamento e ciclo de vida de arquivo demo
    ├── lifecycle.py         # Limpeza de retencao de demos
    ├── registry.py          # Registro de arquivo demo
    └── schema.sql           # Reservado para um futuro registro SQL (atualmente vazio)
```

## Componentes Principais

### Orquestradores Principais

**`demo_loader.py`** -- `DemoLoader`, o parser de demo em tres passadas

- Passada 1: posicoes de jogador por tick; Passada 2: eventos/trajetorias de granadas; Passada 3: tick DataFrame -> objetos `DemoFrame`
- Parsing via demoparser2; tambem extrai round starts, eventos de bomba e kills
- Cache dos resultados parseados como arquivos pickle assinados com HMAC-SHA256 (`.mcn`)
  em um diretorio `demo_cache/` (recai para `ingestion/cache/`), criado em runtime; o
  carregamento usa um unpickler restrito (DS-01) e verifica a assinatura antes da
  desserializacao

**`steam_locator.py`** -- Descoberta de instalacao Steam

- Deteccao de instalacao CS2 multiplataforma (Windows, Linux)
- Parsing de registro (Windows) e varredura de sistema de arquivos, com fallback de varredura de drives
- Auto-deteccao de pasta de demos
- `sync_steam_demos()` enfileira cada demo recem-descoberta como uma linha `IngestionTask`

**`integrity.py`** -- Validacao de integridade de arquivo demo

- `validate_dem_file()` delega para `backend/data_sources/demo_format_adapter`
  (magic bytes PBDEMS2, limites de tamanho; demos CS:GO legadas rejeitadas)
- Helper `compute_sha256()` para hashing de arquivo
- Constantes de tamanho legadas 50 KB / 900 MB mantidas apenas para retrocompatibilidade

## Sub-Pacotes

### `pipelines/`

**`user_ingest.py`** -- Pipeline de ingestao de demo de usuario

- Parsing de demos de usuario via demoparser2
- Persiste PlayerMatchStats, depois RoundStats + enriquecimento via
  `round_stats_builder.persist_round_stats_and_enrichment()`
- Dispara a pipeline ML (`run_ml_pipeline` de `run_ingestion.py`) e
  arquiva a demo somente apos o sucesso de todas as etapas

**`json_tournament_ingestor.py`** -- Ingestao em lote de JSON de torneio

- Importacao em massa de exportacoes de dados de torneio
- Validacao de schema (`_validate_tournament_json`)
- Achatamento da hierarquia match/map/round em um CSV de estatisticas de time por-round

### `registry/`

Registro de arquivo demo e gerenciamento de ciclo de vida.

**`registry.py`** -- `DemoRegistry`, set JSON-backed de demos processadas

- `is_processed()` / `mark_processed()` com locking de thread + arquivo
- Escritas atomicas com recuperacao automatica de backup

**`lifecycle.py`** -- `DemoLifecycleManager`

- `cleanup_old_demos(days=30)` remove arquivos `.dem` arquivados alem da retencao

**`schema.sql`** -- Reservado para um futuro registro baseado em SQL (atualmente vazio)

## Notas Importantes

- O **scraping HLTV** reside em `backend/data_sources/hltv/`, NAO neste pacote
- A funcao principal de orquestracao de ingestao `_ingest_single_demo()` reside em `run_ingestion.py` na raiz do pacote
- O orquestrador de producao **nao** importa este pacote: `run_ingestion.py` parseia via
  `backend/data_sources/demo_parser` e usa `backend/ingestion/` (resource manager).
  Os consumidores deste pacote sao `Programma_CS2_RENAN/reporting/report_generator.py` e
  `apps/qt_app/screens/tactical_viewer_screen.py` (`DemoLoader`), `core/session_engine.py`
  (`steam_locator`), e a suite de testes (`integrity`)
- A ingestao de demo profissional usa o mesmo pipeline central das demos de usuario;
  demos pro parseiam todos os jogadores (target `"ALL"`) enquanto demos de usuario
  visam o `CS2_PLAYER_NAME` configurado
- A descoberta de demos e processamento em lote sao gerenciados por `run_ingestion.py`
  (`StorageManager.list_new_demos()` + a fila `IngestionTask`) e pelo worker
  long-running `run_worker.py`, ambos na raiz do pacote
