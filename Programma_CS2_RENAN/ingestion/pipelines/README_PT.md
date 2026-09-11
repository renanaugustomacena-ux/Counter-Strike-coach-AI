# Implementacoes de Pipeline de Ingestao

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autoridade:** `Programma_CS2_RENAN/ingestion/pipelines/`

## Introducao

Este pacote contem as pipelines de ingestao concretas que transformam fontes de
dados brutas em linhas estruturadas no banco de dados.  Cada pipeline trata um
formato de entrada especifico -- arquivos replay `.dem` de partidas do usuario
e exports JSON estruturados de bancos de dados de torneios.  As pipelines
compartilham um fluxo logico comum (discovery, validation, parsing, enrichment,
persistence, archival) mas divergem na logica de enriquecimento e nas tabelas
de destino.

## Inventario de Arquivos

| Arquivo | Finalidade | API Publica Principal |
|---------|------------|----------------------|
| `__init__.py` | Marcador de pacote (vazio) | -- |
| `user_ingest.py` | Pipeline de ingestao de demos do usuario | `ingest_user_demos(source_dir, processed_dir)` |
| `json_tournament_ingestor.py` | Processador batch de JSON de torneios | `process_tournament_jsons(json_dir, output_csv)` |
| `README.md` | Documentacao (Ingles) | -- |
| `README_IT.md` | Documentacao (Italiano) | -- |
| `README_PT.md` | Documentacao (Portugues) | -- |

## Arquitetura e Conceitos

### O Fluxo de Ingestao

Toda pipeline segue esta sequencia canonica.  Etapas podem ser implicitas em
pipelines mais simples, mas a ordem logica e sempre preservada:

1. **Discovery** -- varredura do diretorio fonte por arquivos nao processados
   (`.dem` ou `.json`).
2. **Validation** -- verificacao da integridade da entrada.  O piso de
   aceitacao para arquivos `.dem` (`MIN_DEMO_SIZE = 10 MB`, invariante DS-12)
   reside em `backend/data_sources/demo_format_adapter`; note que
   `user_ingest.py` em si nao realiza verificacao de tamanho --
   `parse_demo()` verifica apenas existencia e parseabilidade.  Para arquivos
   JSON o helper `_validate_tournament_json()` verifica as chaves top-level
   obrigatorias (`id`, `slug`, `match_maps`) e loga um warning para chaves
   per-map ausentes (`map_name`, `games`).
3. **Parsing** -- extracao de dados estruturados.  Arquivos demo sao parseados
   por `backend/data_sources/demo_parser.parse_demo()` (suportado por
   `demoparser2`).  Arquivos JSON sao carregados diretamente com
   `json.load()`.
4. **Enrichment** -- calculo de estatisticas derivadas.  A pipeline de usuario
   chama `extract_match_stats()` de `base_features.py`, depois persiste o
   enriquecimento em nivel de round via `round_stats_builder`.  Pipelines de
   torneio calculam acuracia e rating economico por-round inline.
5. **Persistence** -- escrita dos resultados no banco de dados.  Pipelines de
   usuario fazem upsert de linhas `PlayerMatchStats` via `DatabaseManager`.
   Pipelines de torneio escrevem em CSV para processamento downstream.
6. **Archival** -- movimentacao dos arquivos ingeridos com sucesso para o
   diretorio `processed_dir` para manter limpo o diretorio fonte.

### `user_ingest.py` em Detalhe

A pipeline de ingestao do usuario trata arquivos `.dem` gravados das partidas
CS2 do jogador local.  E uma pipeline standalone simplificada: a ingestao de
demo do usuario em producao passa por `_ingest_single_demo()` em
`run_ingestion.py`, e `ingest_user_demos()` atualmente nao tem chamadores
in-code.

**Ponto de entrada:** `ingest_user_demos(source_dir: Path, processed_dir: Path)`

Fluxo interno:

1. Glob de `source_dir` por arquivos `*.dem`.
2. Para cada arquivo, chama `_process_single_user_demo()` que envolve toda a
   pipeline em um try/except para que um arquivo corrompido nao aborte o batch.
3. `parse_demo()` retorna um `DataFrame` de estatisticas por-jogador (totais
   do scoreboard final mais medias por-round).
4. `extract_match_stats()` agrega em um dicionario de estatisticas plano.
5. Um objeto ORM `PlayerMatchStats` e criado com `is_pro=False` e o nome do
   jogador lido de `get_setting("CS2_PLAYER_NAME")`.
6. `db_manager.upsert()` persiste a linha (insert ou update on conflict).
7. `persist_round_stats_and_enrichment()` de
   `backend/processing/round_stats_builder` salva `RoundStats` mais campos de
   enriquecimento (fechamento F6-19 -- sem ele, os eixos trade/opening/utility
   ficariam em 0.0 e comparacoes pro seriam fabricadas).
8. `_trigger_ml_pipeline()` importa lazily `run_ml_pipeline` de
   `run_ingestion.py` para evitar imports circulares, entao executa a etapa de
   enriquecimento ML (vetorizacao de features, inferencia do modelo).  Se a
   pipeline reportar uma execucao incompleta, a demo e deixada no lugar para
   retry.
9. `_archive_user_demo()` move o arquivo para `processed_dir` somente apos
   todas as etapas anteriores terem sido bem-sucedidas (invariante R3-H03).

**Limitacao residual:** Extracao de dados em nivel de tick nao e realizada aqui;
isso permanece como tarefa do caminho completo em `run_ingestion.py`.

### `json_tournament_ingestor.py` em Detalhe

O ingestor JSON de torneios processa exports JSON estruturados que contem a
hierarquia match/map/round/team.

**Ponto de entrada:** `process_tournament_jsons(json_dir: str, output_csv: str)`

Fluxo interno:

1. Glob de `json_dir` por arquivos `*.json`.
2. Cada arquivo e validado por `_validate_tournament_json()`.
3. A estrutura aninhada e achatada atraves de uma cadeia de extratores:
   `_extract_match_stats()` -> `_extract_map_stats()` ->
   `_extract_game_stats()` -> `_extract_round_stats()` ->
   `_build_flat_stat()`.
4. Campos numericos passam por `_safe_int()` (invariante DS-04) para tratar
   None, strings e outros valores JSON nao numericos.
5. Metricas derivadas sao calculadas inline: `accuracy = hits / shots`,
   `econ_rating = damage / money_spent`.
6. A lista completa de estatisticas planas e escrita em CSV via
   `pandas.DataFrame`.
7. O progresso e logado a cada 100 arquivos.

Esta pipeline e standalone: pode ser executada como `__main__` com caminhos
hardcoded apontando para `new_datasets/csgo_tournament_data/CS_GO_Tournaments/`
(raiz do repo) e saida em
`Programma_CS2_RENAN/data/external/tournament_advanced_stats.csv`.

## Integracao

### Dependencias Upstream

| Dependencia | Modulo |
|-------------|--------|
| Demo parser | `backend/data_sources/demo_parser.parse_demo()` |
| Extracao de features | `backend/processing/feature_engineering/base_features.extract_match_stats()` |
| Singleton do banco de dados | `backend/storage/database.get_db_manager()` |
| Modelos ORM | `backend/storage/db_models.PlayerMatchStats` |
| Configuracao | `core/config.get_setting()` |
| Logging estruturado | `observability/logger_setup.get_logger()` |

### Consumidores Downstream

- **`run_ingestion.py`** -- o orquestrador que fornece `run_ml_pipeline()`
  chamada apos a ingestao de demos do usuario.
- **`backend/nn/`** -- os modelos ML consomem as linhas `PlayerMatchStats`
  produzidas por estas pipelines.

## Notas de Desenvolvimento

- **Isolamento de erros:** Cada arquivo e processado dentro de seu proprio
  bloco try/except.  Uma demo corrompida nao aborta o batch inteiro.
- **Imports lazy:** `_trigger_ml_pipeline()` usa um import em nivel de funcao
  para quebrar a dependencia circular entre `user_ingest` e `run_ingestion`.
- **Seguranca de arquivamento (R3-H03):** Arquivos sao movidos para
  `processed_dir` somente apos todas as etapas da pipeline terem sido
  bem-sucedidas.  Se qualquer etapa lancar uma excecao, o arquivo permanece no
  diretorio fonte para retry na proxima execucao.
- **Thread safety:** As pipelines em si nao sao thread-safe.  Sao projetadas
  para serem chamadas de uma unica thread.
- **Logging estruturado:** Todas as pipelines logam via
  `get_logger("cs2analyzer.*")` com formato JSON para observabilidade.
- **Invariante DS-04:** O helper `_safe_int()` no ingestor de torneios
  converte todos os campos numericos com seguranca, retornando um default de
  `0` em caso de falha.
- **Invariante DS-12:** O piso de aceitacao `MIN_DEMO_SIZE` (10 MB) e definido
  e aplicado em `backend/data_sources/demo_format_adapter`
  (`validate_demo_file()`).  Essa verificacao NAO esta no call path desta
  pipeline: `user_ingest.py` -> `parse_demo()` nao realiza validacao de
  tamanho.  Demos CS2 reais sao tipicamente 50+ MB.
