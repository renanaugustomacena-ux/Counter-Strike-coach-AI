> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Data Sources -- Integrazioni Esterne

> **Autorita:** `backend/data_sources/`
> **Skill:** `/resilience-check`, `/api-contract-review`, `/security-scan`
> **Consumatori:** `ingestion/`, `backend/services/`, `backend/coaching/pro_bridge.py`

## Panoramica

Il pacchetto data sources e il livello di confine tra il CS2 Analyzer e tutti i sistemi
esterni. Fornisce adapter per il parsing di file demo, ricerche profili Steam, recupero
cronologia partite FACEIT e scraping di statistiche giocatori professionisti da HLTV.
Ogni integrazione esterna risiede qui affinche il resto del codebase non tocchi mai
direttamente I/O grezzo, client HTTP o formati dati di terze parti.

Il pacchetto segue un rigoroso principio di **zero-trust ai confini**: tutti i dati
provenienti da fonti esterne vengono validati, normalizzati e convertiti in schemi
interni prima di essere passati ai consumatori a valle.

> **IMPORTANTE -- Chiarimento HLTV:**
> L'integrazione HLTV raccoglie **statistiche di giocatori professionisti** da hltv.org
> (Rating 2.0, K/D, ADR, KAST, HS%, statistiche clutch, storia carriera). **NON**
> scarica demo, non recupera metadati demo e non interagisce con file .dem in alcun modo.
> Lo scraper HLTV e il demo parser sono sottosistemi completamente indipendenti.

## Inventario File

| File | Esportazione Primaria | Scopo |
|------|----------------------|-------|
| `__init__.py` | Root pacchetto | (vuoto -- solo namespace) |
| `demo_parser.py` | `parse_demo()` | Wrapper demoparser2 con calcolo rating HLTV 2.0, esporta dati per-tick e per-round |
| `demo_format_adapter.py` | `DemoFormatAdapter` | Validazione e conversione formato tra output demo parser e schemi interni (`MIN_DEMO_SIZE=10MB`) |
| `event_registry.py` | Dispatch eventi | Registrazione e dispatch tipi evento per eventi demo (kills, plant, defuse, ecc.) |
| `trade_kill_detector.py` | `TradeKillDetector` | Identifica trade frags da dati tick usando una finestra scorrevole di 3 secondi |
| `round_context.py` | Helper contesto round | Arricchisce dati per-round con metadati contestuali (stato economia, controllo sito, ecc.) |
| `steam_api.py` | `SteamAPI` | Integrazione Steam Web API per sincronizzazione profilo, lista amici, statistiche gioco |
| `steam_demo_finder.py` | `SteamDemoFinder` | Localizza file demo CS2 in directory userdata Steam sul filesystem locale |
| `faceit_api.py` | `FaceitAPI` | Wrapper API piattaforma FACEIT per cronologia partite e statistiche giocatore |
| `faceit_integration.py` | `FaceitIntegration` | Orchestrazione ingestione dati FACEIT di alto livello |
| `hltv_scraper.py` | `HLTVScraper` | Raccoglie statistiche giocatori professionisti da hltv.org (Rating 2.0, K/D, ADR, KAST, HS%) |
| `hltv/` | Sotto-pacchetto | Implementazione HLTV attiva: client FlareSolverr, gestore Docker, fetcher statistiche (selettori CSS + rate limiting inline) |

### Sotto-Pacchetto HLTV (`hltv/`)

| File | Scopo |
|------|-------|
| `__init__.py` | Root sotto-pacchetto (marcatore namespace vuoto) |
| `flaresolverr_client.py` | Client REST che invia richieste al container FlareSolverr locale (porta 8191) per bypassare Cloudflare |
| `docker_manager.py` | Gestisce il ciclo di vita del container Docker FlareSolverr (`docker start`, `docker compose up -d`, health check) |
| `stat_fetcher.py` | `HLTVStatFetcher`: discovery, parsing HTML, persistenza. Selettori CSS inline via `soup.select()`; rate limiting via `CRAWL_DELAY_MIN/MAX_SECONDS` (2-7s) + `random.uniform()` |

## Diagramma Flusso Dati

```
                    Sistemi Esterni
                    ===============

  file .dem        Steam Web API      API FACEIT        hltv.org
      |                 |                 |                 |
      v                 v                 v                 v
 demo_parser.py    steam_api.py     faceit_api.py    hltv_scraper.py
      |                 |                 |                 |
      v                 |                 v                 |
 demo_format_         steam_demo_    faceit_          hltv/ sotto-pacchetto
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
        Schemi Interni
     (pipeline ingestion/,
      backend/storage/,
      match_data/<id>.db)
```

## Descrizioni Moduli

### demo_parser.py -- parse_demo()

La funzione centrale di parsing demo. Incapsula la libreria `demoparser2` per estrarre
lo stato del giocatore per-tick (posizione, salute, armatura, equipaggiamento) e
statistiche aggregate per-round (kills, deaths, assist, danno). Calcola il rating
HLTV 2.0 in tempo reale durante il parsing. Restituisce dati strutturati pronti per la
pipeline di ingestione. Questo e uno dei moduli piu critici per le prestazioni nel
sistema, elaborando milioni di righe tick per demo.

### demo_format_adapter.py -- DemoFormatAdapter

Valida e converte l'output del demo parser in schemi interni. Applica `MIN_DEMO_SIZE
= 10 MB` (invariante DS-12) per rifiutare file demo troncati o corrotti -- le demo CS2
reali sono 50+ MB. Esegue allineamento schema affinche i consumatori a valle (feature
engineering, archiviazione database) ricevano una forma dati consistente indipendentemente
dai cambiamenti di versione del parser.

### event_registry.py -- Dispatch Eventi

Registra e invia eventi demo (player_death, bomb_planted, bomb_defused, round_start,
round_end, ecc.) agli abbonati. Usa un pattern observer cosi che piu moduli di analisi
possano reagire allo stesso flusso di eventi senza accoppiarsi tra loro.

### trade_kill_detector.py -- TradeKillDetector

Modulo di analisi post-parse che identifica trade frags da dati kill a livello tick. Un
trade kill e definito come un kill che avviene entro una finestra di 3 secondi dalla morte
di un compagno, indirizzato allo stesso nemico che ha effettuato il kill originale. I dati
sui trade kill alimentano l'analisi tattica e le raccomandazioni di coaching sulla
disciplina di trade.

### round_context.py -- Helper Contesto Round

Arricchisce i dati per-round con metadati contestuali non direttamente presenti
nell'output grezzo della demo. Calcola campi derivati come vantaggio economico, metriche
di controllo sito e pattern di utilizzo utilita. Questo arricchimento contestuale aiuta
i moduli di coaching a valle a produrre consigli piu pertinenti.

### steam_api.py -- SteamAPI

Integrazione con la Steam Web API per sincronizzazione profilo. Recupera informazioni
profilo giocatore, lista amici e statistiche di gioco specifiche CS2. Richiede una chiave
API Steam memorizzata tramite il sistema credenziali (`get_credential("STEAM_API_KEY")`).
Include logica di retry e rate limiting per gestire fallimenti transienti dell'API.

### steam_demo_finder.py -- SteamDemoFinder

Localizza file demo CS2 sul filesystem locale scansionando directory userdata Steam note.
Consapevole della piattaforma (Windows, Linux, macOS). Usato dalla pipeline di ingestione
per scoprire nuove demo per elaborazione automatizzata senza richiedere all'utente di
specificare manualmente i percorsi file.

### faceit_api.py -- FaceitAPI

Wrapper di basso livello attorno all'API della piattaforma FACEIT. Recupera cronologia
partite, statistiche giocatore e rating ELO. Richiede una chiave API FACEIT memorizzata
tramite il sistema credenziali. Gestisce paginazione, rate limiting e risposte di errore
dall'API FACEIT.

### faceit_integration.py -- FaceitIntegration

Livello di orchestrazione di alto livello che coordina l'ingestione dati FACEIT. Gestisce
il flusso dalle chiamate API attraverso la normalizzazione dati fino all'archiviazione
database. Fornisce un singolo punto di ingresso `sync_player()` che gestisce l'intero
ciclo di vita del recupero e persistenza dati FACEIT per un dato giocatore.

### hltv_scraper.py -- HLTVScraper

Raccoglie statistiche di giocatori professionisti da hltv.org. Estrae: Rating 2.0,
rapporto K/D, ADR (Danno Medio per Round), percentuale KAST, HS% (percentuale
headshot), statistiche clutch e storia carriera. I dati vengono salvati in
`hltv_metadata.db` nelle tabelle `ProPlayer`, `ProPlayerStatCard` e `ProTeam`.
**Questo modulo raccoglie solo statistiche -- non ha alcuna connessione con la gestione
dei file demo.**

### Sotto-pacchetto hltv/

L'implementazione HLTV attiva che gestisce il recupero di pagine protette da Cloudflare.
`docker_manager.py` gestisce il ciclo di vita del container FlareSolverr,
`flaresolverr_client.py` instrada le richieste HTTP attraverso di esso, e
`stat_fetcher.py` orchestra discovery, parsing HTML (selettori CSS inline via
BeautifulSoup4), rate limiting (crawl delay randomizzato 2-7 secondi) e persistenza
database.

## Punti di Integrazione

| Consumatore | Modulo Data Source | Cosa Riceve |
|-------------|-------------------|-------------|
| Pipeline `ingestion/` | `demo_parser.py`, `demo_format_adapter.py` | Dati demo parsati e validati per archiviazione database |
| `backend/processing/` | `event_registry.py`, `trade_kill_detector.py` | Flussi eventi e analisi trade kill per feature engineering |
| `backend/coaching/pro_bridge.py` | `hltv_scraper.py` (via `hltv_metadata.db`) | Baseline giocatori professionisti per confronto coaching |
| `backend/services/` | `steam_api.py`, `faceit_integration.py` | Dati profilo giocatore per contesto sessione |
| `core/session_engine.py` | `steam_demo_finder.py` | Percorsi file demo auto-scoperti per l'IngestionWatcher |

## Note di Sviluppo

- **Validazione ai confini:** Tutti i dati esterni devono essere validati prima di
  attraversare gli schemi interni. Non fidarsi mai di risposte API grezze o output parser
  senza controlli schema.
- **Gestione credenziali:** Le chiavi API (Steam, FACEIT) sono memorizzate tramite
  `get_credential()` da `core/config.py`. Non hard-codare mai segreti o loggarli.
- **Invariante MIN_DEMO_SIZE:** `demo_format_adapter.py` applica `MIN_DEMO_SIZE = 10 MB`
  (invariante DS-12). Non abbassare questa soglia -- demo troncate causano corruzione
  silenziosa nell'elaborazione a valle.
- **HLTV e solo statistiche:** L'integrazione HLTV recupera statistiche di giocatori
  professionisti. Non scarica demo, non gestisce file .dem e non interagisce con la
  pipeline di ingestione demo. Confondere HLTV con la gestione demo e un anti-pattern
  documentato.
- **Dipendenza Docker:** Lo scraper HLTV richiede FlareSolverr in esecuzione in Docker
  per bypassare Cloudflare. `hltv/docker_manager.py` gestisce il ciclo di vita del
  container.
- **Logging strutturato:** Tutti i moduli usano
  `get_logger("cs2analyzer.data_sources.<modulo>")`.
- **Rate limiting:** Sia HLTV che le integrazioni Steam includono rate limiting. Non
  bypassare i rate limit -- porta a ban IP.
- **Testing:** Usa `mock_db_manager` per test dipendenti dal database. Test HLTV e API
  richiedono `@pytest.mark.integration` e `CS2_INTEGRATION_TESTS=1`.

## Dipendenze

- **demoparser2** -- Motore di parsing file demo CS2
- **FlareSolverr/Docker** -- Bypass Cloudflare per scraping HLTV
- **requests** -- Client HTTP per API Steam e FACEIT
- **BeautifulSoup4** -- Parsing HTML per pagine HLTV
- **SQLModel** -- Persistenza database per statistiche giocatori pro
