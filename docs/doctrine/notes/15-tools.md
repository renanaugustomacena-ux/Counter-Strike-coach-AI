# Cluster 15 — tools (root + Programma)

Scope: all scripts under `tools/` (repo root, incl. `fuzz/` and the `.js` file), all scripts under `Programma_CS2_RENAN/tools/`, plus `docs/tooling/generate_zh_pdfs.py`. Read 2026-08-28.

## Files read

- [x] tools/headless_validator.py

## Tool inventory

### tools/headless_validator.py (2914 lines)
Read-only regression gate (~15-20s, no GUI). Imports ~290 production modules across 26 phases, exit 0 PASS / 1 FAIL (warnings allowed). Not importable — raises ImportError unless `__main__` (headless_validator.py:69-72). Detects optional deps (kivy, ncps+hflayers for RAP) and downgrades those checks to warnings (:50-54, :2049). Enforces: METADATA_DIM==25, INPUT_DIM==METADATA_DIM, OUTPUT_DIM==10, NUM_COACHING_CONCEPTS==16, HIDDEN_DIM==128, RAP_POSITION_SCALE==500.0; 19 expected DB tables; checkpoint-name map (jepa→jepa_brain etc. :1315-1330); TRAINING_FEATURES == FeatureExtractor.get_feature_names(); integrity-manifest hash sampling with CRLF→LF normalization (:2268); security scans (torch.load must pass weights_only=True :2289, no subprocess shell=True, no eval/exec, no bare except, no hardcoded secrets); design-token freshness via subprocess `gen_design_tokens.py --check` and `--web --check` (:2777-2821). Cites R4 MED (a formerly no-op drive-letter check, fixed :993-999) and F-0005 (qss template contract :1743-1749). Phase 19 does not exist — numbering jumps 18→20 (:2194).

## The validation gate

## Knowledge-mining pipeline

## Suspicious findings

<!-- END -->
