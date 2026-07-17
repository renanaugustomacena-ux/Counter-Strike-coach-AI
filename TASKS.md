# TASKS.md — Macena CS2 Analyzer Backlog

> **RIPRESA SESSIONE (Linux/SSD): leggere PRIMA `docs/SESSION_HANDOFF.md`** — stato al
> 2026-07-17, findings pass-2, checklist sessione-dati sul monolite e convenzioni operative.

Single source for actionable work items. Bind to AUDIT.md findings via `(AUDIT §x.y)`. Status: **TODO / WIP / DONE / BLOCKED / DROP**.

> Convention: `#N · status · priority · title — context — owner — date-touched`.

---

## Roadmap di completamento — consolidata 2026-07-16 (sessione Windows `C:\PROIECT`)

> Fusione verificata di: questo backlog + AUDIT §12 (2026-07-02) + git log fino a `b688571` + i 74
> piani storici (consolidati in `docs/plans/`, tutti superseded dal completion programme A–G) + piano
> maestro 10-fasi (`docs/plans/archive/2026-06-26__hello-my-brother-how-groovy-gray.md`). **Phase B
> (training engine) CHIUSA** (`2adbc1b`, probe B5 PASSED). Ordine vincolante dell'autore: capire →
> correggere → verificare → **doc per ULTIMA** → **training finale ULTIMISSIMO**. Verità = codice.
> Sub-agenti solo per ricerca/localizzazione meccanica (≤10, mai ragionamento).

**Contesto macchina (2026-07-16):** clone su `C:\PROIECT\Counter-Strike-coach-AI` (Windows, GTX 1650 —
il laptop dual-boot; il worktree Linux era a `dee4ac0`, questo clone è a `b688571`, 1 commit avanti).
Il monolite dati (429M righe, ~90GB demo) vive sull'SSD (`/mnt/wsl/PHYSICALDRIVE2p1/PROIECT/...`,
raggiungibile via WSL). `venv_win` ricreato qui con la ricetta CI (`requirements-ci.txt` + pytest/
pre-commit + rap). TASKS/AUDIT/CLAUDE.md ricopiati dall'SSD (gitignored — **questa copia è ora la più
aggiornata; risincronizzare verso l'SSD a fine sessione**). I 4 `.bat` "modificati" in `git status` =
residuo EOL atteso (index CRLF storico vs policy `68e998f`): NON committare fuori da un commit di
rinormalizzazione dedicato. Hook pre-commit INSTALLATI su questo clone 2026-07-16 (regola 26-ENV-02;
per i commit: `python` del venv deve stare nel PATH del processo git).

**SESSIONE 2026-07-17 — CAMPAGNA MED COMPLETATA (79/79):** main era ROSSO dal merge PR #26
(tests/forensics/test_skill_logic.py::test_pro_skill_levels — fixture senza rating components sotto
la semantica 0.0-is-real). Indagine → scoperto **bug scala sistemico**: i 3 writer di
PlayerMatchStats.rating_* scrivevano scale DIVERSE (demo_parser/base_features raw; aggregate_
match_stats_sql ratio /BASELINE_*) e la baseline consuma raw → z-score POSITIONING/DECISION corrotti
per ogni riga full_sql*. Verificato sul monolite: 1571/2501 righe full_sql* in scala ratio (survival
max 2.67; anomaly fino a -148). FIX: SSOT `rating.compute_rating_components()` (raw) + parity test
sui 3 writer (`test_rating_components_contract.py`) + fixture forensics realistiche → commit
`4d0530c` sul branch PR #28 → **PR #28 MERGIATA, main VERDE, branch eliminato**. Repair dati
monolite = task dedicato (pre-R8). POI: **batch 6-12 = TUTTI i 44 verdetti MED residui chiusi**
su PR #29 (`fix/s-r6-med-batch6`): b6 nn/coaching (VL round_number reale, dead RAP helpers LEAK-01
eliminati, hybrid use_jepa gate, chronovisor timeline per-window + lag entry-units); b7 data
(time_in_round senza clamp 115 + warmup 0.0, tick_rate required x2, HLTV endDate dinamico, faceit
Retry-After RFC7231, trade_kill warning); b8 core (Inf yaw hang, CoachState row create, landmark
DERIVATI da map_callouts + map_config.json RIGENERATO — anche il JSON era rotto, guards headless
asset/map manager); b9 analysis (TT depth invertita + node_type key, flash window seconds+rate,
belief eco-rows DROPPED non fabbricate, win predictor checkpoint wiring
`models/global/win_prob_predictor.pt`); b10 knowledge (opening_duel RATIO on-disk confermato dal
monolite — fix-note del verdetto era da RIBALTARE, threshold ok e testo rotto; miner via
get_db_manager bounded; vector_index rebuild-lock + snapshot atomico + _stack_uniform anti-ragged;
experience replay seeded); b11 tools (--force gated, register_orphan MAX(_total), db_inspector/
project_snapshot status vocabulary, debugger max-streak, Goliath POSIX paths, validator drive-letter
check riabilitato, dead_code Phase C riabilitato → ~40 stale import REALI da triage nel pass LOW);
b12 UI (context emit order, NULL data_quality x2, i18n dock title, COACH_DOCK_VISIBLE
minimize-clobber, boot-failure modal reale, sbert log, effective_player breakdown, focus insight
anti-fabrication, log-bridge leak, CM transport wiring completo scan+disable-until-found,
SoundManager istanziato+nav click). Flaky RNG fixato (TestWinProbabilityPredictor seeded).
Suite 2286 verdi (perf canary verde con CS2_LATENCY_MULTIPLIER=4 doc.) + validator PASS 318/319.
**PR #29 → merge a CI verde.** Studio personal-resources: 3 report distillati (Python/DataEng/SWE)
da C:\Users\Renan\personal-resources. SSD monolite via WSL Ubuntu /mnt/wsl/PHYSICALDRIVE2p1 (mount
cade quando Ubuntu si spegne: keepalive `wsl -d Ubuntu -e sleep 14400` + remount /dev/sdd1).

**RUNTIME E2E 2026-07-17 (branch `fix/s-r7-runtime-e2e`, PR da aprire):** primo giro REALE
end-to-end su Windows con demo pro vera (vitality-vs-the-mongolz-m1-mirage, 500MB, 2.13M tick,
copiata dall'SSD; hltv_metadata.db copiato dal monolite: 161 card/174 pro). TROVATI E FIXATI 5
DIFETTI RUNTIME che nessun test unit aveva preso: (1) batch_ingest crashava su Windows
(os.sysconf→psutil); (2) kill_std/adr_std/impact_rounds morivano a 0.0 SILENZIOSAMENTE — le demo
attuali non portano total_rounds_played sugli eventi senza `other=[...]` di demoparser2; (3)
avg_kast saturava a 1.0 per 8/10 pro — la stima closed-form min(kills+assists*0.8, rounds) tocca il
tetto per chiunque faccia ≥1 kill/round → ORA KAST REALE evento-driven per-round via
calculate_kast_for_round (misurato 0.67-0.80 ✓); (4) coaching lodava le morti ("Strong Deaths
Z+7.1 Keep it up!") → direction-aware _LOWER_IS_BETTER_FEATURES; (5) cleanup 30+ stale import veri
(Phase C del detector riabilitato + noqa-F401/multiline/star/__future__ handling). VERIFICATO OK:
ingestione completa (2.13M tick, 558s), enrichment rate-aware (time_in_round max 163s POST-PLANT
ONESTO ✓, round 1-30 ✓), training dry-run JEPA su dati reali (Epoch 1 train 3.66/val 1.37, B1-XL
rejection sampling, finestre contigue, maturity=doubt corretto, CPU), inferenza coaching con
baseline HLTV reale fusa 3-sorgenti, UI diagnostic 27/27 (landmark rigenerati in-bounds),
comparison=SOLO hltv db by-design ✓, Ollama config gemma4:e2b 2.3B ≤8B ✓ (servizio NON installato
su questa macchina — chat degrada a offline fallback come da design; installare per la verifica
live). Demo archiviata in C:\Users\Renan\ingested\ (archive dir=home — rivedere posizione).
NOTA thin-baseline: il layer demo della pro_baseline si attiva con ESATTAMENTE 10 righe (1 partita)
→ std minuscole, z gonfiati in locale; sul monolite pieno non accade — valutare MIN più alto.

**CAMPAGNA LOW IN CORSO (2026-07-17, branch `fix/s-r8-low-campaign` basato su main=4208dc2):**
67/67 CHIUSI in 10 batch — CAMPAGNA LOW COMPLETA (`0b07a13` qt ×7: PlainText chat FE-01 + streaming FINALMENTE renderizzato nel typing label, CTA connect-once, Typography stat, app_state warn-once + docstring onesta, SteamID64 validato) (`b6245bc` analysis ×7: lethality swap atomico, pro_bridge V-2 kast, blind_spots skip-ratio warn, graph conn cross-thread + factory lock, factory docstring onesti, Elo/Platt dormant-by-design C6/R9) (`4c49f8b` nn-core ×7: maturity off-by-one current snapshot, jepa window +1 e avg per processed, config debug, jepa_model max gating, NN-61 comment onesto + _log_epoch morto) (`05deaf9` processing ×7: header/meta-drift/CSV loud fallbacks, heatmap stride per-demo rate, reconstructor team-elims onesti nel grounding LLM, regression fn DELETED, dem_validator layering documentato) (`9e399fe` core ×7: catena load_frames tick_rate REQUIRED+header resolve — 128-tick giravano a metà velocità, config backup loggato + /media scan guard, frozen_hook getattr _MEIPASS, spatial warn-once anti-fabrication, lifecycle mutex NULL fail-closed, asset cache lock) (`c93bf3a` nn-orch ×4: GPU-notify loggato, chronovisor maturity advisory loud, Hopfield prototypes lookup_weights targeting — Phase 5B era no-op silente, ghost predict_tick None-on-failure + caller skip) (`4c80d1b` data-sources ×5: flaresolverr destroy loggato, steam_api 403 body nell'except raggiungibile, stat_fetcher docstring, TRADE_WINDOW_TICKS 64-baked RIMOSSO + test invertito, steam registry breadcrumb) (`b2866eb` services ×5: lesson DB-check loggato, LLM model lazy per-istanza
— il selettore UI ora ha effetto, server RateLimiter eviction, orchestrator failures_this_match +
exc_info, coaching_dialogue lock RILASCIATO durante LLM call con snapshot/re-acquire — 50 test
dialogue/streaming verdi): `9a8b89a` storage ×10 (window 5s rate-aware in match_data_manager +
orchestrator caller de-hardcoded 320/64; WR-14 warn; DDL default quoting sicuro + duplicate-column
debug-log; remote_file_server config per-call + rate limiter eviction; db_migrate dispose;
backup weekly (iso_year,iso_week); state_manager unknown-daemon raise; db_backup parziale→raise) e
`fb6d891` tools-observability ×8 (ML debugger probe seeded; Goliath factory failures nominate;
rasp fail-closed nei frozen build; build_manifest accumula tutti i binari; rows_skipped_noise
contato — _aggregate_per_player ora ritorna (aggs, noise); dead_code scan re-raise; validator
docstring 50%; _infra color bool+isatty su win32).

**CHIUSURA CAMPAGNA (2026-07-17): PR #31 MERGIATA su main — 67/67 LOW, campagna R4 COMPLETA
173/173 (4C/23H/79M/67L).** Suite 2293 verdi + validator PASS alla chiusura.

**ORPHAN SWEEP (2026-07-17): PR #32 MERGIATA (`697bac7`).** 14 moduli orfani rimossi (~2200
righe: 9 widget UI mai wired dall'aesthetic uplift, asset_bridge mai adottato, bombsite_encoding
KT-10 + demo_prioritizer/demo_quality KT-01 mai wired — recuperabili dagli hash nel commit,
platform_utils residuo Kivy). Detector: coverage rglob su tools/ + evals/ registrati come CLI;
Phase C flips verdict; dev_health esegue il detector con --strict come check CRITICO (baseline
Clean enforced). Nuovo gate in suite: ast.parse su TUTTI i 77 script tooling/evals/root
(test_tools_regressions.py::TestToolingCompiles). Task #8 tooling: SOSTANZIALMENTE CHIUSO.

**R5 IN CORSO (2026-07-17, branch `fix/s-r5-cve-hygiene`):** l'audit del lockfile 2026-02-15
dava 42 CVE apparenti ma descriveva un ambiente MORTO (cryptography/lxml/protobuf nemmeno
installati). Audit dell'ambiente REALE (venv oracolo): solo pillow 11.3.0 (13 PYSEC → bump
12.3.0 ovunque) e transformers 4.57.6 (4 RCE untrusted-model → VEX not_affected in
SECURITY/CVE_LOG.md: unico modello caricato = all-MiniLM-L6-v2 hard-coded; il bump vero è
su transformers 5.x dietro sentence-transformers<5 → decisione owner R6 legata alla finestra
re-embedding R8, EMBEDDING_VERSION bump). Lock rigenerati dal venv verificato: il vecchio
lock-cpu PREDATAVA lo stack RAP/RAG — una release da quel lock avrebbe spedito il coach senza
hopfield/ncps/faiss/sbert (import guarded = rottura invisibile al boot). requirements-dist.txt
ora è la chiusura transitiva calcolata di requirements.in + requirements-rap.in (86 pkg,
hopfield pinnato al commit git). PyInstaller pinnato 6.17.0 in build.yml (era unpinned sopra
il lock). NOTA canary: il perf canary RAP (test_100_forward_passes[rap]) oggi va in timeout
sul laptop anche a macchina scarica (throttling termico dopo ore di run) — verde con
CS2_LATENCY_MULTIPLIER=4 (5 passed) e su CI: policy invariata, budget NON toccato.

**TASKS.md è TRACCIATO in git da 2026-07-17** (richiesta owner): niente più risync manuale
verso l'SSD, arriva col pull.

**PASS 2 COMPRENSIONE (2026-07-17 sera, branch `fix/s-r8-pass2-datapath`) — lettura diretta
dei tool DB-mutanti (fuori dal perimetro pass 1). 9 finding verificati, 3 production-grade:**
(1) **F6-19 CHIUSO:** nessuna pipeline di ingestione chiamava enrich_from_demo → RoundStats
vuota e i 14 campi Class-B a 0.0 di default, MA coach_manager li usa nei delta vs pro →
segnale coaching FABBRICATO per ogni utente. Nuova SSOT
`round_stats_builder.persist_round_stats_and_enrichment()` (idempotente, match
case-insensitive, never-abort) chiamata da run_ingestion e user_ingest; populate_round_stats
importa la mappa dalla SSOT. Verificato live: 300 RoundStats + 10/10 enriched reali.
(2) **Le demo CS2 NON emettono player_blind** (evento CS:GO) → flash_assists/
utility_blind_time/utility_enemies_blinded/blind_kill_pct strutturalmente 0.0 per TUTTI
(pro inclusi). Il builder ora sintetizza gli eventi dalle transizioni per-tick di
flash_duration attribuite al flashbang_detonate temporalmente più vicino (approssimazione
documentata; transizioni non attribuibili = skip, mai guess). Live: ZywOo 3 FA / 50.7s /
5 nemici. 5 unit test sulla sintesi. (3) populate_round_stats matchava player_name ESATTO
vs chiavi builder lowercase → ogni pro mixed-case saltato in silenzio; ora LOWER().
Altri: repair_tick_features join LOWER(TRIM()) (4 colonne 25-dim riparate solo per i nick
minuscoli!) + campi parser mancanti esclusi dall'UPDATE (non più 0 fabbricati) + 2 test;
wipe_safe: il pre-flight psutil CRASHAVA il processo su Windows (access violation nativa
nell'enumerazione handle) → rename-probe su win32; il restore NON eliminava i -wal/-shm
correnti prima dell'extract (SQLite avrebbe replayato un WAL post-snapshot sopra il DB
ripristinato = stati misti) → fix + test; extractall filter="data"; USERNAME su Windows
nell'audit; niente più riferimenti al v4 cancellato. repair_ratings scriveva rating_* NORMALIZZATI (la classe
ratio-corruption di R4!) → verbatim dalla SSOT compute_rating_components. populate_match_results
winner = COIN FLIP (associava CT-start→team_a del filename senza base dati) → outcome
per starting-side only + max() sul gruppo + json.dumps + 3 test. d3_recover: tick_rate=64
HARDCODED nei metadata ricostruiti (classe 26-NORM-01) + "Team 1"/"Team 2" fabbricati →
header-derived rate (contratto GAP-01), sentinel onesti, marker distinti.

**CHECKLIST SESSIONE DATI — ✅ ESEGUITA 2026-07-17 sul box Linux (mount UUID `7c51b2a8-…`, ex "New Volume"):**
1. ✅ `repair_rating_scale.py --commit` — 2501/2501 righe full_sql* ratio→raw + 25 impact_rounds (fase 2), VERIFICATION PASSED, backup CSV in storage/.
2. ✅ `repair_tick_features.py` — 5 demo con .dem, 9.406.210 tick in 121s (fix in-sessione: indice sulla temp table `_repair`; senza, il piano era `SCAN r` O(N×M) → runaway >40min). Le ~253 demo SENZA .dem su disco restano non riparabili (limite dati, sentinel noto).
3. ✅ `populate_round_stats.py --full` — 1.210 righe ricostruite sulle 5 demo, 10/10 player enrichiti (mixed-case ok); ZywOo vitality-m1 riproduce ESATTI i valori E2E dell'handoff (trade 0.0769, opening 0.75, blind 50.698s). Totale: 12.950 righe / 57 demo.
4. ✅ `populate_match_results.py --full` — 258 righe: 53 con winner derivato, 205 honest-None (niente coin-flip).
5. ✅ Re-derive v1-d3-recovered: nuova modalità `d3_recover_shard_metadata.py --rederive-v1` (+5 test) — 0 header-derivabili (nessuna .dem tra le 55), 55/55 rimarcate `v2-d3-recovered-default-rate` (auto-upgrade quando le demo verranno ri-acquisite); report `docs/d3_rederive_report_2026-07-17.json`; path del tool ora via SSOT DP-06 (i mount hardcoded "New Volume" erano morti).
6. ✅ `alembic stamp d4e5f6a7b8c9` + `upgrade head` — alembic_version era VUOTA sul monolite (upgrade da base avrebbe rieseguito 17 migrazioni su schema esistente); schema verificato a livello d4e5f6a7b8c9 prima dello stamp. Primo run FALLITO disco-pieno: l'hook `_pre_migration_backup` copiava 154 GB su 54 liberi → aggiunta guardia free-space a `backup_monolith` (+2 test) e rerun ok.
   Fix collaterali di sessione: `_restrict_db_permissions` best-effort su EPERM (monolite root-owned; +1 test) · `PRO_DEMO_PATH` corretto in user_settings (locale) · rimossi 49 GB temp rsync orfano + 58 GB backup parziale morto. Residuo owner: ~45 GB di backup parziali vecchi (mag) in `backups/database/` da vagliare; `sudo chown -R` su storage/ per ripristinare hardening 0600.

**PUBBLICAZIONE — stato 2026-07-16 ~15:00:** ✅ **PR #23 MERGIATA** (12 commit S-R0/S-R1 su
origin/main, rebase-merge, branch auto-eliminato). Sbloccata correggendo la **branch protection
CLASSICA** (required approvals 1→0 via API — l'owner aveva modificato solo il ruleset; c'erano DUE
livelli di protezione). Ruleset attivi su main: no-delete, no-force-push, linear-history. Auto-merge
di repo NON abilitato. Main locale rebasato su origin/main; **churn EOL dei 4 `.bat` RISOLTO
definitivamente** (commit renormalize EOL-only dedicato, previsto dalla policy 68e998f).
**PR #24 APERTA in attesa di merge** (`fix/s-r2-high-batch1`, 5 commit S-R2: 7 HIGH data-path + chore
EOL): il merge di PR self-authored richiede autorizzazione utente per-PR — chiesta autorizzazione
PERMANENTE al merge con CI verde. Dopo ogni merge: `git fetch && git rebase --autostash --onto
origin/main <ultimo-commit-pubblicato> main` sul clone.

| Ordine | Blocco | Item | Gate/vincolo |
|---|---|---|---|
| R0 | Ambiente Windows | `venv_win` + baseline validator/pytest su questa macchina + acceptance touch-test 26-ENV-01 + hook pre-commit | in corso 2026-07-16 |
| R1 | Verità sul segnale F1 | #64 26-RANGE-01 range target coaching-head (ST-1b, tracciare il path finetune reale) | lettura codice — SUBITO |
| R2 | Fix piccoli invariant-safe | #59 scheduler guard epoche zero-step · #60 C-1 map-fallback throttle + stray `alloc!` · #57 deadcode vendored-exclude · #43 residuo AMP/accum su RAP optimizer | test+validator per fix |
| R3 | Uplift sistematico exception-discipline | #28.1–28.4 broad-except narrowing (coaching_service 12 · session_engine 20 · demo_parser 3 · lifecycle 3) | test+validator |
| R4 | **Comprensione sistematica del codebase** — PASS 1 FATTO 2026-07-16 (S-R1, workflow 10 reader, 233 file, 173 findings: 4C/23H/79M/67L, report `reports/r4_findings_2026-07-16.txt`). **4 CRIT FIXATI** (`10ed2c3` HLTV drop, `b92a187` yaw/FOV, `fd89011` JEPA windows+migration, `751a5af` RAP windows+WR-76). **S-R2: 7 HIGH FIXATI** (`735f621` parser HLTV virgola-migliaia; `859e8b3` meta-drift join+map filter+regex WR-76 condivisa in db_models; `b5f1345` 26-TICK x3: sound-window/utility-entropy/trade-window; `52db6c9` epoch-loss su batch processati). **S-R2b: UI x3 FIXATE in albero (commit pendenti)** — H17 `surface_card`→`surface_raised` + test contratto sistemico sui riferimenti token (`test_design_token_references.py`, vieta la CLASSE); H18 comparison: la clutch_win_pct utente NON finisce più nello slot count — metriche senza equivalente = assenti, la griglia mostra "—" mai uno 0 fabbricato; H19 percentili: `get_rating_history` ora porta kd/adr/kast (era solo rating → percentili sempre ~0) e le chiavi senza dati utente vengono OMESSE (la strip le salta). **S-R2c (commit locali `af8d63f`→`54f1ba4`): +7 HIGH** — telemetry contract x2 (`player_name`+202, test contro lo schema server REALE), session_engine cold-start gate (il test CODIFICAVA il bug — corretto), csv_migrator invariante, belief THREAT_DECAY_LAMBDA→ClassVar (calibrazione era no-op), UI x3. **S-R3 (commit `e930f09`→`2d17285`): ✅ TUTTI I 23 HIGH CHIUSI.** Ultimi 6: half-switch format-aware (momentum + economy: il secondo pistol non è più "full-buy regardless", overtime vero sì); lock `acquire()` atomico O_EXCL + reclaim via rename (TOCTOU chiuso, 16-thread contention test); guard parlante sul finetune (26-RANGE-01); **FOV specchiato verticalmente FIXATO** (grid Y-flip: yaw=90 illuminava il SUD — 4 test direzionali N/S/E/W); rimosse le 6 costanti `*_TICKS` morte (l'assunzione 64-tick import-time non esiste più; design completo resta 26-NORM-01). **CAMPAGNA MED IN CORSO — 20/79 chiusi** (commit locali: `22ca8d7` services ×7, `2c30915` storage ×6, `f0d98c1` processing ×7 — quest'ultimo include DUE ULTERIORI siti yaw-class-CRIT scovati per strada: `own_yaw` del knowledge live e il FOV di memoria leggevano l'attributo inesistente `yaw` → conoscenza sempre rivolta a est; accessor `_tick_yaw` ora UNICO in player_knowledge, tensor_factory lo re-esporta; +Z-guard sulla memoria anti-wallhack multi-level; 2 test aggiornati che CODIFICAVANO i bug: skill 0.0-as-absent, economy overtime). **S-R4: batch 3b (`8b7be92` kast required-kwarg, demo_quality rate-scaled, tensor legacy team warn) + batch 4 nn-core ×6 (`f181ccf`: train.py NN-JM-04 freeze, EMA units retrain, VL device contract, DET-01 finetune seed, MoE aux-loss finalmente consumata, persistence registry loud) = 32/79 MED CHIUSI.** I ~47 MED residui sono stati VERIFICATI dal workflow r4-med-verify (5 agent): **47 CONFIRMED / 1 REFUTED**, verdetti con evidenza fresca e fix-note in `reports/r4_med_verdicts_2026-07-16.json` (su entrambe le copie). **PUNTI CALDI CONFERMATI da fare SUBITO nella prossima ondata:** (a) `demo_parser.parse_sequential_ticks` ha ANCORA il meccanismo di TICK DECIMATION vivo (param `rate` + `df.iloc[::sampling]` — violazione dell'invariante supremo; unico caller prod safe ma il path è esercitato dai test); (b) il negative pool JEPA viene POPOLATO ANCHE DAI BATCH DI VALIDAZIONE (val features come training negatives); (c) NN-MEM-01 conta i forward non gli optimizer-step (Hopfield attivo prima di qualunque step con accumulation); (d) VL round-estimation 64-hardcoded + fallback round-1 silenzioso; (e) helper RAP morti con LEAK-01 latente da eliminare; (f) chronovisor value-timeline 1-entry-per-window. Poi 67 LOW, pass 2 e 3. **STATO PUBBLICAZIONE (chiusura 2026-07-16 sera): batch 1-4 MERGIATI su main (PR #26). Batch 5 (`9ff7cb9`, hot-spot integrità training: decimazione RIMOSSA, negative pool train-only, Hopfield gate step-driven) è su PR #28 APERTA NON MERGIATA — l'owner ha chiuso la sessione dopo commit+push. ALLA RIPRESA: mergiare PR #28 (CI-verde) con --rebase --delete-branch, riallineare main locale, eliminare il branch, POI proseguire coi 44 verdetti MED restanti (r4_med_verdicts: prossimi = VL round-estimation 64-hardcoded, helper RAP morti LEAK-01, chronovisor timeline, round_context clamp 115s, e gli altri).** 35/79 MED chiusi totali. Post-S-R3: fix `77f1d55` server.py sys.path pollution (smascherato dai test telemetry: 3 moduli test root non collezionabili) + `15a0fc8` secondo test che codificava il bug economy. Suite finale: **2246 verdi** (unico fail residuo = perf canary latenza RAP 150ms: SOLO sul laptop dev termicamente throttled, VERDE su entrambe le piattaforme CI — budget NON toccato; run locali perf: `CS2_LATENCY_MULTIPLIER=4`). **PR #25 aperta (9 commit) → merge a CI verde.** | validator PASS | HIGH: FATTO ✅ |
| R5 | Security/dipendenze | ✅ FATTO 2026-07-17 (branch `fix/s-r5-cve-hygiene`): pillow 12.3.0, lock rigenerati dal venv oracolo (il vecchio lock-cpu predatava lo stack RAP/RAG), dist = closure calcolata, PyInstaller pinnato, VEX transformers in CVE_LOG | residuo → R6: bump transformers 5.x/sentence-transformers |
| R6 | Design/decisioni owner | ✅ DECISE 2026-07-17 (owner): #61 26-SCHEMA-02 → **RIMUOVERE** i campi connect-state (feature morta; ri-progettare se/quando servirà, con split DM-02) · C11 26-NORM-01 → **SSOT tick-rate PRE-R8** (accessor unico metadata→header fallback + test anti-letterale-64) · #62 → **cablare eslint 9 flat-config** pinnato nel workspace pnpm · transformers 5.x → **in finestra R8** (bump + re-embedding RAG + EMBEDDING_VERSION insieme al retrain, sulla macchina dove girerà R8). Esecuzione #61/C11/#62: dopo la sessione dati 2026-07-17, prima di R8 | decisioni prese; esecuzione in coda |
| R7 | Ricerca JEPA "tesori" | ✅ FATTO 2026-07-17: 26-LEJEPA-01 + A1 chiusi con `docs/Studies/LeJEPA-SIGReg-vs-EMA.md` (verdetto: NON accoppiare a R8 — baseline R8 su architettura attuale, LeJEPA come rung sperimentale gate-driven, adozione eventuale in R9) · Studio "Visione privilegiata" GIÀ ESISTENTE da sessione 2026-06 (`docs/Studies/Visione-Privilegiata-Training.md`, raccomandazione C→A) — la nota "non ancora esistente" era stale · INDEX.md riga 2511.08544 → 📖 | ricerca, zero codice runtime |
| R8 | Retrain ladder G5/B7 | SBLOCCATO (Phase B chiusa, B1-XL `0cd6aa9` fixato) — sul box Linux col monolite; rungs/gates/promotion nel tuning-doc (`a17dfd0`) | **lancio owner-gated** |
| R9 | Post-retrain | F1.5 A/B bench (G6.4) · #48 GAP-15 LLM A/B · win-prob checkpoint + Platt enable (C6/C10, 26-WINPROB-01/02) · chiusura #58 · concept-head VL-JEPA | dopo R8 |
| R10 | Documentazione (Fase E/9) | 232 README trilingue · doc di vertice · book-coach · fix "11 demo" · numeri CI · traduzioni | **PER ULTIMA** |
| R11 | Training finale (Fase 10) | corpus reale completo · pre-flight §13 del piano maestro · eval_harness confronto baseline | **ULTIMISSIMO, conferma owner** |

Owner-gated permanenti: `sync_pro_players --apply` · `rescrape_placeholder_pros --apply` (#38) ·
commit di `docs/plans/` (untracked, scelta owner) · merge verso `main` remoto · lancio training.

| R12 | **Riscrittura storia commit (A FINE LAVORI, ordine esplicito owner 2026-07-16)** — rimuovere OGNI menzione Claude/AI (trailer `Co-Authored-By: Claude*`/`Opus*`) da tutta la storia + mailmap author `alex.cupsa.1997@gmail.com` → `249985478+renanaugustomacena-ux@users.noreply.github.com` (i commit con la email personale risultano del profilo "alexcupsa1997-del"). Procedura: `git filter-repo --message-callback` (strip trailer) + `--mailmap`; disattivare temporaneamente la rule `non_fast_forward`; force-push coordinato; riattivare; ogni clone va ri-resettato. Config repo-local del clone C:\PROIECT GIÀ corretta (2026-07-16): commit nuovi = identità giusta e zero menzioni | dopo che TUTTI i fix sono pronti; ok esplicito owner al force-push | pianificato |

---

## Sessione 2026-06 — Backlog correzioni (sintesi Fase 4, da AUDIT §12)

> Ordinato per priorità d'implementazione (Fase 5, post-CI-verde). Legenda classe: **(a)** fix sicuro · **(b)** miglioria · **(c)** richiede ok utente / migrazione / ambiente · **(d)** differito. Cross-check invarianti incluso.

| # | Finding | Classe | Invarianti | Azione |
|---|---|---|---|---|
| C1 | ✅ DONE 26-TICK-01/03 finestre memoria/flash + dt LTC a 64 hardcoded | (a) | nessuno toccato (no METADATA_DIM) | FATTO (sync 2026-07-02 da AUDIT §12.3): `0032e4e` finestre derivate da tick_rate + `2ad3a43` attivazione per-demo RAP/LTC dt via `MatchMetadata.tick_rate` + `8d21c74` smoke/molotov expiry tick-rate-aware |
| C2 | ✅ DONE 26-ANGLE-01 yaw/pitch invertiti in demo_prioritizer | (a) | nessuno | FATTO: swap view_x↔view_y, commit `4a818c1` (sync 2026-07-02 da AUDIT §12.3) |
| C3 | ✅ DONE 26-VEC-01 gate P3-A delta globale racy | (a) | P-VEC-02/P3-A | FATTO: contatore thread-local per-batch + test concorrenza, commit `ee47b7d` (sync 2026-07-02 da AUDIT §12.3) |
| C4 | ✅ DONE 26-TICK-02 tick-rate hardcoded contraddittori | (a) | nessuno | `round_reconstructor._TICK_RATE` era dead code → rimosso; `movement_quality` reso tick-rate-aware (sec + `_seconds_to_ticks`), attivato via `analysis_orchestrator._resolve_tick_rate()` SSOT; 10 test rate-equivarianza (AUDIT 26-TICK-02) |
| C5 | ⛔ INVALIDATO-COME-SCOPATO 26-SCHEMA-01 → sostituito da **26-SCHEMA-02** (#61) | (c→design) | DB | Verifica 2026-07-02 (S-C5): i campi NON sono su `PlayerProfile` (che ha solo bio/id/player_name/pic/role) ma su `Ext_PlayerPlaystyle` (tabella conflata DM-02, `db_models.py:313-314`); NESSUN code path li scrive; il lettore (`coach_manager.py:175-176`) leggeva il modello sbagliato → sempre False. Migrazione autogenerate qui sarebbe stata su tabella errata (bozza ritirata prima del push). Vedi #61 |
| C6 | ⏸️ ANALIZZATO 26-WINPROB-01 Platt scaling dormiente | (b) | nessuno | Calibrazione dormiente per ragione VALIDA: predictor 12-dim senza checkpoint addestrato (W-02) e scollegato dal trainer 9-dim (A-12); abilitarla ora = placebo su pesi casuali → abilitazione **DIFFERITA a Fase 10** (post-training + riconciliazione architetturale). L'indagine ha scovato + FIXATO **26-WINPROB-03** (bug segno Hessiana Platt → Newton divergeva a ~3e8; commit `592aa23`, test `TestPlattScaler`) |
| C7 | ✅ VERIFICATO (no-op) 26-SAMP-02 loader pretrain jepa_train.py | (b/d) | DET-01 ok | NESSUNA AZIONE: loader GIÀ DET-01 compliant — `JEPAPretrainDataset._rng=default_rng(42)` campiona seedato (`__getitem__` usa `self._rng.integers`), `DataLoader(shuffle=True, generator=seeded_generator())`, `num_workers=0`, `set_global_seed()`+worker-init. NON legacy: entry CLI standalone `--mode pretrain` testata (`test_jepa_training_pipeline` ~15 test), distinta dal path orchestrato `_fetch_jepa_ticks`. Finding 26-SAMP-02 STALE/già risolto. Verificato 2026-06-26 |
| C8 | 26-DEP-01 lockfile fuori sync con requirements.txt | (c) | reproducibilità | rigenerare lock da requirements.txt (richiede ambiente) |
| C9 | 26-LEJEPA-01 drop EMA-teacher via SIGReg | (d) | NN-16/NN-JM-04 | enhancement ricerca; invalida checkpoint; vedi studio visione |
| C10 | 26-WINPROB-02 win-prob senza checkpoint | (c) | — | rientra nel training finale (Fase 10) |
| C11 | 26-NORM-01 layer normalizzazione tick-rate (SSOT) | (b/design) | DET/data | **Thread aperto** (decisione autore 2026-06-26): `MatchMetadata.tick_rate` come unica fonte risolta una volta per demo, zero default hardcoded, analyzer rate-agnostici via `time_in_round` dove possibile. Blocco di design a sé (non Fase 5). Pattern: `analysis_orchestrator._resolve_tick_rate()` |
| C12 | ✅ DONE 26-ORCH-01 silent failure `_record_module_failure` | (a) | nessuno | FATTO 2026-07-02 (W1.1): `except: pass` → `logger.warning(exc_info=True)` + test di regressione. Commit `91c59f9` |
| C13 | ✅ DONE **26-WIN-02** `_is_pid_alive` inaffidabile su Windows → reclaim lock rotto (mascherato da CI `continue-on-error`) | (a) | nessuno (core infra) | FATTO: `lock_files._is_pid_alive` su Windows ora usa `OpenProcess`+`GetExitCodeProcess` (difetto A crash su PID inesistente + difetto B falso-vivo su PID uscito); test di regressione PID-mai-allocato; `continue-on-error` rimosso da `build.yml` (gamba Windows ri-armata); manifest sync. Suite Windows 2025 passed/0 failed. Commit `baa08e8` (fix+test+manifest) + `60b454c` (re-arm CI). Trovato audit CI 2026-06-26 |
| C14 | ✅ DONE 26-ORCH-02 fallback silenzioso `training_orchestrator._resolve_tick_rate` | (a) | nessuno | FATTO 2026-07-02 (W1.2): entrambi i rami (`:1011` interno + `:1018` esterno) ora `logger.warning(exc_info=True)`, allineati al gemello C4; 2 test. Nello stesso commit W1.6 (costante negatives + log one-shot warmup pool NN-H-03). Commit `fac8a48` |

**Guardrail Fase 5:** (a) prima (qualità-dati: C1-C4), con CI come verifica; (b) poi; (c)/(d) lasciati all'autore. Mai eseguire `sync_pro_players --apply`/`rescrape --apply`. Mai violare il contratto 25-dim.

## Active (open / future work)

| # | Status | Pri | Title |
|---|---|---|---|
| 17 | DONE | MED | MOE-02 dense→sparse gate — closed by #40/GAP-10 (2026-04-25). Top-K sparse gate landed; `gate.0.weight` → `gate.weight`; old checkpoints raise StaleCheckpointError. |
| 33 | DONE | MED | ✅ FATTO 2026-07-02 (`c65ddbe`, F2): streaming end-to-end — `llm_service.chat_stream` (Ollama `stream:true`), `coaching_dialogue.respond_stream`+`cancel_stream` (stall→fallback, disciplina F5-06), Worker `wants_progress`, VM `streaming_changed` per-chunk. 11 test (`test_chat_streaming.py`). *(Programme Phase F2)* |
| 37 | DONE | MED | ✅ FATTO 2026-07-02 (`34ebd1f`, F3): `_retrieve_context` inietta un blocco NN session-scoped per gli intent di coaching (positioning/aim/utility/economy/general) quando `using_pro_reference=True`; cache per-sessione (`_session_ml_cache` — engine+baseline caricati al massimo una volta, F3.3), reset in `clear_session`, degrado silente-loggato su errore. `player_query` mantiene il suo path mention-based più ricco. 5 test + regressioni tutor-mode verdi (F3.4). |
| 38 | TODO | MED | HLTV rescrape for the 24 placeholder players. Tool shipped (#39/GAP-06). Owner runs `--apply` when convenient. *(Programme Phase G3 — owner-gated)* |
| 39 | DONE | HIGH | **GAP-06** `tools/rescrape_placeholder_pros.py` shipped 2026-04-25 — dry-run default lists exactly the 24 names from TASKS#38. Owner runs `--apply` when convenient. Closes TASKS#38 mechanically once applied (acceptance: `tools/purge_default_stats_rag.py --dry-run` reports 0 default cards). |
| 40 | DONE | HIGH | **GAP-10** MOE-02 dense→top-K sparse gate landed 2026-04-25 — `AdvancedCoachNN.gate` is `nn.Linear` raw logits + `_topk_sparse_gate(logits, k=2)` in forward. State-dict key changed (`gate.0.weight` → `gate.weight`); old checkpoints raise StaleCheckpointError. Closes TASKS#17. |
| 41 | DONE | MED | **GAP-09** strategy taxonomy + label column shipped 2026-04-25 — `docs/strategy_taxonomy.md` + alembic `c3d4e5f6a7b8_add_strategy_label_to_coachingexperience` (additive nullable + indexed, reversible). Owner runs `alembic upgrade head` to apply on live DB. |
| 42 | DONE | MED | **Finale gate** 2026-04-25 — 188 scoped tests pass / 4 integration-gated skip; `headless_validator` exit 0; baseline eval written to `reports/eval_20260424T224722+0000.json`. |
| 43 | DONE | LOW | **GAP-08** — mixed precision + grad accum ATTIVI su ENTRAMBI i trainer. JEPA verificato 2026-07-02 (`jepa_trainer.py:119-126`). RAP verificato 2026-07-16 (S-R1): `rap_coach/trainer.py:41-42` GradScaler CUDA-gated, `:54` autocast, `:101` loss/accum_steps + flag `step_optimizer`, `:126-132` flush `_optimizer_step`, unscale→clip→step nell'ordine corretto. Niente da portare. |
| 44 | TODO | LOW | **GAP-11 deferred** — sub-tick movement data (CS2 post-2024-09-15). Position interp already dead-boundary aware; pull only if retrain shows path-prediction error. *(Programme: deferred)* |
| 45 | TODO | LOW | **GAP-12 deferred** — pause/resume + team_switch events. Low blast radius on current feature set. *(Programme: deferred)* |
| 46 | DONE | LOW | **GAP-13** `REFERENCE.md` recreated 2026-04-25 in commit `944dc46`. Sections: architecture, METADATA_DIM=25 contract, critical invariants, Phase 0 hygiene gates, storage architecture, global constants, skill triggers, test layout, env vars, doc debt. Referenced from `CLAUDE.md` "Sibling docs" line. |
| 47 | TODO | LOW | **GAP-14 deferred** — bring `hltv_metadata.db` under alembic. Today schema evolves via `SQLModel.metadata.create_all()` + stale-column drop/recreate. *(Programme Phase G7)* |
| 48 | TODO | LOW | **GAP-15 deferred** — full LLM A/B baseline (Gemma-4 vs RAP coach on a curated CoachingExperience scenario set). Eval harness has the stub; needs fixture corpus + scoring rubric. *(Programme Phase B6/G6)* |
| 49 | DONE | HIGH | **CI pipeline restoration** 2026-04-25 — 19 consecutive failed runs since 2026-04-12 resolved across 3 commits: `241384a` (Python 3.10→3.11 + md5 tag), `3d6d935` (detect-secrets false-positive excludes), `9404815` (theme + skill_assessment test drift). All 8 stages green on run 24919779641. See AUDIT §11. |
| 50 | DONE | LOW | **CI-red notification** 2026-04-28 in commit `9185306` — `.github/workflows/notify-failure.yml` triggers on completed Macena CI Pipeline runs filtered to `main`, opens or comments on a single rolling "main CI red — investigate" issue with run URL/SHA/conclusion/triage steps, auto-closes when main returns green. Single rolling issue avoids per-failure spam. |

---

### #30 · Refactor queue — CLOSED (original 5 targets)

Original 30.1–30.5 targets (app.py::main, round_reconstructor::_build_timeline, jepa_train::train_jepa_pretrain, vectorizer::extract, training_orchestrator::_prepare_rap_batch) were all refactored in the May 2026 de-nesting campaign: commits `d8c710e` (8 production fns, 2026-05-02), `da2d490` (4 tools fns, 2026-05-03). Verified closed 2026-06-13.

### #30-bis · Nesting/length queue — CLOSED (AST census 2026-06-13, resolved 2026-06-20)

Successor to #30. All actionable targets resolved; remaining items dropped (within thresholds or structurally sound).

| # | Status | Target | Before | After | Resolution |
|---|---|---|---|---|---|
| 30b.1 | DROP | `data_quality.py::run_pre_training_quality_check` | 99L/d4 | — | Linear try/with/if flow; depth from exception handling, not problematic nesting. |
| 30b.2 | DONE | `training_orchestrator.py::_run_epoch` | 115L/d6 | 48L/d2 | Resolved by B1-B4 commits (2026-06-19). |
| 30b.3 | DONE | `training_orchestrator.py::run_training` | 206L/d3 | 73L/d1 | Resolved by B1-B4 commits (2026-06-19). |
| 30b.4 | DONE | `jepa_train.py::train_jepa_pretrain` | 133L/d3 | 82L/d2 | Extracted `_jepa_pretrain_process_batch` (2026-06-20). DET-01 seed first-in-path preserved. |
| 30b.5 | DONE | `jepa_trainer.py::train_step_vl` | 106L/d3 | 88L/d2 | Extracted `_resolve_concept_labels` (2026-06-20). G-01 gate unchanged. |
| 30b.6 | DROP | `training_orchestrator.py::_prepare_rap_batch` | 97L/d1 | — | Already flat (depth 1) with 4 phase helpers extracted. Length is domain-essential tensor construction. |
| 30b.7 | DONE | `console.py::run_cli_mode` | 65L/d15 | 35L/d2 | Resolved by prior refactoring. |
| 30b.8 | DROP | `console.py::run_tui_mode` | 120L/d8 | 79L/d4 | Under 80-line threshold after partial improvement. |

### New tracked items (discovered 2026-06-13 reconnaissance)

| # | Status | Pri | Title |
|---|---|---|---|
| 51 | DONE | HIGH | JEPA per-epoch seed rotation in training orchestrator sampling. Root cause of val-loss plateau at ~1.90. All three levers landed: B1 seed=42+epoch (`dd31e39`), B2 --train-samples (`330e28f`), B3 --patience (`4fb2f87`). Closed 2026-06-19. |
| 52 | DONE | MED | ✅ FATTO 2026-07-02 (`97ed13a`, D1): single-sample `extract()` quality gate — path singolo ora gated come il batch (P-VEC-02); contract tests estesi (`test_feature_extractor_contracts.py`). *(Programme Phase D1)* |
| 53 | DONE | LOW | ✅ FATTO 2026-07-02 (`97ed13a`, D2): clamp-log throttle — contatori aggregati rate-limited al posto dello spam per-evento. *(Programme Phase D2)* |
| 54 | DONE | MED | POV-TBL-01 shard schema contract test — pins `MatchTickState.__tablename__ == "matchtickstate"` + ORM write/read same-table probe. Added 2026-06-13. *(Programme Phase A5)* |
| 55 | DONE | MED | Console TUI/CLI de-nesting — `run_cli_mode` 65L/d15→35L/d2 (done); `run_tui_mode` 120L/d8→79L/d4 (within threshold). Closed with #30b queue 2026-06-20. |
| 56 | DONE | MED | ✅ FATTO 2026-07-02: B6.2 dry-run fast path — `2c95765` (skip embedding SBERT pesante) + `dee4ac0` (gate su TUTTE le sezioni pesanti). Da riconfermare <30s alla prossima baseline (era l'unico fail: 2088p/1f). *(Programme Phase B6.2 / W2.3)* |
| 57 | DONE | LOW | ✅ FATTO 2026-07-16 (commit `11f8b12`): `caveman` aggiunto a `EXCLUDE_DIRS` del dead_code_detector (vendored gitignored, esiste solo su alcuni worktree). Detector exit 0 su Windows. |
| 58 | WIP | HIGH | **26-HYB-01/F1** — 2026-07-02: (a) random-weights RISOLTO (`96c2f49`); (b) **adapter core** (`b09c43b`: mapping 10-target→focus_area, ladder maturity con tono hedged in doubt, disciplina loader 26-HYB-01, gate USE_JEPA_MODEL; 12 test); (c) **wiring nel chain** (`c5be1bd`: blocco additivo non-bloccante post-Phase-6 in `generate_new_insights`, finestra tick NO-WALLHACK ultimi 256, persistenza CoachingInsight 'World-model read: <asse>', tier→ladder conservativo MATURE→conviction; 8 test wiring, parity provata da 105 test coaching col flag off). RESTA: F1.5 A/B via cs2_coach_bench (post-retrain, G6.4) + #64 verifica range + concept-head (richiede checkpoint VL-JEPA, assente oggi). |
| 59 | DONE | LOW | ✅ FATTO 2026-07-16 (S-R0, in albero — commit pendente): guard `scheduler.step()` su epoche a zero train-batch — `_run_epoch` espone `_last_train_batch_count`, `_run_epoch_loop` salta lo step e logga warning "TASKS#59" (skip mai silenzioso). 3 test `TestSchedulerZeroStepGuard`; file orchestrator 84/84 verdi. Era: UserWarning PyTorch osservato nel log B4 2026-07-02 (dry-run RAP, batch tutti skippati → primo LR della schedule saltato). |
| 64 | TODO | MED | **26-RANGE-01 — VERIFICA ST-1b FATTA 2026-07-16 (vedi AUDIT §12.1), resta la decisione design (c).** Esito: il finetune CLI reale è **shape-broken** (modello `output_dim=10` WR-63 vs target last-tick **[N,25]** da `load_user_match_sequences` → MSELoss RuntimeError: il path non può girare, nessun checkpoint mai prodotto); i test lo mascherano (fixture `output_dim=25`). I delta [-1,1] di `_calculate_deltas` alimentano SOLO AdvancedCoachNN (tanh — LOSS-02 coerente là); la head JEPA non ha MAI avuto un contratto target. Adapter F1 difensivo + gate 26-HYB-01 → oggi nessuna magnitudine fabbricata. **Fix (pre-requisito R9):** contratto proposto = delta 10-assi `(δ+1)/2` → [0,1], 0.5 neutro per costruzione; CLI deve fallire chiaro nel frattempo; test di contratto su config reale 25→10. |
| 63 | DONE | HIGH | **26-B1-XL** — la fetch B1 degli id tick OOMava sul monolite pieno: `_fetch_jepa_ticks` materializzava TUTTI gli id eleggibili (centinaia di milioni di int Python su 429M righe → decine di GB → earlyoom SIGTERM a ~9 min, exit 143). Scoperto dai probe B5 2026-07-02 (tre tentativi uccisi identici); avrebbe ucciso OGNI rung del retrain G5. FIX `0cd6aa9`: COUNT sceglie la strategia — ≤2M id path esatto invariato; sopra, `_sample_ids_rejection` (campionamento seeded sullo spazio-id, RAM O(sample), DET-01+rotazione B1 preservati, underfill loggato). 4 test XL-path + regression small-path; 153 test suite consumatrici verdi. |
| 62 | TODO | LOW | **26-WEB-01** — gli script `lint` dei 3 web app dichiarano `eslint 'src/**'` ma NESSUNA config eslint né dipendenza esiste nel workspace (risolveva a un ESLint 6 globale). Decisione: cablare eslint 9 flat-config + dep pinnate nel workspace pnpm, oppure rimuovere gli script. Scoperto 2026-07-02 durante W6.3a. Correlato: il lockfile pnpm era STALE (specifiers `{}` per coach-chat/match-detail) — rigenerato; era la causa del fallback npm in tactical-viewer (W0.2). |
| 61 | TODO | MED | **26-SCHEMA-02** (sostituisce 26-SCHEMA-01/C5) — connection-state steam/faceit: feature NON implementata end-to-end. Fatti verificati 2026-07-02: (a) i campi vivono su `Ext_PlayerPlaystyle` (conflazione DM-02 documentata nel docstring), NON su `PlayerProfile`; (b) zero scrittori in tutto il repo; (c) unico lettore `coach_manager.check_prerequisites` leggeva il modello sbagliato → sempre False (commenti/docstring ora onesti); (d) NESSUNA migrazione tocca `ext_playerplaystyle` → il monolite mescola tabelle Alembic-managed e create_all-managed (classe di drift più ampia di GAP-14). Decisione owner: implementare la connect-feature (wizard/steam_config scrivono i flag + lettore su Ext o split DM-02) oppure rimuovere i campi. Pairing naturale col design 26-NORM-01 (SSOT). |
| 60 | DONE | LOW | ✅ FATTO 2026-07-16: (a) throttle C-1 warn-once-per-demo via metadata_cache (commit `34a6903`, 2 test); (b) `alloc!` LOCALIZZATO: `ncps 0.0.7` `torch/ltc_cell.py:113` debug print upstream, rimosso in ncps 1.x → floor alzato a `ncps>=1.0.1` (commit `8f80025`, suite RAP verde su 1.0.1); **la venv Linux va aggiornata** (`pip install -U ncps`). Residuo spostato: backfill/inferenza demo_name→mappa per i demo non mappabili → parte del pre-flight R8 (qualità dati pre-retrain). |
| 65 | TODO | LOW | **26-DEP-03** (S-R0 2026-07-16, AUDIT §12.3) — `requirements-rap.txt` pinna `hflayers>=1.3.0,<2.0` che NON esiste su PyPI; la venv canonica ha `hopfield-layers==1.0.2` (modulo `hflayers`) dal repo ml-jku. Anche l'hint d'errore di `rap_coach/memory.py:35` ("pip install ncps hflayers") non è eseguibile. Fix: pin riproducibile `hopfield-layers @ git+https://github.com/ml-jku/hopfield-layers@<commit>` + hint corretto; verificare in CI (install da git non verificabile da questa sessione). |

---

### #28 · Broad-except narrowing queue (32 sites across 2 files + 3 daemons)

> **2026-07-02 (W1.3, commit `918b0c4`):** oltre la coda originale, sistemati i due file scoperti da ST-1: `backend/server.py` (12 siti: 2 tipizzati, 10 handler top-level tenuti broad documentati + exc_info; 4 erano SILENZIOSI) e `ingestion/demo_loader.py` (8 siti: 2 tipizzati, 6 boundary demoparser2 tenuti broad documentati — demoparser2/PyO3 NON esporta eccezioni tipizzate, verificato). Zero broad-except non documentati residui nei due file.

Per-site analysis: determine which exception types are actually thrown by the wrapped call; replace `except Exception` with the tightest superset. Keep broad-except only at daemon top-levels where escape = daemon crash. Log with `exc_info=True` everywhere.

| # | Status | Pri | Target | Count | Strategy |
|---|---|---|---|---|---|
| 28.1 | TODO | LOW | `backend/services/coaching_service.py` | 12 | Most sites wrap LLM/DB calls. Map each: LLM → `(ollama.RequestError, ConnectionError, TimeoutError)`; DB → `(SQLAlchemyError, OperationalError)`; JSON → `(json.JSONDecodeError, ValueError)`. Keep top-level request-handler `except Exception` but add `exc_info=True`. |
| 28.2 | TODO | LOW | `core/session_engine.py` | 20 | Quad-Daemon orchestrator — top-of-daemon excepts MUST stay (crash-contain). Audit each inner except and narrow: heartbeat IO → `OSError`, state-manager writes → `(SQLAlchemyError, OSError)`, worker spawn → `(RuntimeError, subprocess.SubprocessError)`. |
| 28.3 | TODO | LOW | `backend/data_sources/demo_parser.py` | 3 | demoparser2 boundary — narrow to `(demoparser2.DemoParserException, OSError, ValueError)`. Unknown format → log + skip, don't swallow `KeyboardInterrupt`. |
| 28.4 | TODO | LOW | `core/lifecycle.py` | 3 | Process spawn/kill/reap — narrow to `(OSError, ProcessLookupError, subprocess.SubprocessError)`. |
| 28.5 | TODO | LOW | Audit-noted `alembic/versions/5d5764ef9f26_add_rating_components.py` (6×) | 0 | **DROP** — file does not exist. Audit reference stale. |

## Done (2026-04-19 session 4 — security audit + HIGH remediation)

### Audit (read-only, 3 parallel security-reviewer agents)
- AUDIT §9 added: 0 CRIT, 4 HIGH, 8 MED, 4 LOW. All `file:line`-verified. Verified-clean categories include `torch.load(weights_only=True)` ✓, pickle behind HMAC+SafeUnpickler ✓, no `shell=True` in production, FastAPI bound localhost, no `QWebEngineView`, 14 Alembic migrations all paired upgrade/downgrade.

### Fixes implemented (HIGH only)
- BE-03 · `backend/services/coaching_dialogue.py` — `_sanitize_llm_context` strips ASCII control chars + caps length; `{`/`}` escaped before `SYSTEM_PROMPT_TEMPLATE.format`. Wired at `_build_system_prompt`, `_format_player_analytics`, `_get_ml_analysis_for_players`.
- FE-01 · `apps/qt_app/screens/coach_screen.py` + `match_detail_screen.py` — `setTextFormat(Qt.PlainText)` on 5 DB-sourced QLabel sites blocks Qt AutoText HTML rendering of `file://` / `smb://` links.
- DB-01 · `backend/storage/match_data_manager.py` — `_assert_safe_identifier` / `_assert_safe_col_type` / `_assert_safe_default_literal` helpers guard every DDL f-string. Identifiers double-quoted in `PRAGMA table_info` and `ALTER TABLE`.
- DB-02 · `alembic/versions/{a1b2c3d4e5f6,b2c3d4e5f6a7}_*.py` — `_safe_id` guard added to migration template `_column_exists` helpers.

### Tests
- `tests/test_security_hardening.py` — 51 regression tests (sanitiser pronoun-preservation, brace-escape end-to-end, identifier/type/default-literal whitelists with parameterised valid/invalid corpora).

### Validators
- `pytest -m "not slow and not integration"` — **1910 passed, 0 failed, 7 skipped** (+51 vs session 3's 1859).
- `python tools/headless_validator.py` — **PASS 312/313**, 1 warning (pre-existing long functions).

### MED + LOW remediation (later in same session)
- BE-01 / DB-03 · `backup_manager.py` — `sqlite3.backup()` API replaces `VACUUM INTO` SQL string; label validated at function entry via `_SAFE_BACKUP_LABEL_RE`.
- BE-06 · `backup_manager.py` `create_checkpoint` + `verify_backup` — `Path.resolve().relative_to()` replaces `startswith` traversal guard.
- BE-07 · `remote_file_server.py:run_server` — hard `RuntimeError` on non-localhost bind without TLS; `CS2_ALLOW_INSECURE_BIND=1` opt-out.
- BE-12 / FE-02 · `ingestion/demo_loader.py:_get_cache_hmac_key` — persistent random 32-byte key under `DATA_DIR/demo_cache/.hmac_key` (chmod 0o600), generated via `secrets.token_bytes`.
- FE-03 · `apps/qt_app/screens/tactical_viewer_screen.py:_open_demo` — `os.path.realpath` + extension check + `MIN_DEMO_SIZE` guard before worker dispatch; new `_show_error` helper.
- FE-04 · `core/config.py:save_user_setting` — `os.chmod(SETTINGS_PATH, 0o600)` after atomic rename.
- FE-05 · `apps/qt_app/screens/home_screen.py:_update_status_dot` — `html.escape(status)` before HTML embed.
- FE-06 · `core/config.py` — `STORAGE_API_KEY` added to keyring routing in both write and read paths.
- DB-04 · `backend/storage/database.py:_add_missing_columns` — `_SAFE_COL_TYPE_RE` allowlist gates compiled column type before raw DDL interpolation.
- DB-05 · `backend/storage/state_manager.py:get_status` — return generic "Internal error — see logs"; full `exc_info=True` to log only.
- DB-06 / DB-07 · `backend/storage/database.py` (×2 engines) + `match_data_manager.py` — `PRAGMA foreign_keys=ON` and `PRAGMA wal_autocheckpoint=512` added to all 3 `set_sqlite_pragma` handlers.

### Tests (extended)
- `test_security_hardening.py` grew to **66 regression tests** — added backup-label whitelist parameterised cases + `PRAGMA foreign_keys=ON` reads-back-1 guards.

### Final validators
- `pytest -m "not slow and not integration"` — **1925 passed, 0 failed, 7 skipped** (+15 over HIGH-only run).
- `python tools/headless_validator.py` — **PASS 312/313**, 1 pre-existing warning.

## Done (2026-04-19 session 3 — coaching-chat repair)

### Fixes implemented
- #31 · CHAT-01 · `backend/services/coaching_dialogue.py:36-46` — env-tunable timeouts (opening 90 s, response 180 s, fallback retry 90 s); `CoachingDialogueEngine.__init__` spawns `gemma-warmup` daemon thread to pre-load gemma4:e2b before first user query. Validated via live launch (`./launch.sh` → Qt up, no fallback to `_offline_opening`).
- #32 · CHAT-02 · `backend/services/coaching_dialogue.py` — `_to_third_person` deterministic regex transform (18 case-preserving pairs); wired into `_build_system_prompt`, `_format_player_analytics`, `_get_ml_analysis_for_players`. SYSTEM_PROMPT_TEMPLATE strengthened with explicit tutor-mode forbidding "your KAST" / "you are X% slower" phrasing. 11 regression tests in `test_coaching_dialogue_tutor_mode.py`.
- #34 · CHAT-06 · `backend/knowledge/pro_demo_miner.py` (skip), `backend/services/player_lookup.py` (display "not yet scraped"), `tools/purge_default_stats_rag.py` (one-shot cleanup). Purged 48 polluted RAG rows across 24 placeholder pros; backup at `database.db.pre_chat06_purge_20260419T154146Z`.
- #35 · CHAT-07 · `backend/knowledge/experience_bank.py` — `_dedup_experiences(items, top_k)` greedy keep-1 per `(action, outcome, map, pro)` tuple with spillover; wired into 3 retrieval paths. 7 regression tests in `test_experience_bank_dedup.py`.
- #36 · §8.8 · `backend/storage/match_data_manager.py:243` — `MatchDataManager.__init__` detects broken symlink, logs warning naming dead target, `os.unlink`s, then `makedirs(exist_ok=True)`. Live broken link auto-repaired on smoke test.
- §8.3 · CHAT-03 · `coaching_dialogue.py:_offline_opening` + `_generate_opening` — branch on `using_pro_reference`; tutor-mode opening states "no personal data, coaching from PRO analysis".
- §8.4 · CHAT-04 · `backend/coaching/explainability.py:24, 30, 69` — dropped trailing `s` from `{time}s` template; default ctx `time` value now `"several seconds"`.
- §8.5 · CHAT-05 · `backend/services/player_lookup.py:format_player_context` — `_fmt_pct` / `_fmt_num` helpers render `n/a` for missing HLTV stats (donk KAST/OpeningDuel etc.) instead of fabricated `0.0%`.

### Validators
- `pytest -m "not slow and not integration"` — **1859 passed, 0 failed, 7 skipped** (+88 vs session 2's 1771; 18 of those new are CHAT-02/CHAT-07 regression tests).
- `python tools/headless_validator.py` — **PASS 312/313**, 1 warning (pre-existing long-function quality-adv).
- Live launch smoke — Qt boots, broken symlink auto-replaced, Gemma warmup runs in background, no `Uncaught exception in Qt` in launch log.

## Done (2026-04-19 session 2 — autopilot pass)

### Fixes implemented
- #14 · LEAK-01 · `training_orchestrator.py:596-604` — dropped `round_outcome` fallback; val_mask=False when `_compute_advantage` unavailable (prevents future-round leak into value head).
- #15 · LEAK-02 · `jepa_trainer.py:360-388` — None-RoundStats samples dropped from batch via index_select instead of `torch.full((16,), 0.5)` neutral-label fallback that produced incoherent BCE gradients.
- #20 · REPR-01 · `jepa_train.py:save_jepa_model/load_jepa_model` + `jepa_trainer.py:__init__` — EMA `_ema_step` / `_ema_total_steps` persisted in checkpoint; trainer rehydrates on resume so cosine schedule continues at the saved τ (not restart at 0.996).
- #21 · DET-01/02 · `backend/nn/config.py` — added `seeded_generator()`, `torch.use_deterministic_algorithms(True, warn_only=True)` gated via `CS2_NONDETERMINISTIC`; `jepa_train.py` — per-dataset `np.random.default_rng`, `DataLoader(generator=...)` in both pretrain + finetune paths.
- #18 · DRIFT-01 · `backend/processing/validation/drift.py` — added `TickFeatureDriftMonitor` operating on the 25-dim tick vector (complements match-aggregate `DriftMonitor`).
- #19 · DATA-01 · `jepa_train.py:_load_tick_sequence` — dropped `playermatchstats.avg_kast` per-tick injection (post-hoc match aggregate causing train-serve skew + temporal leakage).
- #23a · `tensorboard_callback.py` — explicit `self.writer is None` guards + `SummaryWriter = None` in except branch; removes optional-dep-unresolved-ref class.
- #23b · `coach_manager.py` — `col(PlayerTickState.demo_name).in_(...)` / `col(PlayerMatchStats.match_date).desc()` using sqlmodel `col()` helper for type-safe column access.
- #23c / #24 · `embedding_projector.py`, `evaluate.py` — `umap = None`, `plt = None`, `shap = None` in `except ImportError` branches + call-site guards.
- #23d · `rap_coach/communication.py:_resolve_angle` — `isinstance(view_angle, (int, float))` narrowing before `float()`.
- #23e · `rap_coach/strategy.py:forward` — `cast(nn.ModuleDict, ...)` annotations; explicit `int(expert_idx.item())`.
- #23f · `backend/nn/factory.py` — `_require_int()` helper coerces `kwargs.get(...)` None/Any → int before passing to model ctor; removed dead `INPUT_DIM` import.
- #23g · `knowledge/vector_index.py` — `# type: ignore[call-arg]` on FAISS Python-wrapper calls (SWIG low-level signature false-positive).
- #23h · `nn/inference/ghost_engine.py` — `SimpleNamespace(**tick_data)` promotion so tensor_factory attribute access works for dict-shaped tick data.
- #22 · TEST-COV · `tests/test_ema_hopfield_drift_invariants.py` — 6 regression tests (5 pass + 1 skip on missing `ncps`/`hflayers`): EMA backup aliasing, EMA shadow in-place-mutation guard, Hopfield partial-load bypass, RAPStrategy top-2 non-zero output, TickFeatureDriftMonitor positive + noop paths.
- #27 · `training_monitor.py` — `_coerce_json_safe()` converts NaN/±Inf → None; `json.dump(..., allow_nan=False)` fails loudly on future regressions.
- #29 · `core/config.py` — `ML_BELIEF_VARIANCE_THRESHOLD=0.5` added to defaults dict.

### False-positives verified (no code change)
- #16 · LOSS-02 · `backend/nn/model.py:125` — AdvancedCoachNN target from `coach_manager._calculate_deltas` is `np.clip(delta, -1, 1)`; `torch.tanh` output range matches exactly. Audit misidentified target as one-hot {0,1}.
- #23i / #23j · Qt enum refs in `main.py` / `settings_screen.py` — main.py has zero Qt refs (audit wrong file). All qt_app files correctly `from PySide6.QtCore import Qt`; PyCharm stub flags PySide6 scoped-enum shim backward-compat — runtime clean.
- #23k · `analytics.py` / `pro_comparison_vm.py` SQLA select — `select(col1, col2, ...)` IS valid SA 2.x multi-column syntax; Row index access is correct. PyCharm stub only shows single-entity overload.
- #26 · `session.execute` → `session.exec` — remaining `execute()` calls wrap raw `text()` / `sqlite_insert` / PRAGMAs where `execute()` IS the correct API. `session.query()` / `save_hardware_budget()` / FastAPI `on_event` already migrated.
- #11 · DB/Alembic — 14 migrations all have paired upgrade/downgrade; drops mirror adds; no broad-except in migration files; audit-cited `5d5764ef9f26_add_rating_components.py` does not exist.

### Validators
- `pytest -m "not slow and not integration"` — **1771 passed, 0 failed, 25 skipped** (+5 vs session 1's 1766).
- `python tools/headless_validator.py` — **PASS 307/313** (+1 vs session 1's 306), 6 warnings (optional deps + pre-existing 200+ line functions).
- `pre-commit` not runnable (git ownership mismatch on external volume — infra issue); `black` + `isort` clean for touched files.

## Dropped / Won't-Fix
_(empty)_
