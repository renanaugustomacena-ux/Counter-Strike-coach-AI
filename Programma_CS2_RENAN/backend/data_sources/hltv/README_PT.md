# Scraper de Estatisticas de Jogadores Profissionais HLTV

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

---

## Competencia e Escopo

| Atributo | Valor |
|----------|-------|
| **Dominio** | Estatisticas de jogadores profissionais CS2 de hltv.org |
| **Tecnologia** | BeautifulSoup4 + FlareSolverr (Docker) para bypass de Cloudflare |
| **Banco de Dados** | `hltv_metadata.db` (SQLite WAL) |
| **Modelos** | `ProPlayer`, `ProPlayerStatCard`, `ProTeam` |
| **Entry Point** | `hltv_sync_service.py` (orquestrador, externo a este pacote) |
| **Pacote** | `Programma_CS2_RENAN.backend.data_sources.hltv` |

---

## Esclarecimento OBRIGATORIO: O que este servico FAZ e NAO faz

### O que ele FAZ

- Faz scraping de **estatisticas textuais publicamente visiveis** das paginas de jogadores
  profissionais em hltv.org
- Busca: Rating 2.0, K/D, KPR, DPR, ADR, KAST, HS%, Impact, Maps Played
- Busca secoes de traits: Firepower, Entrying, Utility
- Busca sub-paginas: Clutches (1v1, 1v2, 1v3), Multikills (3k, 4k, 5k),
  Historico de rating da carreira
- Descobre automaticamente os Top 50 jogadores a partir da pagina de ranking do HLTV
- Salva todos os dados nas tabelas `ProPlayer` + `ProPlayerStatCard` em `hltv_metadata.db`
- Respeita `robots.txt` e aplica rate limiting entre as requisicoes
- Usa FlareSolverr (container Docker) para contornar a protecao Cloudflare em hltv.org

### O que ele NAO faz

- **NAO baixa demos** -- arquivos demo (`.dem`) sao tratados por uma pipeline completamente separada
- **NAO faz download de demos** -- nao existe nenhuma funcionalidade de download de demos neste
  pacote
- **NAO gerencia arquivos `.dem`** -- a ingestao de demos fica em `ingestion/`
- **NAO interage com a ingestao de demos** -- este pacote e a ingestao de demos sao completamente
  isolados
- **NAO baixa replays de partidas** -- apenas estatisticas textuais dos jogadores
- **NAO usa Playwright** -- toda automacao de navegador passa pelo container Docker FlareSolverr

Essa distincao e critica. O servico HLTV existe unicamente para construir uma baseline de
estatisticas profissionais que o motor de coaching utiliza para comparar o desempenho do usuario
contra os padroes profissionais.

---

## Inventario de Arquivos

| Arquivo | Linhas | Proposito |
|---------|--------|-----------|
| `__init__.py` | 1 | Inicializacao do pacote (marcador vazio) |
| `docker_manager.py` | 139 | Ciclo de vida do container Docker/FlareSolverr: iniciar, health-check, parar |
| `flaresolverr_client.py` | 141 | Cliente REST para API FlareSolverr: gerenciamento de sessoes, HTTP GET via proxy |
| `rate_limit.py` | 33 | `RateLimiter` com delays em niveis para simular padroes de navegacao humana |
| `selectors.py` | 29 | `HLTVURLBuilder` (construcao de URL) + `PlayerStatsSelectors` (seletores CSS) |
| `stat_fetcher.py` | 438 | `HLTVStatFetcher`: logica principal de fetch, parsing HTML, persistencia no banco |

---

## Diagrama de Arquitetura

```
                        +--------------------------+
                        |   hltv_sync_service.py   |
                        |   (orquestrador —        |
                        |    chama                 |
                        |    HLTVStatFetcher)      |
                        +------------+-------------+
                                     |
                                     v
                        +------------+-------------+
                        |     stat_fetcher.py      |
                        |   Classe HLTVStatFetcher |
                        |   - preflight_check()    |
                        |   - fetch_top_players()  |
                        |   - fetch_and_save()     |
                        +---+--------+--------+----+
                            |        |        |
                   +--------+   +----+----+   +--------+
                   |            |         |            |
                   v            v         v            v
          +--------+--+  +-----+------+  +-----+------+
          | selectors |  | rate_limit |  | flaresolverr |
          | .py       |  | .py        |  | _client.py   |
          | Construcao|  | Delays em  |  | Cliente REST |
          | URL + CSS |  | niveis     |  | para proxy   |
          +-----------+  +------------+  +------+-------+
                                                |
                                                v
                                     +----------+---------+
                                     |  docker_manager.py |
                                     |  Iniciar/parar/    |
                                     |  health-check      |
                                     |  container         |
                                     +----------+---------+
                                                |
                                                v
                                     +----------+---------+
                                     |  FlareSolverr      |
                                     |  Container Docker  |
                                     |  (porta 8191)      |
                                     +----------+---------+
                                                |
                                                v
                                     +----------+---------+
                                     |    hltv.org        |
                                     |  (Cloudflare CDN)  |
                                     +----------+---------+
                                                |
                                                v
                                     +----------+---------+
                                     |  Resposta HTML     |
                                     |  (BeautifulSoup4   |
                                     |   analisa em       |
                                     |   dados estrutur.) |
                                     +----------+---------+
                                                |
                                                v
                                     +----------+---------+
                                     | hltv_metadata.db   |
                                     | - ProPlayer        |
                                     | - ProPlayerStatCard|
                                     | - ProTeam          |
                                     +--------------------+
```

---

## Como Funciona (Passo a Passo)

1. **Preflight**: `HLTVStatFetcher.preflight_check()` verifica que `HLTV_SCRAPING_ENABLED` esta
   ativo nas configuracoes e que `robots.txt` nao proibe os caminhos alvo.
2. **Verificacao Docker**: `docker_manager.ensure_flaresolverr()` garante que o container
   FlareSolverr esta rodando na porta 8191. Tenta primeiro `docker start flaresolverr`,
   depois recorre a `docker compose up -d` se o container nao existir.
3. **Descoberta**: `fetch_top_players()` faz scraping da pagina de ranking Top 50 para coletar
   automaticamente as URLs dos perfis dos jogadores.
4. **Fetch por jogador**: Para cada URL de jogador, `fetch_and_save_player()` inicia um deep crawl:
   - Pagina de visao geral: Rating 2.0, KPR, DPR, ADR, KAST, HS%, Impact, Maps Played
   - Secoes de traits: Firepower, Entrying, Utility (extraidas da mesma pagina)
   - Sub-paginas: Clutches, Multikills, Historico de carreira (requisicoes HTTP separadas para cada)
5. **Parsing**: BeautifulSoup4 analisa as respostas HTML usando seletores CSS definidos em
   `selectors.py` e inline em `stat_fetcher.py`.
6. **Persistencia**: Os dados analisados sao inseridos/atualizados nas tabelas `ProPlayer` e
   `ProPlayerStatCard` em `hltv_metadata.db` via SQLModel. O KAST e convertido de percentual
   para razao (P-SAN-01).

---

## Rate Limiting

A classe `RateLimiter` usa um **sistema de delays em niveis** (nao um token bucket) que simula
o comportamento de navegacao humana com jitter aleatorio para evitar deteccao:

| Nivel | Intervalo de Delay | Proposito |
|-------|-------------------|-----------|
| `micro` | 2.0 -- 3.5s | Pequenas esperas dentro de uma sequencia de paginas |
| `standard` | 4.0 -- 8.0s | Navegacao normal entre jogadores |
| `heavy` | 10.0 -- 20.0s | Transicao entre diferentes secoes de estatisticas |
| `backoff` | 45.0 -- 90.0s | Apos suspeita de bloqueio ou falha de rede |

Alem disso, `stat_fetcher.py` aplica seus proprios `CRAWL_DELAY_MIN_SECONDS = 2` e
`CRAWL_DELAY_MAX_SECONDS = 7` entre cada requisicao HTTP, usando `random.uniform()`.

O jitter aleatorio e intencionalmente **nao seedado** (F6-25): um jitter deterministico criaria
padroes de requisicao detectaveis. A deteccao anti-scraping depende de aleatoriedade
aparentemente humana.

O delay minimo efetivo entre quaisquer duas requisicoes e **2.0 segundos** (piso rigido).

---

## Modelo de Dados (O que e Armazenado)

### Tabela `ProPlayer`

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `hltv_id` | int | Identificador unico do jogador no HLTV (extraido da URL) |
| `nickname` | str | Nickname do jogador (ex: "FalleN", "s1mple") |

### Tabela `ProPlayerStatCard`

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `player_id` | int | FK para `ProPlayer.hltv_id` |
| `rating_2_0` | float | HLTV Rating 2.0 |
| `kpr` | float | Kills per round |
| `dpr` | float | Deaths per round |
| `adr` | float | Average damage per round |
| `kast` | float | Razao KAST [0, 1] (convertido de percentual via P-SAN-01) |
| `impact` | float | Impact rating |
| `headshot_pct` | float | Percentual de headshot |
| `maps_played` | int | Total de mapas jogados |
| `opening_kill_ratio` | float | Razao de opening kill |
| `opening_duel_win_pct` | float | Percentual de vitoria em opening duel |
| `detailed_stats_json` | str | Blob JSON: clutches, multikills, carreira, secoes de traits |
| `time_span` | str | Sempre `"all_time"` (implementacao atual) |

### Estrutura `detailed_stats_json`

```json
{
  "firepower": {"kpr": 0.85, "adr": 82.3, "adr_win": 95.1, "kpr_win": 1.02},
  "entrying": {"opening_win_pct": 55.2, "traded_deaths_pct": 18.7},
  "utility": {"flash_assists": 0.12},
  "clutches": {"1on1_wins": 142, "1on1_losses": 98, "1on2_wins": 31, "1on3_wins": 8},
  "multikills": {"3k": 215, "4k": 42, "5k": 7},
  "career": {"rating_history": {"2020": 1.12, "2021": 1.08, "2022": 1.15, "2023": 1.10}}
}
```

---

## Tratamento de Erros

- **FlareSolverr inacessivel**: `docker_manager.py` tenta `docker start`, depois
  `docker compose up -d`, e entao retorna `False`. O servico de sync registra um erro e aborta.
- **Falha no challenge Cloudflare**: FlareSolverr retorna status diferente de 200;
  `flaresolverr_client.py` registra o erro via `self.last_error` e retorna `None`.
- **Falhas de parsing HTML**: Se os seletores CSS nao encontram elementos correspondentes, os
  valores padrao sao `0.0` via `_safe_float()`. Isso e registrado no nivel DEBUG.
- **Timeouts de rede**: O cliente FlareSolverr tem um timeout padrao de 60 segundos. O health-check
  do Docker faz polling por ate 45 segundos em intervalos de 3 segundos.
- **Falhas de sub-paginas**: Falhas de fetch de sub-paginas individuais (clutches, multikills,
  carreira) sao registradas em WARNING (DS-07) mas nao abortam o fetch geral do jogador. A secao
  JSON correspondente sera um dict vazio `{}`.
- **Verificacao robots.txt**: `check_robots_txt()` aborta todo o sync se o HLTV proibir
  explicitamente o caminho alvo. Se `robots.txt` nao estiver acessivel (Cloudflare bloqueia
  requisicoes diretas), o scraping prossegue com um warning.

---

## Aviso Legal / Etico (D-23)

Este modulo faz scraping de dados textuais publicamente visiveis de hltv.org. Os Termos de Servico
do HLTV podem restringir acesso automatizado. O scraper:

- Verifica `robots.txt` antes de cada ciclo de sync e aborta se proibido
- Aplica delays aleatorios de 2--7 segundos entre cada requisicao HTTP
- Pode ser desabilitado completamente via `HLTV_SCRAPING_ENABLED=false` nas configuracoes

O uso deste modulo e responsabilidade do operador. Desabilite o scraping se voce nao tem certeza
sobre a conformidade na sua jurisdicao.

---

## Notas de Desenvolvimento

### Pre-requisitos

- Docker Desktop (ou Docker Engine) deve estar instalado e rodando
- Imagem do container FlareSolverr: `ghcr.io/flaresolverr/flaresolverr:v3.4.6`
- Dependencia Python: `beautifulsoup4` (import opcional; lanca `ImportError` na instanciacao)

### Inicio Rapido

```bash
# Pull e iniciar FlareSolverr
docker pull ghcr.io/flaresolverr/flaresolverr:v3.4.6
docker run -d --name flaresolverr -p 8191:8191 \
    -e LOG_LEVEL=info -e TZ=America/Sao_Paulo \
    --restart unless-stopped \
    ghcr.io/flaresolverr/flaresolverr:v3.4.6

# Verificar health
curl http://localhost:8191/
```

### Logging

Todos os modulos usam logging estruturado via `get_logger("cs2analyzer.<modulo>")`:
- `cs2analyzer.docker_manager` -- eventos do ciclo de vida do container
- `cs2analyzer.flaresolverr` -- interacoes com API REST do FlareSolverr
- `cs2analyzer.hltv.rate_limit` -- nivel de delay e duracao do sleep
- `cs2analyzer.hltv_stat_fetcher` -- descoberta de jogadores, parsing, persistencia no banco

### Configuracao

| Configuracao | Padrao | Descricao |
|--------------|--------|-----------|
| `HLTV_SCRAPING_ENABLED` | `"true"` | Chave mestra para habilitar/desabilitar o scraping |

### Manutencao de Seletores

Quando o HLTV muda o layout de suas paginas, atualize os seletores CSS em dois lugares:
1. `selectors.py` -- classe `PlayerStatsSelectors` (linhas de tabela, coluna nome, coluna rating)
2. `stat_fetcher.py` -- chamadas `soup.select()` inline nos metodos de parsing

### Gerenciamento de Sessoes FlareSolverr

`FlareSolverrClient` suporta sessoes de navegador persistentes para reutilizacao de cookies entre
multiplas requisicoes. As sessoes sao criadas com `create_session()` e destruidas com
`destroy_session()`. Se nenhuma sessao esta ativa, cada requisicao cria um contexto de navegador
novo.

### Invariantes Chave

| ID | Regra |
|----|-------|
| P-SAN-01 | KAST convertido de percentual (74.0) para razao (0.74) antes do armazenamento |
| D-23 | `robots.txt` verificado antes de cada ciclo de sync; aborta se proibido |
| DS-05 | Caminho `project_root` resolvido e validado antes do `cwd` do subprocess |
| DS-07 | Falhas de fetch de sub-paginas registradas em WARNING, nao abortam o fetch do jogador |
| F6-05 | Delay do rate limiter registrado em DEBUG com nome do nivel |
| F6-25 | Jitter aleatorio intencionalmente nao seedado para evitar padroes detectaveis |
