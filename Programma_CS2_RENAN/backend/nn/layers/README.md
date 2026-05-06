# `backend/nn/layers/` — Reusable neural building blocks

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** `Programma_CS2_RENAN/backend/nn/layers/`
> **Skill:** `/ml-check`

## Purpose

This package owns the small, reusable `nn.Module` building blocks that more than one model in the project depends on. Anything that is unique to a single model architecture stays inside that model's package — only blocks with multiple consumers get promoted here.

## File inventory

| File | Purpose | Key Exports |
|------|---------|-------------|
| `__init__.py` | Package marker. | — |
| `superposition.py` | `SuperpositionLayer` — context-gated linear layer with L1 sparsity regularisation, gate-observability hooks (`get_gate_statistics()`, `get_gate_activations()`), and tracing controls. | `SuperpositionLayer` |

## `SuperpositionLayer` in one paragraph

A standard linear projection wrapped in a learnable, context-conditioned gate. The gate output is L1-regularised so the layer learns to keep most of its capacity inactive on a given input, only "lighting up" the subspace relevant to the current state. Used by the RAP Coach Strategy layer to combine multiple expert sub-policies under a single shared parameterisation. Provides observability hooks so the trainer can log gate sparsity per step.

## Why this directory exists

Before the G-06 cleanup, the project briefly had two parallel implementations of the superposition mechanism (one in `backend/nn/advanced/superposition_net.py`, one inline in the RAP model). Both diverged. G-06 consolidated the canonical implementation here. There must remain exactly one `SuperpositionLayer` definition in the entire codebase — see the warning in `backend/nn/advanced/README.md`.

## Adding a new layer

A block belongs here only when it is:

1. **Reused by ≥ 2 models.** A block used by a single model lives in that model's package.
2. **Stateless w.r.t. training/inference mode** beyond the standard `model.eval()` switch — no global registries, no module-level mutable state.
3. **Documented in this README.** Update the file inventory table and add a one-paragraph summary.

## Do not

- Do **not** duplicate `SuperpositionLayer`. There is one canonical implementation.
- Do **not** add training-side state (optimizer, scheduler, EMA) to a module in this package.
- Do **not** put feature-engineering logic here. Feature extraction is owned by `backend/processing/feature_engineering/`.

## Related

- RAP Coach Strategy consumer: `backend/nn/experimental/rap_coach/strategy.py`
- Empty-stub history: `backend/nn/advanced/README.md` (G-06 cleanup notes)
- Feature dimension: `METADATA_DIM = 25` from `backend/processing/feature_engineering/vectorizer.py`
