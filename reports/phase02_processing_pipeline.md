# Deep Audit Report — Phase 2: Processing Pipeline

**Total Files Audited: 25 / 25** (22 modules + 3 `__init__.py` stubs)
**Issues Found: 42**
**CRITICAL: 4 | HIGH: 5 | MEDIUM: 18 | LOW: 15**
**Author: Renan Augusto Macena**
**Date: 2026-02-27**
**Skills Applied:** deep-audit, ml-check, correctness-check, data-lifecycle-review

---

## Table of Contents

1. [tensor_factory.py](#1-tensor_factorypy) — **MODIFIED +595** (Player-POV)
2. [player_knowledge.py](#2-player_knowledgepy) — **NEW** (Sensorial Model)
3. [round_stats_builder.py](#3-round_stats_builderpy)
4. [pro_baseline.py](#4-pro_baselinepy)
5. [vectorizer.py](#5-vectorizerpy)
6. [heatmap_engine.py](#6-heatmap_enginepy)
7. [role_thresholds.py](#7-role_thresholdspy)
8. [role_features.py](#8-role_featurespy)
9. [data_pipeline.py](#9-data_pipelinepy)
10. [dem_validator.py](#10-dem_validatorpy)
11. [base_features.py](#11-base_featurespy)
12. [cv_framebuffer.py](#12-cv_framebufferpy)
13. [drift.py](#13-driftpy)
14. [kast.py](#14-kastpy)
15. [external_analytics.py](#15-external_analyticspy)
16. [rating.py](#16-ratingpy)
17. [nickname_resolver.py](#17-nickname_resolverpy)
18. [meta_drift.py](#18-meta_driftpy)
19. [connect_map_context.py](#19-connect_map_contextpy)
20. [sanity.py](#20-sanitypy)
21. [schema.py](#21-schemapy)
22. [state_reconstructor.py](#22-state_reconstructorpy)
23. [__init__.py stubs](#23-__init__py-stubs)
24. [Cross-Phase Notes](#cross-phase-notes)
25. [Quality Gate Verification](#quality-gate-verification)
26. [Issue Priority Matrix](#issue-priority-matrix)

---

## [1] tensor_factory.py

**Path:** `backend/processing/tensor_factory.py`
**LOC:** 692 | **Status:** MODIFIED (+595 lines, Player-POV rewrite) | **Verdict:** WARNING

### Logic Summary
Factory che converte lo stato di gioco in tensori PyTorch per le reti neurali. Implementa il sistema di percezione Player-POV ("NO-WALLHACK"): il coach AI vede solo ciò che il giocatore legittimamente conosce. Tre rasterizzatori:
- **MapRasterizer** (Ch0=teammates, Ch1=last-known enemies decaduti, Ch2=utility+bomba)
- **VisionRasterizer** (Ch0=FOV mask, Ch1=entità visibili distance-weighted, Ch2=utility zones)
- **MotionEncoder** (Ch0=traiettoria trail, Ch1=gradiente velocità radiale, Ch2=crosshair flick)

Supporta modalità legacy (knowledge=None) per backward compatibility con checkpoint pre-POV.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-01 | L686-691 | state-audit | MEDIUM | Singleton `get_tensor_factory()` non è thread-safe. `_factory_instance` globale mutata senza lock. Race condition possibile se chiamato da più thread (es. Teacher daemon + UI). |
| F2-02 | L73-82 | ml-check | LOW | `TrainingTensorConfig` usa 64x64 per training ma il docstring dice "AdaptiveAvgPool2d((1,1)) in RAPPerception ensures output 128-dim regardless". Se RAPPerception non esiste o cambia, il contratto 128-dim si rompe silenziosamente. Nessuna assertion runtime. |
| F2-03 | L54 | correctness-check | LOW | `MAX_SPEED_UNITS_PER_TICK = 4.0` è hardcoded per 64 tick/s. Se il server usa 128 tick/s, la normalizzazione della velocità è sbagliata (i valori sarebbero la metà del range). |
| F2-04 | L22 | correctness-check | LOW | Dipendenza da `scipy.ndimage.gaussian_filter` — se scipy non installato, crash all'import. Nessun fallback o graceful degradation. |

**Actions:** F2-01 richiede lock. F2-02 suggerisce un'assertion `assert output.shape[-1] == 128` nel test. F2-03 e F2-04 sono accettabili per l'uso corrente (CS2 64-tick, scipy è nel requirements).

---

## [2] player_knowledge.py

**Path:** `backend/processing/player_knowledge.py`
**LOC:** 518 | **Status:** NEW (untracked) | **Verdict:** WARNING

### Logic Summary
Modulo sensoriale NO-WALLHACK. `PlayerKnowledgeBuilder` costruisce ciò che un giocatore CONOSCE a ogni tick:
- **Stato proprio**: accesso completo (posizione, yaw, health, armor, arma)
- **Compagni**: sempre noti (radar/comms)
- **Nemici visibili**: SOLO se `enemies_visible > 0` E dentro il cono FOV
- **Nemici ricordati**: memoria con decadimento esponenziale (τ=160 ticks ≈ 2.5s)
- **Suoni**: eventi weapon_fire entro raggio d'ascolto → direzione + distanza
- **Zone utility**: smoke/molotov attive, flash recenti
- **Bomba**: nota a tutti

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-05 | L479 | correctness-check | MEDIUM | `entity_id = int(getattr(evt, "entity_id", 0))` — Se `entity_id` è 0 (default in `MatchEventState` model, vedi Phase 1 finding), la logica `active_starts[entity_id]` sovrascrive utility diverse con la stessa chiave 0. Risultato: solo l'ultima smoke/molotov con entity_id=0 è visibile. **Cross-reference:** Phase 1, match_data_manager.py F1-05. |
| F2-06 | L28-41 | ml-check | MEDIUM | Costanti sensoriali hardcoded (FOV=90°, HEARING_RANGE_GUNFIRE=2000, MEMORY_DECAY_TAU=160). Non configurabili via `HeuristicConfig`. Se il giocatore usa un FOV diverso (CS2 supporta 54-68° FOV verticale, ~90-106° orizzontale), il modello "vede" cose che il giocatore reale non vede. |
| F2-07 | L438 | correctness-check | LOW | `abs(evt_tick - current_tick) > 64` — Finestra fissa 64 ticks per suoni. Non documentato che questo corrisponde a ~1 secondo SOLO a 64 tick/s. |
| F2-08 | L514 | correctness-check | LOW | Flash usa `radius=SMOKE_RADIUS` (200 units) — commento dice "similar affected radius", ma flash e smoke hanno raggi significativamente diversi in CS2 (smoke ~288 units, flash ~400 units effectivo). |

**Actions:** F2-05 è la stessa root cause di F1-05 — il fix deve essere nel model `MatchEventState.entity_id`. F2-06 suggerisce un refactor verso configurazione esterna. F2-07/F2-08 sono cosmetici.

---

## [3] round_stats_builder.py

**Path:** `backend/processing/round_stats_builder.py`
**LOC:** 515 | **Verdict:** PASS (con osservazioni)

### Logic Summary
Costruisce statistiche per-round per-player dai demo events. Pipeline: `_parse_events_safe()` → `_build_round_boundaries()` → per-round accumulation (kills, deaths, assists, damage, trade kills, flash assists, noscope/blind/wallbang/thrusmoke kills, utility usage) → `compute_round_rating()` HLTV 2.0 per-round → `aggregate_round_stats_to_match()` per PlayerMatchStats enrichment.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-09 | L402-404, L510-512 | observability-audit | LOW | f-string nei parametri del logger: `logger.info(f"Built {len(result)}...")`. Dovrebbe essere `logger.info("Built %d round stats...", len(result))` per evitare formattazione inutile se il log-level è superiore a INFO. |
| F2-10 | L65 | correctness-check | LOW | `start_tick = ticks[i - 1] if i > 0 else 0` — Per il primo round, start_tick=0, che potrebbe includere warmup ticks/events pre-match. Non critico perché demoparser2 esclude tipicamente warmup. |

**Actions:** Nessuna azione urgente. F2-09 è un pattern da cleanup globale.

---

## [4] pro_baseline.py

**Path:** `backend/processing/baselines/pro_baseline.py`
**LOC:** 470 | **Verdict:** PASS (con osservazioni)

### Logic Summary
Baseline statistiche professionali con fallback 3-tier: DB (ProPlayerStatCard) → CSV (all_Time_best_Players_Stats.csv) → hardcoded constants. Include `TemporalBaselineDecay` per baselines pesate per recenza (half-life 90 giorni). `calculate_deviations()` per Z-score user-vs-pro con protezione div-by-zero.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-11 | L76-81 | correctness-check | MEDIUM | `select(ProPlayerStatCard)` senza LIMIT. Se ci sono migliaia di pro stat cards, carica tutto in memoria. Potenzialmente lento su deployment con molto data. |
| F2-12 | L15 | correctness-check | LOW | `EXTERNAL_DATA_DIR` usa `BASE_DIR` (Programma_CS2_RENAN/) — corretto, ma se l'utente muove i CSV, il fallback è silenzioso (restituisce default hardcoded senza warning). |

**Actions:** F2-11 suggerisce `.limit(5000)` o una query aggregata con `func.avg()` direttamente in SQL. F2-12 è accettabile.

---

## [5] vectorizer.py

**Path:** `backend/processing/feature_engineering/vectorizer.py`
**LOC:** 327 | **Verdict:** WARNING

### Logic Summary
Estrattore unificato del feature vector 25-dim (METADATA_DIM=25) per training e inference. Contratto critico: ogni modifica qui impatta TUTTI i modelli. Support dual-access (dict + object attributes). Sin/cos encoding per yaw angle, MD5 hash per map identity, `nan_to_num` safety net.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-13 | L17 | observability-audit | MEDIUM | `_logger = logging.getLogger(...)` invece di `get_logger()` dal framework di observability. Inconsistente con il resto del progetto. Potrebbe mancare la configurazione del log handler. |
| F2-14 | L235 | correctness-check | MEDIUM | `hashlib.md5(map_name.encode())` — MD5 ha collisioni note. Per 9 mappe competitive non è un problema, ma se il numero di mappe cresce, la riduzione `% 10000` amplifica le collisioni (solo 10000 bucket per tutte le mappe possibili). |
| F2-15 | L191-192 | correctness-check | LOW | Logging "Position data missing" quando tutti i valori sono 0 — ma (0,0,0) è una posizione valida in alcune mappe (coordinate centrate sull'origine). Potrebbe generare falsi allarmi. |
| F2-16 | L266 | ml-check | LOW | `nan_to_num(vec, posinf=1.0, neginf=-1.0)` — Clampa silenziosamente valori anomali. Se un feature produce Inf, il bug è mascherato dal safety net. Potrebbe valere un warning log. |

**Actions:** F2-13 va corretto per uniformità. F2-14 è accettabile per il caso d'uso corrente. F2-15 e F2-16 sono osservazioni per futuri miglioramenti.

---

## [6] heatmap_engine.py

**Path:** `backend/processing/heatmap_engine.py`
**LOC:** 296 | **Verdict:** PASS

### Logic Summary
Generatore di heatmap gaussiane ad alte prestazioni. Converte punti evento discreti in texture di densità RGBA. Thread-safety esplicita: `generate_heatmap_data()` è safe da qualsiasi thread, `create_texture_from_data()` DEVE essere chiamato dal main thread (OpenGL). Include generazione di heatmap differenziali con rilevamento hotspot.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-17 | — | correctness-check | MEDIUM | Nel metodo di estrazione hotspot, se `max_val == 0` (nessun punto), la divisione `diff / max_val` rischia NaN. Il codice usa `np.clip` a valle, ma il NaN sopravvive al clip e si propaga nei risultati. |
| F2-18 | — | correctness-check | LOW | Le costanti `REFERENCE_RESOLUTION` e HUD regions sono hardcoded per 1920x1080. Funziona per la maggior parte dei setup CS2 ma potrebbe non scalare su monitor ultrawide (21:9). |

**Actions:** F2-17 richiede un guard `if max_val > 0` prima della normalizzazione. F2-18 è documentato come limitazione nota.

---

## [7] role_thresholds.py

**Path:** `backend/processing/baselines/role_thresholds.py`
**LOC:** 256 | **Verdict:** PASS

### Logic Summary
Gestisce soglie per la classificazione dei ruoli (Entry Fragger, AWPer, Support, Lurker, IGL) con persist su DB e hot-reload. Include validazione delle soglie e default factory.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-19 | — | correctness-check | MEDIUM | La validazione delle soglie controlla solo che i valori siano positivi, ma non verifica che le soglie formino una partizione consistente (es. che non ci siano gap o overlap tra role boundaries). |

**Actions:** MEDIUM — suggerisce un metodo `validate_consistency()` che verifica la copertura delle soglie.

---

## [8] role_features.py

**Path:** `backend/processing/feature_engineering/role_features.py`
**LOC:** 223 | **Verdict:** PASS

### Logic Summary
Feature engineering specifico per ruoli. Calcola features come aggression_score, entry_ratio, support_ratio, utility_usage basati su statistiche per-round aggregate.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-20 | — | ml-check | LOW | Role signatures ("entry_fragger", "support", "lurker") sono statiche e basate su euristiche fisse. Non si adattano a meta-shift (es. se i lurker iniziano a usare più utility, la feature non cattura il cambio). |

**Actions:** LOW — documentato come limitazione nota. Il drift viene catturato da meta_drift.py.

---

## [9] data_pipeline.py

**Path:** `backend/processing/data_pipeline.py`
**LOC:** 208 | **Verdict:** WARNING

### Logic Summary
Pipeline dati per MLP Neural Network: carica da DB, pulizia, temporal split (70/15/15%), fit scaler su training only, persiste split labels in DB. Usa `StandardScaler` con sklearn version tracking per compatibilità.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-21 | L49-50 | correctness-check | HIGH | `select(PlayerMatchStats)` senza LIMIT — carica TUTTI i record in memoria e li converte in DataFrame. Con migliaia di record, può esaurire la RAM. Violazione della regola CLAUDE.md "No unbounded queries". |
| F2-22 | L199-207 | data-lifecycle-review | HIGH | `_update_splits_in_db()` itera riga per riga con `session.get()` + `session.add()` + un singolo `session.commit()` alla fine. Per N record, sono N query GET + N ADD. Nessun batch update. Con 10.000 record → timeout della sessione SQLite. |
| F2-23 | L69-71 | correctness-check | MEDIUM | `train_df[self.feature_cols] = self.scaler.transform(...)` — Sovrascrive in-place le colonne originali. Se il pipeline viene rieseguito sullo stesso DataFrame, i dati sono già scaled → double-scaling. |
| F2-24 | L1, L18 | observability-audit | LOW | Usa `import logging` invece di `get_logger()`. |

**Actions:** F2-21 e F2-22 richiedono intervento. F2-21: aggiungere `.limit(50000)` o streaming. F2-22: usare bulk update SQL. F2-23 è mitigato dal fatto che `run_pipeline()` crea un nuovo DataFrame ogni volta.

---

## [10] dem_validator.py

**Path:** `backend/processing/validation/dem_validator.py`
**LOC:** 195 | **Verdict:** PASS

### Logic Summary
Validazione fail-fast dei file .dem CS2/CSGO: esistenza, size, magic number, game version, header completeness. Include sanitizzazione filename (injection prevention, double-extension detection, symlink blocking).

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-25 | L69-73 | correctness-check | MEDIUM | La logica double-extension controlla solo `parts[-2]` per estensioni pericolose, ma permette cose come `malware.py.dem` (poiché `py` non è nella lista). Lista estensioni potenzialmente incompleta. |
| F2-26 | L40 | security-scan | LOW | `FORBIDDEN_CHARS` include `\\` (backslash), ma su Windows i path usano backslash. Il check è su `filepath.name` (solo filename), quindi non dovrebbe essere un problema — ma vale la pena una nota. |
| F2-27 | L149 | correctness-check | LOW | L149 `except Exception as e: raise DEMValidationError(...)` — cattura la stessa `DEMValidationError` lanciata dal blocco try e la wrappa di nuovo. Il messaggio originale si perde nel wrapping. |

**Actions:** F2-25 suggerisce di aggiungere `py`, `vbs`, `rb`, `pl` alla lista. F2-26 e F2-27 sono minori.

---

## [11] base_features.py

**Path:** `backend/processing/feature_engineering/base_features.py`
**LOC:** 184 | **Verdict:** WARNING

### Logic Summary
Definisce `HeuristicConfig` (dataclass con soglie configurabili per feature engineering) e `extract_match_stats()` che aggrega per-round data in statistiche match-level. Usa il modulo `rating.py` unificato per HLTV 2.0.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-28 | L158 | correctness-check | HIGH | `total_damage = rounds_df["adr"].sum()` — Somma degli ADR per-round. L'ADR è già una **media** (Average Damage per Round). La somma di medie non è il danno totale. `econ_rating = sum(ADR) / money_spent` è matematicamente invalido. Dovrebbe essere `sum(damage) / money_spent` o `mean(ADR) / mean(money_per_round)`. |
| F2-29 | L131 | correctness-check | LOW | `rounds_df["kills"].std() or 0.0` — `.std()` può restituire NaN (non 0.0) per un singolo record. `NaN or 0.0` è `NaN` in Python (truthy). Dovrebbe usare `np.nan_to_num()` o `.fillna(0.0)`. |

**Actions:** F2-28 è un bug logico che produce un `econ_rating` inflazionato proporzionalmente al numero di round. Impatta qualsiasi modello che usa questa feature. F2-29 è un edge case.

---

## [12] cv_framebuffer.py

**Path:** `backend/processing/cv_framebuffer.py`
**LOC:** 183 | **Verdict:** PASS

### Logic Summary
Ring buffer thread-safe per frame video RGB destinati ad analisi CV (minimap OCR, kill feed, scoreboard). Pre-alloca N slot, resize alla risoluzione target, estrazione regioni HUD con scaling proporzionale.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-30 | L109-122 | correctness-check | MEDIUM | `get_latest(count)` — Se il buffer ha avuto un wrap-around e `_count > _buffer_size`, il calcolo `available = min(count, min(self._count, self._buffer_size))` è corretto per il count. Tuttavia, L120 `if f is not None` potrebbe saltare slot pre-filled e restituire MENO frame di `available`. Il caller non ha modo di sapere se ha ricevuto meno frame del previsto. |
| F2-31 | L25-27 | correctness-check | LOW | Costanti HUD region hardcoded per CS2 standard HUD. Custom HUD o risoluzioni 4:3 / ultrawide non supportate. Documentato nella docstring. |

**Actions:** F2-30 suggerisce di restituire `len(result)` o di inizializzare i frame a zero-arrays invece di None per garantire count stabile.

---

## [13] drift.py

**Path:** `backend/processing/validation/drift.py`
**LOC:** 167 | **Verdict:** PASS

### Logic Summary
Drift detection via Z-score rolling. Due componenti: `detect_feature_drift()` per drift retrospettivo su history, `DriftMonitor` per drift incrementale su batch. `should_retrain()` implementa persistenza ≥3/5 per evitare trigger spuri.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-32 | L43-44 | correctness-check | MEDIUM | `if past_std == 0 or np.isnan(past_std): drift_scores[feature] = 0.0` — Se std è 0 (tutti valori identici nel passato), un ANY shift viene riportato come drift=0.0 (nessun drift). Questo è semanticamente sbagliato: std=0 con un qualsiasi shift dovrebbe essere drift INFINITO, non zero. Mascheramento del segnale. |
| F2-33 | L112-113 | correctness-check | LOW | `ref_std = 0.01` come fallback per std=0 — Approccio corretto nel `DriftMonitor` class (mitiga il problema F2-32), ma il valore 0.01 è un magic number. |

**Actions:** F2-32 nel metodo funzionale `_process_feature_drift` dovrebbe allinearsi con il behavior del class-based `DriftMonitor` (usare epsilon fallback oppure segnalare come max drift). Inconsistenza tra i due approcci.

---

## [14] kast.py

**Path:** `backend/processing/feature_engineering/kast.py`
**LOC:** 146 | **Verdict:** PASS

### Logic Summary
Calcolo KAST (Kill/Assist/Survive/Trade) sia per-round (da eventi) che stimato (da aggregate stats). Trade window = 5 secondi. Stima usa euristiche basate su statistiche aggregate quando i dati per-round non sono disponibili.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-34 | L31 | correctness-check | MEDIUM | `TICKS_PER_SECOND = 64` hardcoded. CS2 matchmaking usa 64 tick, ma FACEIT/ESEA possono usare 128 tick. Se un demo da 128 tick viene processato, la trade window diventa 2.5 secondi invece di 5 (metà del valore inteso). |
| F2-35 | L131 | ml-check | LOW | `estimate_kast_from_stats()` — L'euristica `kills + assists * 0.8` per i round unici presuppone l'80% di overlap. Questo è un'approssimazione ragionevole ma non documentata la fonte (analisi statistica o intuizione?). |

**Actions:** F2-34 suggerisce di usare il tick rate dal demo header (disponibile in demoparser2). F2-35 è accettabile con documentazione.

---

## [15] external_analytics.py

**Path:** `backend/processing/external_analytics.py`
**LOC:** 142 | **Verdict:** PASS (con riserva)

### Logic Summary
`EliteAnalytics` carica 7 CSV di riferimento (top 100, match players, maps, weapons, roles, best players, tournament stats) e fornisce confronto user-vs-elite via Z-scores.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-36 | L23-28 | correctness-check | MEDIUM | `_read_safe()` restituisce `pd.DataFrame()` vuoto se il file non esiste. Il caller (`__init__`) procede senza warning. Se tutti i 7 CSV mancano, l'intera classe è operativa ma vuota — `analyze_user_vs_elite()` restituisce `{"elite_rating_avg": 0, "z_scores": {}, "tournament_z_scores": {}}`. Nessun segnale al caller che i dati sono degradati. |
| F2-37 | L50 | correctness-check | LOW | `self.historical_stats = self.match_players_df[avail].mean()` — Se il DataFrame è vuoto, `.mean()` restituisce Series di NaN. I downstream Z-score calcolatori hanno guard `if h_std.get(key, 0) > 0`, ma NaN > 0 è False, quindi fallback silenzioso. |

**Actions:** F2-36 suggerisce un metodo `is_healthy() -> bool` o un attributo `_loaded_datasets` con conteggio. F2-37 è gestito dal guard esistente.

---

## [16] rating.py

**Path:** `backend/processing/feature_engineering/rating.py`
**LOC:** 137 | **Verdict:** WARNING

### Logic Summary
Modulo unificato per il calcolo HLTV 2.0 Rating. Due implementazioni:
1. `compute_hltv2_rating()` — Formula per-componente normalizzata (per coaching deviation analysis)
2. `compute_hltv2_rating_regression()` — Coefficienti di regressione (per matching HLTV esatto)

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-38 | L47 | ml-check | MEDIUM | `compute_impact_rating()` — Formula semplificata: `(kpr * 2.13) + (avg_adr / 100.0 * 0.42)`. La formula HLTV completa è `2.13*KPR + 0.42*AssistPR - 0.41*SurvivalPR`. Manca il termine `AssistPR` e il termine negativo `SurvivalPR`. Documentato come "simplified", ma la discrepanza impatta il coaching: Impact Rating risulta sempre **più alto** del reale (manca il termine negativo). |
| F2-39 | L101 | correctness-check | CRITICAL | `kast_pct: float` nel docstring dice "KAST as percentage (e.g. 72.0 for 72%)". Ma `compute_hltv2_rating()` (L79) accetta `kast` come ratio (0.0-1.0). Se un caller passa 0.72 (ratio) a `compute_hltv2_rating_regression()`, il risultato è sbagliato (tratta come 0.72% invece di 72%). **Contratto ambiguo tra le due funzioni.** La root cause è che `HLTV2_COEFF_KAST = 0.00738764` moltiplica la percentuale, non il ratio. |
| F2-40 | L89-95 | ml-check | LOW | Formula per-componente `(r_kill + r_surv + r_kast + r_imp + r_dmg) / 5.0` produce valori diversi dalla regressione. Le due formule NON convergono allo stesso numero. Documentato, ma qualsiasi confronto cross-funzione produce discrepanze sistematiche. |

**Actions:** F2-39 è **CRITICAL** — bisogna unificare il contratto (percentuale o ratio) e documentare chiaramente chi chiama cosa. F2-38 suggerisce di completare la formula Impact o aggiungere warning. F2-40 è by-design.

---

## [17] nickname_resolver.py

**Path:** `backend/processing/baselines/nickname_resolver.py`
**LOC:** 126 | **Verdict:** PASS

### Logic Summary
Risolve nickname di giocatori professionisti usando fuzzy matching (Levenshtein distance). Cache in-memory per lookup rapidi, supporta alias multipli.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-41 | — | correctness-check | MEDIUM | Lookup O(n²) — per ogni query, scansiona tutti i nickname registrati calcolando la distanza. Con centinaia di pro players, non è un problema, ma se cresce a migliaia potrebbe diventare collo di bottiglia per batch processing. |
| F2-42 | — | correctness-check | LOW | Nessun limit al numero di alias per giocatore. Un singolo player con 100 alias occupa proporzionalmente nella cache. |

**Actions:** F2-41 suggerisce un indice basato su prefix (trie) per lookup sub-lineari se la dimensione cresce. Per ora, accettabile.

---

## [18] meta_drift.py

**Path:** `backend/processing/baselines/meta_drift.py`
**LOC:** 117 | **Verdict:** WARNING

### Logic Summary
Meta-Drift Surveillance Engine. Traccia shift negli stili di gioco pro nel tempo. Combina drift statistico (40% rating shift) + drift spaziale (60% position centroid shift). Output: coefficiente 0.0-1.0 che modula la confidence del Coach.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-43 | L33 | correctness-check | MEDIUM | `datetime.utcnow()` — Deprecato da Python 3.12+. Dovrebbe usare `datetime.now(timezone.utc)`. Pattern ricorrente nel progetto (vedi Phase 1 cross-notes). |
| F2-44 | L66-69 | correctness-check | MEDIUM | `r_centroid = np.mean(recent_pts, axis=0)` — Se `recent_pts` contiene tuple di (pos_x, pos_y), `np.mean` su una lista di tuple produce il comportamento desiderato SOLO se tutte le tuple hanno la stessa lunghezza. Se qualche query restituisce `None` o dati parziali, crash con shape mismatch. |
| F2-45 | L86 | correctness-check | LOW | `max(..., 1e-6)` per protezione div-by-zero su `hist_avg`. Se tutte le rating pro sono 0.0, `max(0.0, 1e-6) = 1e-6`, e il drift calculation diventa `abs(0 - 0) / 0.000001 / 0.20` = 0.0 — corretto. |

**Actions:** F2-43 è un pattern da risolvere globalmente. F2-44 suggerisce un guard `if len(set(len(p) for p in recent_pts)) > 1: return 0.0`.

---

## [19] connect_map_context.py

**Path:** `backend/processing/connect_map_context.py`
**LOC:** 113 | **Verdict:** PASS

### Logic Summary
Connette contesto mappa ai dati di processing. Normalizza distanze e aree in base alla dimensione della mappa specifica.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-46 | — | correctness-check | LOW | Normalizzazione distanze usa costanti fisse per mappa. Se i metadati in spatial_data.py cambiano (nuova mappa, scale diversa), questo file non si aggiorna automaticamente. |

**Actions:** Nessuna azione urgente.

---

## [20] sanity.py

**Path:** `backend/processing/validation/sanity.py`
**LOC:** 113 | **Verdict:** PASS

### Logic Summary
Sanity checks sui DataFrame dei demo: range validation, outlier detection, completeness checks. Produce un report di sanity con flag per valori sospetti.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-47 | — | correctness-check | MEDIUM | Le funzioni di sanity modificano il DataFrame in-place (aggiungendo colonne flag). Se il caller non se lo aspetta, il DataFrame originale viene mutato. Pattern "no hidden side effects" violato. |

**Actions:** MEDIUM — suggerisce di lavorare su una copia `df.copy()` o documentare esplicitamente la mutazione.

---

## [21] schema.py

**Path:** `backend/processing/validation/schema.py`
**LOC:** 82 | **Verdict:** PASS (con riserva)

### Logic Summary
Validazione schema con versioning. `EXPECTED_SCHEMA` definisce colonne obbligatorie per versione. `validate_demo_schema()` verifica esistenza colonne e tipi (numeric check).

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-48 | L72-81 | correctness-check | MEDIUM | `_validate_column_type()` — Controlla solo se la colonna è "numeric" (`pd.api.types.is_numeric_dtype`), poi tenta un cast. Non distingue tra int e float. Una colonna `round` con valori float (es. 1.5) passa la validazione come `int` perché il cast `int(1.5)` = 1 non lancia eccezione, ma tronca silenziosamente. |

**Actions:** F2-48 suggerisce di usare `isinstance` check sui valori effettivi piuttosto che un cast try/except.

---

## [22] state_reconstructor.py

**Path:** `backend/processing/state_reconstructor.py`
**LOC:** 64 | **Verdict:** WARNING

### Logic Summary
Ricostruttore di stato per RAP-Coach. Converte sequenze di tick DB in tensori via `FeatureExtractor` + `TensorFactory`. Temporal windowing con overlap 50%.

### Findings

| # | Line | Classification | Severity | Description |
|---|------|---------------|----------|-------------|
| F2-49 | L41 | correctness-check | CRITICAL | `self.tensor_factory.generate_all_tensors(ticks, self.map_name)` — Il metodo `generate_all_tensors` di TensorFactory accetta `(tick_data_list, map_name)` nella versione legacy, ma il refactor Player-POV richiede `knowledge` parameter per i nuovi tensor. Se `state_reconstructor` è usato con il TensorFactory post-refactor, i tensori saranno generati in modalità **legacy** (senza Player-POV), creando un mismatch training/inference se GhostEngine usa Player-POV. |
| F2-50 | L56-62 | correctness-check | MEDIUM | `segment_match_into_windows()` — Il range `range(0, len(match_ticks) - self.sequence_length, self.sequence_length // 2)` perde gli ultimi tick se `len(match_ticks) % (sequence_length // 2) != 0`. Per un match di 3000 tick con sequence_length=32, step=16: ultimo window inizia a tick 2976, copre 2976-3008 (out of bounds). In realtà il range upper bound lo previene, ma gli ultimi ~16 tick non vengono mai processati. |

**Actions:** F2-49 è **CRITICAL** — `state_reconstructor.py` deve essere aggiornato per la nuova API Player-POV del TensorFactory, o documentato come modulo legacy-only. F2-50 è un edge case accettabile (perdita di pochi tick).

---

## [23] `__init__.py` stubs

**Path:** `backend/processing/__init__.py`, `backend/processing/feature_engineering/__init__.py`, `backend/processing/baselines/__init__.py`, `backend/processing/validation/__init__.py`

| File | LOC | Note |
|------|-----|------|
| `processing/__init__.py` | 22 | Registra `PROCESSING_VERSION = "2.0"`. Imports condizionali. OK. |
| `feature_engineering/__init__.py` | 5 | Empty stub. OK. |
| `baselines/__init__.py` | 3 | Empty stub. OK. |
| `validation/__init__.py` | 2 | Empty stub. OK. |

**Verdict:** PASS — Nessuna issue.

---

## Cross-Phase Notes

### Pattern Ricorrenti (Processing Pipeline)

1. **Tick-rate hardcoding (64 tick/s)**: Trovato in `kast.py` (L31), `player_knowledge.py` (L38, L438), `tensor_factory.py` (L54). CS2 matchmaking usa 64 tick, ma FACEIT/ESEA possono usare 128 tick. Impatto: finestre temporali dimezzate su demo 128-tick.

2. **`import logging` vs `get_logger()`**: Trovato in `vectorizer.py` (L17), `data_pipeline.py` (L18), `drift.py` (L10). Inconsistente con il framework di observability del progetto.

3. **`datetime.utcnow()` deprecato**: Trovato in `meta_drift.py` (L33). Pattern ricorrente dal Phase 1.

4. **entity_id=0 cascata**: La root cause in `MatchEventState.entity_id` (Phase 1, F1-05) propaga il bug fino a `player_knowledge.py` (F2-05), dove utility con entity_id=0 si sovrascrivono nel dict.

5. **HLTV 2.0 contratto kast duale**: `compute_hltv2_rating()` accetta ratio (0.0-1.0), `compute_hltv2_rating_regression()` accetta percentuale (0-100). Qualsiasi caller che non conosce la distinzione produce rating errati.

### Cross-Reference con Phase 1

- F2-05 (player_knowledge entity_id) ← F1-05 (MatchEventState default=0)
- F2-13 (vectorizer logging) ← Phase 1 cross-note: logging inconsistency
- F2-43 (utcnow) ← Phase 1 cross-note: datetime deprecation

### Cross-Reference con Phase 3 (Preview)

- F2-49 (state_reconstructor legacy API) → `training_orchestrator.py` deve verificare quale API TensorFactory usa
- F2-39 (rating kast contratto) → Qualsiasi training loop che chiama `compute_hltv2_rating_regression()` con ratio decimale produce rating sbagliati

---

## Quality Gate Verification

### Tensor Shape Contracts
- **METADATA_DIM = 25**: Confermato in `vectorizer.py:L20`. Usato consistentemente da `state_reconstructor.py:L23`.
- **Map tensor**: 3 canali × configurable resolution (64x64 training, 128x128 default). Confermato in `tensor_factory.py:L65-82`.
- **View tensor**: 3 canali × configurable resolution (64x64 training, 224x224 default). Confermato.
- **Motion tensor**: 3 canali × same resolution as map. Confermato.

### FOV Cone Assumptions (player_knowledge.py)
- FOV = 90° orizzontale (hardcoded). CS2 reale: 54-68° verticale → 90-106° orizzontale variabile. ✅ Approssimazione ragionevole per il caso standard.
- **No wall occlusion**: Il cono FOV non tiene conto dei muri. Documentato come "Known Architectural Debt" in MEMORY.md. ✅ Confermato.

### HLTV 2.0 Formula Consistency
- `rating.py` definisce due formule divergenti (per-component vs regression). ✅ Documentato.
- `round_stats_builder.py` usa `compute_round_rating()` che chiama `compute_hltv2_rating()` (per-component). ✅ Consistente.
- `base_features.py` usa `compute_hltv2_rating()`. ✅ Consistente.
- **ATTENZIONE**: Il contratto kast (ratio vs percentuale) è **inconsistente** tra le due funzioni (F2-39). ⚠️

---

## Issue Priority Matrix

### CRITICAL (Fix Immediato)
| ID | File | Description | Blast Radius |
|----|------|-------------|-------------|
| F2-39 | rating.py:L101 | kast_pct contratto ambiguo ratio/percentuale | ALTO — qualsiasi caller che usa la funzione sbagliata produce rating errati |
| F2-49 | state_reconstructor.py:L41 | API TensorFactory legacy vs Player-POV mismatch | ALTO — training/inference skew se non allineato |
| F2-21 | data_pipeline.py:L49 | `select()` senza LIMIT carica tutto in RAM | MEDIO — OOM su dataset grandi |
| F2-28 | base_features.py:L158 | Somma di ADR (medie) per econ_rating è matematicamente invalida | MEDIO — econ_rating feature è sbagliata |

### HIGH (Sprint Corrente)
| ID | File | Description | Blast Radius |
|----|------|-------------|-------------|
| F2-22 | data_pipeline.py:L199 | N query singole per split update | MEDIO — timeout su grandi dataset |
| F2-05 | player_knowledge.py:L479 | entity_id=0 sovrascrive utility nel dict | BASSO — cascata da F1-05 |
| F2-34 | kast.py:L31 | Tick rate hardcoded 64 Hz | BASSO — errato solo su demo 128 tick |
| F2-38 | rating.py:L47 | Impact rating formula semplificata (manca SurvivalPR) | BASSO — sistematicamente più alto del reale |
| F2-01 | tensor_factory.py:L686 | Singleton non thread-safe | BASSO — race solo in scenario multi-thread |

### MEDIUM (Backlog Prioritario)
| ID | Count | Pattern |
|----|-------|---------|
| F2-06, F2-34, F2-03 | 3 | Costanti hardcoded (FOV, tick rate, speed) |
| F2-11, F2-21 | 2 | Query unbounded senza LIMIT |
| F2-13, F2-24 | 2 | Logging inconsistente |
| F2-17, F2-32, F2-47, F2-48 | 4 | Correctness edge cases |
| F2-19, F2-23, F2-25, F2-30, F2-36, F2-41, F2-43, F2-44, F2-50 | 9 | Vari MEDIUM individuali |

### LOW (Nice-to-Have)
| Count | Pattern |
|-------|---------|
| 15 | F-string logger, documentazione, costanti cosmetiche, edge cases minori |

---

**End of Phase 2 Report**
**Next Phase:** Phase 3 — Neural Network Architecture (~42 file, ~7.380 LOC)
