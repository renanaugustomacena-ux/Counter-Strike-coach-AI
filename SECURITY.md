# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
responsibly. **Do not open a public issue.**

### How to Report

Email **renan.macena@proton.me** with:

1. A description of the vulnerability and its potential impact.
2. Steps to reproduce (or a proof-of-concept if applicable).
3. The affected component (e.g., demo parsing, database, API, credential storage).

### What to Expect

- **Acknowledgment** within 72 hours of your report.
- **Assessment and fix** targeting 14 days for critical issues, 30 days for others.
- **Credit** in the CHANGELOG and release notes (unless you prefer anonymity).

### Scope

The following are in scope:

- Authentication/authorization bypass
- SQL injection or command injection
- Secrets exposure (API keys, credentials)
- Path traversal or arbitrary file access
- Denial of service via crafted demo files
- Supply chain compromise (dependency vulnerabilities)

### Out of Scope

- Social engineering attacks
- Issues in third-party dependencies with existing CVEs (report upstream)
- Attacks requiring physical access to the machine

## Security Measures

This project implements:

- **RASP** (Runtime Application Self-Protection) with integrity manifest verification
- **OS keyring** integration — no plaintext credential storage
- **Bandit SAST**, **detect-secrets**, and **pip-audit** in every CI pipeline run
- **SHA-pinned GitHub Actions** to prevent supply chain attacks
- **Input validation** with Pydantic models at all system boundaries
- **SQLite WAL mode** with parameterized queries (no SQL injection surface)
