# Incident Response Runbooks

**Version:** 1.0
**Date:** 2026-04-25
**Methodology:** NIST SP 800-61 r2 phases (Preparation → Detection & Analysis → Containment → Eradication → Recovery → Post-Incident Activity)
**Owner:** Renan Augusto Macena

> *"Incidents are inevitable. Systems that cannot be investigated are invalid."* — Doctrine §60

---

## 0. Preparation (always-on)

The following must be in place at all times so the runbooks below are executable:

1. **Audit log** (`Programma_CS2_RENAN/observability/audit_log.py`) running with HMAC chain key in `SecretStorage`.
2. **Integrity manifest** signed with `CS2_MANIFEST_KEY`; verified hourly by RASP continuous mode.
3. **`goliath.py panic`** kill-switch installed; tested in dry-run during release certification.
4. **Backups** of `Programma_CS2_RENAN/backend/storage/database.db*` and `*.db-wal`/`*.db-shm` available
   via `Programma_CS2_RENAN/backups/` and `tools/wipe_for_reingest_safe.py --snapshot`.
5. **Up-to-date** [`CONTROL_CATALOG.md`](CONTROL_CATALOG.md), [`THREAT_MODEL.md`](THREAT_MODEL.md), and
   [`CONFIG_REFERENCE.md`](CONFIG_REFERENCE.md).
6. **Operator awareness** — this document read by the operator within 7 days of any change to it.

## 0.1 Severity Levels

| Severity | Trigger | Response time |
|---|---|---|
| **SEV-1** | Confirmed RCE, confirmed token leak with active misuse, audit-log tamper detected | Immediate (within 1 h) |
| **SEV-2** | Suspected RCE, suspected token leak, manifest verify fails on production install | Same day |
| **SEV-3** | Reachable CVE in dependency, anomalous resource usage | Within 72 h |
| **SEV-4** | Hardening regression, operational drift | Next business day |

## 0.2 Universal first-30-seconds checklist

Regardless of scenario, before reaching for a runbook below:

- [ ] Note current UTC timestamp.
- [ ] Note exact symptoms verbatim.
- [ ] Snapshot current `audit.log*`, `cs2_analyzer.log*`, and `database.db*` to a labeled directory before any further action.
  - Command: `python tools/forensic_snapshot.py --label "incident_<short>_$(date -u +%Y%m%dT%H%M%SZ)"`
- [ ] Open the matching runbook below.

---

## IR-01 — Steam / FaceIt Token Compromise

**Severity baseline:** SEV-1 if active misuse confirmed; SEV-2 if suspected; SEV-3 if precautionary.

### Detection signals

- `audit.log` event `oauth.token.unexpected_use` from a non-local IP / unfamiliar user-agent hash
- `pip-audit` reports a CVE in the API-key request path (e.g., `requests`/`urllib3`/`pyjwt` advisory)
- User reports anomalous Steam profile activity (unknown game purchases, profile-picture change, friend-requests)
- FaceIt notifies of token-use from another region
- Sentry event with redacted-but-visible `Authorization` header pattern

### Containment (≤ 15 min)

1. `python goliath.py panic --revoke=steam,faceit --reason="IR-01 token compromise <UTC ts>"`
   - Stops daemons
   - Calls `set_secret('STEAM_API_KEY','')`, `set_secret('FACEIT_API_KEY','')`, `TokenStore.clear('faceit')`
   - Background daemons reading via `get_credential()` now fail-fast
2. Verify via `audit.log` that revocation events appear: `secret.delete{key=...}`, `oauth.revoke{provider=...}`
3. If FaceIt OAuth, also `POST https://api.faceit.com/auth/v1/oauth/revoke?token=<refresh>&token_type_hint=refresh_token`

### Eradication

1. User generates new API key at <https://steamcommunity.com/dev/apikey> (Steam) or FaceIt developer portal
2. User saves via UI (`steam_config_screen` / `faceit_config_screen`); wizard validates with a tracer call
3. For OAuth: user re-authenticates; new tokens flow into `TokenStore`
4. Confirm `audit.log` shows `auth.key.rotated` event

### Recovery

1. Resume daemons.
2. Run `python tools/headless_validator.py` to confirm system clean.
3. If a CVE was the root cause, also `pip install --require-hashes -r requirements-lock-cpu.txt` after the fix lands; bump `requirements*.in` and recompile lock.

### Postmortem template (within 7 days)

- **What happened?** (timeline UTC)
- **Leak vector?** (log? screenshot? clipboard? phishing? compromised CI artifact?)
- **Control failure(s)?** (was redaction filter active? was Sentry opt-in actually opt-out? was refresh-rotation enabled?)
- **Detect → contain elapsed time?**
- **Follow-ups (with owner + due-date):**
  - …
- **Preventive control (NEW)?** Add to `CONTROL_CATALOG.md`.

---

## IR-02 — Malicious `.dem` RCE Attempt

**Severity baseline:** SEV-1 if sandbox bypass confirmed; SEV-2 if seccomp-killed.

### Detection signals

- `audit.log` event `sandbox.child_killed{reason="seccomp"}` — parser attempted disallowed syscall
- `audit.log` event `sandbox.child_killed{reason="rlimit_cpu"|"rlimit_as"|"timeout"}` — DoS attempt
- Demoparser2 sandbox child returns non-zero with stderr containing `Killed: SIGSYS`
- `IntegrityError` from RASP after a parse — sandbox bypass suspected
- Abnormal CPU spike in Qt-UI process during parse (sandbox prevents this — if it occurs, sandbox bypassed)
- Demo file size very near `MAX_DEMO_SIZE` and parser hangs

### Containment

1. Quarantine the offending `.dem`:
   ```
   mv "<path/to/demo>" "<DATA_DIR>/quarantine/$(basename <demo>).$(date -u +%Y%m%dT%H%M%SZ).quarantine"
   chmod 000 "<DATA_DIR>/quarantine/..."
   ```
2. Disable auto-ingest:
   ```
   python -c "from Programma_CS2_RENAN.core.config import save_user_setting; save_user_setting('INGEST_MODE_AUTO', False)"
   ```
3. Kill all running parses:
   ```
   pkill -f demo_parser_sandbox
   ```

### Eradication

1. Compute SHA-256 of the offending demo and add to `SECURITY/policies/quarantined_demos.txt`.
2. Rotate cache HMAC key:
   ```
   rm "<DATA_DIR>/demo_cache/.hmac_key"   # next parse generates a new key; old cache invalidated
   ```
   Or, more cautiously: `python goliath.py rotate cache`
3. Bump `CACHE_VERSION` in `Programma_CS2_RENAN/ingestion/demo_loader.py` if the data shape was impacted.
4. Run `python goliath.py integrity` to confirm manifest still valid (i.e. no in-process tampering occurred).

### Recovery

1. SBOM diff vs prior known-good run:
   ```
   python goliath.py sbom > sbom-current.cdx.json
   diff sbom-prior.cdx.json sbom-current.cdx.json
   ```
2. `pip-audit --strict` against `demoparser2` and transitives.
3. Consider temporarily pinning `demoparser2` to last-known-good if the new release is implicated.
4. Resume ingestion only after a clean fuzz run (`python tools/fuzz/fuzz_demo_parser.py --time-budget 1800`).

### Postmortem

- **Mandatory fields:** demo SHA-256, sandbox enabled? trace of seccomp violation, time-to-detect, kernel version (seccomp dependency).
- **Was demoparser2 fuzzed against this kind of input?** If not, add to corpus.

---

## IR-03 — Corrupted Database

**Severity baseline:** SEV-2.

### Detection signals

- `audit.log` event `db.write.failed` with payload digest
- `db_governor.py` `PRAGMA quick_check` non-OK at startup
- Foreign-key violation on startup (POL-DB-02 prevents broad-except masking the error)
- `alembic upgrade head` reports `sqlalchemy.exc.OperationalError`
- "database is locked" in `cs2_analyzer.log` under sustained ingestion (also implicates writer broker)

### Containment

1. Stop all daemons. Run `python goliath.py panic --reason="IR-03 db corruption"` (it kills children atomically).
2. Disable ingestion auto-mode (see IR-02 step 2).
3. Snapshot current state:
   ```
   cp Programma_CS2_RENAN/backend/storage/database.db Programma_CS2_RENAN/backend/storage/database.db.corrupted_$(date -u +%Y%m%dT%H%M%SZ)
   cp Programma_CS2_RENAN/backend/storage/database.db-wal Programma_CS2_RENAN/backend/storage/database.db-wal.corrupted_$(date -u +%Y%m%dT%H%M%SZ)
   cp Programma_CS2_RENAN/backend/storage/database.db-shm Programma_CS2_RENAN/backend/storage/database.db-shm.corrupted_$(date -u +%Y%m%dT%H%M%SZ)
   ```
   These are gitignored (`*.db*`).

### Eradication

1. Restore from the latest `Programma_CS2_RENAN/backups/` snapshot taken by `backup_manager.py` or `tools/wipe_for_reingest_safe.py --snapshot`.
2. Verify pragmas after restore:
   ```
   sqlite3 Programma_CS2_RENAN/backend/storage/database.db <<'EOF'
   PRAGMA quick_check;
   PRAGMA foreign_key_check;
   PRAGMA journal_mode;       -- expect: wal
   PRAGMA wal_autocheckpoint; -- expect: 512
   EOF
   ```
3. `alembic upgrade head` must succeed.
4. Run `python tools/headless_validator.py` (24-phase gate).

### Recovery

1. Re-ingest the last N demos that were lost between the backup and the corruption point.
2. Verify lineage: `python goliath.py audit verify --from <backup-date>`.

### Postmortem

- Was POL-DB-02 (no broad-except in alembic) violated upstream?
- Was the writer-broker active? If not, that's a finding (T-005).
- What was the read-write concurrency at the moment of failure?

---

## IR-04 — Compromised PyPI Dependency

**Severity baseline:** SEV-1 if confirmed malicious code present in shipped artifact; SEV-2 if reachable CVE in production lockfile; SEV-3 if dev-only dep.

### Detection signals

- `pip-audit --strict` fails in CI
- SBOM diff (`goliath sbom`) shows unexpected transitive
- Bandit or detect-secrets reports a finding tied to a specific package version after lockfile bump
- `actions/attest-build-provenance` fails verification
- External advisory: PyPI / GHSA / OSV / Snyk / vendor announcement

### Containment

1. Determine impact zone:
   ```
   pip-audit --strict --vulnerability-service osv --requirement requirements-lock-cpu.txt
   ```
2. Add an emergency policy override pinning the previous good version in `requirements*.in`:
   ```
   <package>==<previous good version>
   ```
3. Mark the bad version in `SECURITY/waivers.yaml` as `denylist`:
   ```yaml
   - rule: POL-DEPS-DENY-<id>
     path: requirements-lock*.txt
     match: '<package>==<bad version>'
     risk: HIGH
     expires: <issue date + 14 days>
     owner: renanaugustomacena
     justification: "Pinned away from compromised version <CVE/GHSA-id>; await upstream fix"
   ```
4. If the compromised version was already in a published `.exe` release: revoke the GitHub Release (hide); rotate code-signing certificate; communicate to users.

### Eradication

1. Wait for upstream fix or fork the dependency.
2. Recompile lockfile: `uv pip compile --generate-hashes --output-file requirements-lock-cpu.txt requirements.in`
3. CI must pass `pip-audit --strict` before re-release.
4. Rebuild distribution; sign with EV cert; produce SLSA attestation; attach SBOM.

### Recovery

1. Publish CHANGELOG note describing the issue (no need to disclose proof-of-concept; user instructions for upgrade).
2. Force-bump installer minor version so users see an update prompt.

### Postmortem

- Did `--require-hashes` catch it at install time? (If C-SC-03 was deployed, yes — supply chain T-006 contained.)
- Did SLSA provenance verify? (If C-SC-07 was deployed, yes.)
- Did SBOM tracking surface it?
- Should this dep be replaced with a more trusted alternative?

---

## IR-05 — Leaked Manifest HMAC Key

**Severity baseline:** SEV-2.

### Detection signals

- `audit.log` event `manifest.key.read.unexpected_path` (unusual file access)
- Static fallback warning RP-01 visible in dev mode of a frozen build (impossible if release flow forces env var injection)
- External claim of manifest-forgery capability
- Mismatch between `tools/sync_integrity_manifest.py --verify-only` output and expected hashes despite no code change

### Containment

1. Treat the existing manifest as compromised but do not yet rotate; first take a forensic snapshot.
2. `python tools/forensic_snapshot.py --label "ir05_manifest_$(date -u +%Y%m%dT%H%M%SZ)"`
3. In the next build, generate a new `CS2_MANIFEST_KEY` and increment `MANIFEST_VERSION`:
   ```
   python tools/rotate_manifest_key.py --version-bump
   ```
4. Configure verifier (`observability/rasp.py`) to **reject** manifest versions older than the new one, forcing users onto the upgraded build.

### Eradication

1. Long-horizon: replace HMAC manifest with **ed25519 public-key signing**. Asymmetric primitives turn key compromise into a signing-key issue, not an forgery-equivalence; only the build pipeline holds the private key.
2. Track this as an issue: "C-RASP-06 — ed25519 manifest signing".

### Recovery

1. Ship new release tagged with the new `MANIFEST_VERSION`.
2. Deprecate the old release in GitHub Releases (mark as pre-release).
3. User upgrades via installer.

### Postmortem

- Was the static fallback `"macena-cs2-integrity-v1"` ever shipped?
- Was the env var leaked in CI logs? (Should be masked; verify.)
- Did rotation discipline (C-ROT-01) include manifest? If yes, why didn't auto-rotation prevent this?

---

## Postmortem Template (canonical)

Copy this for every incident, fill in, file under `SECURITY/postmortems/<YYYY-MM-DD>-<short-name>.md`.

```markdown
# Postmortem — <short title>

## Incident
- **ID:** IR-NN — <one-liner>
- **Severity:** SEV-X
- **Date:** YYYY-MM-DD (UTC)
- **Detected:** YYYY-MM-DD HH:MM (UTC)
- **Contained:** YYYY-MM-DD HH:MM (UTC)
- **Resolved:** YYYY-MM-DD HH:MM (UTC)
- **Owner:** Renan Augusto Macena

## Timeline (UTC)
- HH:MM — <event>
- HH:MM — <event>

## Root cause
<5 Whys analysis>

## Detection
What signal caught it? Was the detection signal added pre-incident or after?

## Containment
What stopped the bleeding? Did `goliath.py panic` work?

## Recovery
What restored normal operation?

## Control failures
- Which controls in `CONTROL_CATALOG.md` should have caught this and didn't?
- Were they MISSING, PARTIAL, or did they fail despite being PRESENT?

## Action items
| ID | Action | Owner | Due | Status |
|---|---|---|---|---|
| AI-1 | … | RM | YYYY-MM-DD | open |

## Threat-model updates
Lines added/changed in `THREAT_MODEL.md`.

## Control-catalog updates
New rows in `CONTROL_CATALOG.md` or status changes.

## Lessons learned
Two paragraphs max — what was surprising, what we'd do differently.
```

---

## References

- **NIST SP 800-61 r2** Computer Security Incident Handling Guide
- **NIST SP 800-86** Guide to Integrating Forensic Techniques
- **ISO/IEC 27035-1:2023** Information security incident management — Principles
- **ISO/IEC 27001:2022** Annex A.5.24, A.5.25, A.5.26, A.5.27, A.5.28
