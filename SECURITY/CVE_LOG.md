# CVE Log

Append-only log of CVE triage decisions for `Programma_CS2_RENAN` and its dependencies.

## Schema

Each entry MUST include:

| Field | Description |
|---|---|
| **CVE / GHSA ID** | The advisory identifier |
| **Component** | Affected package + version |
| **Discovered** | ISO date the team first saw the advisory (via `pip-audit`, OSV, Dependabot, manual) |
| **Severity** | Vendor severity + our local re-rating after threat-model context |
| **Exploitability in our context** | Is the vulnerable code path reachable from a trust boundary? |
| **Triaged** | ISO date triage decision was made |
| **Decision** | `patch` / `mitigate` / `accept-with-waiver` / `reject` |
| **Deployed** | ISO date fix shipped (if `patch`) |
| **Residual risk** | What remains after the action |
| **Owner** | Who is accountable |
| **Reference** | Link to advisory + PR + audit-log event |

## Format

Use this template:

```markdown
### CVE-YYYY-NNNNN — <Short title>
- **Component:** `<package>==<version>`
- **Discovered:** YYYY-MM-DD via `pip-audit` / Dependabot / OSV / manual
- **Severity:** Vendor=<X>; Local=<Y> (rationale: …)
- **Exploitability in our context:** <reachable / not reachable / requires-prior-compromise>
- **Triaged:** YYYY-MM-DD
- **Decision:** <patch / mitigate / accept-with-waiver / reject>
- **Deployed:** YYYY-MM-DD (PR #NNN)
- **Residual risk:** …
- **Owner:** Renan Augusto Macena
- **Reference:** <advisory URL>
```

## Discipline

- Entries are **append-only**. Corrections go below as a new entry referencing the old.
- Audit-log emits `cve.triaged` event on every triage decision.
- `accept-with-waiver` requires a corresponding `SECURITY/waivers.yaml` entry with `expires:` ≤ 90 days
  and a documented compensating control.
- `pip-audit --strict` runs in CI; un-triaged HIGH/CRITICAL findings block release.

---

## Entries

_(none yet — this log begins 2026-04-25)_
