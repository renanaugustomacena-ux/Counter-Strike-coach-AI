# SESSION HANDOFF — ripresa sviluppo (Linux ⇄ Windows)

> Sezione **2026-07-26** in testa; lo storico 2026-07-17 segue più sotto ed è ancora
> valido per convenzioni operative e invarianti (fondo file).

---

## LEGGI PRIMA — dove si trova il progetto (2026-07-26)

Il **codice è al sicuro**: tutto su GitHub, `renanaugustomacena-ux/Counter-Strike-coach-AI`.
Un `git clone` ricostruisce il 100% del codice. Nessun disco può perderlo.

I **dati non sono in git**. Stato reale:

| Cosa | Dimensione | Dove | Se sparisce |
|---|---|---|---|
| `database.db` (monolite) | **254 G** | `New Volume6` — SATA **USB**, NTFS, `/dev/sdc1` | ricostruibile dai demo, costa ore di re-parse |
| shard per-match (314) | 41 G | `/data/PROIECT/DEMO_PRO_PLAYERS/match_data` — **NVMe interno**, ext4 | ricostruibili dal monolite |
| demo pool `.dem` (98) | 42 G | `/data/PROIECT/DEMO_PRO_PLAYERS/` — NVMe interno | riscaricabili da HLTV |
| archivi HLTV `.rar` (34, 31 da estrarre) | 67 G | `New Volume6` — USB | riscaricabili da HLTV |
| `hltv_metadata.db` | 536 K | nel repo, gitignored | ri-scrapabile |
| modelli allenati | 53 M | nel repo (`Programma_CS2_RENAN/models/`) | ri-allenabili |
| backup DB stantio | 178 G | `WORK_RECOVERED` — `database.db.old_20260721`, ~4 h indietro | cancellabile |

**Niente qui è irrecuperabile.** I 96 demo che alimentano il training esistono ancora
come `.dem` su `/data`. I 259 demo storici i cui sorgenti sono persi sono già
permanentemente ineleggibili (shard schema-only): zavorra, non tesoro.

### Cosa si rompe cambiando macchina — esattamente 3 righe

```
Programma_CS2_RENAN/backend/storage/database.db -> /media/renan/New Volume6/AI/database.db
Programma_CS2_RENAN/backend/storage/match_data  -> /data/PROIECT/DEMO_PRO_PLAYERS/match_data
PRO_DEMO_PATH  (in user_settings.json — punta a un disco morto)
```

Due symlink e un setting. Tutto il resto arriva da GitHub.

## RIPRESA SU WINDOWS — procedura

1. **Su Windows**: `git clone` o `git pull`. Il codice è completo e i test girano.
   `venv_win` esiste già; ricetta `requirements-ci.txt` + pytest + pre-commit + rap.
2. **Windows NON vede** `/data` (ext4) né i symlink Linux. Aspettati:
   - `backend/storage/match_data` assente → il codice crea una dir vuota (comportamento
     corretto di primo avvio, **non** perdita dati).
   - `backend/storage/database.db` assente → niente monolite.
   Quindi su Windows: **sviluppo, test e review sì — ingestion e training no**, a meno
   di ricollegare i dischi e ripuntare i path.
3. **Fast Startup di Windows sporca i volumi NTFS.** Esegui una volta `powercfg /h off`,
   oppure spegni sempre con `shutdown /s /f /t 0`. Altrimenti al ritorno su Linux i
   dischi tornano *dirty*, udisks li monta con `force` e alcuni non si montano affatto.
4. **Al ritorno su Linux**: ricollegare i dischi e verificare
   `ls Programma_CS2_RENAN/backend/storage/match_data/*.db | wc -l` → deve dare **314**.
   Se un symlink è rotto l'app ora **fallisce con un errore chiaro** invece di
   cancellarlo (fix di oggi): segui le istruzioni nel messaggio.

## Stato al 2026-07-26 (fine sessione Linux)

### Git
- **PR #41 MERGIATA** — `8f92b66` (merge commit, 6 commit conservati): campagna
  patch-14160 (demoparser2 0.41.4, numerazione round ordinale, archive best-effort,
  RNN su ATen per ROCm, bf16 autocast, scoreboard all'ultimo tick, split eleggibili).
- **PR #42 APERTA** — branch `fix/split-eligibility-hardening`, MERGEABLE, CI verde.
  **Va revisionata e mergiata.** Sei difetti, tutti trovati confrontando ciò che il
  sistema *dichiara* con ciò che è davvero su disco (la suite era verde per tutti):
  1. Frammenti `-p1`/`-p2` (2/5/6/7/9 round) dentro TRAIN, uno con aggregati tutti 0.0
     → gate `MIN_COMPLETE_MAP_ROUNDS = 13` + aggregati non-zero.
  2. **Leak train/test**: `temporal_assign` tagliava la lista di *righe*, non di match;
     due partite avevano giocatori su entrambi i lati del confine. Ora si taglia fra match.
  3. Un solo shard illeggibile azzerava tutto il segnale di completezza (`None` → gate
     disattivato → rientravano i 259 demo storici). Ora per-item.
  4. `PRO_DEMO_PATH` defaultava a `$HOME` → radice shard a `~/match_data`.
  5. La "one-time migration" in `get_match_data_manager()` **spostava** l'intero corpus
     shard come effetto collaterale della costruzione del singleton.
  6. Un symlink `match_data` rotto veniva **cancellato** e sostituito da una dir vuota.
- `main` è protetto: solo PR.

### Dati / infrastruttura
- **Shard consolidati**: 314 file, 43.5 G, tutti verificati SHA-256, su
  `/data/PROIECT/DEMO_PRO_PLAYERS/match_data` (percorso canonico del codebase).
  `~/match_data` (fallback storico) rimosso.
- **45 shard "persi"** dal volume NTFS: **recuperati tutti**. Erano stati *spostati* dal
  bug 5, non corrotti — la diagnosi iniziale di corruzione NTFS era sbagliata.
- Disco `/` recuperato da 0 → 42 G liberi (cache pip/npm/chrome/puppeteer/trivy purgate).
- `match_data.old_20260721` cancellato (41 shard verificati superati).
- `IngestionTask` id=5 (bloccato in `processing` dal 2026-06-04, path su disco morto)
  marcato `failed`.

### Split applicati al DB live
```
TRAIN 63 demo / VAL 14 / TEST 14   (91 eleggibili)
UNASSIGNED 261
demo a cavallo di due split: 0     frammenti rimasti negli split: 0
```

### Dry run training — passato fino a metà
`run_full_training_cycle.py --dry-run` su RX 9070 XT (ROCm 7.2):
```
Data Quality Report: PASS — 619,843,348 tick, zero-position 0.15%
Resumed from jepa_brain, best_val_loss=0.006491 ripristinato
B1-XL: 4545/124,397,700 tick TRAIN · 909/30,759,370 VAL
Epoch 1/1 | Train 0.1516 | Val 0.0117
GPU reclaimed after JEPA — 15666 MB free
>>> Phase 2: RAP Coach Training <<<   ← interrotto qui su richiesta utente
```
Nessun crash MIOpen, nessun OOM. **Fase JEPA verificata end-to-end; fase RAP mai
completata** — primo punto da riprendere.

### Costi misurati (per pianificare)
- Il `COUNT(*)` di eleggibilità cammina ~10⁸ voci di indice: **~13 min** sul monolite via
  USB. È **cachato per processo** (`_fetch_scale_cache`): si paga una volta per run, non
  per epoca. TRAIN e VAL hanno chiavi cache separate.
- Per quasi tutto il run: `state=Dl`, GPU al 3-6%. Il carico è **I/O-bound sull'USB**, non
  compute-bound. Spostare il monolite su NVMe è la prossima vera vittoria di performance
  (servono ~271 G liberi: nessun volume montato oggi li ha).
- Per-epoca dopo la cache: ~25 s. 100 epoche ≈ 1-2 h per fase.

## PROSSIMI PASSI (in ordine)

1. **Revisionare e mergiare PR #42.**
2. **Lanciare il training reale**:
   ```bash
   .venv/bin/python run_full_training_cycle.py            # 100 epoche, JEPA + RAP
   tail -f Programma_CS2_RENAN/logs/cs2_analyzer.log      # <-- il log VERO (INFO)
   ```
   La console logga solo WARNING+; l'INFO va in `Programma_CS2_RENAN/logs/cs2_analyzer.log`
   (NON quello nella root del repo). `train.sh` punta a `~/.venvs/cs2analyzer`, che **non
   esiste** su questa macchina: usa `.venv/` direttamente o correggi lo script.
3. **`data_quality.py:117-130`** — 4ª istanza dello stesso bug: l'enumerazione shard è in
   un solo `try` con `except Exception: logger.debug(...)`, quindi il primo shard legacy
   (`match_181401633`, primo in ordine numerico) la aborta all'**iterazione 0**. Il report
   stampa `Complete matches: 0, Incomplete: 0` (vero: 96) e dice comunque **PASS**. Solo
   informativo — il gate usa il percorso corretto — ma è un numero falso in un report
   verde. Fix: stesso trattamento per-item + alzare il log da `debug` a `warning`.
4. **`match_date` è il timestamp di ingestion, non la data della partita.** Lo split
   "cronologico anti-leak" ordina di fatto per ordine di ingestion. `matchresult.date` è
   pure un timestamp di ingestion e `hltv_metadata.db` non ha date per demo. Serve una
   fonte vera (metadata evento HLTV o header del demo).
5. **Rehome `PRO_DEMO_PATH`** → `/data/PROIECT/DEMO_PRO_PLAYERS`. Ora è **sicuro**: la
   consolidazione ha già messo `match_data` sotto quel path, quindi `MATCH_DATA_PATH`
   risolve dove il symlink punta già. Il rischio split-brain non c'è più.
6. **31 archivi HLTV** ancora da estrarre/ingestare (3 di 34 fatti).
7. **6 part-demo** ancora ingeriti come partite separate: il gate li tiene fuori dagli
   split, ma unirli (`-p1` + `-p2` = una mappa) recupererebbe dati di training reali.
8. **Audit numerazione round su tutto il DB**: 47 demo storici con
   `data_quality='full_sql_round_count_anomaly'` (461 righe, ingest 2026-05-08). Tutti in
   UNASSIGNED, non toccano il training oggi.

## Note operative aggiunte oggi
- **Mai** aprire SQLite su NTFS con `?mode=ro`: crea comunque `-shm`/`-wal` e può fare
  checkpoint. Usa `?immutable=1&mode=ro` per letture davvero non distruttive.
- Prima di scrivere su un mount `/media/...`: `findmnt <path> -o OPTIONS`; se compare
  `force`, il volume era *dirty* (Fast Startup).
- `checkpoint_hashes.json` è tracciato ma riscritto a runtime con path assoluti (porta già
  i path di tre macchine morte): sporca il worktree a ogni salvataggio. Valutare gitignore.
- `pgrep -f "<pattern>"` matcha anche il processo che lo esegue: un `until ! pgrep -f ...`
  non termina mai. Usare un pattern che non può auto-matcharsi (es. `[v]env/bin/python`).

---

## Storico — sessione 2026-07-17

> Scritto il 2026-07-17 a fine sessione Windows (`C:\PROIECT`). Questo file è il ponte
> di contesto per la prossima sessione: la roadmap operativa vive in `TASKS.md`
> (tracciato in git da oggi), i dettagli tecnici dei fix vivono nei commit message.
> Le copie locali gitignorate (`AUDIT.md`, `CLAUDE.md`, `REFERENCE.md`) esistono già
> sulla copia SSD ma sono ferme al 2026-07-16: la sezione "findings pass-2" di
> AUDIT.md è riassunta qui sotto perché non viaggia col pull.

## Stato al 2026-07-17 (fine sessione Windows)

- **Campagna R4 COMPLETA 173/173** (4 CRIT / 23 HIGH / 79 MED / 67 LOW) — PR #26→#31.
- **Orphan sweep** (PR #32): −14 moduli mai importati (~2200 righe, hash di origine nel
  commit); dead-code detector ora `--strict` e CRITICO in `tools/dev_health.py`
  (baseline Clean vincolante); compile-gate AST su tutti i 77 script tooling in suite.
- **R5 sicurezza dipendenze** (PR #33): pillow 12.3.0 ovunque; lockfile rigenerati dal
  venv verificato — il vecchio `requirements-lock-cpu.txt` PREDATAVA lo stack RAP/RAG
  (una release da quel lock spediva il coach senza hopfield/ncps/faiss/sbert);
  `requirements-dist.txt` = chiusura transitiva calcolata (86 pkg, hopfield pinnato a
  commit git); PyInstaller 6.17.0 pinnato in build.yml; VEX transformers (4 RCE
  untrusted-model, not_affected: unico modello = all-MiniLM-L6-v2 hard-coded) nelle
  prime due entry di `SECURITY/CVE_LOG.md`. Bump a transformers 5.x = decisione R6.
- **Pass-2 sweep dei tool DB-mutanti** (PR #35, commit `359502b` + `015f942`):
  11 finding, tutti FIXED — dettaglio sotto.
- Suite: **2305 verdi** + validator PASS 318/319 (unico escluso by-design: perf canary
  RAP, che sul laptop dev va in timeout SOLO per throttling termico — verde su CI e a
  macchina fresca; per run locali sotto carico: `CS2_LATENCY_MULTIPLIER=4`).
- Repo: **un solo branch (main)**, zero PR aperte, storia lineare.
- **Verifica E2E reale**: re-ingest completo di `vitality-vs-the-mongolz-m1-mirage`
  attraverso `run_ingestion._ingest_single_demo` → 2.127.460 tick, 300 RoundStats,
  10/10 player con enrichment REALE (ZywOo: trade 0.077, opening 0.75, 50.7s blind).

## Findings pass-2 (sintesi di AUDIT.md §13 — non viaggia col pull)

| ID | Sev | Cosa | Stato |
|---|---|---|---|
| P2-01 | CRIT | Nessuna pipeline di ingestione scriveva RoundStats/enrichment (F6-19): i 14 campi Class-B restavano 0.0 e coach_manager li confrontava coi pro → segnale coaching fabbricato | FIXED: SSOT `round_stats_builder.persist_round_stats_and_enrichment()` chiamata da run_ingestion e user_ingest |
| P2-02 | CRIT | Le demo CS2 NON emettono `player_blind` (evento CS:GO) → flash_assists / utility_blind_time / utility_enemies_blinded / blind_kill_pct strutturalmente 0.0 per TUTTI, pro inclusi | FIXED: sintesi da transizioni per-tick di `flash_duration` attribuite via `flashbang_detonate` (+5 test) |
| P2-03 | HIGH | Il pre-flight di `wipe_for_reingest_safe` crashava il processo su Windows (access violation nativa in psutil open_files) | FIXED: rename-probe su win32 |
| P2-04 | HIGH | Il restore del wipe non rimuoveva i `-wal`/`-shm` correnti → replay di WAL post-snapshot sopra il DB ripristinato | FIXED (+test) |
| P2-05 | HIGH | `ingest_pro_demos --full` cancellava TUTTA playertickstate (anche le demo utente) dichiarando "pro only" | FIXED: DELETE scoped sugli stem pro; rimosso il monkeypatch globale del dedup |
| P2-06 | MED | Finestre dello strategy miner baked a 64 tick (dimezzate sui 128-tick) | FIXED: secondi × `match_metadata.tick_rate` per-shard (+2 test) |
| P2-07 | MED | Join case-sensitive vs chiavi lowercase: `populate_round_stats` (enrichment) e `repair_tick_features` (4 colonne del vettore 25-dim) saltavano ogni nick mixed-case ("ZywOo") | FIXED: LOWER() da entrambi i lati (+2 test) |
| P2-08 | MED | `repair_ratings` scriveva rating_* NORMALIZZATI (la classe ratio-corruption di R4) | FIXED: verbatim dalla SSOT `compute_rating_components` |
| P2-09 | MED | `populate_match_results`: winner = coin flip (CT-start associato a team_a del filename senza base dati) | FIXED: outcome per starting-side only, max() sul gruppo, json.dumps (+3 test) |
| P2-10 | MED | `d3_recover_shard_metadata` scriveva tick_rate=64 hardcoded + team name fabbricati nei metadata ricostruiti | FIXED: header-derived (GAP-01), sentinel onesti, marker `v2-*` |
| P2-11 | LOW | `mine_shard_strategies --fresh` troncava TUTTA coachingexperience dichiarando "miner rows" | FIXED: DELETE WHERE strategy_label IS NOT NULL |

## DA FARE SUBITO su Linux — sessione dati sul monolite (in ordine)

Sul box dati il monolite è locale (niente WSL): percorsi tipo
`/media/renan/New Volume/PROIECT/Counter-Strike-coach-AI/...`, venv canonica
`~/.venvs/cs2analyzer`. Dopo `git pull`:

1. `python tools/repair_rating_scale.py --db <monolite> --commit`
   (fase 1: ricalcolo rating_* delle 2501 righe `full_sql*` ratio→raw; fase 2:
   riparazione impact_rounds dai RoundStats. Dry-run già verificato; backup CSV +
   transazione + verifica post inclusi. Una copia del tool sta anche in
   `PROIECT/repair_rating_scale.py` sull'SSD, ma post-pull usare quella del repo.)
2. `python tools/repair_tick_features.py` — POST-fix P2-07: i player mixed-case hanno
   ancora is_crouching/is_blinded/has_helmet/has_defuser rotti sul monolite.
3. `python tools/populate_round_stats.py --full` — POST-fix P2-02/P2-07: rienrichisce
   TUTTI i pro (metriche blind ora sintetizzabili + mixed-case ora matchati).
4. `python tools/populate_match_results.py --full` — rigenera le righe `demo:%` il cui
   winner era un coin flip.
5. Verificare le righe `match_metadata` con `parser_version='v1-d3-recovered'`
   (tick_rate 64 hardcoded) e ri-derivarle dagli header (il tool fixato marca `v2-*`).
6. `alembic upgrade head` — porta l'indice JEPA `e5f6a7b8c9d0` sul box dati.
   OBBLIGATORIO prima del retrain R8.

Dopo la sessione dati, la coda della roadmap (dettagli in `TASKS.md`):
**R6** decisioni owner (26-SCHEMA-02 connect-feature; 26-NORM-01 SSOT tick-rate;
eslint web; bump sentence-transformers→transformers 5.x con re-embedding RAG +
EMBEDDING_VERSION) → **R7** studio JEPA (zero codice runtime) → **R8** retrain
(owner-gated) → **R9** post-retrain (wiring Platt/Elo win-prob, F1.5 A/B, #48, #64)
→ **R10** documentazione trilingue (per ULTIMA) → **R11** training finale →
**R12** riscrittura storia git (a fine lavori, ok esplicito owner).

Residui minori noti: Ollama da installare per la chat live (modello ≤8B, es.
gemma leggero); ispezione estetica UI su display reale; thin-baseline locale
(soglia min 10 righe da rivalutare); directory di archivio demo in home utente
da rivedere.

## Convenzioni operative della sessione (collaudate, non regredire)

- **Flusso commit**: `pre-commit run --files <files>` → `python
  Programma_CS2_RENAN/tools/sync_integrity_manifest.py` → `git add` → `git commit -F
  <msgfile>`. MAI leggere l'exit di una pipe (`cmd | tail` maschera il codice: usare
  `set -o pipefail` o `; EXIT=$?`).
- **Flusso PR**: branch `fix/s-*`, push, PR con body Problem/Solution/Verification/
  Risk, attendere CI verde (17 SUCCESS + 2 SKIPPED by-design), `gh pr merge N --rebase
  --delete-branch`, `git checkout main && git fetch --prune && git reset --hard
  origin/main`, eliminare il branch locale. La repo deve restare a UN branch.
- **Gate obbligatori post-task**: suite `pytest Programma_CS2_RENAN/tests/ tests/ -m
  "not slow and not integration"` (≥2305 attesi) + `python tools/headless_validator.py`
  exit 0. Il dead-code detector è CRITICO in `tools/dev_health.py` (baseline Clean).
- **TASKS.md è tracciato in git** (da 2026-07-17): aggiornarlo nei commit, niente
  sync manuale. `AUDIT.md`/`CLAUDE.md`/`REFERENCE.md` restano locali (gitignored) —
  su questa copia SSD esistono già.
- Invarianti supremi (violazione = corruzione silenziosa): tick decimation FORBIDDEN;
  `GLOBAL_SEED=42`; METADATA_DIM=25; rating_* = componenti RAW (normalizzazione SOLO
  nell'aggregato `rating`); KAST ratio [0,1]; impact_rounds = share [0,1]; tick rate
  SEMPRE per-demo dall'header/metadata, mai 64 hardcodato; niente dati fabbricati —
  meglio un sentinel documentato di uno zero plausibile.
