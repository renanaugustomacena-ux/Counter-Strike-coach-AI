# Campaign Risk Register (live)

| R# | Risk | Mitigation hook | Status |
|---|---|---|---|
| R1 | Context compaction loses reading nuance | Dossiers + ledger committed same-batch; post-compaction re-orientation from dossiers only | active |
| R2 | Fix waves regress behavior | Full gate per wave; regression test in same commit as each P0/P1 fix; both CI legs green before next wave | active |
| R3 | Windows-local green, Linux CI red (Qt effects, timeout plugin, paths) | Ubuntu leg is deploy truth; S3 effect-sweep pre-empts the no-QGraphicsEffect rule | active |
| R4 | Recon-vs-clone contradiction on tracked binaries (.venv/DBs reported committed; git ls-files shows none) | W5 preflight inventory is authoritative; nothing deleted on disk | active |
| R5 | Baseline already red (manifest verify FAILS: changed/new files + phantom main.py) | BASELINE.md captured at R0; F-0001 logged; isolated resync commit opens W1 | active |
| R6 | Finding volume (~154.6k LOC) overwhelms campaign | P3 tooling-only; P2 batched; CP0 user triage prunes scope | active |
| R7 | Manifest drift during fix waves (hashed set includes hot files) | Wave checklist: touched file ∈ manifest set → regen manifest same commit; --verify-only in backend gate | active |
| R8 | Sweep false positives contaminate findings; T-DIAG hangs or dirties DBs | Sweeps are pointers-only, per-candidate re-verification; T-DIAG bounded timeout against backed-up DB state | active |
