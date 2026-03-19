# Error Codes Reference

All error codes used across the CS2 Analyzer project. Each code is formally
registered in `Programma_CS2_RENAN/observability/error_codes.py`.

## Logger Setup

| Code | Severity | Description | Remediation |
|---|---|---|---|
| LS-01 | MEDIUM | RotatingFileHandler unavailable — using plain FileHandler | Check file permissions. On Windows, close other processes holding the log file. |

## RASP (Runtime Protection)

| Code | Severity | Description | Remediation |
|---|---|---|---|
| RP-01 | HIGH | CS2_MANIFEST_KEY not set — using static fallback HMAC key | Set `CS2_MANIFEST_KEY` environment variable for production builds. |
| R1-12 | HIGH | HMAC manifest signing for integrity verification | Ensure `CS2_MANIFEST_KEY` is set at build time. |

## Data Access

| Code | Severity | Description | Remediation |
|---|---|---|---|
| DA-01-03 | LOW | Malformed JSON from database (pc_specs_json) | Re-run hardware detection or manually edit player profile. |

## Pipeline / Processing

| Code | Severity | Description | Remediation |
|---|---|---|---|
| P0-07 | LOW | Attribute initialized to prevent AttributeError | No user action needed. |
| P3-01 | LOW | Role enum canonical mapping | No user action needed. |
| P4-B | MEDIUM | Configurable zombie task threshold | Adjust `ZOMBIE_TASK_THRESHOLD_SECONDS` if large demos are being reset. |
| P7-01 | HIGH | API keys stored in plaintext settings.json | Migrate to OS credential store via the keyring library. |
| P7-02 | HIGH | Secret sanitization in error messages | Ensure all secret keys are listed in the sanitization loop. |

## Feature / Fix

| Code | Severity | Description | Remediation |
|---|---|---|---|
| F6-03 | LOW | Explicit commit for trained sample count | No user action needed. |
| F6-06 | LOW | sys.path bootstrap for direct script execution | Remove when entrypoints are configured in pyproject.toml. |
| F6-SE | HIGH | Backup failure — training gate engaged | Resolve backup issue and restart session engine. |
| F7-12 | LOW | sys.path bootstrap for root-level CLI entry points | Remove when `pip install -e .` is standard. |
| F7-19 | LOW | Training status card KivyMD properties | No user action needed. |
| F7-30 | MEDIUM | API key masking shows last 4 characters | Acceptable until keyring is integrated. |

## Session Engine

| Code | Severity | Description | Remediation |
|---|---|---|---|
| SE-02 | MEDIUM | Daemon thread join for graceful shutdown | No user action needed. |
| SE-04 | MEDIUM | Config validation for zombie threshold | Ensure `ZOMBIE_TASK_THRESHOLD_SECONDS` is a positive integer. |
| SE-05 | HIGH | Backup failure surfaced to UI | Check backup manager configuration and disk space. |
| SE-06 | LOW | Short wait for faster shutdown response | No user action needed. |
| SE-07 | MEDIUM | Settings reload once per scan cycle (TOCTOU window) | Next cycle picks up new values. |

## Ingestion Manager

| Code | Severity | Description | Remediation |
|---|---|---|---|
| IM-03 | MEDIUM | Event wait/clear ordering to prevent lost wakeup signals | No user action needed. |

## Neural Network

| Code | Severity | Description | Remediation |
|---|---|---|---|
| NN-02 | MEDIUM | Module-level training lock prevents concurrent training | No user action needed. |

## Game Analysis

| Code | Severity | Description | Remediation |
|---|---|---|---|
| G-07 | LOW | Belief calibration wired to Teacher daemon | No user action needed. |

## Knowledge / HLTV

| Code | Severity | Description | Remediation |
|---|---|---|---|
| H-02 | LOW | One-time knowledge base population from pro demos | No user action needed. |
