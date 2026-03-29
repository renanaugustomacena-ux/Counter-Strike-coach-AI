You are working on the Macena CS2 Analyzer project. A comprehensive Deep Audit has been completed across 194 production Python files, documenting 247 issues in reporting.md at the
  project root.

  YOUR TASK

  Fix ALL 247 issues documented in reporting.md — every CRITICAL, HIGH, MEDIUM, and LOW. The goal is ZERO issues remaining. Work one file at a time, following this exact workflow:

  Workflow Per Issue

  1. READ the next unresolved finding in reporting.md (look for entries WITHOUT a [x] checkbox)
  2. READ the source file mentioned in the finding (exact file path and line numbers are provided)
  3. FIX the issue according to the "Action" section of that finding
  4. VALIDATE by running: python3 tools/headless_validator.py — it MUST exit with code 0
  5. UPDATE reporting.md — replace the entire finding section with a compact completed entry (format below)
  6. Proceed immediately to the next unresolved finding

  Completed Entry Format

  When ALL issues in a file section are fixed, replace the ENTIRE section (from ## [N]. to the next ---) with:

  ## [N]. filename.py — [x] COMPLETED
  **Original Status:** WARNING | **Issues Fixed:** X | **Severities:** MEDIUM, LOW

  Priority Order

  Fix issues in this priority order:
  1. CRITICAL severity first (9 issues)
  2. HIGH severity next (19 issues)
  3. MEDIUM severity (100 issues)
  4. LOW severity last (119 issues)

  Rules You MUST Follow

  - One file at a time — do NOT batch multiple files in a single pass
  - Read before modify — always read the current source code before making any change
  - Zero-regression guarantee — python3 tools/headless_validator.py must pass after EVERY fix
  - No over-engineering — fix exactly what the audit finding describes, nothing more
  - Preserve behavior — fixes must not change existing functionality unless the finding explicitly calls for it
  - Structured logging — when the fix involves logging, use get_logger("cs2analyzer.<module>") from Programma_CS2_RENAN.observability.logger_setup
  - No magic numbers — if extracting constants, use named constants or config dataclasses
  - ALL severities matter — LOW issues MUST be fixed too. The goal is 0 issues remaining.

  What NOT to Fix

  - Entries already marked with [x] COMPLETED
  - Anything in tests/ or tools/ directories (excluded from audit scope)

  Reporting.md Header Update

  After every 10 completed files, update the header counters:
  - Decrement the total issue count by the number of issues fixed
  - Adjust CRITICAL/HIGH/MEDIUM/LOW counts accordingly
  - The file should shrink as completed sections are replaced with one-liners

  Autonomous Operation

  Work continuously through the issues without stopping for approval. If a fix is ambiguous or could break behavior, make the safest conservative choice and add a brief comment in the
  code explaining the decision. Only stop and ask me if:
  - The validator fails and you cannot determine why after 2 attempts
  - A fix requires changing a public API signature
  - Two findings conflict with each other

  START

  Begin by reading reporting.md and identifying the first unresolved CRITICAL-severity finding. Fix it, validate, update reporting.md, and continue to the next.
