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

### PYSEC-2026 pillow batch (13 advisories) — image decoder memory-safety fixes
- **Component:** `pillow==11.3.0` (dev venv + requirements.in/txt; `pillow==12.0.0` in requirements-dist.txt)
- **Advisories:** PYSEC-2026-165, -2249, -2250, -2251, -2252, -2253, -2254, -2255, -2256, -2257, -2874, -3451, -3452, -3453
- **Discovered:** 2026-07-17 via `pip-audit` (R5 campaign)
- **Severity:** Vendor=various (decoder OOB reads/writes, DoS); Local=MEDIUM (pillow is transitive — matplotlib/sentence-transformers image paths; the app itself renders via Qt QPixmap and never feeds user files to PIL directly)
- **Exploitability in our context:** not directly reachable (no PIL import in first-party code), but decoder bugs in a bundled library violate the zero-trust boundary rule — patch, don't waive
- **Triaged:** 2026-07-17
- **Decision:** patch — bump to `pillow==12.3.0` (covers every listed advisory)
- **Deployed:** 2026-07-17 (R5 PR: venv + requirements.in + requirements.txt + requirements-dist.txt + regenerated locks)
- **Residual risk:** none known for these advisories
- **Owner:** Renan Augusto Macena
- **Reference:** https://osv.dev/list?q=pillow (individual PYSEC ids above)

### CVE-2025-14929 / CVE-2026-5241 / CVE-2026-1839 / CVE-2026-4372 — transformers untrusted-model RCE family
- **Component:** `transformers==4.57.6` (transitive: `sentence-transformers==3.4.1` → SBERT embeddings for the RAG index)
- **Advisories:** PYSEC-2025-217 (X-CLIP checkpoint conversion deserialization), PYSEC-2026-2290 (LightGlue model-repo code execution), PYSEC-2026-2288 (`Trainer._load_rng_state()` torch.load of attacker checkpoint), PYSEC-2026-2289 (malicious `config.json` `auto_map` code execution)
- **Discovered:** 2026-07-17 via `pip-audit` (R5 campaign)
- **Severity:** Vendor=CRITICAL (RCE); Local=LOW (rationale below)
- **Exploitability in our context:** not reachable. Every advisory requires loading a model artifact from an attacker-controlled source. This codebase loads exactly one embedding model, `all-MiniLM-L6-v2`, whose name is hard-coded in `rag_knowledge.py:53`; there is no code path where a user-supplied string, file or repo reaches `from_pretrained`/`Trainer`. X-CLIP, LightGlue and `Trainer` are never instantiated (transformers is consumed only through sentence-transformers inference).
- **Triaged:** 2026-07-17
- **Decision:** reject (VEX `not_affected`, justification `vulnerable_code_not_in_execute_path`)
- **Deployed:** n/a (no code change required; decision recorded here)
- **Residual risk:** the fixed releases live on the 5.x line while `sentence-transformers==3.4.1` pins `transformers<5.0.0` — upgrading means a sentence-transformers major bump, which changes the embedding model runtime and therefore requires re-embedding the RAG index (`EMBEDDING_VERSION` bump). Scheduled as an owner-review item (R6) to be executed with the R8 retrain window. Compensating posture until then: model name pinned in code, no dynamic model loading, no `trust_remote_code`.
- **Owner:** Renan Augusto Macena
- **Reference:** https://osv.dev/vulnerability/PYSEC-2026-2289 (and sibling ids above)
