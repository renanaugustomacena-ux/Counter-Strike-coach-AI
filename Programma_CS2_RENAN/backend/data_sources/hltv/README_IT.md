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
- Scopre automaticamente gli URL dei giocatori tramite il ranking mondiale dei team HLTV (top 30 team, ~150 giocatori). Ricade su `/stats/players` se la discovery via team restituisce zero
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
| `__init__.py` | 0 | Inizializzazione pacchetto (marcatore vuoto) |
| `docker_manager.py` | 138 | Ciclo di vita container Docker/FlareSolverr: `ensure_flaresolverr()`, health-check, `stop_flaresolverr()` |
| `flaresolverr_client.py` | 140 | Client REST per API FlareSolverr: gestione sessioni (`create_session`/`destroy_session`), `get()` tramite proxy |
| `stat_fetcher.py` | 676 | `HLTVStatFetcher`: discovery (`fetch_top_teams`, `fetch_top_players`), parsing HTML tramite `soup.select()` inline, rate limiting tramite `CRAWL_DELAY_MIN/MAX_SECONDS`, persistenza database |

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
3. **Scoperta**: `fetch_top_teams(count=30)` effettua scraping di `/ranking/teams/` (conforme a
   robots.txt) per estrarre i team top e i loro roster, ottenendo ~150 URL statistiche giocatore.
   Se la discovery via team restituisce zero, il chiamante ricade su `fetch_top_players()` che
   punta a `/stats/players` (nota: `/stats/players?rankingFilter=Top50` e vietato da
   `robots.txt` HLTV al 2026-04-12 — vedi stat_fetcher.py:57-108).
4. **Fetch per giocatore**: Per ogni URL giocatore, `fetch_and_save_player()` avvia un deep crawl:
   - Pagina panoramica: Rating 2.0, KPR, DPR, ADR, KAST, HS%, Impact, Maps Played
   - Sezioni trait: Firepower, Entrying, Utility (analizzate dalla stessa pagina)
   - Sotto-pagine: Clutches, Multikills, Storico carriera (richieste HTTP separate per ciascuna)
5. **Parsing**: BeautifulSoup4 analizza le risposte HTML usando selettori CSS definiti inline
   in `stat_fetcher.py` tramite `soup.select()` con fallback multi-selettore (`_select_fallback()`).
6. **Persistenza**: I dati analizzati vengono inseriti/aggiornati nelle tabelle `ProPlayer` e
   `ProPlayerStatCard` in `hltv_metadata.db` tramite SQLModel. Il KAST viene convertito da
   percentuale a rapporto (P-SAN-01).

---

## Rate Limiting

Il rate limiting e implementato direttamente in `stat_fetcher.py` come costanti a livello di
modulo, non come classe separata:

```python
CRAWL_DELAY_MIN_SECONDS = 2  # stat_fetcher.py:50
CRAWL_DELAY_MAX_SECONDS = 7  # stat_fetcher.py:51
```

Ogni richiesta HTTP attraverso FlareSolverr e preceduta da
`time.sleep(random.uniform(CRAWL_DELAY_MIN_SECONDS, CRAWL_DELAY_MIN_SECONDS + 2))` o
equivalente (vedi stat_fetcher.py:201, 239). Il ritardo effettivo tra due richieste
qualsiasi e quindi di **2.0-7.0 secondi** con jitter uniforme.

Il jitter casuale e intenzionalmente **non seedato** (F6-25): un jitter deterministico
creerebbe pattern di richiesta rilevabili. Il rilevamento anti-scraping si basa su casualita
apparentemente umana. Sleep aggiuntivi di dormienza (un'ora tra cicli di sync, sei ore quando
HLTV e irraggiungibile) sono applicati dal chiamante `hltv_sync_service.run_sync_loop()`.

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
- `cs2analyzer.hltv_stat_fetcher` -- scoperta giocatori, parsing, persistenza database

### Configurazione

| Impostazione | Default | Descrizione |
|--------------|---------|-------------|
| `HLTV_SCRAPING_ENABLED` | `"true"` | Interruttore principale per abilitare/disabilitare lo scraping |

### Manutenzione Selettori

Quando HLTV modifica il layout delle pagine, aggiornare i selettori CSS inline in
`stat_fetcher.py`. L'helper `_select_fallback()` (stat_fetcher.py:131-156) accetta una lista
ordinata di selettori candidati e logga un warning quando il selettore primario fallisce e
un fallback viene attivato, cosicche la drift di layout venga rilevata precocemente senza
interrompere lo scraping. Ispezionare i log WARNING per messaggi "CSS fallback activated" e
aggiungere nuovi selettori primari sopra quelli esistenti.

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
