# `backend/nn/experimental/` — Experimental neural-network sandbox

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** `Programma_CS2_RENAN/backend/nn/experimental/`
> **Status:** Active sandbox — code here is gated behind feature flags and is **not** loaded by the default coaching pipeline.

## Purpose

This package is the staging area for neural-network architectures that are not yet ready for the production coaching pipeline. Code here is:

- **Gated by feature flags** (e.g. `USE_RAP_MODEL=True`).
- **Importable but inert** unless the corresponding flag is set.
- **Not** a hard runtime dependency of `coaching_service.py` — the service degrades to traditional / RAG modes when experimental components fail.

If a module in here graduates to production-ready, it moves to a non-experimental location (typically `backend/nn/<domain>/`) and the experimental sub-package is updated to remove or stub the original.

## Layout

```
experimental/
├── __init__.py
└── rap_coach/        # RAP Coach (Reasoning + Acting + Pedagogy) — see rap_coach/README.md
```

## Sub-packages

| Sub-package | Status | Flag | Description |
|-------------|--------|------|-------------|
| `rap_coach/` | Experimental | `USE_RAP_MODEL=True` | 7-layer multi-head policy net (perception, memory, strategy, pedagogy, communication, etc.). Uses `ncps` LTC cells with the RAP-LTC-FIX shape patch in `memory.py`. |

See `rap_coach/README.md` for the full RAP architecture.

## Why "experimental" is its own package

Keeping experimental code in a clearly-marked sub-package buys three things:

1. **Reviewability.** A reviewer can immediately tell whether a change touches production or sandbox code by looking at the import path.
2. **Test isolation.** CI pytest can include or exclude experimental tests based on a path filter without changing every file.
3. **Safe deletion.** When an experiment is abandoned, the entire sub-package can be removed in one commit without grep-and-replace risk across the rest of `nn/`.

## Adding a new experimental architecture

1. Create `experimental/<your_module>/` with `__init__.py`.
2. Add a feature flag in `core/config.py` defaults (default `False`).
3. Wire the flag check at the orchestrator boundary in `training_orchestrator.py`. **Do not** import experimental code unconditionally elsewhere.
4. Provide a README that documents: purpose, flag name, dependencies, training entry point, and graduation criteria.
5. Add a smoke test that asserts the flag gate raises when `False`.

## Do not

- Do **not** import from `experimental/` in `coaching_service.py`, `correction_engine.py`, or any path that runs in the default coaching mode.
- Do **not** ship a flag default of `True` for experimental code without explicit owner approval.
- Do **not** rely on experimental modules in PyInstaller frozen builds without a fallback path.

## Related

- RAP Coach details: `experimental/rap_coach/README.md`
- Production NN sub-packages: `backend/nn/README.md`
- Feature-flag handling: `core/config.py:get_setting()`
- Orchestrator flag gate: `backend/nn/training_orchestrator.py:69-73`
