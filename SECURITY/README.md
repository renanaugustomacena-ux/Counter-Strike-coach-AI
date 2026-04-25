# SECURITY/ — Macena CS2 Analyzer Security Documentation

This directory is the single source of truth for the security posture of `Programma_CS2_RENAN`.
All docs here are version-controlled, reviewed via `CODEOWNERS`, and authoritative.

## Doctrine

Security is a **structural property of the system**, not a post-step. We model:

```
code → build → artifact → deploy → run
```

with security signals, feedback loops, and policy enforcement at every stage. Every non-trivial
decision in this directory is defended with **risk-addressed / residual-risk / tradeoffs / assumptions**.

## Layout

| File | Purpose |
|---|---|
| [`THREAT_MODEL.md`](THREAT_MODEL.md) | STRIDE + LINDDUN matrix, DFD, asset register, trust boundaries |
| [`CONTROL_CATALOG.md`](CONTROL_CATALOG.md) | Controls mapped to NIST SSDF, OWASP ASVS L2, CWE Top 25 |
| [`INCIDENT_RESPONSE.md`](INCIDENT_RESPONSE.md) | NIST SP 800-61 r2 runbooks for IR-01…IR-05 |
| [`SLSA.md`](SLSA.md) | SLSA Build Level 3 posture and gap analysis |
| [`CONFIG_REFERENCE.md`](CONFIG_REFERENCE.md) | Environment variables: defaults, sensitivity, validation |
| [`CVE_LOG.md`](CVE_LOG.md) | Append-only CVE triage log |
| [`BOUNDARY_FILES.txt`](BOUNDARY_FILES.txt) | Trust-boundary file list — PRs touching any line require security review |
| [`WIPE_RUNBOOK.md`](WIPE_RUNBOOK.md) | Standard operating procedure for `tools/wipe_for_reingest*.py` |
| `policies/` | Policy-as-code rules consumed by `tools/policy_runner.py` |
| `waivers.yaml` | Time-bound exceptions to policies (every entry: `risk:`, `expires:`, `owner:`, `justification:`) |

## How a contributor uses this directory

1. **Before writing code** — read `THREAT_MODEL.md` for the trust boundary your change crosses.
2. **While writing** — `tools/policy_runner.py` runs in pre-commit (warn-mode initially) and prevents drift.
3. **Before merging** — if your change touches a path in `BOUNDARY_FILES.txt`, the CI labels the PR
   `security-review-required` and `CODEOWNERS` enforces a security review.
4. **At release** — `goliath.py audit` runs the full chain (SBOM, SLSA attestation, integrity manifest, RASP).
5. **During an incident** — `INCIDENT_RESPONSE.md` defines the named scenarios; `goliath.py panic` is the kill-switch.

## Standards anchoring

- **NIST SP 800-218 v1.1** (Secure Software Development Framework — SSDF)
- **NIST SP 800-53 r5** / **800-161 r1** (supply-chain risk management)
- **NIST SP 800-61 r2** (computer security incident handling guide)
- **NIST SP 800-63B** (digital identity / authentication)
- **OWASP ASVS 4.0.3 Level 2**
- **OWASP Top 10:2021**
- **CWE Top 25 (2024)**
- **SLSA v1.0** (Build Level 3 target)
- **CycloneDX 1.6** SBOM
- **ISO/IEC 27001:2022** Annex A controls A.5–A.8
- **LINDDUN GO (2023)** privacy threats
- **RFC 6749 / 7636 / 7519 / 7517 / 8252** (OAuth + JWT)
- **OpenID 2.0 Final** (Steam login)
- **OpenID Connect Core 1.0** (FaceIt)
- **GDPR Art. 5** (data minimization)

## Contact

Reports of vulnerabilities or security concerns must reach the repository owner:
**Renan Augusto Macena** — see CODEOWNERS for contact routing.

For coordinated disclosure, do **not** open a public issue. Use a private channel.
