# `logs/` — Repo-root log staging

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Runtime log staging (read-only by convention)

## Where logs actually go

The application's primary log file is **`Programma_CS2_RENAN/logs/cs2_analyzer.log`** (rotated to `.log.1`, `.log.2`, `.log.3`). That is the file `app_logger` writes to via `observability/logger_setup.py`.

This top-level `./logs/` directory exists as a fallback / staging area for tooling that runs before the package logger is configured (e.g. very early bootstrap output, ROCm smoke tests, packaging-script output).

```
logs/
└── cs2_analyzer.log     # Legacy bootstrap/early-startup log (small)
```

For active investigation, **read `Programma_CS2_RENAN/logs/cs2_analyzer.log`**, not the file here.

## Log format

All `app_logger` output is **structured JSON** with one event per line:

```json
{"ts":"2026-05-06T14:21:41+0200","lvl":"INFO","mod":"cs2analyzer.app","thread":"MainThread","msg":"..."}
```

Fields:

| Key | Meaning |
|-----|---------|
| `ts` | ISO 8601 timestamp with timezone offset |
| `lvl` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `mod` | Logger name (`cs2analyzer.<domain>.<module>`) |
| `thread` | Thread identifier |
| `msg` | Free-form message (may contain Unicode escapes) |

## Filtering

```bash
# Last 50 ERRORs from the package log
grep '"lvl":"ERROR"' Programma_CS2_RENAN/logs/cs2_analyzer.log | tail -50

# Training cycle entries
grep '"mod":"cs2analyzer.app"' Programma_CS2_RENAN/logs/cs2_analyzer.log | grep -i training

# Per-module rate
awk -F'"mod":"' 'NF>1{split($2,a,"\"");print a[1]}' Programma_CS2_RENAN/logs/cs2_analyzer.log | sort | uniq -c | sort -rn | head -20
```

## Rotation

Rotation is handled by the standard library `RotatingFileHandler` configured in `observability/logger_setup.py`. Defaults: 5 MB per file, 3 backups. The package log directory is the canonical target — this `./logs/` directory at the repo root does NOT participate in rotation.

## Do not

- Do not commit large log files. Add new patterns to `.gitignore` if a tool starts depending on this dir.
- Do not parse logs with assumptions about line ordering across threads — concurrent writes interleave.
- Do not log secrets. The `app_logger` configuration scrubs credentials, but custom logging calls must still avoid PII / API keys per the security rules.

## Related

- Logger configuration: `Programma_CS2_RENAN/observability/logger_setup.py`
- Validator output (separate, stdout-only): `tools/headless_validator.py`
- Log buffering pitfalls (long-running processes under `tee`): see `CLAUDE.md` notes
