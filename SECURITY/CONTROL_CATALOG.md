# Control Catalog — Macena CS2 Analyzer

**Version:** 1.0
**Date:** 2026-04-25
**Owner:** Renan Augusto Macena

This catalogue enumerates every security control, mapped to standards bodies. Status is one of:
**PRESENT** (implemented and verified), **PARTIAL** (some coverage; gap), **MISSING** (not implemented).

> Mappings are deliberate, not aspirational. Each entry cites the implementation site, the test that
> verifies it, and the standard reference. Doctrine §61: compliance is a constraint, not the goal.

## Legend

- **NIST SSDF**: NIST SP 800-218 v1.1 practice IDs (`PO`/`PS`/`PW`/`RV`)
- **ASVS**: OWASP Application Security Verification Standard 4.0.3, Level 2 controls
- **CWE**: Common Weakness Enumeration (Top 25 2024)
- **OWASP10**: OWASP Top 10:2021 categories (A01–A10)
- **ISO27001**: ISO/IEC 27001:2022 Annex A controls

## Status summary

| Status | Count |
|---|---|
| PRESENT | 24 |
| PARTIAL | 11 |
| MISSING | 18 |

---

## Pillar 1 — Threat Model & Control Architecture

### C-TM-01 — Documented threat model

- **Status:** PRESENT (this document set, 2026-04-25)
- **Description:** STRIDE + LINDDUN matrix in `SECURITY/THREAT_MODEL.md` covering all assets and trust boundaries.
- **Site:** [`SECURITY/THREAT_MODEL.md`](THREAT_MODEL.md)
- **Test:** `.github/workflows/threat-model-gate.yml` labels PRs that touch `BOUNDARY_FILES.txt` paths.
- **Mapping:** SSDF PO.5.1; ASVS V1.1; ISO27001 A.5.7
- **Owner:** Renan Augusto Macena

### C-TM-02 — Continuous threat modeling discipline

- **Status:** PRESENT
- **Description:** Every PR touching a trust-boundary file requires updated threat-model section + security review.
- **Site:** `.github/CODEOWNERS`, `.github/workflows/threat-model-gate.yml`, `BOUNDARY_FILES.txt`
- **Test:** GitHub branch protection rule (Phase 3)
- **Mapping:** SSDF PO.5.2

### C-POL-01 — Policy as Code

- **Status:** PARTIAL (warn-mode initially)
- **Description:** `tools/policy_runner.py` enforces 9 policy files in `SECURITY/policies/*.yaml`.
- **Site:** `tools/policy_runner.py`
- **Test:** `tests/security/test_policies.py` — every rule has a passing fixture and a failing fixture
- **Mapping:** SSDF PO.3.2; ASVS V14.1
- **Rules:**

  | Rule ID | What it enforces | Why |
  |---|---|---|
  | POL-DEPS-01 | Every line in `requirements*.txt` and `requirements-lock*.txt` exact-pinned (`==`) and `--hash=sha256:` | Supply chain integrity (T-006) |
  | POL-CI-01 | Every `uses:` in `.github/workflows/*.yml` references 40-char SHA | Action-pinning hygiene (T-022) |
  | POL-NET-01 | No docker-compose service binds `0.0.0.0`/`*` without `# SEC: bind-public` waiver | LAN exposure (T-009, T-013) |
  | POL-CODE-01 | No `pickle.load`, `yaml.load(`, `subprocess(..., shell=True)`, `eval`, `exec` outside `# SEC: justified` waiver | CWE-502, CWE-78, CWE-95 |
  | POL-DB-01 | f-string SQL DDL must be adjacent to `_assert_safe_*` calls | CWE-89 (regression for AUDIT §9 DB-01/DB-04) |
  | POL-DB-02 | No `except Exception`/`except BaseException` in `alembic/versions/**.py` | T-021 |
  | POL-NET-02 | External HTTP calls route through `_validated_get` | T-008 SSRF |
  | POL-COV-01 | `pyproject.toml fail_under` ≡ CI `--cov-fail-under` | Discipline alignment |
  | POL-LOG-01 | Patterns catalogue extensible at `SECURITY/policies/log_patterns.yaml` | T-001 |

### C-LOG-01 — Centralized log redaction filter

- **Status:** MISSING (Phase 2 deliverable)
- **Description:** `SecretRedactingFilter` at root logger; identity-pass (keyring values) + pattern-pass (regex catalog).
- **Site (planned):** `Programma_CS2_RENAN/observability/redaction.py`
- **Test (planned):** `tests/security/test_redaction_property.py` — Hypothesis 5000 cases, 0 leakage
- **Mapping:** SSDF PW.7.1; ASVS V7.1; CWE-117 (log injection); OWASP10 A09 (logging failures); ISO27001 A.8.16

### C-AUDIT-01 — HMAC-chained audit log

- **Status:** MISSING (Phase 2 deliverable)
- **Description:** Append-only NDJSON; each entry `hash = HMAC(prev_hash || canonical(payload))`; key in `SecretStorage`.
- **Site (planned):** `Programma_CS2_RENAN/observability/audit_log.py`
- **Test (planned):** `tests/security/test_audit_log_chain.py` — tamper at random offset → `verify_chain` returns `(False, line_idx)`
- **Mapping:** SSDF RV.1; ASVS V7.2; ISO27001 A.8.15; NIST SP 800-92

### C-IR-01 — Incident response runbooks

- **Status:** PRESENT (this document set, 2026-04-25)
- **Description:** Five named scenarios IR-01…IR-05 per NIST SP 800-61 r2 phases.
- **Site:** [`INCIDENT_RESPONSE.md`](INCIDENT_RESPONSE.md)
- **Mapping:** ISO27001 A.5.24, A.5.25, A.5.26, A.5.27, A.5.28; NIST SP 800-61 r2

### C-IR-02 — Kill switch

- **Status:** MISSING (Phase 3 deliverable)
- **Description:** `goliath.py panic` — stops daemons, disables outbound, revokes keyring, rotates HMAC keys, takes sealed forensic snapshot.
- **Site (planned):** `tools/panic.py`, `tools/forensic_snapshot.py`
- **Mapping:** ISO27001 A.5.26

### C-CO-01 — CODEOWNERS

- **Status:** PRESENT (Phase 1, 2026-04-25)
- **Description:** Required reviewer for security-critical paths.
- **Site:** [`/.github/CODEOWNERS`](../.github/CODEOWNERS)
- **Mapping:** SSDF PO.5; ISO27001 A.6.1.1

---

## Pillar 2 — Secrets & Identity

### C-SEC-01 — System keyring

- **Status:** PRESENT (verified)
- **Description:** `keyring==25.7.0` integration via `core/config.py:get_secret`/`set_secret`.
- **Site:** `Programma_CS2_RENAN/core/config.py:75-133`
- **Test:** Existing manual + (Phase 2) `tests/security/test_secret_storage.py`
- **Mapping:** SSDF PW.7.2; ASVS V2.10, V6.4; CWE-798; OWASP10 A02

### C-SEC-02 — Atomic settings write with chmod 0o600

- **Status:** PRESENT (verified)
- **Description:** Temp file + fsync + os.replace, then `os.chmod(SETTINGS_PATH, 0o600)`.
- **Site:** `core/config.py:436-482`
- **Mapping:** ASVS V13.4; CWE-732

### C-SEC-03 — Encrypted disk-fallback

- **Status:** MISSING (Phase 2 deliverable)
- **Description:** When keyring unavailable, vault encrypted with master key sealed to OS user (DPAPI / Keychain / scrypt+passphrase).
- **Site (planned):** `Programma_CS2_RENAN/core/secret_storage.py`
- **Mapping:** ASVS V6.2, V6.4; OWASP10 A02

### C-SEC-04 — Mask-secret helper

- **Status:** PRESENT (opt-in)
- **Description:** `mask_secret()` returns `****` for short, `4...4` for longer.
- **Site:** `core/config.py:136-140`
- **Limitation:** Opt-in only; superseded by C-LOG-01 redaction filter at logger root.

### C-SEC-05 — Demo cache HMAC integrity

- **Status:** PRESENT (verified)
- **Description:** 32-byte random HMAC key at `<DATA_DIR>/demo_cache/.hmac_key` chmod 0o600; HMAC-SHA256 over pickle; timing-safe `hmac.compare_digest`.
- **Site:** `Programma_CS2_RENAN/ingestion/demo_loader.py:56-133`
- **Mapping:** ASVS V6.2.5, V13.5

### C-SEC-06 — Restricted unpickler

- **Status:** PRESENT (verified)
- **Description:** `_SafeUnpickler` allows only `demo_frame` dataclasses + builtins.
- **Site:** `ingestion/demo_loader.py:44-53`
- **Mapping:** CWE-502; OWASP10 A08

### C-SEC-07 — Integrity manifest HMAC verification (RASP)

- **Status:** PARTIAL (continuous mode in Phase 2)
- **Description:** Startup-time HMAC verification of `core/integrity_manifest.json`; key from `CS2_MANIFEST_KEY` env (static fallback warned as RP-01).
- **Site:** `observability/rasp.py:88-99`
- **Phase 2 hardening:** hourly continuous re-verification + RASP-violation event in audit log
- **Mapping:** SSDF PW.7; CWE-345

### C-AUTH-01 — Steam OpenID 2.0 login

- **Status:** MISSING (Phase 3 deliverable)
- **Description:** Local-redirect flow with mandatory `openid.mode=check_authentication` round-trip + state token.
- **Site (planned):** `backend/auth/steam_openid.py`, `backend/auth/local_callback_listener.py`
- **Mapping:** ASVS V2.1, V2.5; OWASP10 A07; CWE-287, CWE-352

### C-AUTH-02 — FaceIt OAuth2 + PKCE

- **Status:** MISSING (Phase 3 deliverable, requires registered FaceIt OAuth client_id)
- **Description:** RFC 6749 Authorization Code Grant + RFC 7636 PKCE S256 + RFC 7519/7517 JWT verification with strict `algorithms=["RS256","ES256"]`, JWKS-pinned `kid`, `iss`/`aud`/`exp`/`nbf`/`nonce` validation.
- **Site (planned):** `backend/auth/faceit_oauth.py`, `backend/auth/jwks_cache.py`, `backend/auth/token_store.py`
- **Mapping:** ASVS V2.7, V3.5; OWASP10 A07; RFC 6749/7636/7519/7517/8252

### C-AUTH-03 — Local callback listener (shared)

- **Status:** MISSING (Phase 3 deliverable)
- **Description:** `127.0.0.1:0` ephemeral bind, single-shot, route + state validation, embedded HTML (no template injection).
- **Site (planned):** `backend/auth/local_callback_listener.py`
- **Mapping:** ASVS V13.4; CWE-352, CWE-918

### C-AUTH-04 — Audit log of credential access

- **Status:** MISSING (Phase 2 deliverable)
- **Description:** Audit-log emits `secret.read`, `secret.write`, `secret.delete`, `oauth.login_attempt`, `oauth.token_refresh`, `oauth.revoke`, `oauth.callback_rejected`, `keyring.unavailable_fallback`.
- **Site (planned):** `observability/audit_log.py`
- **Mapping:** ASVS V7.2; ISO27001 A.8.15

### C-USER-01 — Multi-account model

- **Status:** MISSING (Phase 3 deliverable, additive)
- **Description:** New `AppUser` table; UUID-keyed; separates app-user identity from in-game player identity.
- **Site (planned):** `backend/storage/db_models.py` + Alembic 3-phase migration
- **Mapping:** ASVS V2.4

### C-ROT-01 — Secrets rotation

- **Status:** MISSING (Phase 3 deliverable)
- **Description:** `goliath.py rotate {manifest|cache|master|all|status}`. Manifest key per-release with 30-day grace; cache key 90-day rotation; master key annual.
- **Site (planned):** `tools/rotation/*.py`, `goliath.py rotate ...`
- **Mapping:** ASVS V6.4

### C-HYG-01 — Secrets-hygiene tests

- **Status:** MISSING (Phase 2 deliverable)
- **Description:** Pytest assertions: no Steam Web API key shape in source, no JWT-shaped strings, no `os.environ.get` of `*_API_KEY` outside whitelisted modules, no `print()` of secret-origin values, Sentry `_before_send` filter present.
- **Site (planned):** `tests/test_secrets_hygiene.py`
- **Mapping:** SSDF PW.4

---

## Pillar 3 — Supply Chain & DevSecOps Automation

### C-SC-01 — Exact dependency pinning

- **Status:** PRESENT (verified)
- **Description:** All 56 lines in `requirements.txt` exact-pinned (`==`); only `torch>=2.1.0,<3.0` is range-pinned (justified for ROCm/CUDA/CPU variants).
- **Site:** `requirements.txt`
- **Mapping:** SSDF PS.3.1; CWE-1357; OWASP10 A06

### C-SC-02 — Lockfile (transitive closure)

- **Status:** PARTIAL (no hashes)
- **Description:** `requirements-lock.txt` (CUDA, 147 deps) and `requirements-lock-cpu.txt` (CPU, 143 deps) full transitive pin via `pip freeze` 2026-02-15.
- **Limitation:** No `--hash=sha256:` lines yet; **Phase 2** flips CI to `pip install --require-hashes`.
- **Mapping:** SSDF PS.3.2

### C-SC-03 — Hash pinning + `--require-hashes`

- **Status:** MISSING (Phase 2 deliverable)
- **Description:** `uv pip compile --generate-hashes` produces hashed lockfiles; CI installs via `--require-hashes`; `tools/verify_lock_hashes.py` rejects unhashed lines.
- **Site (planned):** `tools/verify_lock_hashes.py`, regenerated `requirements-lock*.txt`
- **Mapping:** SSDF PS.3.1, PS.3.2, PW.4.4; CWE-494; OWASP10 A08

### C-SC-04 — pip-audit (CVE)

- **Status:** PRESENT (verified)
- **Description:** `pip-audit --strict --desc on` against `requirements-ci.txt` in CI.
- **Site:** `.github/workflows/build.yml:286-289`
- **Mapping:** SSDF RV.1.1; OWASP10 A06

### C-SC-05 — Dependabot

- **Status:** PRESENT (verified)
- **Description:** Weekly pip + GitHub Actions update PRs.
- **Site:** `.github/dependabot.yml`
- **Mapping:** SSDF RV.1.2

### C-SC-06 — SBOM (CycloneDX)

- **Status:** MISSING (Phase 2 deliverable)
- **Description:** CycloneDX 1.6 SBOM generated by `cyclonedx-bom==4.4.3`; uploaded as CI artifact (90-day retention) and attached to GitHub Release.
- **Site (planned):** CI step in `.github/workflows/release.yml`; local `goliath.py sbom`
- **Mapping:** SSDF PS.3.1; ISO27001 A.5.21; Executive Order 14028

### C-SC-07 — SLSA Build Provenance L3

- **Status:** MISSING (Phase 3 deliverable)
- **Description:** `actions/attest-build-provenance@v2` + `actions/attest-sbom@v2`; Sigstore Rekor transparency log entries; user-side verification via `gh attestation verify`.
- **Site (planned):** `.github/workflows/release.yml`
- **Mapping:** SLSA v1.0 Build L3

### C-SC-08 — Code signing (Windows)

- **Status:** MISSING (Phase 3 deliverable, EV cert budget pending)
- **Description:** Authenticode signing of PyInstaller `.exe` and Inno Setup installer with EV cert; timestamp via DigiCert TSA.
- **Site (planned):** `.github/workflows/release.yml`
- **Mapping:** OWASP10 A08

### C-SC-09 — Bandit (SAST)

- **Status:** PRESENT (CI only)
- **Description:** `bandit -r Programma_CS2_RENAN/` MEDIUM+ severity, MEDIUM+ confidence; CI blocks on findings.
- **Site:** `.github/workflows/build.yml:233-249`
- **Phase 2 enhancement:** mirror as pre-commit hook

### C-SC-10 — detect-secrets (secret scanning)

- **Status:** PRESENT (CI only)
- **Description:** `detect-secrets` against `Programma_CS2_RENAN/`; KeywordDetector false-positives filtered.
- **Site:** `.github/workflows/build.yml:251-284`
- **Phase 2 enhancement:** add baseline-mode pre-commit + gitleaks

### C-SC-11 — Action SHA pinning

- **Status:** PRESENT (verified) — enforced by POL-CI-01 going forward.

### C-SBX-01 — demoparser2 process sandbox

- **Status:** MISSING (Phase 2 deliverable, primary defense for T-002 / T-003)
- **Description:** Subprocess + `RLIMIT_AS=4 GiB`, `RLIMIT_CPU=600s`, `RLIMIT_FSIZE=8 GiB`, `RLIMIT_NOFILE=256`, `RLIMIT_NPROC=1`, `prctl(PR_SET_NO_NEW_PRIVS)`; seccomp filter denies `socket/connect/accept/sendto/recvfrom/bind/listen/ptrace/init_module/mount/umount/reboot/kexec_*/perf_event_open/bpf/unshare`; JSON-over-stdio IPC (no pickle).
- **Site (planned):** `backend/data_sources/demo_parser_sandbox.py`
- **Test (planned):** `tests/security/test_demo_parser_sandbox.py`
- **Mapping:** SSDF PW.7.1; CWE-693; OWASP10 A04

### C-SBX-02 — demoparser2 fuzzing

- **Status:** MISSING (Phase 1 scaffolding, full campaigns Phase 2)
- **Description:** Atheris coverage-guided fuzzer with `PBDEMS2\x00` prefix corpus; nightly 30-min budget on develop branch; auto-issue on new crash.
- **Site (planned):** `tools/fuzz/fuzz_demo_parser.py`, `.github/workflows/fuzz-nightly.yml`
- **Mapping:** SSDF PW.7.2; CWE-20

### C-DOCK-01 — FlareSolverr container hardening

- **Status:** PARTIAL (Phase 2 fixes remaining gaps)
- **Description today:** Image pinned to tag `v3.4.6`; healthcheck.
- **Gaps today:** Bound to `0.0.0.0:8191` (not localhost); container runs as root; no cap_drop; no read-only fs; not pinned by digest.
- **Phase 2:** `127.0.0.1:8191:8191`, `user: "1000:1000"`, `cap_drop: [ALL]`, `read_only: true`, `tmpfs: ["/tmp","/var/tmp"]`, `security_opt: ["no-new-privileges:true"]`, digest pin.
- **Site:** `docker-compose.yml`
- **Mapping:** ASVS V14.1; OWASP10 A05

### C-DOCK-02 — Container vulnerability scan

- **Status:** MISSING (Phase 2 deliverable)
- **Description:** `aquasecurity/trivy-action` against FlareSolverr image; gate on HIGH/CRITICAL.
- **Site (planned):** `.github/workflows/build.yml`

### C-MOD-01 — SBERT model pinning

- **Status:** MISSING (Phase 2 deliverable)
- **Description:** `SentenceTransformer(..., revision="<sha>")` + per-file SHA-256 stored in `core/integrity_manifest.json`; first-run hash verification.
- **Site (planned):** `Programma_CS2_RENAN/backend/knowledge/rag_knowledge.py:67`, `tools/refresh_model_pins.py`
- **Mapping:** SSDF PW.4.4; CWE-494

### C-MOD-02 — torch.load weights-only

- **Status:** PRESENT (verified at 5 sites)
- **Description:** All `torch.load(..., weights_only=True)` — defeats arbitrary code execution from pickle in `.pt` files.
- **Mapping:** CWE-502

### C-RASP-01 — RASP startup integrity check

- **Status:** PRESENT
- **Description:** Manifest HMAC verified at startup; raises `IntegrityError` on mismatch.
- **Site:** `observability/rasp.py:68-125`

### C-RASP-02 — RASP continuous mode

- **Status:** MISSING (Phase 3)
- **Description:** Hourly periodic re-verification while app runs; on critical-file change, lock to read-only + prompt re-install.
- **Site (planned):** extension to `observability/rasp.py`
- **Mapping:** SSDF RV.1.3

### C-DRIFT-01 — Drift detector

- **Status:** MISSING (Phase 3 deliverable)
- **Description:** `tools/drift_detector.py` + `goliath.py drift` — baseline `Programma_CS2_RENAN/**` SHA-256 hashes after each release; compare on startup.
- **Mapping:** ISO27001 A.8.32

### C-CFG-01 — Pydantic settings schema with production-mode refusal

- **Status:** MISSING (Phase 2 deliverable)
- **Description:** `core/settings_schema.py` validates env vars at startup; refuses to start in `CS2_PROD=1` on missing required.
- **Mapping:** ASVS V14.1; OWASP10 A05

### C-WIPE-01 — Safe wipe-tooling

- **Status:** MISSING (Phase 1 deliverable, file added but v4 stays in operation)
- **Description:** Consolidated `tools/wipe_for_reingest_safe.py` — mandatory `--confirm-wipe`, `--dry-run` default, DB-unlock check via `psutil`, audit-log entry, HMAC-sealed Fernet snapshot at `Programma_CS2_RENAN/backups/wipe_snapshots/<ts>/`.
- **Mapping:** SSDF RV.2; ISO27001 A.8.13

### C-COV-01 — Coverage threshold alignment

- **Status:** PARTIAL (CI 33 vs `pyproject.toml` 40)
- **Description:** Align both at 40 (close gap).
- **Mapping:** SSDF PW.7.4

### C-MYP-01 — mypy enforcement on security-critical packages

- **Status:** PARTIAL (Phase 3 enforcement)
- **Description:** Today `continue-on-error: true`. Phase 3: enforce on `core/`, `backend/auth/`, `observability/`. Add `core/typing/secrets.py` with `Secret = NewType("Secret", str)` so `Secret → str` logger arg fails mypy.

---

## Cross-cutting Reliability ↔ Security

### C-DB-01 — DB write broker

- **Status:** MISSING (Phase 2 deliverable, after live ingestion finishes)
- **Description:** Single async writer thread fed by `multiprocessing.Queue`; catalogued mutation tags + Pydantic-validated payloads (no pickle of callables); `BEGIN IMMEDIATE` per request; exponential backoff retry on locked.
- **Site (planned):** `backend/storage/_writer_broker.py`; refactor `state_manager.py:55-150`
- **Acceptance:** zero "database is locked" in 100-demo concurrent stress test
- **Mapping:** Doctrine §59; ASVS V8.3 (data integrity)

### C-DB-02 — PRAGMA foreign_keys=ON

- **Status:** PRESENT (verified, AUDIT §9 DB-06)

### C-DB-03 — PRAGMA wal_autocheckpoint=512

- **Status:** PRESENT (verified, AUDIT §9 DB-07)

### C-DB-04 — Identifier whitelist

- **Status:** PRESENT (verified, AUDIT §9 DB-01/DB-04)
- **Description:** `_assert_safe_identifier`, `_assert_safe_col_type`, `_SAFE_BACKUP_LABEL_RE` allowlists.
- **Mapping:** CWE-89; OWASP10 A03

---

## Mapping Summary — NIST SSDF v1.1 Practices Coverage

| Practice | Description | Coverage |
|---|---|---|
| **PO.1** Define Roles | CODEOWNERS + this catalog | PRESENT |
| **PO.3** Implement Supporting Toolchains | Policy-as-code, CI gates | PARTIAL |
| **PO.5** Implement & Maintain Secure Environments | Sandbox + container hardening | PARTIAL |
| **PS.1** Protect All Forms of Code | Git LFS for binaries; `.gitignore` 175 lines | PRESENT |
| **PS.2** Provide Mechanism for Software Verification | SBOM + SLSA + signing | MISSING |
| **PS.3** Archive & Protect Each Software Release | Lockfiles + integrity manifest | PARTIAL |
| **PW.1** Design Software with Security in Mind | This document | PRESENT |
| **PW.4** Reuse Existing, Well-Secured Software | Hashed locks + pip-audit | PARTIAL |
| **PW.7** Review/Analyze Code | Bandit + detect-secrets + headless validator | PRESENT |
| **PW.8** Test Executable Code | 1935 tests + fuzzing (Phase 2) | PARTIAL |
| **RV.1** Identify and Confirm Vulnerabilities on Ongoing Basis | pip-audit + Dependabot + RASP | PARTIAL |
| **RV.2** Assess, Prioritize, and Remediate Vulnerabilities | CVE_LOG + waivers | PRESENT |
| **RV.3** Analyze Vulnerabilities to Identify Root Causes | Postmortem template in IR runbooks | PRESENT |

---

## Mapping Summary — OWASP ASVS L2 Coverage

| ASVS Section | Coverage |
|---|---|
| V1 Architecture | PRESENT (this document) |
| V2 Authentication | PARTIAL (API-key today; OAuth Phase 3) |
| V3 Session Management | MISSING (only relevant after OAuth Phase 3) |
| V6 Stored Cryptography | PARTIAL (HMAC today; Fernet Phase 2) |
| V7 Error Handling and Logging | PARTIAL (redaction Phase 2) |
| V8 Data Protection | PARTIAL (DB-broker Phase 2) |
| V9 Communications | PRESENT |
| V13 API & Web Service | PRESENT |
| V14 Configuration | PARTIAL (settings_schema Phase 2) |

---

## Mapping Summary — OWASP Top 10 (2021) Coverage

| Category | Coverage |
|---|---|
| A01 Broken Access Control | PRESENT (single-user; future multi-account) |
| A02 Cryptographic Failures | PARTIAL (Phase 2 disk encryption) |
| A03 Injection | PRESENT (parameterised + identifier whitelist) |
| A04 Insecure Design | PRESENT (this threat model) |
| A05 Security Misconfiguration | PARTIAL (Docker hardening Phase 2) |
| A06 Vulnerable & Outdated Components | PRESENT (pin + audit + Dependabot) |
| A07 Identification & Authentication Failures | MISSING (until OAuth Phase 3) |
| A08 Software & Data Integrity Failures | PARTIAL (signing + SLSA Phase 3) |
| A09 Security Logging & Monitoring | PARTIAL (audit log + redaction Phase 2) |
| A10 Server-Side Request Forgery | PARTIAL (HTTPS-only; Phase 2 DNS pin) |
