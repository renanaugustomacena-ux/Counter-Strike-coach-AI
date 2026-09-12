# Scraper de Estatisticas de Jogadores Profissionais HLTV

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

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
- Busca da pagina de visao geral: estatisticas por funcao (40 estatisticas entre lados combined/CT/T) e pontuacoes de secao (0-100, ex. Firepower)
- Busca sub-paginas: Individual (incl. rounds multikill 2k-5k e duelos de abertura), Historico de rating da carreira, Opponents, Clutches (contagens por tier 1on1-1on5)
- Descobre automaticamente URLs de jogadores via ranking mundial de times HLTV (top 30 times, ~150 jogadores). Recai para `/stats/players` se a descoberta via times retornar zero
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
| `__init__.py` | 0 | Inicializacao do pacote (marcador vazio) |
| `docker_manager.py` | 138 | Ciclo de vida do container Docker/FlareSolverr: `ensure_flaresolverr()`, health-check, `stop_flaresolverr()` |
| `flaresolverr_client.py` | 162 | Cliente REST para API FlareSolverr: gerenciamento de sessoes (`create_session`/`destroy_session`), `get()` via proxy com retries (backoff 5s/15s/45s) |
| `stat_fetcher.py` | 969 | `HLTVStatFetcher`: discovery (`fetch_top_teams`, `fetch_top_players`), parsing HTML via `soup.select()` inline, rate limiting via `CRAWL_DELAY_MIN/MAX_SECONDS` (2-7s) + `random.uniform()` + backoff adaptativo em falhas consecutivas, persistencia no banco |

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
                        |   - fetch_top_teams(30)  |
                        |   - fetch_top_players()  |
                        |   - fetch_and_save_player|
                        |   soup.select() inline   |
                        |   CRAWL_DELAY 2-7s       |
                        +------------+-------------+
                                     |
                                     v
                                     +----------+---------+
                                     | flaresolverr_      |
                                     | client.py          |
                                     | REST via :8191     |
                                     +----------+---------+
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
3. **Descoberta**: `fetch_top_teams(count=30)` faz scraping de `/ranking/teams/` (compativel com
   robots.txt) para extrair os times de topo e seus rosters, gerando ~150 URLs de estatisticas
   de jogadores. Se a descoberta por times retornar zero, o chamador recai para
   `fetch_top_players()` que visa `/stats/players` (nota: `/stats/players?rankingFilter=Top50`
   e proibido por `robots.txt` do HLTV desde 2026-04-12 -- veja `check_robots_txt()` em
   stat_fetcher.py:70).
4. **Fetch por jogador**: Para cada URL de jogador, `fetch_and_save_player()` inicia um deep crawl:
   - Pagina de visao geral: Rating 2.0, KPR, DPR, ADR, KAST, HS%, Impact, Maps Played, perfil
     (nome real, pais, idade), estatisticas por funcao e pontuacoes de secao (extraidas da mesma pagina)
   - Sub-paginas (requisicao HTTP separada para cada): Individual, Career, Opponents, Clutches.
     Sub-paginas sao filtradas por data a partir de `HLTV_STATS_START_DATE` (2021-06-01) ate **hoje**,
     calculado no momento da requisicao (R4 MED: uma data final hardcoded era usada para congelar a janela).
   - Contagens de multikill (2k-5k) e estatisticas de duelos de abertura sao derivadas da pagina Individual;
     nao existe uma sub-pagina separada de Multikills.
5. **Parsing**: BeautifulSoup4 analisa as respostas HTML usando seletores CSS definidos inline
   em `stat_fetcher.py` via `soup.select()` com fallback multi-seletor (`_select_fallback()`).
6. **Persistencia**: Apos uma verificacao H2 de estatisticas minimas viaveis (jogadores com campos
   centrais ausentes ou rating <= 0 sao ignorados como provaveis falhas de parse), os dados sao
   inseridos/atualizados nas tabelas `ProPlayer` e `ProPlayerStatCard` em `hltv_metadata.db` via
   SQLModel. KAST, HS% e percentual de vitoria em duelos de abertura sao convertidos de percentual
   para razao (P-SAN-01).

---

## Rate Limiting

O rate limiting e implementado diretamente em `stat_fetcher.py` como constantes a nivel de modulo,
nao como uma classe separada:

```python
CRAWL_DELAY_MIN_SECONDS = 2  # stat_fetcher.py:51
CRAWL_DELAY_MAX_SECONDS = 7  # stat_fetcher.py:52
```

Cada requisicao HTTP via FlareSolverr e precedida por um sleep adaptativo:
`base_delay = CRAWL_DELAY_MIN_SECONDS + min(consecutive_failures * 2, 10)` seguido de
`time.sleep(random.uniform(base_delay, base_delay + 3))`. Quando saudavel, o atraso efetivo
e portanto uniforme em **2-5 segundos** (paginas de visao geral de jogadores adicionam +1s: 3-6
segundos), crescendo em ate +10 segundos sob falhas consecutivas (backoff adaptativo;
cada sucesso decrementa o contador de falhas).

O jitter aleatorio e intencionalmente **nao seedado** (F6-25): um jitter deterministico criaria
padroes de requisicao detectaveis. A deteccao anti-scraping depende de aleatoriedade
aparentemente humana. Sleeps dormentes adicionais (uma hora entre ciclos de sync, seis horas
quando HLTV esta inacessivel) sao aplicados pelo chamador `hltv_sync_service.run_sync_loop()`.

---

## Modelo de Dados (O que e Armazenado)

### Tabela `ProPlayer`

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `hltv_id` | int | Identificador unico do jogador no HLTV (extraido da URL) |
| `nickname` | str | Nickname do jogador (ex: "FalleN", "s1mple") |
| `real_name` | str? | Nome real da caixa de perfil (opcional) |
| `country` | str? | Pais da caixa de perfil (opcional) |
| `age` | int? | Idade da caixa de perfil (opcional) |
| `team_id` | int? | FK para `ProTeam.hltv_id` (ON DELETE SET NULL, R2-07) |
| `last_updated` | datetime | Timestamp UTC da ultima sincronizacao |

### Tabela `ProPlayerStatCard`

| Coluna | Tipo | Descricao |
|--------|------|-----------|
| `player_id` | int | FK para `ProPlayer.hltv_id` (ON DELETE CASCADE, R2-07) |
| `rating_2_0` | float | HLTV Rating 2.0 |
| `kpr` | float | Kills per round |
| `dpr` | float | Deaths per round |
| `adr` | float | Average damage per round |
| `kast` | float | Razao KAST [0, 1] (convertido de percentual via P-SAN-01) |
| `impact` | float | Impact rating |
| `headshot_pct` | float | Razao de headshot [0, 1] (convertido de percentual) |
| `maps_played` | int | Total de mapas jogados |
| `opening_kill_ratio` | float | Razao de opening kill |
| `opening_duel_win_pct` | float | Razao de vitoria em opening duel [0, 1] (convertido de percentual) |
| `clutch_win_count` | int | Soma de contagens de clutch entre tiers (da pagina Clutches) |
| `multikill_round_pct` | float | Rounds multikill (2k-5k) como % de rounds jogados |
| `detailed_stats_json` | str | Blob JSON: veja estrutura abaixo (limitado em tamanho por um validador) |
| `time_span` | str | Sempre `"all_time"` (implementacao atual) |
| `last_updated` | datetime | Timestamp UTC da ultima sincronizacao |

### Estrutura `detailed_stats_json`

```json
{
  "summary_boxes": {"...": "valores brutos das summary-box da visao geral"},
  "rating_version": "2.1",
  "rating_tier": "...",
  "legacy_stats": {"...": "pares label/valor brutos das linhas de stats da visao geral"},
  "role_stats": {"combined": {"...": 0.0}, "ct": {"...": 0.0}, "t": {"...": 0.0}},
  "section_scores": {"Firepower": 85, "Entrying": 62},
  "individual": {"opening_kill_ratio": 1.2, "2_kill_rounds": 300},
  "career": {"2023": {"all": 1.10, "online": 1.08, "lan": 1.15, "majors": 1.05}},
  "opponents": [{"...": "linhas por oponente"}],
  "clutch_counts": {"1on1": 142, "1on2": 31, "1on3": 8},
  "multikill_counts": {"2k": 300, "3k": 215, "4k": 42, "5k": 7}
}
```

---

## Tratamento de Erros

- **FlareSolverr inacessivel**: `docker_manager.py` tenta `docker start`, depois
  `docker compose up -d`, e entao retorna `False`. O servico de sync registra um erro e aborta.
- **Falha no challenge Cloudflare**: FlareSolverr retorna status diferente de 200;
  `flaresolverr_client.py` registra o erro via `self.last_error` e retorna `None`.
- **Falhas de parsing HTML**: `_select_fallback()` registra um WARNING quando todos os
  seletores CSS candidatos falham; valores de estatisticas nao analisaveis recebem padrao `0.0`
  via `_safe_float()` (registrado em DEBUG). `_safe_float()` distingue virgulas de milhar
  ("39,606") de virgulas decimais ("0,85") -- correcao R4 HIGH.
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
- `cs2analyzer.hltv_stat_fetcher` -- descoberta de jogadores, parsing, persistencia no banco

### Configuracao

| Configuracao | Padrao | Descricao |
|--------------|--------|-----------|
| `HLTV_SCRAPING_ENABLED` | `"true"` | Chave mestra para habilitar/desabilitar o scraping |

### Manutencao de Seletores

Quando o HLTV muda o layout de suas paginas, atualize os seletores CSS inline em
`stat_fetcher.py`. O helper `_select_fallback()` (stat_fetcher.py:145) aceita uma lista
ordenada de seletores candidatos e registra um warning quando o seletor primario falha e um
fallback e ativado, para que a derrapagem de layout seja detectada precocemente sem interromper
o scraping. Inspecione os logs WARNING para mensagens "CSS fallback activated" e adicione novos
seletores primarios acima dos existentes.

### Gerenciamento de Sessoes FlareSolverr

`FlareSolverrClient` suporta sessoes de navegador persistentes para reutilizacao de cookies entre
multiplas requisicoes. As sessoes sao criadas com `create_session()` e destruidas com
`destroy_session()`. Se nenhuma sessao esta ativa, cada requisicao cria um contexto de navegador
novo.

### Invariantes Chave

| ID | Regra |
|----|-------|
| P-SAN-01 | KAST (e outros %) convertido de percentual (74.0) para razao (0.74) antes do armazenamento |
| D-23 | `robots.txt` verificado antes de cada ciclo de sync; aborta se proibido |
| DS-05 | Caminho `project_root` resolvido e validado antes do `cwd` do subprocess |
| DS-07 | Falhas de fetch de sub-paginas registradas em WARNING, nao abortam o fetch do jogador |
| H2 | Validacao de estatisticas minimas viaveis antes da persistencia (pula provaveis falhas de parse) |
| F6-25 | Jitter aleatorio intencionalmente nao seedado para evitar padroes detectaveis |
