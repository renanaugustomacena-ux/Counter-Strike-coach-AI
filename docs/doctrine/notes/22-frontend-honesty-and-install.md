# Frontend honesty + installable ingestion and training (2026-09-12 → 2026-09-13)

Mission (user review, 2026-09-12): the database on the development machine holds
only pro matches, yet the dashboard showed those numbers as the user's own and
produced second-person advice from them; two of the three in-app guides were
unreadable; a "little weird window" opened at launch; and the Inno Setup
installer the author is about to ship must let ANY user ingest their own or
downloaded pro `.dem` files, trigger training locally and have the result
recorded in the program database — "just like I do here in development".

Decisions taken by the author before work started: strict own-data-only
personal screens with honest empty states and a labelled third-person "Pro
reference"; the in-app Train action drives jepa_v2 exactly like the developer's
run (CPU-only torch assumption); the 48 test rows in the dev database are purged
after a backup. Plan file: `~/.claude/plans/hello-friend-i-would-eager-zephyr.md`.
Method: read before fixing, one `fix/*` branch and PR per work package, TDD
(every test watched RED first), the full gate + headless validator +
portability + manifest before every commit, harness renders eyeballed, real
launches, register entries last.

## Work packages and evidence

| WP | PR | Findings | Gate at merge |
|----|----|----------|---------------|
| WP3 boot | #106 | D-47 parentless children shown as top-level windows (the stray window was "Pick a pro from the comparison screen." from pro_player_detail); D-48 splash held by `Console.boot()`/`docker compose` + blocking SBERT, daemon spawned without `CREATE_NO_WINDOW`, watcher crash on empty `PRO_DEMO_PATH`, second launch dialog | full gate green (+35 tests), headless 318/319, portability 10/10, real launch python + pythonw: one visible window, daemon lived and died with the GUI |
| WP1 honest data | #107 | D-49 `_player_filter` all-rows fallback, coach fallback to anyone's insights, mixed demo counts, arbitrary pro row in match detail; D-50 tests wrote 48 second-person rows into the production DB | 51 rows purged with backup, conftest tripwire on the real DB, harness renders performance/coach/home pro-only |
| WP2 guides | #108 | D-51 raw markdown in a `QLabel`, false content (Steam/FACEIT ID, Kivy, Playwright) | `markdown_article.py`, trilingual truthful guides, `test_help_docs_truthful.py` |
| WP4a install paths | #109 | D-52 DB pinned under the install dir, `get_resource_path` one level off the spec, `logs/` in cwd, RASP import raise, `BASE_DIR` consumers; D-43 absolute hash keys | 3082 passed / 57 skipped; frozen import proven in a subprocess inside a fake install dir that must stay byte-identical; wizard renders |
| WP4b train in the app | #110 | D-53 no way to train from the UI, both triggers hit the D-01 freeze, exporter outside the package, `/data/PROIECT` literal (D-41) | 3119 passed / 57 skipped; pipeline smoke on a file-backed monolith (train, dry run, stop, skip); home renders with the training card |
| WP4c packaging | #111 | D-32 spec shipped no models / seed / book / alembic.ini; installer version hardcoded, 32-bit view, silent data deletion; Kivy check in the build script; packaged exe never executed | see PR #111 (counts in its Verification section) |

## What the installed app does now

- Data root: `%LOCALAPPDATA%\MacenaCS2Analyzer` or the folder chosen in the
  wizard (database included); the choice is applied by a relaunch before any
  backend boot. Nothing is ever written beside the executable.
- Bundled resources resolve to `_MEIPASS/Programma_CS2_RENAN/<rel>`, pinned to
  the spec by a contract test; factory models, the HLTV seed, the coach book
  and `alembic.ini` ship.
- Own demos and a downloaded pro pool are analyzed from the Dashboard cards; the
  pro pool is reference material, never counted as the user's matches.
- Train coach (Dashboard, Settings) asks the background service for a jepa_v2
  run: splits → episode shards under the data root → `run_jepa_v2` → a
  `TrainedModel` row; Stop parks a resumable checkpoint; the active model line
  reads the registry. Legacy training stays frozen behind
  `ALLOW_LEGACY_NEURAL_TRAINING`.
- The packaged `--selftest` proves the paths, writes `selftest_report.json`
  under the data root, and runs in the build script and in CI before the
  artifact upload.

## Honest limits

- The coach's advice text does not consume the trained encoder until CORREZIONE
  Parte III steps 6-8 land (D-33); the UI and the guides say so.
- The frozen app WAS built on the development machine (PyInstaller 6.17.0
  installed into `.venv` for it; onedir 1.6 GB in 4 min 21 s) and the packaged
  `--selftest` passed with `LOCALAPPDATA` pointed at a scratch folder: data root,
  database, models and logs resolved under it, `alembic.ini`, the HLTV seed, the
  docs and the factory checkpoints were found in `_internal`, and the file count
  of the dist folder was identical before and after the run (10 416 files —
  nothing written beside the exe). That run also exposed a missing datas entry
  (the SVG icon sprite under `design/assets/icons/`), fixed in the same PR.
- Not done: Inno Setup is not installed on this machine, so
  `Macena_CS2_Installer_<version>.exe` was not compiled, and nothing was
  installed on a second Windows account. The end-to-end wizard → Analyze →
  Train run on an installed copy is the next manual step (BUILD_CHECKLIST).
- Out of scope by plan: arming `USE_JEPA_MODEL` / `USE_RAP_MODEL`, coach_v2 and
  Parte III steps 5-9, the 20k-step GPU exam and `docs/benchmarks/`, a CUDA
  installer, HLTV/Docker sync in frozen builds, shipping a pruned pro monolith.

## Lessons for the next round

- Parentless children added to a layout only when their text is non-empty
  become top-level windows on `setVisible(True)` (D-47): parent every child and
  add it to the layout unconditionally.
- Lambda receivers across threads after boot produced a native access
  violation; post-boot chains live in a `QObject` with real slots.
- Tests must never touch the production database: `tests/_memory_db.py` and the
  conftest tripwire are the guard; the honest-dashboard defects were partly the
  residue of tests that had.
- Paths are import-time constants in `core/config.py`: a data-root change is a
  relaunch, and the frozen layout is only provable in a subprocess.
