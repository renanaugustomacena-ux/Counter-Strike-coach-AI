> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Data Sources -- Integracoes Externas

> **Autoridade:** `backend/data_sources/`
> **Skill:** `/resilience-check`, `/api-contract-review`, `/security-scan`
> **Consumidores:** `ingestion/`, `backend/services/`, `backend/coaching/pro_bridge.py`

## Visao Geral

O pacote data sources e a camada de fronteira entre o CS2 Analyzer e todos os sistemas
externos. Fornece adaptadores para parsing de arquivos demo, consultas de perfis Steam,
recuperacao de historico de partidas FACEIT e scraping de estatisticas de jogadores
profissionais do HLTV. Toda integracao externa reside aqui para que o restante do
codebase nunca toque diretamente em I/O bruto, clientes HTTP ou formatos de dados de
terceiros.

O pacote segue um rigoroso principio de **confianca zero nas fronteiras**: todos os dados
vindos de fontes externas sao validados, normalizados e convertidos em esquemas internos
antes de serem passados aos consumidores a jusante.

> **IMPORTANTE -- Esclarecimento sobre HLTV:**
> A integracao HLTV coleta **estatisticas de jogadores profissionais** do hltv.org
> (Rating 2.0, K/D, ADR, KAST, HS%, estatisticas de clutch, historico de carreira).
> **NAO** baixa demos, nao busca metadados de demos e nao interage com arquivos .dem
> de nenhuma forma. O scraper HLTV e o demo parser sao subsistemas completamente
> independentes.

## Inventario de Arquivos

| Arquivo | Exportacao Primaria | Proposito |
|---------|--------------------|-----------|
| `__init__.py` | Raiz do pacote | (vazio -- apenas namespace) |
| `demo_parser.py` | `parse_demo()` | Wrapper demoparser2 com calculo de rating HLTV 2.0, exporta dados por tick e por round |
| `demo_format_adapter.py` | `DemoFormatAdapter` | Validacao e conversao de formato entre saidas do demo parser e esquemas internos (`MIN_DEMO_SIZE=10MB`) |
| `event_registry.py` | Despacho de eventos | Registro e despacho de tipos de evento para eventos de demo (kills, plants, defuses, etc.) |
| `trade_kill_detector.py` | `TradeKillDetector` | Identifica trade frags a partir de dados de tick usando uma janela deslizante de 3 segundos |
| `round_context.py` | Helper de contexto de round | Enriquece dados por round com metadados contextuais (estado economico, controle de site, etc.) |
| `steam_api.py` | `SteamAPI` | Integracao com Steam Web API para sincronizacao de perfil, lista de amigos, estatisticas de jogo |
| `steam_demo_finder.py` | `SteamDemoFinder` | Localiza arquivos de demo CS2 em diretorios userdata do Steam no filesystem local |
| `faceit_api.py` | `FaceitAPI` | Wrapper da API da plataforma FACEIT para historico de partidas e estatisticas de jogador |
| `faceit_integration.py` | `FaceitIntegration` | Orquestracao de ingestao de dados FACEIT de alto nivel |
| `hltv_scraper.py` | `HLTVScraper` | Coleta estatisticas de jogadores profissionais do hltv.org (Rating 2.0, K/D, ADR, KAST, HS%) |
| `hltv/` | Sub-pacote | Implementacao HLTV ativa: cliente FlareSolverr, gerenciador Docker, seletores CSS, rate limiting, buscador de estatisticas |

### Sub-Pacote HLTV (`hltv/`)

| Arquivo | Proposito |
|---------|-----------|
| `__init__.py` | Raiz do sub-pacote |
| `flaresolverr_client.py` | Cliente HTTP que roteia requisicoes atraves de FlareSolverr/Docker para contornar protecao Cloudflare |
| `docker_manager.py` | Gerencia o ciclo de vida do container Docker FlareSolverr (inicio, parada, health check) |
| `selectors.py` | Seletores CSS para parsing de paginas HTML HLTV (perfis de jogadores, tabelas de estatisticas) |
| `rate_limit.py` | Logica de rate limiting para evitar bloqueio pelo hltv.org |
| `stat_fetcher.py` | Orquestrador de alto nivel para busca de estatisticas que coordena os modulos acima |

## Diagrama de Fluxo de Dados

```
                    Sistemas Externos
                    =================

  arquivos .dem    Steam Web API      API FACEIT        hltv.org
      |                 |                 |                 |
      v                 v                 v                 v
 demo_parser.py    steam_api.py     faceit_api.py    hltv_scraper.py
      |                 |                 |                 |
      v                 |                 v                 |
 demo_format_         steam_demo_    faceit_          hltv/ sub-pacote
 adapter.py           finder.py      integration.py   (FlareSolverr)
      |                 |                 |                 |
      v                 v                 v                 v
 event_registry.py      |                 |           hltv_metadata.db
      |                 |                 |           (ProPlayer,
      v                 |                 |            ProPlayerStatCard,
 trade_kill_            |                 |            ProTeam)
 detector.py            |                 |
      |                 |                 |
      +--------+--------+---------+-------+
               |
               v
        Esquemas Internos
     (pipeline ingestion/,
      backend/storage/,
      match_data/<id>.db)
```

## Descricoes dos Modulos

### demo_parser.py -- parse_demo()

A funcao central de parsing de demos. Encapsula a biblioteca `demoparser2` para extrair
o estado do jogador por tick (posicao, saude, armadura, equipamento) e estatisticas
agregadas por round (kills, deaths, assists, dano). Calcula o rating HLTV 2.0 em tempo
real durante o parsing. Retorna dados estruturados prontos para a pipeline de ingestao.
Este e um dos modulos mais criticos em termos de desempenho no sistema, processando
milhoes de linhas de tick por demo.

### demo_format_adapter.py -- DemoFormatAdapter

Valida e converte a saida do demo parser em esquemas internos. Aplica `MIN_DEMO_SIZE
= 10 MB` (invariante DS-12) para rejeitar arquivos demo truncados ou corrompidos --
demos CS2 reais tem 50+ MB. Realiza alinhamento de esquema para que consumidores a
jusante (feature engineering, armazenamento em banco de dados) recebam uma forma de
dados consistente independentemente de mudancas de versao do parser.

### event_registry.py -- Despacho de Eventos

Registra e despacha eventos de demo (player_death, bomb_planted, bomb_defused,
round_start, round_end, etc.) para assinantes. Usa um padrao observer para que multiplos
modulos de analise possam reagir ao mesmo fluxo de eventos sem acoplamento entre si.

### trade_kill_detector.py -- TradeKillDetector

Modulo de analise pos-parse que identifica trade frags a partir de dados de kill em
nivel de tick. Um trade kill e definido como um kill que ocorre dentro de uma janela de
3 segundos apos a morte de um companheiro de equipe, direcionado ao mesmo inimigo que
realizou o kill original. Dados de trade kill alimentam a analise tatica e recomendacoes
de coaching sobre disciplina de trade.

### round_context.py -- Helper de Contexto de Round

Enriquece dados por round com metadados contextuais que nao estao diretamente presentes
na saida bruta da demo. Calcula campos derivados como vantagem economica, metricas de
controle de site e padroes de uso de utilidades. Este enriquecimento contextual ajuda
modulos de coaching a jusante a produzir conselhos mais relevantes.

### steam_api.py -- SteamAPI

Integracao com a Steam Web API para sincronizacao de perfil. Recupera informacoes de
perfil do jogador, lista de amigos e estatisticas de jogo especificas de CS2. Requer uma
chave de API Steam armazenada via sistema de credenciais
(`get_credential("STEAM_API_KEY")`). Inclui logica de retry e rate limiting para lidar
com falhas transientes da API.

### steam_demo_finder.py -- SteamDemoFinder

Localiza arquivos de demo CS2 no filesystem local escaneando diretorios userdata Steam
conhecidos. Consciente da plataforma (Windows, Linux, macOS). Usado pela pipeline de
ingestao para descobrir novas demos para processamento automatizado sem exigir que o
usuario especifique manualmente os caminhos de arquivo.

### faceit_api.py -- FaceitAPI

Wrapper de baixo nivel em torno da API da plataforma FACEIT. Recupera historico de
partidas, estatisticas de jogador e ratings ELO. Requer uma chave de API FACEIT
armazenada via sistema de credenciais. Gerencia paginacao, rate limiting e respostas
de erro da API FACEIT.

### faceit_integration.py -- FaceitIntegration

Camada de orquestracao de alto nivel que coordena a ingestao de dados FACEIT. Gerencia
o fluxo desde chamadas de API atraves da normalizacao de dados ate o armazenamento em
banco de dados. Fornece um unico ponto de entrada `sync_player()` que gerencia o ciclo
de vida completo de busca e persistencia de dados FACEIT para um dado jogador.

### hltv_scraper.py -- HLTVScraper

Coleta estatisticas de jogadores profissionais do hltv.org. Extrai: Rating 2.0, razao
K/D, ADR (Dano Medio por Round), porcentagem KAST, HS% (porcentagem de headshot),
estatisticas de clutch e historico de carreira. Os dados sao salvos em
`hltv_metadata.db` nas tabelas `ProPlayer`, `ProPlayerStatCard` e `ProTeam`.
**Este modulo coleta apenas estatisticas -- nao tem nenhuma conexao com gerenciamento
de arquivos demo.**

### Sub-pacote hltv/

A implementacao HLTV ativa que lida com a recuperacao de paginas protegidas por
Cloudflare. `docker_manager.py` gerencia o container FlareSolverr,
`flaresolverr_client.py` roteia as requisicoes HTTP atraves dele, `selectors.py` fornece
seletores CSS para parsing HTML, `rate_limit.py` previne scraping agressivo e
`stat_fetcher.py` orquestra o fluxo de trabalho completo de busca de estatisticas.

## Pontos de Integracao

| Consumidor | Modulo Data Source | O Que Recebe |
|------------|-------------------|--------------|
| Pipeline `ingestion/` | `demo_parser.py`, `demo_format_adapter.py` | Dados de demo analisados e validados para armazenamento em banco de dados |
| `backend/processing/` | `event_registry.py`, `trade_kill_detector.py` | Fluxos de eventos e analise de trade kill para feature engineering |
| `backend/coaching/pro_bridge.py` | `hltv_scraper.py` (via `hltv_metadata.db`) | Baselines de jogadores profissionais para comparacao de coaching |
| `backend/services/` | `steam_api.py`, `faceit_integration.py` | Dados de perfil de jogador para contexto de sessao |
| `core/session_engine.py` | `steam_demo_finder.py` | Caminhos de arquivos demo auto-descobertos para o IngestionWatcher |

## Notas de Desenvolvimento

- **Validacao nas fronteiras:** Todos os dados externos devem ser validados antes de
  cruzar para esquemas internos. Nunca confie em respostas de API brutas ou saida de
  parser sem verificacoes de esquema.
- **Gerenciamento de credenciais:** Chaves de API (Steam, FACEIT) sao armazenadas via
  `get_credential()` de `core/config.py`. Nunca escreva segredos diretamente no codigo
  ou os registre em logs.
- **Invariante MIN_DEMO_SIZE:** `demo_format_adapter.py` aplica `MIN_DEMO_SIZE = 10 MB`
  (invariante DS-12). Nao reduza este limiar -- demos truncadas causam corrupcao
  silenciosa no processamento a jusante.
- **HLTV e apenas estatisticas:** A integracao HLTV busca estatisticas de jogadores
  profissionais. Nao baixa demos, nao gerencia arquivos .dem e nao interage com a
  pipeline de ingestao de demos. Confundir HLTV com gerenciamento de demos e um
  anti-pattern documentado.
- **Dependencia Docker:** O scraper HLTV requer FlareSolverr rodando em Docker para
  contornar Cloudflare. `hltv/docker_manager.py` gerencia o ciclo de vida do container.
- **Logging estruturado:** Todos os modulos usam
  `get_logger("cs2analyzer.data_sources.<modulo>")`.
- **Rate limiting:** Tanto HLTV quanto as integracoes Steam incluem rate limiting. Nao
  ignore os rate limits -- isso leva a bloqueios de IP.
- **Testes:** Use `mock_db_manager` para testes dependentes de banco de dados. Testes
  HLTV e de API requerem `@pytest.mark.integration` e `CS2_INTEGRATION_TESTS=1`.

## Dependencias

- **demoparser2** -- Motor de parsing de arquivos demo CS2
- **FlareSolverr/Docker** -- Bypass de Cloudflare para scraping HLTV
- **requests** -- Cliente HTTP para APIs Steam e FACEIT
- **BeautifulSoup4** -- Parsing HTML para paginas HLTV
- **SQLModel** -- Persistencia em banco de dados para estatisticas de jogadores pro
