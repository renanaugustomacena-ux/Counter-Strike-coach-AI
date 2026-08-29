# Verification round 2 — frontend, integrity, tooling (2026-08-29)

Mission (user directive): verify the frontend, the entire codebase's integrity and
stability, and update the tools/tests that round 1 made stale. Training deferred to
Linux. Method: static impact inventory of every round-1 change, the full validation
ladder run bottom-to-top, all 15 Qt screens rendered offscreen and eyeballed
individually, and every failure adjudicated by reading the failing tool — no
failure dismissed as "environmental" without evidence.

## Ladder results (all runs in the project venv, Windows)

| Gate | Result | Notes |
|---|---|---|
| L1 headless_validator | PASS 318/319 | 1 warn: optional `shap` not installed |
| L2 pytest (both roots) | **2706 passed, 56 skipped, 0 failed** | includes qt suites + ui_smoke |
| L3 backend_validator | PASS 35/40 | 5 env warns: no CUDA, no backups/checkpoints/registry yet, HLTV daemon off |
| L4 Ultimate_ML_Coach_Debugger | PASS 18/21 | 3 env warns |
| L4 Goliath_Hospital | PASS 682/768 | after D-27 scanner fixes |
| Meta-gate verify_all_safe | 27/28 | the one red is `verify_lock_hashes` reporting a REAL policy violation (D-29) |

## D-15b — amendment to D-15 (my round-1 fix was itself defective)

The round-1 D-15 fix filtered `dataset_split = 'train'` (the enum VALUE).
SQLAlchemy's `Enum` column stores the enum **NAME** (`'TRAIN'`) on disk — verified
against the production DB (ORM matched 1 row; raw lowercase SQL matched 0; DDL is
plain `VARCHAR(10)`). The "fixed" loaders matched **zero rows on real databases**:
training would have started with an empty corpus and the round-1 test suite passed
because its fixture seeded the same wrong assumption (lowercase rows).

Fix (PR #84): loaders filter `UPPER(dataset_split) = ?` with the literal derived
from `DatasetSplit.TRAIN.name` (SSOT, not a string). The rewritten test writes a
row THROUGH the ORM and reads it back through the raw-SQL loader
(`TestOnDiskRepresentationLockstep`), so any future change to the on-disk
representation fails loudly instead of silently emptying the corpus.

Lesson recorded: a test that shares its fixture assumptions with the code under
test verifies nothing. When code and storage layer meet, pin the REAL on-disk
representation end-to-end.

## D-27 — Goliath_Hospital scanner defects (PR #85)

Goliath's 3 failures were all scanner bugs, not codebase bugs:

1. The "hardcoded credential" pattern flagged `api_key="test"` dummies — now
   requires an 8+-char literal.
2. The bare-namespace check was a line-`startswith` scan that matched the
   docstring prose "from ingestion order." in match_date_resolver.py — rewritten
   AST-based (real `Import`/`ImportFrom` nodes only).
3. CRITICAL_MODULES pinned `core/logger.py`, which never existed — repointed to
   `observability/logger_setup.py` (replace-not-delete).

Also in that PR: `observe_training_cycle.py` compared `dataset_split == "TRAIN"`
as a string literal — repointed to `DatasetSplit.TRAIN` (enum SSOT).

## D-28 — sweep tool honesty (PR #86)

The meta-gate's 11 failures adjudicated one by one:

- **verify_lock_hashes crashed** with UnicodeEncodeError under a piped cp1252
  stdout (the ✓/✗ summary lines) — the crash was MASKING the tool's real verdict.
  Fixed with a UTF-8 `reconfigure`; the tool now honestly exits 1 with 252
  findings (→ D-29).
- **sync_pro_players crashed** (`no such table: proplayer`) on a fresh main DB
  where the honest answer is "nothing to purge". Absent legacy tables now count
  as zero rows, probed via the session bind so the GAP-05 test fakes still work.
- **9 tools cannot succeed bare by design** (argparse-required args, missing
  recorded baseline, external services: audit_scanner, build_web,
  coach_answer_eval, drift_detector, merge_demo_pool, seed_hltv_apply_vision,
  seed_hltv_top_n, test_tactical_pipeline, validate_coaching_pipeline). The skip
  list is now a name→reason dict and the sweep report prints every skip with its
  reason — a visible skip, never silent coverage erosion.

**The F-0039 guard worked**: my uncommitted skip-list change tripped
`test_verify_all_safe_gate.py` (it pinned drift_detector/merge_demo_pool as
"stay scheduled") inside build_pipeline's test stage. Both were re-adjudicated
empirically (bare exit 2: argparse `required=True`; no baseline in repo) before
the guard was updated in the same commit — and the guard now also asserts every
named skip carries a stated reason. This episode is the round's best evidence
that the gates are real.

## D-29 (registered, OPEN — user decision required)

`verify_lock_hashes` reports **252 MISSING_HASH findings**: neither
requirements-lock file carries a single `--hash` line, violating POL-DEPS-01 /
C-SC-03 (hash-pinned installs). This is a real, standing policy violation — the
meta-gate stays honestly red until it is resolved. NOT fixed unilaterally
because regenerating locks (`uv pip compile --generate-hashes`) needs network,
changes 250+ pins, and may affect the planned Linux training environment. The
decision belongs to the operator.

## Frontend verification (15/15 screens)

All screens rendered offscreen (`tools/ui_screenshot.py`, fixture + live data)
and eyeballed by name: home, coach, tactical_viewer, performance, match_history,
match_detail, pro_comparison, pro_player_detail, settings, wizard, help, profile,
user_profile, faceit_config, steam_config.

- **One content bug found and fixed** (PR #86): help docs (en/it/pt
  `help_step5_desc`) said `gemma3:e2b`; the production default ladder
  (`OLLAMA_MODEL` env → `LLM_COACH_MODEL` setting → default) resolves to
  `gemma4:e2b`. Atlas renders regenerated — help.png now shows the corrected
  text. The D-03 surface (model caption + MODEL picker on coach) is intact.
- **Observation, not a defect**: pro_player_detail shows an honest "No pro
  selected" empty state (hltv_metadata.db uninitialized on this machine).
- **Observation (registered, not fixed)**: 14/15 atlas renders plus both
  galleries are byte-deterministic across consecutive `ui_screenshot.py` runs;
  **wizard.png hashes differently on every run** (three runs, three hashes) —
  some nondeterministic element in the wizard screen. Consequence: every bare
  sweep dirties this one tracked file. D-28-class follow-up: find and pin the
  varying element (or render the wizard with it frozen) before it trains anyone
  to `git checkout --` render diffs unread.
- user_profile renders the real live-DB player ("Knowledge_mc") — the screen
  reads production data correctly.

## Legacy data finding (registered, DB untouched)

The user's 2 PlayerMatchStats rows (written 2026-08-09 by a pre-enum writer)
carry uppercase split values consistent with today's writers; no current writer
disagrees. Remediation is the sanctioned path — `assign_dataset_splits` re-runs
at the next training cycle. Per standing rule, the user's database was not
mutated by a verification pass.

## Shipped

PR #84 (D-15b loaders + lockstep test), PR #85 (D-27 Goliath + enum SSOT),
PR #86 (D-28 sweep honesty + gemma4 staleness + atlas renders). Register
updated: D-15 amended, D-27/D-28 fixed, D-29 open.
