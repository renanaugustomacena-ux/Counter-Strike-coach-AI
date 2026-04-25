# Threat Model — Macena CS2 Analyzer (`Programma_CS2_RENAN`)

**Version:** 1.0
**Date authored:** 2026-04-25
**Methodology:** STRIDE + LINDDUN GO + Data-Flow Diagram (DFD)
**Standards:** NIST SP 800-218 v1.1 (SSDF), NIST SP 800-53 r5, OWASP ASVS 4.0.3 L2, OWASP Top 10:2021, CWE Top 25 (2024), ISO/IEC 27001:2022
**Owner:** Renan Augusto Macena

> *"Threat models are living artefacts."* — Doctrine §55
>
> Every PR that touches a path in [`BOUNDARY_FILES.txt`](BOUNDARY_FILES.txt) requires updating the
> matching trust boundary section here. Reviewers verify the threat model section was updated before
> approving.

---

## 0. Context

`Programma_CS2_RENAN` is a Python 3.10+ desktop coaching app for Counter-Strike 2 players. It ingests
`.dem` files via `demoparser2` (Rust C extension), maintains an SQLite-WAL database of tick-level
features and aggregated stats, trains JEPA / RAP neural-network models, scrapes HLTV pro-player stats
through a containerised FlareSolverr proxy, and surfaces tactical insight in a PySide6/Qt UI.

It currently authenticates to Steam Web API and FaceIt API via API keys stored in the OS keyring with
encrypted disk fallback. **Imminent change:** integrate Steam OpenID 2.0 login and FaceIt OAuth2 +
PKCE login, i.e., third-party identity bound to the local install.

This document enumerates **what an attacker would target, by what means, and what we do about it**.

---

## 1. Goals & Non-Goals

### 1.1 In scope

- Single-user desktop install on Windows / macOS / Linux.
- Local SQLite databases; local model checkpoints; local demo cache.
- Outbound network: HLTV (via FlareSolverr), FaceIt API, Steam Web API, Ollama (local LLM),
  HuggingFace (SBERT model), GitHub Releases (updates), Sentry (optional telemetry).
- Inbound network: none by default. The `remote_file_server.py` is a localhost-only HTTP read-only
  server for one-host LAN sharing of demo files; it is gated by HMAC API key + TLS-required-non-localhost.
- Account linkage: Steam Web API key, Steam OpenID 2.0 (planned), FaceIt API key, FaceIt OAuth2 (planned).
- Supply chain: PyPI (Python deps), GHCR (FlareSolverr image), HuggingFace Hub (SBERT model).
- Build & release: GitHub Actions, PyInstaller, Inno Setup.

### 1.2 Explicitly out of scope (documented for transparency)

- **Multi-user workstation hardening** — assumed: the user owns the machine.
- **Hardware-backed key storage (TPM)** — only TPM-bound storage defeats same-user malware
  unwrapping via OS-level APIs (DPAPI / Keychain). Out of scope for desktop coaching app.
- **Forced cloud sync of vault** — explicitly **forbidden**: cloud sync of `~` would broaden the
  attack surface. We assume the user's keyring vault is local-only.
- **GDPR right-to-erasure across backups** — handled separately by backup retention policy.
- **macOS / Linux installer signing** — Phase 4 (deferred).
- **Hermetic builds (Nix / Bazel)** — SLSA Build L4 evaluation is Phase 4.
- **FIDO2 / WebAuthn second factor** — designed in `INCIDENT_RESPONSE.md` discussion but Phase 4.

---

## 2. Assets & Trust Boundaries

### 2.1 Asset Register (sensitivity per ISO 27001:2022 A.5.12)

| ID | Asset | Sensitivity | Today's location | Confidentiality | Integrity | Availability |
|---|---|---|---|---|---|---|
| **A1** | Steam Web API key | SECRET | OS keyring or `user_settings.json` chmod 0o600 | HIGH | HIGH | LOW |
| **A2** | FaceIt API key + future OAuth tokens (access/refresh/id) | SECRET | OS keyring | HIGH | HIGH | LOW |
| **A3** | SteamID64 + FaceIt user_id (PII) | INTERNAL | Future `AppUser` SQLite table | MED | HIGH | LOW |
| **A4** | Demo files (.dem) | INTERNAL | `<DATA_DIR>/demo_cache/` and originals | LOW | MED | LOW |
| **A5** | Trained model checkpoints (.pt) | INTERNAL | `MODELS_DIR/` | LOW | HIGH | MED |
| **A6** | Ingestion / coaching DB (monolith) | INTERNAL | `Programma_CS2_RENAN/backend/storage/database.db` | MED | HIGH | HIGH |
| **A7** | HLTV scraped stats DB | INTERNAL | `Programma_CS2_RENAN/backend/storage/hltv_metadata.db` | LOW | MED | LOW |
| **A8** | Per-match shard DBs | INTERNAL | `<PRO_DEMO_PATH>/match_data/match_{id}.db` | MED | HIGH | MED |
| **A9** | Integrity manifest HMAC key (`CS2_MANIFEST_KEY`) | SECRET | Env var or static fallback (gap RP-01) | HIGH | HIGH | MED |
| **A10** | Demo-cache HMAC key | SECRET | `<DATA_DIR>/demo_cache/.hmac_key` chmod 0o600 | HIGH | HIGH | LOW |
| **A11** | Audit log (new) | INTERNAL — integrity-critical | `logs/audit.log*` | LOW | **CRITICAL** | MED |
| **A12** | RAG knowledge base + SBERT model | INTERNAL | `~/.cache/torch/sentence_transformers/` | LOW | HIGH | LOW |
| **A13** | App source — released `.exe` | PUBLIC — integrity-critical | GitHub Releases | LOW | **CRITICAL** | MED |
| **A14** | Encrypted-disk-fallback master key | SECRET | DPAPI (Windows) / Keychain (macOS) / scrypt+passphrase (Linux) | HIGH | HIGH | LOW |
| **A15** | Audit chain HMAC key | SECRET | Encrypted vault (`SecretStorage`) | HIGH | **CRITICAL** | LOW |

### 2.2 Trust Boundaries

| TB | From | To | Today's validators | Hardening (this plan) |
|---|---|---|---|---|
| **TB-1** | HLTV (via FlareSolverr) | scrape parser | Text-only extraction, regex IDs, robots.txt preflight | DNS pinning, response size cap, FlareSolverr container hardening |
| **TB-2** | FaceIt CDN | demo download | HTTPS-only, basename strip, streaming `MAX_DEMO_SIZE` cap | DNS-rebinding defense, JWT verification on id_token |
| **TB-3** | Steam Web API | profile fetch | TLS, 17-digit numeric SteamID validation | OpenID `check_authentication` round-trip |
| **TB-4** | Local file system (.dem from picker / FaceIt) | `demoparser2` (C extension) | `realpath` + magic-byte + size + extension | **Process sandbox** (subprocess + seccomp + rlimit) + nightly fuzzing |
| **TB-5** | `demoparser2` → Qt UI | dataclass dicts | `METADATA_DIM=25` contract | Sandbox boundary; JSON-over-stdio IPC; **no pickle across boundary** |
| **TB-6** | LLM (Ollama) | UI surfaces | `_sanitize_llm_context` (control chars, length cap, brace-escape) | unchanged |
| **TB-7** | HuggingFace Hub | SBERT model | none | Revision pinning + per-file SHA-256 in integrity manifest |
| **TB-8** | PyPI | dependencies | Exact version pins, pip-audit, Dependabot | `--require-hashes`, SBOM (CycloneDX), SLSA L3 |
| **TB-9** | GHCR | FlareSolverr image | Tag pin (`v3.4.6`) | Digest pin + Trivy scan |
| **TB-10** | OS keyring | secret store | `keyring==25.7.0` | Encrypted disk fallback (DPAPI / Keychain / scrypt+passphrase) |
| **TB-11** | Local LAN | `remote_file_server.py` | HMAC API key (timing-safe), TLS-required-non-localhost, per-IP rate limit 10 req/min | Unchanged (already hardened per AUDIT §9) |

### 2.3 Adversary Model

| Adversary | Capability | Goal | Defended? |
|---|---|---|---|
| **External attacker (network)** | Active MITM on outbound HTTP, DNS hijack | Inject responses; redirect downloads; exfil tokens via SSRF | TLS-only; HTTPS scheme allow-list; future DNS pinning |
| **Malicious peer (community demo donor)** | Crafts a `.dem` with parser-RCE payload | Code execution in coaching app process | Sandbox (Phase 2); fuzzing nightly; magic-byte+size pre-check |
| **Compromised PyPI dependency** | Maintainer-takeover or typosquat publishes malicious version | Inject code into build artifact | Hash-pinned lockfile; pip-audit; SBOM; SLSA Build L3 |
| **Compromised GHCR image** | FlareSolverr image tag re-signed with malicious content | RCE inside FlareSolverr container; attempt host pivot | Digest pin; non-root user; cap_drop; read-only fs; localhost-only bind |
| **Compromised HuggingFace model snapshot** | Malicious SBERT swap | Manipulate embedding outputs (data integrity) | Revision pin + per-file SHA-256 verify; `torch.load(weights_only=True)` for any .pt |
| **Malicious local user (other accounts on shared box)** | Read `~`, list FS, attempt path-traversal | Read tokens, demos, DB | chmod 0o600 + encrypted-disk-fallback (DPAPI/Keychain) |
| **Curious local user (same account)** | Browse FS, read keyring | Casual disclosure | chmod 0o600; not defendable against same-user reads via OS APIs (residual) |
| **Lost / stolen device** | Full FS access, attempt boot from external media | Token & data extraction | OS-level disk encryption assumed; encrypted vault; documented residual on out-of-process attacks |
| **Steam API compromise** | Steam returns malicious `claimed_id` or profile data | Account takeover via forged identity | OpenID `check_authentication` POST round-trip; strict regex on `claimed_id` |
| **FaceIt API compromise** | Forged JWKS, tampered id_token, malicious demo URL | Token forgery; SSRF via `demo_url` | Strict JWT validation (RS256/ES256, JWKS-pinned, nonce); HTTPS-only `demo_url`; basename strip |

---

## 3. Data-Flow Diagram (DFD)

Mermaid notation. Trust boundaries shown as dashed lines.

```mermaid
graph LR
    subgraph user["User Workstation"]
        UI[Qt/Kivy UI]
        APP[App process]
        DB[(SQLite WAL\ndatabase.db)]
        CACHE[(Demo cache\n+HMAC key)]
        VAULT[(Keyring /\nEncrypted vault)]
        AUDIT[(audit.log\nHMAC chain)]
        MODELS[(Model checkpoints)]
    end

    subgraph sandbox["Sandboxed parser process"]
        DPARSE[demoparser2\n+seccomp+rlimit]
    end

    subgraph fls["FlareSolverr container"]
        FLARE[Headless Chromium\nlocalhost-only\nnon-root, cap_drop]
    end

    subgraph net["Public Internet"]
        STEAM[Steam Web API\n+ OpenID 2.0]
        FACEIT[FaceIt API + OAuth2]
        HLTV[hltv.org]
        OLLAMA[Ollama localhost]
        HF[HuggingFace Hub]
        PYPI[PyPI]
        GHCR[GHCR]
    end

    UI -->|user actions| APP
    APP -->|JSON over stdio\nNO pickle| DPARSE
    DPARSE -->|frame chunks| APP
    APP -->|parameterised queries| DB
    APP -->|HMAC-verified pickle| CACHE
    APP -->|get/set_secret| VAULT
    APP -->|append-only HMAC chain| AUDIT
    APP -->|weights_only=True| MODELS

    APP -.TB-3.->|HTTPS + check_authentication| STEAM
    APP -.TB-2.->|HTTPS + JWKS-strict| FACEIT
    APP -.TB-1.->|via FLARE| FLARE
    FLARE -.TB-1.->|HTTPS| HLTV
    APP -.TB-6.->|local HTTP| OLLAMA
    APP -.TB-7.->|revision-pinned| HF

    PYPI -.TB-8.->|--require-hashes| APP
    GHCR -.TB-9.->|digest-pinned| FLARE
```

---

## 4. STRIDE Matrix (Excerpt — Top Threats)

The full matrix (all asset × threat-class combinations) is maintained in this section.
Below is the prioritised excerpt; every `T-NNN` ID is referenced from `CONTROL_CATALOG.md`.

| ID | Class | Threat | Asset(s) | Current control | Residual gap | Hardening |
|---|---|---|---|---|---|---|
| **T-001** | I | Secrets leak via logs (incl. `exc_info=True`, Sentry breadcrumbs, third-party module logs) | A1, A2, A9, A10, A14, A15 | Opt-in `mask_secret()` only; Sentry `_before_send` strips PII but optional | High — any developer mistake leaks; bytes-typed logs not scrubbed | §4.3 plan: `SecretRedactingFilter` at root logger; identity-pass + pattern-pass |
| **T-002** | T/E | Malicious `.dem` triggers parser RCE in `demoparser2` (Rust C extension) | A4 → app process | Size/magic-byte/realpath/extension; in-process | Parser CVEs grant Qt-process RCE → keyring access | Phase 2: subprocess sandbox + seccomp + rlimit; nightly Atheris fuzz |
| **T-003** | I | Compromised `demoparser2` exfils to network | A1, A2, A9, A10, A14 → attacker | None — runs in same process as keyring access | Critical | Phase 2: seccomp filter denies `socket/connect/sendto/...` |
| **T-004** | T | Path traversal via crafted demo path or symlink | A6, A8 (overwrite), A4 (read other-user files) | `os.path.realpath()` before parser; basename-strip on FaceIt match_id | Low — already hardened | Periodically re-verify symlink test in CI |
| **T-005** | D/T | DB-lock contention during ingestion corrupts provenance trail; lost progress writes; retry storms | A6, A8, A11 | `pool_size=1`, `busy_timeout=30s`, `wal_autocheckpoint=512`, in-process `_lock` | **Active production failure** (2026-04-25 ingestion); reliability ↔ security per doctrine §59 | Phase 2: writer-broker (`backend/storage/_writer_broker.py`) |
| **T-006** | T | Compromised PyPI dep (typosquat / maintainer takeover) | A13, A6 (build pipeline) | Exact version pins, pip-audit `--strict`, Dependabot | No `--require-hashes`; index-poisoning at lock-time still possible | Phase 2: hash-pinned lockfiles; `tools/verify_lock_hashes.py` gate |
| **T-007** | I | Path traversal via FaceIt-controlled `match_id` in download path | A4 | `os.path.basename(str(match_id))` + reject mismatch | Low | Audited green |
| **T-008** | T | SSRF / DNS rebinding on FaceIt `demo_url` | A4 → internal hosts | HTTPS scheme check | DNS rebinding (attacker domain → 127.0.0.1) | Phase 2: DNS allowlist + post-resolve IP-class check |
| **T-009** | I | HLTV scraper triggers Cloudflare JS exploit in headless Chromium | FlareSolverr container → host | Container isolation (Docker bridge), localhost not bound today | **Gap:** `8191:8191` binds 0.0.0.0; container runs as root | Phase 2: bind 127.0.0.1 only; non-root `1000:1000`; cap_drop ALL; read-only fs |
| **T-010** | I | SBERT model swap via HuggingFace mirror MITM or typosquat | A12 | None — auto-downloaded, no revision pin, no hash check | High during first-run | Phase 2: revision pin + per-file SHA-256 in `integrity_manifest.json` |
| **T-011** | T | Tampered model checkpoint → poisoned coaching | A5, A12 | `torch.load(weights_only=True)` (5 sites) | Mid — only structural defense; data-poisoning not detected | Long-horizon: ed25519 checkpoint signing |
| **T-012** | E | Privileged action via subprocess shell injection | command surface | `shell=False` everywhere; one `# nosec B602` in build_tools | Low | Audited green; policy POL-CODE-01 prevents regression |
| **T-013** | I/E | LAN attacker reaches `remote_file_server` or FlareSolverr | A4, A6, network | TLS-required-non-localhost gate (read-only HTTP); HMAC API key timing-safe | FlareSolverr 0.0.0.0 (gap — Phase 2 fix) | Phase 2: bind 127.0.0.1 only |
| **T-014** | I | Sentry telemetry leaks PII to remote SaaS | A3, A4, A11 | `_before_send` PII strip, Sentry **opt-in** with `SENTRY_ENABLED` | Mid — opt-in default off, but risk if user enables without redaction filter | Phase 2: extend `_before_send` with redaction regex pass (defense-in-depth) |
| **T-015** | R | Tampered audit / log trail (post-incident forensics) | A11 | None today — JSON logs are not tamper-evident | High during incident response | Phase 2: HMAC-chained audit log; `goliath audit verify` |
| **T-016** | S | Forged Steam OpenID 2.0 assertion (replay attack) | A3 | n/a (not yet implemented) | Critical for OpenID rollout | Phase 3: mandatory `openid.mode=check_authentication` POST |
| **T-017** | S | OAuth authorisation code interception (public client without PKCE) | A2 (FaceIt tokens) | n/a (not yet implemented) | Critical for OAuth rollout | Phase 3: PKCE S256 + nonce + JWKS-strict id_token |
| **T-018** | I | First-run SBERT download MITM | A12 | None | Mid | See T-010 |
| **T-019** | I | API key visible in `user_settings.json` if keyring unavailable | A1, A2 | chmod 0o600 only | Mid — backup recovery, lost laptop, cloud sync of `~` | Phase 2: encrypted-disk-fallback (DPAPI / Keychain / scrypt) |
| **T-020** | T | Wipe-tooling accidental data loss | A6, A8 | None — v4 has no `--confirm-wipe`, no snapshot | High operator-error risk | Phase 1: consolidated `wipe_for_reingest_safe.py` with mandatory `--confirm-wipe`, `--dry-run` default, HMAC-sealed snapshot |
| **T-021** | T | Alembic migration broad `except Exception` masks failure → silent corruption | A6 | Currently broad excepts in `5d5764ef9f26_*.py` | High — silent failure mode | Policy POL-DB-02 forbids broad `except` in `alembic/versions/**` |
| **T-022** | T | GitHub Actions tag-pinning enables supply-chain attack | A13 | All actions SHA-pinned today (verified) | Low — but discipline can drift | Policy POL-CI-01 enforces SHA pinning permanently |
| **T-023** | E | Privilege escalation via integrity-manifest HMAC key compromise (static fallback) | A9, A13 | `CS2_MANIFEST_KEY` env or static `"macena-cs2-integrity-v1"` fallback | High in dev mode of frozen build | Phase 3: per-release rotation; audit-log event `manifest.key.rotated` |

---

## 5. LINDDUN GO Privacy Threats (Selected)

LINDDUN: **L**inkability, **I**dentifiability, **N**on-repudiation, **D**etectability,
**D**isclosure of information, **U**nawareness, **N**on-compliance.

| ID | Class | Threat | Asset(s) | Mitigation |
|---|---|---|---|---|
| **L-001** | L | SteamID + match history → linkable to in-game player identity (Steam profile is public) | A3 | Per-feature consent prompt before linking demos to SteamID; data minimisation (Art. 5(1)(c)) |
| **L-002** | I | API request URLs with embedded SteamID logged identify the user across sessions | A3 in logs | `SecretRedactingFilter` redacts SteamID64 (regex `\b7656119\d{10}\b`) by default |
| **L-003** | D | Audit log is detectable on disk; an attacker with FS read can correlate user activity | A11 | Documented residual; off-host export for high-stakes installs |
| **L-004** | D | First-launch HuggingFace download identifies the user to HF (IP + user-agent) | A12 | Deferred: optional offline-only mode that ships SBERT in the installer |
| **L-005** | D | Disclosure | Sentry telemetry could disclose match content to remote SaaS | Sentry opt-in default OFF; `_before_send` redaction; documented sensitivity classification |
| **L-006** | U | Unawareness — user does not know what is sent to FaceIt / Steam / Sentry / HF | All telemetry | First-run privacy notice; settings UI showing "what is sent" per provider |
| **L-007** | N | Non-compliance — GDPR Art. 5 data minimisation on Steam profile | A3 | Initial fields only: SteamID, display name, avatar URL. **No email, friends list, activity history without per-feature consent.** |

---

## 6. Layered Adversaries

The threat model assumes the following layered adversaries; each subsequent layer can do everything
the previous layer can plus its own capabilities.

1. **Network passive observer** — sees traffic patterns. Defended by HTTPS-only and minimal telemetry.
2. **Network active adversary** — MITM, DNS hijack. Defended by TLS verification, HTTPS-only allow-list,
   future DNS pinning + JWKS-strict JWT validation.
3. **Compromised peer (community demo donor)** — crafts hostile `.dem`. Defended by sandbox + size/magic
   gates + nightly fuzz.
4. **Compromised dependency** — PyPI / GHCR / HF supply-chain. Defended by `--require-hashes`, digest pin,
   revision pin, SBOM, SLSA L3.
5. **Curious local user (same account)** — reads `~`. **Partially defended** (chmod 0o600); residual is
   documented (OS-level same-user APIs cannot be defeated without TPM).
6. **Malicious local user (other account on shared box)** — chmod 0o600 + encrypted disk fallback bind to
   user UID via DPAPI / Keychain.
7. **Lost / stolen device** — encrypted vault sealed to user account; OS-level disk encryption assumed.
8. **Compromised host (root)** — out of scope. Documented as "not defendable without TPM-bound key
   storage". Forensic readiness via HMAC-chain audit log helps post-incident.

---

## 7. Continuous Threat Modeling Discipline

Per doctrine §55 — "Threat models are living artefacts."

**Process:**
1. Every PR that touches a path matching `BOUNDARY_FILES.txt` triggers `.github/workflows/threat-model-gate.yml`.
2. The workflow labels the PR `security-review-required` and posts a comment listing the matched
   trust boundaries.
3. The PR template ([`/.github/pull_request_template.md`](../.github/pull_request_template.md)) includes a
   "Threat model section updated" checklist.
4. CODEOWNERS enforces a security review.
5. Quarterly: full threat-model walkthrough by repo owner; output appended to this document with date.

**Quarterly review log:**

| Date | Reviewer | Changes |
|---|---|---|
| 2026-04-25 | Renan Augusto Macena | Initial document |

---

## 8. References

- **NIST SP 800-218 v1.1** — Secure Software Development Framework (SSDF v1.1)
- **NIST SP 800-53 r5** / **800-161 r1** — Supply chain risk management
- **NIST SP 800-30 r1** — Risk Assessment
- **NIST SP 800-61 r2** — Computer Security Incident Handling Guide
- **OWASP ASVS 4.0.3** — Application Security Verification Standard, Level 2
- **OWASP Top 10:2021**
- **CWE Top 25 (2024)**
- **ISO/IEC 27001:2022** Annex A
- **LINDDUN GO (2023)** — Privacy threat catalogue
- **MITRE ATT&CK for Enterprise**
- **STRIDE** — Microsoft SDL threat-modeling methodology
- **OAuth 2.0 Threat Model and Security Considerations** — RFC 6819
- **OAuth 2.0 for Native Apps** — RFC 8252
