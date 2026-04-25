# Configuration Reference — Environment Variables

**Version:** 1.0
**Date:** 2026-04-25
**Owner:** Renan Augusto Macena

This document is the authoritative catalogue of every environment variable consumed by
`Programma_CS2_RENAN`. Each variable is classified by sensitivity and validated at startup.

> Verified state (2026-04-25): `.env` exists locally but is **not** tracked in git. Only `.env.example`
> is tracked. `.gitignore` lines 50, 89-91 cover the pattern.

---

## Sensitivity classification

| Class | Definition | Storage rules |
|---|---|---|
| **PUBLIC** | Disclosure has no security impact | Plain `.env` / commit safe |
| **INTERNAL** | Disclosure is undesirable but not catastrophic | Plain `.env`; never logged in plain |
| **SECRET** | Disclosure permits identity theft, account compromise, integrity bypass, or data exfil | Keyring or encrypted vault only; never `.env` in plain (`.env` is gitignored but the file still exists on disk; encrypted disk fallback or keyring required for SECRET class) |

---

## Validation strategy

Phase 2 will introduce `Programma_CS2_RENAN/core/settings_schema.py` using `pydantic.BaseSettings`
with strict validators. Until then, validation is per-call-site.

In production mode (`CS2_PROD=1`), the app **refuses to start** if any `Required-in-production` SECRET
is missing or invalid. In development mode, it warns and proceeds.

---

## Variable Catalogue

### Authentication & Identity

#### `STEAM_API_KEY`
- **Sensitivity:** SECRET
- **Default:** (empty)
- **Required:** Required for Steam profile fetch / vanity URL resolution
- **Validation:** `^[A-F0-9]{32}$` (32-char uppercase hex)
- **Source:** Steam Web API console (<https://steamcommunity.com/dev/apikey>)
- **Storage:** OS keyring → fallback `user_settings.json` chmod 0o600 (sentinel `"PROTECTED_BY_WINDOWS_VAULT"` written to disk when keyring active)
- **Owner module:** `Programma_CS2_RENAN/backend/data_sources/steam_api.py`
- **Audit-log:** `secret.read{key="STEAM_API_KEY"}` on every consumption

#### `STEAM_ID`
- **Sensitivity:** INTERNAL
- **Default:** (empty)
- **Required:** No
- **Validation:** Exactly 17 digits starting `7656119`
- **Notes:** SteamID64 is publicly resolvable from a profile URL; sensitive only for linkability

#### `FACEIT_API_KEY`
- **Sensitivity:** SECRET
- **Default:** (empty)
- **Required:** Required for FaceIt API (today's flow)
- **Validation:** UUID-shape (`^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$`)
- **Source:** FaceIt developer portal
- **Storage:** Same as `STEAM_API_KEY`
- **Owner module:** `Programma_CS2_RENAN/backend/data_sources/faceit_api.py`, `faceit_integration.py`

#### `FACEIT_OAUTH_CLIENT_ID` _(Phase 3)_
- **Sensitivity:** PUBLIC (client_id is meant to be public; PKCE replaces client_secret)
- **Default:** (empty)
- **Required:** Required when `CS2_ENABLE_OAUTH_LOGIN=1`
- **Validation:** Non-empty string assigned by FaceIt at OAuth-app registration
- **Owner module:** `Programma_CS2_RENAN/backend/auth/faceit_oauth.py`

### Local services

#### `OLLAMA_URL`
- **Sensitivity:** INTERNAL
- **Default:** `http://localhost:11434`
- **Required:** No
- **Validation:** Parseable URL; production refuses non-localhost without explicit waiver
- **Owner module:** `backend/services/llm_service.py:24`

#### `OLLAMA_MODEL`
- **Sensitivity:** PUBLIC
- **Default:** `gemma4:e2b`
- **Required:** No
- **Validation:** Ollama-compatible model identifier
- **Owner module:** `backend/services/llm_service.py:25`

#### `FLARESOLVERR_URL`
- **Sensitivity:** INTERNAL
- **Default:** `http://localhost:8191/v1`
- **Required:** No
- **Validation:** **Must** be `127.0.0.1` or `localhost` (per `core/settings_schema.py` `must_be_localhost` validator)
- **Owner module:** `backend/data_sources/hltv/flaresolverr_client.py:23-32`

### Storage & Remote

#### `STORAGE_API_KEY`
- **Sensitivity:** SECRET
- **Default:** (empty)
- **Required:** Required only if remote file server is in use
- **Validation:** Min 32 chars high entropy
- **Storage:** OS keyring via `set_secret`/`get_secret`
- **Owner module:** `backend/storage/remote_file_server.py:94`

#### `CS2_ALLOW_INSECURE_BIND`
- **Sensitivity:** INTERNAL
- **Default:** `0`
- **Required:** No
- **Validation:** `0` or `1`. When `1`, `remote_file_server.py` allows non-localhost bind without TLS — **dev only**, never prod
- **Owner module:** `backend/storage/remote_file_server.py`

### Integrity & Observability

#### `CS2_MANIFEST_KEY`
- **Sensitivity:** SECRET
- **Default:** (warning if empty — falls back to static `"macena-cs2-integrity-v1"` which RP-01 flags as a build-time gap)
- **Required:** Required in `CS2_PROD=1`
- **Validation:** Min 32 bytes high entropy (recommended `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- **Storage:** Env var injected at build time; rotated per-release with 30-day grace via `goliath rotate manifest`
- **Owner module:** `Programma_CS2_RENAN/observability/rasp.py:12-22`

#### `CS2_AUDIT_KEY` _(Phase 2)_
- **Sensitivity:** SECRET
- **Default:** Random `secrets.token_bytes(32)` on first run
- **Required:** No (auto-generated)
- **Validation:** 32 bytes
- **Storage:** `SecretStorage` keyring entry `AUDIT_CHAIN_KEY`
- **Owner module:** `Programma_CS2_RENAN/observability/audit_log.py`

#### `CS2_WIPE_SNAPSHOT_KEY` _(Phase 1)_
- **Sensitivity:** SECRET
- **Default:** (empty — wipe tool refuses to run without explicit `--no-snapshot`)
- **Required:** Required when running `tools/wipe_for_reingest_safe.py` with snapshot enabled
- **Validation:** Min 32 bytes
- **Storage:** Env var or OS keyring
- **Owner module:** `tools/wipe_for_reingest_safe.py`

#### `SENTRY_DSN`
- **Sensitivity:** SECRET (URL embeds project token)
- **Default:** (empty)
- **Required:** No
- **Validation:** Sentry DSN URL format (`https://<key>@<host>/<project>`)
- **Notes:** Triple opt-in — also requires `SENTRY_ENABLED=1`
- **Owner module:** `Programma_CS2_RENAN/observability/sentry_setup.py`

#### `SENTRY_ENABLED`
- **Sensitivity:** PUBLIC
- **Default:** `0`
- **Required:** No
- **Validation:** `0` or `1`

#### `CS2_TELEMETRY_URL`
- **Sensitivity:** INTERNAL
- **Default:** `http://localhost:8000`
- **Required:** No
- **Validation:** URL parseable
- **Owner module:** `backend/services/telemetry_client.py`

#### `CS2_LOG_LEVEL`
- **Sensitivity:** PUBLIC
- **Default:** (set by `logger_setup.py`)
- **Required:** No
- **Validation:** One of `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`
- **Owner module:** `Programma_CS2_RENAN/observability/logger_setup.py:29`

### Performance & Modes

#### `HP_MODE`
- **Sensitivity:** PUBLIC
- **Default:** `0`
- **Required:** No
- **Validation:** `0` or `1` (high-performance mode for ingestion)

#### `CS2_PROD`
- **Sensitivity:** PUBLIC
- **Default:** `0`
- **Required:** No
- **Validation:** `0` or `1`. When `1`, all `Required-in-production` validators are enforced (start-time refusal on missing values)

#### `CS2_INTEGRATION_TESTS`
- **Sensitivity:** PUBLIC
- **Default:** `0`
- **Required:** No (testing only)

#### `CS2_DEMO_SANDBOX` _(Phase 2)_
- **Sensitivity:** PUBLIC
- **Default:** `1`
- **Required:** No
- **Validation:** `0` or `1`. Feature flag — `0` disables sandbox (rollback handle for first release after Phase 2)

#### `CS2_ENABLE_OAUTH_LOGIN` _(Phase 3)_
- **Sensitivity:** PUBLIC
- **Default:** `0`
- **Required:** No
- **Validation:** `0` or `1`. Feature flag — when `1`, Steam OpenID + FaceIt OAuth UI is wired

#### `CS2_ENABLE_NEW_SECRETS_PIPELINE` _(Phase 2)_
- **Sensitivity:** PUBLIC
- **Default:** `0` (Phase 2) → `1` (Phase 3 GA)
- **Required:** No
- **Validation:** `0` or `1`. Feature flag — when `1`, `core/secret_storage.py` is used; legacy `core/config.py:get_secret`/`set_secret` delegates

#### `CI`
- **Sensitivity:** PUBLIC
- **Default:** `0`
- **Required:** No
- **Validation:** `0` / `1` / `true`. When set, `core/config.py` venv-guard is bypassed

#### `KIVY_NO_ARGS`, `KIVY_LOG_LEVEL`, `QT_QUICK_BACKEND`
- **Sensitivity:** PUBLIC
- Standard third-party env vars — see Kivy / Qt docs

### HuggingFace / Model

#### `SENTENCE_TRANSFORMERS_HOME`
- **Sensitivity:** INTERNAL
- **Default:** `~/.cache/torch/sentence_transformers/`
- **Required:** No
- **Validation:** Path writable

---

## Discipline

- Adding a new env var requires:
  1. Documenting it here with all fields above
  2. Adding to `Programma_CS2_RENAN/core/settings_schema.py` (Phase 2)
  3. Adding to `.env.example`
  4. CODEOWNERS review
- Removing or renaming an env var requires a deprecation cycle:
  - First release: warn on use of old name
  - Second release: still accept old name + warn
  - Third release: remove

## File permissions

- `.env`: chmod 0o600 (owner-readable only). Documented; not enforced by app today.
- `Programma_CS2_RENAN/user_settings.json`: chmod 0o600 (enforced by `core/config.py:474-476`).
- Phase 2: encrypted-disk-fallback vault at `<get_writeable_dir()>/secrets.vault` chmod 0o600.

---

## References

- **NIST SP 800-53 r5** — control SC-12 (Cryptographic Key Establishment)
- **OWASP ASVS 4.0.3** — V14 Configuration
- **CWE-526** Cleartext Storage of Sensitive Information in Environment
- **12-Factor App Methodology** — Config (factor 3)
