# Implementações de Pipeline de Ingestão

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Visão Geral

Pipelines de ingestão de arquivos de demo para diferentes fontes de dados: demos de usuários, demos profissionais e arquivos JSON de torneios. Todas as pipelines agora incluem enriquecimento estatístico em nível de round via `round_stats_builder.py`.

## Pipelines Principais

### `user_ingest.py`
- **`ingest_user_demos()`** — Pipeline de processamento de arquivos de demo do usuário
- Analisa arquivos `.dem` do diretório Steam CS2 do usuário
- Extrai eventos em nível de tick, estados de jogadores, resultados de rounds
- **Enriquecimento de estatísticas de round**: Chama `aggregate_round_stats_to_match()` + `enrich_from_demo()`
- Persiste nas tabelas `PlayerMatchStats` (agregado) e `RoundStats` (por-round)
- Cria banco de dados SQLite por-partida via `MatchDataManager`

### `pro_ingest.py`
- **`ingest_pro_demos()`** — Pipeline de processamento de demos profissionais
- Busca demos do diretório `PRO_DEMO_PATH`
- Enriquecimento de metadados HLTV via `HLTVApiService` (nomes de jogadores, composições de times, contexto de torneio)
- **Enriquecimento de estatísticas de round**: Igual à pipeline de usuário — `enrich_from_demo()` popula `RoundStats`
- Popula tabelas `ProPlayer`, `MatchResult`, `TeamComposition`
- Gera registros de conhecimento tático para recuperação RAG

### `json_tournament_ingestor.py`
- **`process_tournament_jsons()`** — Ingestão de arquivos JSON de torneios
- Processa exportações JSON estruturadas de bancos de dados de torneios
- Valida schema, extrai metadados de partida, estatísticas de jogadores, linhas do tempo de rounds
- Inserção em lote com limites de transação
- Usado para importação de dados históricos e análise de torneios offline

## Padrões Comuns

Todas as pipelines seguem este fluxo:
1. **Discovery**: Escaneia diretório fonte por arquivos não processados
2. **Validation**: Verifica integridade de arquivo, formato, schema
3. **Parsing**: Extrai dados estruturados via parser de demo
4. **Enrichment**: Estatísticas de round, metadados HLTV, dados espaciais
5. **Persistence**: Escritas DB atômicas com rollback em erro
6. **Registration**: Marca arquivo como processado no registro `DemoFileRecord`

## Integração de Round Stats (2026-02-16)

Fase 1 do Fusion Plan conectou a pipeline de agregação:
- `round_stats_builder.py` agora chamado por ingestão de usuário e pro
- Rating HLTV 2.0 por-round, kills noscope, kills blind, flash assists todos persistidos
- Tabela `RoundStats` estendida com novos campos
- Construção de linha do tempo de momentum agora usa `RoundStats.compute_round_rating()`

## Tratamento de Erros

Falhas de ingestão são logadas com IDs de correlação. Ingestão parcial sofre rollback. Arquivos falhados são marcados com estado de erro no registro para revisão manual.
