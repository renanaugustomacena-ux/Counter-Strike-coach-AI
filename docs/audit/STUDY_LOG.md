# Study Log — 04-PROGRAMMAZIONE-PYTHON companion

Targeted-mastery track: 22-clean-code, 07-error-handling, 09-type-hints, 10-async,
33-profiling-memoria-gc, 20-gui, 08-testing, 30-troubleshooting — each read immediately
before the batch it informs (see BATCHES.md). Other modules consulted on demand.

| Module | Date | Key lessons (bullets) | Applied to (F-ids / B-ids) |
|---|---|---|---|
| 22-clean-code (4,051 ln, full read) | 2026-08-14 | • §19 Code-Review Checklist (7 sections: leggibilità/struttura/type-safety/sicurezza/testing/qualità/config) adopted verbatim as the pass-1 per-file rubric • Extended smells catalog: data clumps, shotgun surgery, primitive obsession, inappropriate intimacy — on top of long-methods/god-class/feature-envy/magic-numbers/deep-nesting/duplication/dead-code/flag-args • Thresholds: function <50 ln, file <800 ln, cyclomatic <10, nesting ≤4 • CQS (command vs query, `stack.pop` pragmatic exception) • Value objects (frozen dataclass slots=True) vs primitive obsession • Null Object kills scattered None-checks • mypy strict adoption ladder = global strict + per-module overrides, shrink overrides progressively (feeds W4c) • TODO/FIXME require ticket refs • Boy-Scout rule bounded by our no-drive-by-fix discipline (findings register instead) • Tech-debt quadrants: track deliberate-prudent explicitly | Rubric for ALL pass-1 batches (B01–B76); F-0002 (magic number); W4b ruff ruleset candidates (E,W,F,I,UP,B,SIM,C4,DTZ,T20,RUF,PT,ERA per §Pre-commit); W4c mypy ladder |
