# Exit Codes Reference

All exit codes used by the CS2 Analyzer project.

| Code | Meaning | Used By |
|---|---|---|
| `0` | Success / Normal exit | `main.py`, all tools, `console.py` |
| `1` | Runtime failure / Integrity failure / Build failure | `main.py` (RASP), `console.py`, `build_pipeline.py`, `Sanitize_Project.py` |
| `2` | Not in virtualenv (pre-import guard) | `main.py`, `console.py`, all tools, all test scripts |

## Notes

- Exit code `2` is used exclusively by venv guards at the top of entry-point
  scripts. These fire before any import is possible, so they must use
  `print(stderr)` rather than the logging system.
- Exit code `0` is also used for the duplicate-instance check in `main.py`,
  where detecting an existing running instance is not an error condition.
