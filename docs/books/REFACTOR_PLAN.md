# Coach Books — Refactor Plan

> **Status:** Audit + plan only. No book content has been edited yet. This document is the contract for the refactor; execution happens in subsequent sessions.
>
> **Authored:** 2026-04-08
> **Scope:** All 4 books in `docs/books/` (Book-Coach-1A, 1B, 2, 3) — total ~8,128 lines of Italian markdown.
> **Goals (per user):** drift fixes + new content + structural restructure (renumber, retitle, consolidate duplicates) + IT/EN dual-language maintenance.

---

## 1. Executive summary

The four Coach Books are a deeply technical Italian-language engineering reference covering the entire CS2 Coach architecture. They contain real engineering value but suffer from **three categories of problems**:

1. **Structural** — overlapping section numbers between books, missing section headers, duplicated topics in two volumes, no consistent frontmatter style.
2. **Drift** — code-level details (file paths, line counts, model names, hyperparameters, table counts, version numbers) have drifted from current state. Evidence collected in §5 below.
3. **Coverage gaps** — major work landed *since* the books were written (Coach Book v3, llama3.1:8b swap, asset purge, demo re-aggregation discovery, the Quality Roadmap itself) is not documented.

Doing this in one session is impossible. The plan in §7 sequences ~8 sessions with clear deliverables per session, IT-first then EN translation.

---

## 2. Master inventory (verified 2026-04-08)

| Book | File | Lines | H1 frontmatter? | Sections (current) | Topic |
|---|---|---|---|---|---|
| 1A | `Book-Coach-1A.md` | 1,315 | ✅ Yes — title + blockquote topics + Renan's introduction + Indice | §1, §2, §3 (clean) | Neural architecture, JEPA/VL-JEPA/LSTM+MoE, 25-dim contract, NO-WALLHACK, system overview |
| 1B | `Book-Coach-1B.md` | 1,178 | ✅ Yes — title + Indice | **§4 header MISSING** (content jumps straight in), then §5 | RAP Coach 7-component model, ChronovisorScanner, GhostEngine, data sources (Demo Parser, HLTV, Steam, FACEIT) |
| 2 | `Book-Coach-2.md` | 2,492 | ❌ **No frontmatter** — starts cold with `## 5.` | §5, §5B, §6, §7, §8, §9, §10, §11, §12, §13 | Coaching services, knowledge & retrieval, analysis engines, feature engineering, training pipeline, loss functions |
| 3 | `Book-Coach-3.md` | 3,143 | ❌ **No frontmatter** — starts cold with `## 9.` | §9, §10, §11, §12 (with subsections 12.1-12.28) | Database schema, training regime, loss catalog, full program logic |

PDFs in the same directory (`Book-Coach-*.pdf`) are exports from March 2026 — older than the .md files. Treat .md as the live source.

---

## 3. Structural problems

### 3.1 Section number collisions

Two books share the same numbers for entirely different topics:

| § | Book 1B | Book 2 | Book 3 |
|---|---|---|---|
| 5 | Sorgenti Dati | Servizi di Coaching | — |
| 9 | — | Sottosistema 7 — Modulo di Controllo | Schema del database e ciclo di vita dei dati |
| 10 | — | Sottosistema 8 — Progresso e Tendenze | Regime di formazione e limiti di maturità |
| 11 | — | Sottosistema 9 — Database e Storage | Catalogo delle funzioni di perdita |
| 12 | — | Pipeline di Addestramento e Orchestrazione | Logica Completa del Programma |

Cross-references between books are currently ambiguous: "vedi §11" could mean either Book 2 §11 (Database) or Book 3 §11 (Loss functions).

### 3.2 Topic duplication between Book 2 and Book 3

Three topics are documented in BOTH Book 2 and Book 3, with overlapping but inconsistent content:

| Topic | Book 2 location | Book 3 location | Action |
|---|---|---|---|
| Database & Storage | Book 2 §11 (`backend/storage/`, db_models, MatchDataManager, BackupManager…) | Book 3 §9 (`Schema del database e ciclo di vita dei dati`) | **Consolidate into Book 3** |
| Training pipeline | Book 2 §12 (`TrainingOrchestrator`, JEPATrainer, RAPTrainer, train.py, callbacks) | Book 3 §10 (`Regime di formazione e limiti di maturità`) | **Consolidate into Book 3** |
| Loss functions | Book 2 §13 (`jepa_contrastive_loss`, `vl_jepa_concept_loss`, `compute_sparsity_loss`, position loss…) | Book 3 §11 (`Catalogo delle funzioni di perdita`) | **Consolidate into Book 3** |

These duplications mean Book 2 currently runs to §13 partly because it grew chapters that overlap with Book 3's territory. Once consolidated, Book 2 ends naturally at §10 (Progresso e Tendenze) and Book 3 inherits Database/Training/Losses cleanly.

### 3.3 Missing structural elements

- **Book 1B has no §4 header.** The book opens, then content for "RAP Coach 7-component model" begins at line ~30 with no section number, then suddenly §5 Sorgenti Dati appears at line 613. RAP details deserve §4.
- **Book 2 has no H1 title, no Indice, no introduction.** Reader is dropped into `## 5.` with no context.
- **Book 3 has no H1 title, no Indice, no introduction.** Same problem, dropped into `## 9.`.
- **No global glossary across books.** Book 3 has a terminal "Glossario Tecnico" (line 3114) but it covers only Book 3's terms.
- **No "Mappa delle Interconnessioni"** at the front of any book; Book 3 has one at the END (line 3048). Should be at the front of Book 1A as a global map.

---

## 4. Proposed new structure — continuous numbering

Single linear chapter numbering across all four volumes. Each book has a clean contiguous range. No collisions. No duplications.

### 4.1 Final layout (4 books, 19 chapters)

| Book | New title (IT) | English title | Chapters | Topic |
|---|---|---|---|---|
| **Vol. I — Parte 1A** | "Il Cervello" | "The Brain" | **1, 2, 3** | Neural architecture, system overview |
| **Vol. I — Parte 1B** | "I Sensi e lo Specialista" | "The Senses and the Specialist" | **4, 5** | RAP Coach internals + data sources |
| **Vol. II — Parte 2** | "Servizi, Conoscenza e Analisi" | "Services, Knowledge, and Analysis" | **6, 7, 8, 9, 10, 11, 12** | Coaching services, knowledge subsystem, analysis engines, feature engineering, control, trends |
| **Vol. III — Parte 3** | "Database, Addestramento e Programma" | "Database, Training, and Program" | **13, 14, 15, 16, 17, 18, 19** | Database, training pipeline, losses, program logic, ingestion, UI, build/tests |

### 4.2 Chapter-by-chapter mapping (current → new)

| New § | New title | Current location | Notes |
|---|---|---|---|
| **Book 1A — Il Cervello** |
| 1 | Riepilogo esecutivo | 1A §1 | Drift check: claims about JEPA training status, 38 demos (now 110), GPU spec |
| 2 | Panoramica dell'architettura del sistema | 1A §2 | Drift check: NO-WALLHACK, 25-dim contract still valid; verify Quad-Daemon names |
| 3 | Sottosistema 1 — Nucleo della rete neurale | 1A §3 | Drift check: hyperparameters, ModelFactory, NeuralRoleHead existence |
| **Book 1B — I Sensi e lo Specialista** |
| 4 | Sottosistema 2 — RAP Coach (architettura 7 componenti) | 1B (currently NO § header) | **NEW HEADER**. Wraps Perception, Memory LTC+Hopfield, Strategy, Pedagogy, Skill Model, Trainer, ChronovisorScanner, GhostEngine |
| 5 | Sottosistema 3 — Sorgenti Dati Esterne | 1B §5 | Drift check: HLTV scraping (FlareSolverr+Docker now), FACEIT, Steam, demo parser, FrameBuffer, FAISS |
| **Book 2 — Servizi, Conoscenza e Analisi** |
| 6 | Sottosistema 4 — Servizi di Coaching | 2 §5 | Drift check: CoachingService, OllamaCoachWriter (new model name), AnalysisOrchestrator |
| 7 | Sottosistema 5 — Motori di Coaching | 2 §5B | Drift check: HybridCoachingEngine, CorrectionEngine, ProBridge, all line counts |
| 8 | Sottosistema 6 — Conoscenza e Recupero | 2 §6 | **HIGH DRIFT** — see §5.1. Add Coach Book v3, book/ dir, 6 categories, 151 entries, loader changes |
| 9 | Sottosistema 7 — Motori di Analisi | 2 §7 | Drift check: 10 analysis engines (role_classifier, win_probability, game_tree, belief_model, deception_index, momentum, entropy, blind_spots, engagement_range, utility_economy) |
| 10 | Sottosistema 8 — Elaborazione e Feature Engineering | 2 §8 | Drift check: vectorizer 25-dim, rating, tensor_factory, heatmap, validation, PlayerKnowledge, ProBaseline, RoleThresholdStore |
| 11 | Sottosistema 9 — Modulo di Controllo | 2 §9 | Drift check: Console singleton, ServiceSupervisor, DatabaseGovernor, IngestionManager, MLController |
| 12 | Sottosistema 10 — Progresso e Tendenze | 2 §10 | Likely thin; verify FeatureTrend, TrendAnalysis still exist |
| **Book 3 — Database, Addestramento e Programma** |
| 13 | Sottosistema 11 — Database e Storage (consolidato) | **2 §11 + 3 §9** | **MAJOR CONSOLIDATION**. Merge Book 2's Database/Storage chapter with Book 3's Schema del database. Update table count (22+3=25), document duplicated proplayer/proplayerstatcard/proteam in both DBs, document hltvdownload table |
| 14 | Sottosistema 12 — Pipeline di Addestramento (consolidato) | **2 §12 + 3 §10** | **MAJOR CONSOLIDATION**. TrainingOrchestrator + JEPATrainer + RAPTrainer + train.py + callbacks, plus the "regime di formazione e limiti di maturità" framing |
| 15 | Sottosistema 13 — Funzioni di Perdita (consolidato) | **2 §13 + 3 §11** | **MAJOR CONSOLIDATION**. Loss catalog: jepa_contrastive_loss, vl_jepa_concept_loss, compute_sparsity_loss, position loss, win_prob loss |
| 16 | Logica Completa del Programma — Dal Lancio al Consiglio | 3 §12 (sections 12.1–12.28) | Drift check entire chapter — biggest single chapter, ~2,400 lines. Most subsections will need fact-checks |
| 17 | Pipeline di Ingestione | 3 §12.6 + §12.23 + §12.24 | Promote ingestion to its own chapter — too important to be a subsection |
| 18 | Interfaccia Desktop e Frontend (Qt/PySide6) | 3 §12.5 + §12.10 | Promote UI to its own chapter — Qt migration is a big topic |
| 19 | Build, Test, Tooling e Operations | 3 §12.17–§12.21 + §12.25–§12.28 | Promote ops/build/test to its own chapter |

After this restructure: **4 books, 19 contiguous chapters, zero collisions, zero duplications, every chapter has a unique number.**

### 4.3 What to keep as-is

- **Renan's "Introduzione di Renan" in Book 1A** — personal voice, do not edit.
- **The mermaid diagrams** — preserve all of them; only update labels where they reference renamed/removed components.
- **The "Analogia" blockquotes** — they're a teaching device, keep the style intact.
- **The Glossario Tecnico at the end of Book 3** — promote it to a global cross-book glossary at the start of Book 1A (or as an appendix in Book 3, doesn't matter, but make it global).

---

## 5. Drift hotspots — concrete examples found in audit

This is **not** an exhaustive list. Per-chapter drift audits happen during execution. Below are examples found while spot-checking 3 sections; expect dozens more across the full ~8,000 lines.

### 5.1 Book 2 §6 (Knowledge & Retrieval) — HIGH DRIFT (lines 486-650)

Found in a single 130-line section:

| Line | Claim | Reality (verified) |
|---|---|---|
| 506 | `CURRENT_VERSION = "v2"` | **`v3`** (bumped 2026-04-07) |
| 507 | "Categorie 11: obiettivo, posizionamento, utilità, movimento, economia, strategia, posizionamento del mirino, comunicazione, mentale, senso del gioco, trading" | **6 categories** (Coach Book v3): `positioning, utility, economy, aim_and_duels, mid_round, retakes_post_plant` |
| 504 | "Similarità del coseno tramite `scipy.spatial.distance.cosine`" | numpy dot product (`rag_knowledge.py:359`); no scipy import |
| 595-607 | Knowledge Graph with `kg_entities`, `kg_relations` SQLite tables | **No such tables exist** in `database.db` (verified via SELECT) |
| 609 | "init_knowledge_base.py, 111 righe" | ~125 lines after the v3 loader changes |
| 613 | "data/tactical_knowledge.json" | Wrong path: `Programma_CS2_RENAN/backend/knowledge/tactical_knowledge.json`; the **primary** source is now `book/index.json` |
| missing | Coach Book v3, `book/` directory, loader index detection, allow-list strip, Renan's session 2026-04-07 work | Entirely absent |

### 5.2 Book 3 §9 (Database) — HIGH DRIFT (lines 1-329)

| Line | Claim | Reality (verified) |
|---|---|---|
| 3 | "21 tabelle SQLModel principali distribuite su 2 database" | **22 in database.db + 3 in hltv_metadata.db = 25** |
| 5 | "database.db (18 tabelle)" + table list | Actual: 22 tables. Missing from list: `hltvdownload`, `proplayer`, `proplayerstatcard`, `proteam` (yes, also in main DB — duplication issue) |
| 6 | "hltv_metadata.db ... (3 tabelle)" | **Verified correct** |
| 6 | "Separato dal monolite perché viene scritto da un processo separato (HLTV sync service) per eliminare la contesa WAL" | True for hltv_metadata.db, but the main DB ALSO has these tables — the architecture is more nuanced (or this is migration leftover) |

### 5.3 Book 2 §5 (Servizi di Coaching) — KNOWN DRIFT

This section documents `OllamaCoachWriter` and `llm_service`. Yesterday I changed the default model from `llama3.2:3b` → `llama3.1:8b` across 7 files including documentation. **Book-Coach-2.md line ~210 was already updated as part of that swap.** The rest of §5 (and §5B onwards) needs a full pass to verify the line counts in the section labels (e.g. "HybridCoachingEngine, 643 righe") against current code.

### 5.4 Categories of drift to expect everywhere

- **Line count claims** in section labels ("foo.py, 643 righe") — almost all stale. These should be either updated or removed entirely (line counts are noise, not signal).
- **Hyperparameter values** (lr, batch size, epochs, etc.) — verify against current `nn/config.py`, `jepa_train.py`, `rap_coach/trainer.py`.
- **Demo count** (38 vs 110 vs 140) — must be consistent with `project_quality_roadmap.md` reality: 110 unique demos on disk, 38 aggregated.
- **GPU references** — book likely doesn't mention GTX 1650 4 GB. The Quality Roadmap does.
- **CSGO-era references** — book might still mention Vertigo, Cache, Train as active maps. Per Coach Book v3, active duty is now Anubis/Ancient/Dust2/Inferno/Mirage/Nuke/Overpass.
- **Kivy references** — Book 1A line 21 already has the Kivy→Qt migration note, but other sections may still describe Kivy as primary.
- **File paths** — spot checks already turned up `data/tactical_knowledge.json` (wrong); expect more wrong paths.

---

## 6. Coverage gaps — content to ADD

Things that landed in the codebase since the books were written and have ZERO documentation:

| New thing | Where it lives | Add to chapter |
|---|---|---|
| **Coach Book v3** (book/ dir, 8 files, 151 entries, 6 categories, S4 active duty) | `Programma_CS2_RENAN/backend/knowledge/book/` | Ch. 8 (Knowledge) |
| **`KnowledgePopulator` index format detection + allow-list** | `rag_knowledge.py:KnowledgePopulator.populate_from_json` | Ch. 8 |
| **`CURRENT_VERSION` v2→v3 migration** | `rag_knowledge.py:48` | Ch. 8 |
| **Llama 3.1 8B model swap** | `backend/services/llm_service.py:25` | Ch. 6 |
| **Legacy asset purge** (50 PNGs + 1 DDS, list of removed maps) | `Programma_CS2_RENAN/PHOTO_GUI/maps/`, `Programma_CS2_RENAN/assets/maps/` | Ch. 18 (UI/frontend) or Ch. 19 (ops) |
| **Demo re-aggregation gap** (38 in production tables, 110 on disk) | `Programma_CS2_RENAN/backend/storage/match_data` symlink | Ch. 13 (Database) and Ch. 17 (Ingestion) |
| **Quality Roadmap** (`docs/COACH_QUALITY_ROADMAP.md`) | docs/ | Reference from Ch. 1 (Riepilogo esecutivo) and Ch. 14 (Training) |
| **JEPA Phase F unblocked but parked** | data curation completion 2026-04-04 | Ch. 14 (Training) |
| **Data curation phases A-E completed** | `tools/populate_round_stats.py`, `tools/repair_kast.py`, `tools/mine_coaching_experience.py` | Ch. 13 + Ch. 17 |
| **Pre-commit hooks (13 hooks)** | `.pre-commit-config.yaml` | Ch. 19 (build/ops) |
| **`tools/headless_validator.py`** | `tools/` | Ch. 19 |
| **CS2 Premier S4 active duty alignment** | Coach Book v3 docs | Ch. 5 (data sources) and Ch. 8 |

This list is **inevitably incomplete**. Per-chapter audits during execution will surface more.

---

## 7. Execution plan — session by session

The user wants both Italian AND English versions. Strategy: **IT-first restructure + drift fix + new content**, then **EN translation as a separate pass**. Doing both languages simultaneously triples the cognitive load and guarantees inconsistency.

### Phase 1 — IT restructure & drift fix (5 sessions)

| Session | Scope | Output |
|---|---|---|
| **1** | Create the structural skeleton: rename files (`Book-Coach-1A.md` → `Book-1-Parte-1A-Cervello.md` or similar), add H1 + Indice frontmatter to Books 2 and 3, add §4 header to Book 1B, prepare consolidated chapter shells in Book 3 for the Database/Training/Loss merges. Also: copy Book 2 §11/§12/§13 content into Book 3 chapters 13/14/15 (do not yet delete from Book 2 — that's the next session). | New file names, all H1/Indice in place, content duplicated for safe consolidation, NO drift fixes yet |
| **2** | Drift fix Book 1A (1,315 lines, §1-§3). Verify against current code: JEPA hyperparameters, RAP architecture references, NeuralRoleHead, ModelFactory, Quad-Daemon names, NO-WALLHACK, 25-dim contract. Add Quality Roadmap link in §1. | Book 1A clean and current |
| **3** | Drift fix Book 1B (1,178 lines). Add the missing §4 header. Verify RAP 7-component code paths still match. Verify HLTV/FACEIT/Steam/demo parser paths. Update FrameBuffer, FAISS, RoundContext sections. | Book 1B clean and current |
| **4** | Drift fix Book 2 (2,492 lines, but minus the §11/§12/§13 that moved to Book 3 in session 1). Big focus: Ch. 8 (Knowledge) needs full rewrite for Coach Book v3. Also Ch. 6 (services) for the Llama swap. Verify all 10 analysis engines. | Book 2 clean and current |
| **5** | Drift fix + consolidation finalize Book 3 (3,143 lines). Big focus: Ch. 13 (Database) — fix table count, document table duplication, update schema diagrams. Ch. 14 (Training) — merge content from old Book 2 §12. Ch. 15 (Losses) — merge content from old Book 2 §13. Ch. 16-19 — drift fix the program logic monster chapter. | Book 3 clean, consolidated, current. End of Phase 1 |

### Phase 2 — EN translation (3 sessions)

| Session | Scope | Output |
|---|---|---|
| **6** | Create English mirror files: `Book-1-Part-1A-Brain.md`, `Book-1-Part-1B-Senses.md`, etc. Translate Book 1A and 1B in full. Maintain parallel section numbers and IDs. Build a glossary of canonical translations (e.g. "Sottosistema" → "Subsystem", "Cervello" → "Brain"). | Book 1A + 1B in English, glossary started |
| **7** | Translate Book 2 in full. | Book 2 in English |
| **8** | Translate Book 3 in full. End of Phase 2. | Book 3 in English. Both languages complete and parity-checked |

### Phase 3 — Optional (deferred until after Phase 2)

- Re-export PDFs from the new .md files (replaces the March exports in `docs/books/*.pdf`).
- Build a single combined "Coach Book Omnibus" PDF with all 4 books + global glossary + global index.
- Add anchor IDs to every section so cross-references are stable.

### Total estimate: **8 sessions** for full IT+EN refactor.

---

## 8. What this session (the audit) produces

- **`docs/books/REFACTOR_PLAN.md`** (this file) — the contract.
- Memory entry `project_books_refactor.md` with the active plan.
- `MEMORY.md` updated.
- **No book content edited.** No PDFs touched. No file renames.

The very next session (Session 1 in §7) starts the structural skeleton work.

---

## 9. Risks and what NOT to touch

### Do not touch
- **Renan's "Introduzione di Renan"** in Book 1A. Personal voice, hard-earned, off-limits.
- **Mermaid diagram aesthetics** — only update labels when components are renamed/removed. Do not redo color schemes or layouts.
- **The "Analogia" teaching blockquotes** — they're the books' pedagogical signature. Keep the voice and length even if updating facts inside them.
- **The PDF exports** in `docs/books/*.pdf` until after Phase 1 is complete. Re-export at the END.

### Risks
| Risk | Mitigation |
|---|---|
| Italian translation quality varies by section | Per-chapter quality review pass after each session; keep a glossary of canonical translations |
| Consolidation loses information that was in only one of the duplicated chapters | Phase 1 Session 1 keeps content in BOTH books temporarily; only delete from Book 2 after the merge into Book 3 is verified complete |
| Drift fixes introduce new errors (we say "X" when current code is "Y") | Every fact changed must cite the file:line of the verifying source. No memory-based claims. |
| Numbering changes break external references | After renumbering, do a global grep for old "§5", "§9" etc. patterns and update or annotate |
| Sessions take longer than estimated | Each session can be split (e.g. "Book 3 §16 only") if context budget pressures arise |
| Translation drift between IT and EN versions over time | After Phase 2, every future change must be applied to BOTH languages in the same session |

---

## 10. Open questions to resolve before Session 1

1. **File naming convention.** Current: `Book-Coach-1A.md`, `Book-Coach-1B.md`, `Book-Coach-2.md`, `Book-Coach-3.md`. Proposed for IT: `Libro-1-Parte-1A-Cervello.md`, etc. Or keep current names and only update content? Or use neutral names like `Book-1A.md`, `Book-1B.md`, `Book-2.md`, `Book-3.md`?
2. **English file naming.** Parallel to IT? Suffix? Subdirectory `docs/books/en/`?
3. **Title format.** Currently "Ultimate CS2 Coach — Parte 1A: Il Cervello". Keep "Ultimate CS2 Coach"? Switch to "Macena CS2 Coach"? Drop the marketing word?
4. **Glossary location.** Keep at end of Book 3, move to start of Book 1A, or create a separate `Book-0-Glossary.md`?
5. **Line count claims** in section labels (e.g. "643 righe") — drop them entirely, or keep and maintain? **Recommendation: drop them.** They're noise that drifts on every commit.
6. **Cross-references.** When Ch. 8 (Knowledge) references Ch. 14 (Training), do we use "(vedi Cap. 14)" or markdown anchor links `[Cap. 14](#14-pipeline-di-addestramento)`?

These need answers before Session 1 starts. Captured here so the next session opens with explicit alignment.
