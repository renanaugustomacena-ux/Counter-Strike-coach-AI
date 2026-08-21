# SESSION HANDOFF — superseded (sanitized 2026-08-21)

> The machine-state snapshots that used to live here (2026-07-17 Windows and
> 2026-07-26 Linux sessions: disk inventory, symlink map, split state, PR queue)
> are **obsolete** — the project has since moved machines again and every listed PR
> was merged. The "DA FARE SUBITO su Linux" data checklist was verified executed
> point-by-point on 2026-08-03 (see TASKS.md, sessione 2026-08-03).
>
> **Still-open items were moved to [OPEN_ISSUES.md](OPEN_ISSUES.md)** (data backlog
> OI-3…OI-9, plus the two code-level defects OI-1/OI-2 that originated here).
> The actionable backlog lives in [../TASKS.md](../TASKS.md).
>
> What remains below is the one part still in force: the proven operational
> conventions (the tracked copy — CLAUDE.md/AUDIT.md/REFERENCE.md are gitignored).

## Convenzioni operative (collaudate, non regredire)

- **Flusso commit**: `pre-commit run --files <files>` → `python
  Programma_CS2_RENAN/tools/sync_integrity_manifest.py` → `git add` → `git commit -F
  <msgfile>`. MAI leggere l'exit di una pipe (`cmd | tail` maschera il codice: usare
  `set -o pipefail` o `; EXIT=$?`).
- **Flusso PR**: branch `fix/s-*`, push, PR con body Problem/Solution/Verification/
  Risk, attendere CI verde (17 SUCCESS + 2 SKIPPED by-design), `gh pr merge N --rebase
  --delete-branch`, `git checkout main && git fetch --prune && git reset --hard
  origin/main`, eliminare il branch locale. La repo deve restare a UN branch.
- **Gate obbligatori post-task**: suite `pytest Programma_CS2_RENAN/tests/ tests/ -m
  "not slow and not integration"` + `python tools/headless_validator.py`
  exit 0. Il dead-code detector è CRITICO in `tools/dev_health.py` (baseline Clean).
- **TASKS.md è tracciato in git** (da 2026-07-17): aggiornarlo nei commit, niente
  sync manuale. `AUDIT.md`/`CLAUDE.md`/`REFERENCE.md` restano locali (gitignored).
- Invarianti supremi (violazione = corruzione silenziosa): tick decimation FORBIDDEN;
  `GLOBAL_SEED=42`; METADATA_DIM=25; rating_* = componenti RAW (normalizzazione SOLO
  nell'aggregato `rating`); KAST ratio [0,1]; impact_rounds = share [0,1]; tick rate
  SEMPRE per-demo dall'header/metadata, mai 64 hardcodato; niente dati fabbricati —
  meglio un sentinel documentato di uno zero plausibile.

## Note operative durevoli (dalle sessioni 2026-07)

- **Mai** aprire SQLite su NTFS con `?mode=ro`: crea comunque `-shm`/`-wal` e può fare
  checkpoint. Usa `?immutable=1&mode=ro` per letture davvero non distruttive.
- Prima di scrivere su un mount `/media/...`: `findmnt <path> -o OPTIONS`; se compare
  `force`, il volume era *dirty* (Windows Fast Startup — eseguire `powercfg /h off`
  su Windows, o spegnere con `shutdown /s /f /t 0`).
- `pgrep -f "<pattern>"` matcha anche il processo che lo esegue: usare un pattern che
  non può auto-matcharsi (es. `[v]env/bin/python`).
