# Scraper Statistiche Giocatori Professionisti HLTV

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

---

## Competenza e Ambito

| Attributo | Valore |
|-----------|--------|
| **Dominio** | Statistiche giocatori professionisti CS2 da hltv.org |
| **Tecnologia** | BeautifulSoup4 + FlareSolverr (Docker) per bypass Cloudflare |
| **Database** | `hltv_metadata.db` (SQLite WAL) |
| **Modelli** | `ProPlayer`, `ProPlayerStatCard`, `ProTeam` |
| **Entry Point** | `hltv_sync_service.py` (orchestratore, esterno a questo pacchetto) |
| **Pacchetto** | `Programma_CS2_RENAN.backend.data_sources.hltv` |

---

## Chiarimento OBBLIGATORIO: Cosa fa e cosa NON fa questo servizio

### Cosa FA

- Effettua scraping di **statistiche testuali pubblicamente visibili** dalle pagine dei giocatori
  professionisti su hltv.org
- Recupera: Rating 2.0, K/D, KPR, DPR, ADR, KAST, HS%, Impact, Maps Played
- Recupera sezioni trait: Firepower, Entrying, Utility
- Recupera sotto-pagine: Clutches (1v1, 1v2, 1v3), Multikills (3k, 4k, 5k),
  Storico rating carriera
- Scopre automaticamente i Top 50 giocatori dalla pagina ranking di HLTV
- Salva tutti i dati nelle tabelle `ProPlayer` + `ProPlayerStatCard` in `hltv_metadata.db`
- Rispetta `robots.txt` e applica rate limiting tra le richieste
- Usa FlareSolverr (container Docker) per bypassare la protezione Cloudflare su hltv.org

### Cosa NON fa

- **NON scarica demo** -- i file demo (`.dem`) sono gestiti da una pipeline completamente separata
- **NON effettua download di demo** -- non esiste alcuna funzionalita di download demo in
  questo pacchetto
- **NON gestisce file `.dem`** -- l'ingestion delle demo si trova in `ingestion/`
- **NON interagisce con l'ingestion delle demo** -- questo pacchetto e l'ingestion sono
  completamente isolati
- **NON scarica replay delle partite** -- solo statistiche testuali dei giocatori
- **NON usa Playwright** -- tutta l'automazione browser passa attraverso il container Docker
  FlareSolverr

Questa distinzione e fondamentale. Il servizio HLTV esiste unicamente per costruire una baseline
di statistiche professionali che il motore di coaching utilizza per confrontare le prestazioni
dell'utente con gli standard professionistici.

---

## Inventario File

| File | Righe | Scopo |
|------|-------|-------|
| `__init__.py` | 1 | Inizializzazione pacchetto (marcatore vuoto) |
| `docker_manager.py` | 139 | Ciclo di vita container Docker/FlareSolverr: avvio, health-check, arresto |
| `flaresolverr_client.py` | 141 | Client REST per API FlareSolverr: gestione sessioni, HTTP GET tramite proxy |
| `rate_limit.py` | 33 | `RateLimiter` con ritardi a livelli per simulare pattern di navigazione umana |
| `selectors.py` | 29 | `HLTVURLBuilder` (costruzione URL) + `PlayerStatsSelectors` (selettori CSS) |
| `stat_fetcher.py` | 438 | `HLTVStatFetcher`: logica principale di fetch, parsing HTML, persistenza database |

---

## Diagramma Architettura

```
                        +--------------------------+
                        |   hltv_sync_service.py   |
                        |   (orchestratore —       |
                        |    chiama                |
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
          | Costruz.  |  | Ritardi    |  | Client REST  |
          | URL + CSS |  | a livelli  |  | per proxy    |
          +-----------+  +------------+  +------+-------+
                                                |
                                                v
                                     +----------+---------+
                                     |  docker_manager.py |
                                     |  Avvio/arresto/    |
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
                                     |  Risposta HTML     |
                                     |  (BeautifulSoup4   |
                                     |   analizza in      |
                                     |   dati strutturati)|
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

## Come Funziona (Passo dopo Passo)

1. **Preflight**: `HLTVStatFetcher.preflight_check()` verifica che `HLTV_SCRAPING_ENABLED` sia
   attivo nelle impostazioni e che `robots.txt` non vieti i percorsi target.
2. **Controllo Docker**: `docker_manager.ensure_flaresolverr()` garantisce che il container
   FlareSolverr sia in esecuzione sulla porta 8191. Prova prima `docker start flaresolverr`,
   poi ricade su `docker compose up -d` se il container non esiste.
3. **Scoperta**: `fetch_top_players()` effettua scraping della pagina ranking Top 50 per
   raccogliere automaticamente gli URL dei profili dei giocatori.
4. **Fetch per giocatore**: Per ogni URL giocatore, `fetch_and_save_player()` avvia un deep crawl:
   - Pagina panoramica: Rating 2.0, KPR, DPR, ADR, KAST, HS%, Impact, Maps Played
   - Sezioni trait: Firepower, Entrying, Utility (analizzate dalla stessa pagina)
   - Sotto-pagine: Clutches, Multikills, Storico carriera (richieste HTTP separate per ciascuna)
5. **Parsing**: BeautifulSoup4 analizza le risposte HTML usando selettori CSS definiti in
   `selectors.py` e inline in `stat_fetcher.py`.
6. **Persistenza**: I dati analizzati vengono inseriti/aggiornati nelle tabelle `ProPlayer` e
   `ProPlayerStatCard` in `hltv_metadata.db` tramite SQLModel. Il KAST viene convertito da
   percentuale a rapporto (P-SAN-01).

---

## Rate Limiting

La classe `RateLimiter` usa un **sistema di ritardi a livelli** (non un token bucket) che simula
il comportamento di navigazione umana con jitter randomizzato per evitare il rilevamento:

| Livello | Intervallo Ritardo | Scopo |
|---------|-------------------|-------|
| `micro` | 2.0 -- 3.5s | Piccole attese all'interno di una sequenza di pagine |
| `standard` | 4.0 -- 8.0s | Navigazione normale tra giocatori |
| `heavy` | 10.0 -- 20.0s | Transizione tra diverse sezioni di statistiche |
| `backoff` | 45.0 -- 90.0s | Dopo un sospetto blocco o errore di rete |

Inoltre, `stat_fetcher.py` applica i propri `CRAWL_DELAY_MIN_SECONDS = 2` e
`CRAWL_DELAY_MAX_SECONDS = 7` tra ogni richiesta HTTP, usando `random.uniform()`.

Il jitter casuale e intenzionalmente **non seedato** (F6-25): un jitter deterministico creerebbe
pattern di richiesta rilevabili. Il rilevamento anti-scraping si basa su casualita apparentemente
umana.

Il ritardo minimo effettivo tra due richieste qualsiasi e **2.0 secondi** (soglia minima).

---

## Modello Dati (Cosa Viene Salvato)

### Tabella `ProPlayer`

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| `hltv_id` | int | Identificativo unico giocatore HLTV (dall'URL) |
| `nickname` | str | Nickname del giocatore (es. "FalleN", "s1mple") |

### Tabella `ProPlayerStatCard`

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| `player_id` | int | FK a `ProPlayer.hltv_id` |
| `rating_2_0` | float | HLTV Rating 2.0 |
| `kpr` | float | Kills per round |
| `dpr` | float | Deaths per round |
| `adr` | float | Average damage per round |
| `kast` | float | Rapporto KAST [0, 1] (convertito da percentuale tramite P-SAN-01) |
| `impact` | float | Impact rating |
| `headshot_pct` | float | Percentuale headshot |
| `maps_played` | int | Mappe totali giocate |
| `opening_kill_ratio` | float | Rapporto opening kill |
| `opening_duel_win_pct` | float | Percentuale vittoria opening duel |
| `detailed_stats_json` | str | Blob JSON: clutches, multikills, carriera, sezioni trait |
| `time_span` | str | Sempre `"all_time"` (implementazione attuale) |

### Struttura `detailed_stats_json`

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

## Gestione Errori

- **FlareSolverr non raggiungibile**: `docker_manager.py` prova `docker start`, poi
  `docker compose up -d`, infine restituisce `False`. Il servizio di sync logga un errore e si
  interrompe.
- **Fallimento challenge Cloudflare**: FlareSolverr restituisce uno status non-200;
  `flaresolverr_client.py` logga l'errore tramite `self.last_error` e restituisce `None`.
- **Fallimenti parsing HTML**: Se i selettori CSS non trovano elementi corrispondenti, i valori
  predefiniti sono `0.0` tramite `_safe_float()`. Questo viene loggato a livello DEBUG.
- **Timeout di rete**: Il client FlareSolverr ha un timeout predefinito di 60 secondi. L'health-check
  Docker esegue polling fino a 45 secondi a intervalli di 3 secondi.
- **Fallimenti sotto-pagine**: I fallimenti di fetch delle singole sotto-pagine (clutches,
  multikills, carriera) vengono loggati a WARNING (DS-07) ma non interrompono il fetch complessivo
  del giocatore. La sezione JSON corrispondente sara un dict vuoto `{}`.
- **Controllo robots.txt**: `check_robots_txt()` interrompe l'intero sync se HLTV vieta
  esplicitamente il percorso target. Se `robots.txt` non e raggiungibile (Cloudflare blocca le
  richieste dirette), lo scraping procede con un warning.

---

## Avviso Legale / Etico (D-23)

Questo modulo effettua scraping di dati testuali pubblicamente visibili da hltv.org. I Termini di
Servizio di HLTV possono limitare l'accesso automatizzato. Lo scraper:

- Controlla `robots.txt` prima di ogni ciclo di sync e si interrompe se vietato
- Applica ritardi casuali di 2--7 secondi tra ogni richiesta HTTP
- Puo essere disabilitato interamente tramite `HLTV_SCRAPING_ENABLED=false` nelle impostazioni

L'uso di questo modulo e responsabilita dell'operatore. Disabilitare lo scraping se non si e
sicuri della conformita nella propria giurisdizione.

---

## Note per lo Sviluppo

### Prerequisiti

- Docker Desktop (o Docker Engine) deve essere installato e in esecuzione
- Immagine container FlareSolverr: `ghcr.io/flaresolverr/flaresolverr:v3.4.6`
- Dipendenza Python: `beautifulsoup4` (import opzionale; lancia `ImportError` all'istanziazione)

### Avvio Rapido

```bash
# Pull e avvio FlareSolverr
docker pull ghcr.io/flaresolverr/flaresolverr:v3.4.6
docker run -d --name flaresolverr -p 8191:8191 \
    -e LOG_LEVEL=info -e TZ=America/Sao_Paulo \
    --restart unless-stopped \
    ghcr.io/flaresolverr/flaresolverr:v3.4.6

# Verifica health
curl http://localhost:8191/
```

### Logging

Tutti i moduli usano logging strutturato tramite `get_logger("cs2analyzer.<modulo>")`:
- `cs2analyzer.docker_manager` -- eventi ciclo di vita container
- `cs2analyzer.flaresolverr` -- interazioni API REST FlareSolverr
- `cs2analyzer.hltv.rate_limit` -- livello ritardo e durata sleep
- `cs2analyzer.hltv_stat_fetcher` -- scoperta giocatori, parsing, persistenza database

### Configurazione

| Impostazione | Default | Descrizione |
|--------------|---------|-------------|
| `HLTV_SCRAPING_ENABLED` | `"true"` | Interruttore principale per abilitare/disabilitare lo scraping |

### Manutenzione Selettori

Quando HLTV modifica il layout delle pagine, aggiornare i selettori CSS in due punti:
1. `selectors.py` -- classe `PlayerStatsSelectors` (righe tabella, colonna nome, colonna rating)
2. `stat_fetcher.py` -- chiamate `soup.select()` inline nei metodi di parsing

### Gestione Sessioni FlareSolverr

`FlareSolverrClient` supporta sessioni browser persistenti per il riutilizzo dei cookie tra piu
richieste. Le sessioni vengono create con `create_session()` e distrutte con `destroy_session()`.
Se nessuna sessione e attiva, ogni richiesta crea un contesto browser nuovo.

### Invarianti Chiave

| ID | Regola |
|----|--------|
| P-SAN-01 | KAST convertito da percentuale (74.0) a rapporto (0.74) prima del salvataggio |
| D-23 | `robots.txt` controllato prima di ogni ciclo di sync; interrompe se vietato |
| DS-05 | Percorso `project_root` risolto e validato prima del `cwd` subprocess |
| DS-07 | Fallimenti fetch sotto-pagine loggati a WARNING, non interrompono il fetch giocatore |
| F6-05 | Ritardo rate limiter loggato a DEBUG con nome del livello |
| F6-25 | Jitter casuale intenzionalmente non seedato per evitare pattern rilevabili |
