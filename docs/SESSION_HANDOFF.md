# SESSION HANDOFF — ripresa sviluppo su Linux (box dati SSD)

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
