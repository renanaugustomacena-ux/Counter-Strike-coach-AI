# Coach Quality Roadmap

> **Goal:** make the Macena CS2 Coach the world's best AI on its narrow domain — better than GPT-5 / Gemini / Claude on CS2-specific questions, with the long-term ambition that scope.gg, ESL, FACEIT, or Valve itself would want to integrate or acquire it.

This document has two parts. **Part 1** is the original strategic plan, kept verbatim as it was first spoken in conversation. **Part 2** is the expanded technical depth — grounded in the actual repo state, with concrete commands, hyperparameters, dataset math, and execution sequencing.

---

# Part 1 — The Original Plan (verbatim)

## The honest reality

A 8B general LLM with RAG over 151 entries **will not** outclass GPT-5/Gemini/Claude on raw CS2 knowledge — those models have ingested the entire CS2 internet. What we *can* do is win on three vectors where general LLMs structurally cannot compete:

1. **Demo-grounded specifics.** Frontier LLMs have never seen *your* tick data, *your* round outcomes, *your* opening duels. We have 38 pro demos already parsed into 70M ticks. That is irreplaceable context.
2. **Curated, retrieval-friendly corpus.** Frontier LLMs know CS2 broadly but their knowledge is unstructured and contaminated with CS:GO-era misinformation. A clean, current, S4-aligned, professionally-structured book beats them on retrieval precision.
3. **Player-specific feedback loop.** When (eventually) the user has their own demos, the coach can give advice grounded in *that* player's actual habits. No frontier model can do that.

> **Important caveat about "train more on the same demos":** Re-running training over the same 38 demos does NOT improve quality past 2-3 epochs — it just overfits. Quality gains come from (a) **more diverse data**, (b) **better targets/labels**, (c) **better architectures**, or (d) **fine-tuning the LLM itself on domain Q&A pairs**. Repetition alone is not progress.

## Where the leverage actually is, ranked by ROI

Reading from the project state in memory (38 demos, JEPA parked, Coach Book v3 just landed, 3,378 experience bank records), here are the realistic wins, cheapest-first:

### Tier 1 — Cheap, big wins (do this week)

| # | Action | Cost | Impact |
|---|---|---|---|
| 1 | **10× the Coach Book** (151 → ~1500 entries). Add map veto theory, anti-strat patterns, role-specific play (entry/lurk/IGL/AWP/support), economy decision trees, every common scenario. | Time only | Massive — most queries hit RAG before LLM |
| 2 | **Mine more from existing 38 demos.** We already extracted 3,378 experience records. The same demos can yield: opening duel patterns by map, economy decision outcomes, post-plant survival rates, utility ROI per spot. | Days | Big — adds quantitative grounding |
| 3 | **Ingest more pro demos.** 38 → 200+. HLTV match pages have demo links. Same pipeline, more data. The single biggest cheap win for ML quality. | Bandwidth + time | Massive |

### Tier 2 — Medium effort (weeks)

| # | Action | Cost | Impact |
|---|---|---|---|
| 4 | **Run JEPA Phase F pretraining** (already unblocked from data curation). Trains a CS2-specific encoder. Gives the coach a learned representation of game states no general LLM has. | GPU hours | Medium-large for downstream tasks |
| 5 | **Better RAG retrieval** — re-rank with a CS2-tuned cross-encoder, query expansion ("Anubis A defense" → also retrieves "heaven hold", "ticket hold", etc.). | Days | Big — improves answer relevance |
| 6 | **Add HLTV pro stats grounding.** When the user asks "how does s1mple play Mirage?" the coach should pull actual numbers from `hltv_metadata.db`, not improvise. | Days | Medium-big |

### Tier 3 — Hard, expensive, but where we start *winning* (months)

| # | Action | Cost | Impact |
|---|---|---|---|
| 7 | **LoRA fine-tune Llama 3.1 8B on a CS2 Q&A dataset.** Generate 5,000-20,000 (question, answer) pairs from the book + experience bank + pro stats + demo events. Fine-tune. This is the step that actually starts outperforming frontier models on the narrow domain. | GPU days, careful dataset curation | Game-changing |
| 8 | **RLHF / DPO loop on user feedback.** Every thumbs-up/down on a chat answer feeds preference data. Periodically re-tune. | Ongoing | Compounding |
| 9 | **Active learning on user demos.** Once the user has demos, mine player-specific patterns and feed them back into the experience bank. | Ongoing | Compounding |

### Tier 4 — The dream tier (quarters)

| # | Action | Cost | Impact |
|---|---|---|---|
| 10 | **CS2-specific reasoning evals.** Build a benchmark of 200 expert-graded CS2 questions. Score Llama 8B vs GPT-4 vs Claude vs your fine-tuned model. Publish. *This* is what gets scope.gg / Valve to notice. | Weeks | Marketing + credibility |
| 11 | **Multimodal: feed the LLM actual radar snapshots from demos.** A coach that can reason about "this exact round at this exact moment" with tick data is a category nobody else has. | Months | Category-defining |

## My recommendation for *this session* and the next few

You asked "is there a way to train more?" The most productive answer is: **don't re-train on the same data, instead expand the data and tune the LLM**.

Concrete proposal — pick one of these as a follow-up session:

**Option A — "Bulk up the Coach Book to 1500 entries"** (no new infrastructure, pure content engineering, biggest immediate quality jump for chat answers).

**Option B — "Run JEPA Phase F pretraining"** (uses what's already built, validates the pipeline end-to-end, gives us a CS2 encoder for downstream work).

**Option C — "Build the LoRA fine-tuning pipeline"** (most ambitious, biggest payoff, requires more setup — generate Q&A dataset, set up training script, GPU time).

**Option D — "Expand the demo corpus"** (download 100+ more pro demos, re-run ingestion, mine again — multiplies everything else).

For *right now*, before you test the chat: I'd say **test the chat first** with what's live (Llama 3.1 8B + run init_knowledge_base for the v3 book). See how it actually performs. That tells us where the weakest link is — retrieval, model, or knowledge — and we attack that next session with one of A/B/C/D.

---

# Part 2 — Technical Depth

## 2.1 Repo state snapshot (verified 2026-04-07/08)

### Training infrastructure that already exists — DO NOT REBUILD

| Component | File | What it does | CLI? |
|---|---|---|---|
| RAP Coach trainer | `Programma_CS2_RENAN/backend/nn/experimental/rap_coach/trainer.py` | 7-layer perception→strategy→value→position with LTC + Hopfield memory. lr=1e-4, AdamW, cosine. Loss weights strategy=1.0, value=0.5, sparsity=1.0, position=1.0, z-penalty=2.0. | No — invoked via `TrainingOrchestrator` |
| JEPA standalone trainer | `Programma_CS2_RENAN/backend/nn/jepa_train.py` | Self-supervised context→target prediction, EMA target encoder, InfoNCE contrastive. Pretrain: 50 epochs, batch 16, lr 1e-4, 8 negatives. Finetune: 30 epochs, lr 1e-3. EMA τ 0.996→1.0. | **Yes**: `python -m Programma_CS2_RENAN.backend.nn.jepa_train --mode {pretrain\|finetune} --model-path <path>` |
| JEPA orchestrator integration | `Programma_CS2_RENAN/backend/nn/jepa_trainer.py` | Same model, called from `TrainingOrchestrator`. | No |
| Win probability trainer | `Programma_CS2_RENAN/backend/nn/win_probability_trainer.py` | 9→32→16→1 sigmoid MLP. 100 epochs, Adam lr 1e-3, early stop patience 10. | No |
| Legacy router | `Programma_CS2_RENAN/backend/nn/train.py` | Detects JEPA vs supervised configs and routes. | Internal |

### Knowledge mining tools that already exist — REUSE FOR DATASET BUILDING

| Component | File | Purpose |
|---|---|---|
| Pro demo / archetype miner | `Programma_CS2_RENAN/backend/knowledge/pro_demo_miner.py` | `auto_populate_from_pro_demos()` — mines archetypes from `ProPlayerStatCard` (star_fragger, sniper, support, entry_opener) |
| Round stats builder | `Programma_CS2_RENAN/backend/processing/round_stats_builder.py` | Aggregates per-round stats: economy, utility, engagements, KAST, opening duels |
| Player knowledge | `Programma_CS2_RENAN/backend/processing/player_knowledge.py` | Role / playstyle classifier |
| Tactical analysis | `Programma_CS2_RENAN/backend/analysis/{belief_model,blind_spots,deception_index,momentum,win_probability,game_tree}.py` | All ready to feed Q&A generation |
| Existing one-shot tools | `tools/populate_round_stats.py`, `tools/repair_kast.py`, `tools/mine_coaching_experience.py` | Idempotent dataset builders — re-runnable on the new corpus |

### What does NOT exist (must be built from scratch)

- ❌ **Any LLM fine-tuning scaffolding.** Zero hits in the codebase for `peft`, `lora`, `transformers`, `bitsandbytes`, `Trainer(`. Chat is prompt-only via Ollama.
- ❌ **Any Q&A / instruction dataset builder.** No `q_and_a.json`, no `instructions/`, no `dataset_builder.py`.
- ❌ **Any CS2-specific eval harness or benchmark.** Tests are unit/integration only. `tests/test_baselines.py` validates numeric model outputs against historical baselines, not coaching quality.
- ❌ **Any RLHF / DPO scaffolding.**
- ❌ **Cloud GPU automation.** No `train_on_runpod.sh`, no Vast.ai launcher.

### Hardware (verified `nvidia-smi`)

- **GPU:** NVIDIA GeForce GTX 1650 Mobile (Max-Q) — 4 GB VRAM
- **CUDA:** 13.0 driver, runtime via `torch==2.5.1+cu121`
- **System:** CPU-side has plenty of RAM and disk; the bottleneck is exclusively VRAM
- **Implication:** local 8B fine-tuning is **not feasible**. See §2.5 for the three documented paths.

## 2.2 Demo corpus reality (verified 2026-04-08)

This was the single biggest discovery while planning.

| Source | Count | Status |
|---|---|---|
| Raw `.dem` files at `/media/renan/New Volume/Counter-Strike-coach-AI/DEMO_PRO_PLAYERS/` | **112 files** (110 unique) | ✅ Present on disk |
| Per-match `.db` files in same tree | **188 files** | ✅ Demos parsed into per-match dbs |
| Aggregated into `database.db::roundstats` | **38 demos** (765 `playermatchstats` rows ≈ 38 × ~20) | ⚠️ Re-aggregation gap |

**The re-aggregation gap is the single biggest unlock for everything in this roadmap.**

~110 demos are sitting on disk, parsed into per-match databases, but only 38 of them have been rolled up into the production aggregated tables. That means every downstream consumer — `roundstats`, `experience bank`, `pro_demo_miner`, RAG knowledge population — is operating on **~35% of the available signal**.

Tournament pedigree of the corpus is excellent and worth recording:
- BLAST Bounty 2026 Season 1 finals (Falcons, ParaVision, Furia, Spirit)
- BLAST Open Rotterdam 2026 (NRG, Furia)
- ESL Pro League Season 19 (Vitality, MOUZ)
- ESL Pro League Season 23 finals (FUT, Astralis, NaVi, Aurora)
- Esports World Cup 2024 (FaZe, FlyQuest, Furia, The Mongolz, G2, NaVi)

All tier-1, all current era, no CSGO contamination.

### Action item: re-aggregation pass

This is the **first concrete action** in the roadmap. Estimated cost: 1-3 hours of compute, no GPU needed.

```bash
# 1. Verify the per-match dbs are all present and openable
python -c "
from pathlib import Path
import sqlite3
root = Path('/media/renan/New Volume/Counter-Strike-coach-AI/DEMO_PRO_PLAYERS')
dbs = list(root.rglob('*.db'))
print(f'found {len(dbs)} per-match dbs')
broken = []
for db in dbs:
    try:
        sqlite3.connect(db).execute('SELECT 1').fetchone()
    except Exception as e:
        broken.append((db, e))
print(f'broken: {len(broken)}')
"

# 2. Re-run roundstats population over all per-match dbs
python tools/populate_round_stats.py --rebuild-all

# 3. Re-mine the experience bank
python tools/mine_coaching_experience.py --rebuild-all

# 4. Re-run knowledge base init (will pick up the v3 book + new pro stats)
python -m Programma_CS2_RENAN.backend.knowledge.init_knowledge_base
```

**Expected outcome (rough):**
- `roundstats` rows: 8,230 → ~24,000 (3× lift)
- `coachingexperience` records: 3,378 → ~10,000 (3× lift)
- `tacticalknowledge` rows: ~150 → ~150 + ~200 newly mined ≈ 350 (book stays the same, mined stats grow)

**This is a free 3× quality multiplier** for everything in Options A and C downstream. Do it first. If `populate_round_stats.py` doesn't have a `--rebuild-all` flag, that flag is the first patch we land.

## 2.3 The eval-first principle

Before fine-tuning anything, we build a CS2-specific evaluation harness. **Without it we cannot tell whether the LoRA fine-tune helped or hurt.** This is non-negotiable.

### What the eval looks like

`evals/cs2_coach_bench/` (new directory):

```
evals/cs2_coach_bench/
├── README.md
├── questions.jsonl              # 200 expert-graded CS2 questions
├── rubric.md                    # scoring rubric (5 dimensions, 0-3 each)
├── run_eval.py                  # invokes a model, scores answers, writes a report
├── score_with_judge.py          # GPT-4 / Claude as a judge with the rubric
└── reports/
    ├── 2026-04-XX_llama31_8b_baseline.md
    ├── 2026-04-XX_llama31_8b_v3book.md
    └── 2026-04-XX_cs2coach_8b_v1.md
```

### Question categories (40 each, 200 total)

1. **Map tactics** — "On Anubis, the T side has lost connector. What is the highest-EV B execute?"
2. **Economy decisions** — "0-3 down, 1750$ each, what's the optimal buy?"
3. **Mid-round adaptation** — "Your A entry just got picked at apartments on Inferno. Your call?"
4. **Pro player knowledge** — "How does m0NESY's positioning on Mirage A compare to ZywOo's?"
5. **CS2-specific mechanics** — "How does the new sub-tick system change pre-fire timing on common angles?"

### Scoring rubric (per question, judged by GPT-4 with deterministic seed)

| Dimension | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **Tactical correctness** | wrong | partially correct | mostly correct | exactly right |
| **CS2-currentness** | uses CSGO-era info | mostly CS2 | all CS2 | references current meta |
| **Specificity** | generic platitudes | some specifics | named callouts | concrete tick-level specifics |
| **Pro grounding** | no references | vague references | named pros/teams | named pros + verifiable stats |
| **Actionability** | descriptive only | one action | multi-step | multi-step + decision criteria |

Max score per question: 15. Total: 3000.

### Baseline measurements (mandatory before any fine-tune)

Run the eval against:
1. Vanilla Llama 3.1 8B (no RAG, no book)
2. Llama 3.1 8B + Coach Book v3 RAG
3. GPT-4o (paid API, one-time benchmark)
4. Claude Opus / Sonnet (paid API, one-time benchmark)
5. Gemini 1.5 / 2.0 Pro (paid API, one-time benchmark)

This tells us **the gap we are trying to close** and **what success looks like**. Without these numbers, "world's best on CS2" is unmeasurable hand-waving.

## 2.4 Option A — Coach Book to 1500 entries

### Current state (post Coach Book v3)

- 151 entries across 8 files in `Programma_CS2_RENAN/backend/knowledge/book/`
- 6 categories: positioning, utility, economy, aim_and_duels, mid_round, retakes_post_plant
- 7 maps × ~18 entries + 25 general

### Target

- **1,500 entries** (10× growth)
- **12 categories** (add 6 new)
- **More depth per (map, category) cell**

### New categories to add

| Category | What it covers | ~Count |
|---|---|---|
| `anti_strat` | Recognizing and countering opponent patterns | 100 |
| `role_play_entry` | Entry fragger principles by map | 80 |
| `role_play_lurk` | Lurker positioning and timing | 80 |
| `role_play_igl` | IGL decision frameworks | 100 |
| `role_play_awp` | AWP positioning, repositioning, info-AWPing | 100 |
| `role_play_support` | Support player utility, trades, sacrifice plays | 80 |
| `map_veto` | Veto theory, opponent map preferences, tilt maps | 60 |
| `clutch_play` | 1vX scenario decision trees | 80 |
| `comms` | Callout standards, info hierarchy, protocol | 50 |
| `mental_game` | Tilt management, momentum, pressure | 50 |

That's 780 new specialized entries, plus another ~570 across the existing 6 categories to thicken (map, category) cells from 3 entries to 8-10. Total target: **~1500**.

### Source mix (rough)

| Source | Share | Method |
|---|---|---|
| Hand-authored (you + me, pair-coaching) | 60% | Same voice and quality bar as Coach Book v3 |
| Mined from per-match dbs (the new 110-demo corpus) | 25% | Existing analysis modules → templated entries |
| Mined from HLTV pro stats (`hltv_metadata.db`) | 15% | `pro_demo_miner.py` extension |

### Quality controls (mandatory checklist per entry)

- [ ] No fabricated stats. Use phrasings like "Pro meta:" or "Tier-1 average:" not made-up percentages.
- [ ] Voice consistency: imperative, second-person, terse, action-oriented.
- [ ] Title is searchable (contains map name + category keyword).
- [ ] `situation` field is a real player query, not abstract framing.
- [ ] `pro_example` is verifiable or labeled as illustrative.
- [ ] Aligned to current CS2 (no CSGO-era callouts, no old map versions).

### Loader changes needed (small)

Extend `_ALLOWED_ENTRY_KEYS` in `Programma_CS2_RENAN/backend/knowledge/rag_knowledge.py:KnowledgePopulator` to optionally accept:

```python
_ALLOWED_ENTRY_KEYS = frozenset((
    "title", "description", "category", "situation", "map_name", "pro_example",
    # New optional fields:
    "tags",         # list[str] — for filtering and re-ranking
    "revision",    # int — content version for A/B testing
    "source_demo", # str — provenance from a specific demo if mined
    "confidence",  # float 0-1 — for soft retrieval weighting
))
```

These fields require either (a) extending `add_knowledge()` to accept them and persist into a JSON column on `TacticalKnowledge`, or (b) keeping them in JSON only and stripping at load (forward-compat — current behavior). **Recommendation: do (a), add a `meta` JSON column.** Small migration, big optionality.

### Embedding cost

1500 × ~600 ms per entry through `sentence-transformers all-MiniLM-L6-v2` ≈ **15 minutes one-time SBERT pass**. Trivial.

## 2.5 Option C — LoRA fine-tuning a CS2 chat model

This is where we actually start beating frontier models on the narrow domain. It is also the hardest stage in the roadmap.

### Stage 0 — Eval harness (PREREQUISITE)

See §2.3. Build the benchmark BEFORE you fine-tune. Measure the baseline. This is non-negotiable.

### Stage 1 — Q&A dataset generation

Target: **15,000-25,000 high-quality (question, answer) pairs**.

Sources and rough yield (assuming the re-aggregation pass in §2.2 has been done):

| Source | Yield method | Pairs |
|---|---|---|
| 1500 Coach Book entries | Templated Q&A (3-5 questions per entry, GPT-4 or Claude as the question generator) | 6,000 |
| Experience bank (~10,000 records post re-aggregation) | "What happened? What was the right call?" framing | 3,000 |
| HLTV pro stats DB | "How does {player} compare to {player} on {map}?" | 2,000 |
| Per-match round narratives (110 demos × ~25 rounds × selected events) | "It is round X, score Y-Z, T side just plant B. What is the post-plant call?" | 4,000-12,000 |
| Hand-authored gold examples | High-quality seeds for harder reasoning | 500 |
| **Total target** | | **15,000-25,000** |

### Stage 2 — Dataset curation

A new module: `Programma_CS2_RENAN/backend/training/dataset_builder/`

```
dataset_builder/
├── __init__.py
├── sources/
│   ├── from_book.py            # walks book/*.json, generates Q&A via LLM
│   ├── from_experience.py      # walks coachingexperience table
│   ├── from_hltv.py            # walks ProPlayerStatCard
│   ├── from_demo_rounds.py     # walks per-match dbs, picks decision moments
│   └── from_seeds.py           # hand-authored gold examples
├── transforms/
│   ├── dedupe.py               # near-dup via MinHash on question
│   ├── length_filter.py        # 8 ≤ q ≤ 200 tokens, 16 ≤ a ≤ 800 tokens
│   ├── quality_filter.py       # GPT-4 grader, drops low-quality pairs
│   └── hard_negatives.py       # adds rejected answers for DPO later
├── splits.py                   # train/val/test stratified by category
└── build.py                    # CLI: python -m ...dataset_builder.build --output dataset/v1
```

Output format (HuggingFace datasets-compatible):

```jsonl
{"id": "book-anubis-positioning-001-q1", "question": "On Anubis, how should CTs hold A site against a fast hit?", "answer": "Heaven hold with one-way smoke...", "source": "book", "category": "positioning", "map": "de_anubis", "split": "train"}
```

### Stage 3 — LoRA training setup

A new directory `Programma_CS2_RENAN/backend/training/finetune/` and a separate requirements file `requirements-finetune.txt`:

```
peft==0.14.0
transformers==4.46.0
bitsandbytes==0.44.1
accelerate==1.1.1
datasets==3.1.0
trl==0.12.0
```

Kept separate from production deps so the chat app remains light.

LoRA config (recommended starting point):

```python
from peft import LoraConfig
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)
```

4-bit quantization via `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_quant_type="nf4")`.

### Stage 4 — Training run

| Hyperparameter | Value | Rationale |
|---|---|---|
| Epochs | 3 | More overfits on small specialized data |
| Per-device batch size | 4 | Memory budget |
| Gradient accumulation | 8 | Effective batch 32 |
| Learning rate | 2e-4 | Standard for LoRA |
| LR scheduler | cosine with 3% warmup | Standard |
| Max seq length | 2048 | Most CS2 Q&As fit |
| Optimizer | paged_adamw_8bit | Memory savings |
| Eval every | 200 steps | On val split |
| Save every | 500 steps | |
| Estimated wall time | 6-12 hours on RTX 4090 24 GB | At 20k pairs |

### Stage 5 — Convert and serve

Convert LoRA adapter → merge into base → quantize to GGUF → register with Ollama:

```bash
# Merge adapter
python -m Programma_CS2_RENAN.backend.training.finetune.merge_adapter \
    --base meta-llama/Meta-Llama-3.1-8B-Instruct \
    --adapter checkpoints/cs2coach-8b-v1 \
    --output merged/cs2coach-8b-v1

# Convert to GGUF (uses llama.cpp's convert_hf_to_gguf.py)
python llama.cpp/convert_hf_to_gguf.py merged/cs2coach-8b-v1 \
    --outfile cs2coach-8b-v1.gguf --outtype q4_K_M

# Register with Ollama
cat > Modelfile <<EOF
FROM ./cs2coach-8b-v1.gguf
PARAMETER temperature 0.6
PARAMETER top_p 0.9
SYSTEM """You are the Macena CS2 Coach. You only answer Counter-Strike 2 questions. Be concrete, terse, and actionable."""
EOF
ollama create cs2coach:8b-v1 -f Modelfile
```

Then update `Programma_CS2_RENAN/backend/services/llm_service.py:25` `DEFAULT_MODEL` to `cs2coach:8b-v1`.

### Stage 6 — Re-eval and decide

Re-run the eval harness from §2.3 against `cs2coach:8b-v1`. Compare to:
- Vanilla Llama 3.1 8B (the baseline)
- Llama 3.1 8B + RAG (the production setup as of v3 book)
- GPT-4 / Claude / Gemini (the frontier reference)

**Ship criterion: cs2coach:8b-v1 must beat (Llama 3.1 8B + RAG) by >25% on the eval, AND beat GPT-4 by at least 5% on the CS2-currentness and pro-grounding dimensions.** If it doesn't, iterate on the dataset before iterating on training.

### Hardware reality and the three paths

The local GPU is a **GTX 1650 Mobile, 4 GB VRAM**. This is below the floor for local 4-bit LoRA on 8B (which wants ~12 GB VRAM minimum). Three documented paths:

#### Path A — Cloud GPU rental (recommended)

| Provider | GPU | Cost/hr | One full run cost (8h) | Notes |
|---|---|---|---|---|
| Vast.ai | RTX 4090 24 GB | $0.30-0.50 | $2.40-4.00 | Cheapest, spot instances possible |
| Runpod | RTX 4090 24 GB | $0.40-0.70 | $3.20-5.60 | Better UX, persistent volumes |
| Runpod | A100 40 GB | $1.00-1.50 | $8.00-12.00 | Faster, larger batches |
| Lambda | A100 40 GB | $1.10 | $8.80 | Easiest setup |
| Modal | A100 40 GB | ~$2.00 | ~$16.00 | Serverless, fastest iteration |

**Recommendation: Runpod RTX 4090 24 GB. ~$5 per training run. Persistent volume for the dataset.**

Workflow:
1. Build the dataset locally (CPU work).
2. `rsync` it to Runpod persistent storage (~500 MB).
3. SSH in, clone the repo, install `requirements-finetune.txt`, run training.
4. `rsync` the LoRA adapter back (~50 MB).
5. Merge + GGUF + Ollama on the local machine.

Total cycle time: ~12 hours for one experiment, ~$5 cost.

#### Path B — Pivot to a smaller base model (local fallback)

If you want to iterate locally without paying for cloud, fine-tune a smaller base model that fits in 4 GB VRAM:

| Model | Params | 4-bit VRAM | Quality vs Llama 3.1 8B |
|---|---|---|---|
| Phi-3-mini-4k-instruct | 3.8B | ~3.5 GB | -25% on general tasks, -15% on narrow specialized |
| Qwen 2.5 3B Instruct | 3.0B | ~2.8 GB | -30% / -20% |
| Llama 3.2 3B Instruct | 3.2B | ~3.0 GB | -25% / -15% |

**Use this for fast iteration cycles.** Validate the dataset, training script, and eval harness at small scale, then re-do the production run on cloud with Llama 3.1 8B.

#### Path C — CPU QLoRA (not recommended)

Technically possible with `bitsandbytes` CPU mode + `accelerate cpu_offload`, but glacially slow — multiple days per epoch. Only worth doing as proof-of-concept.

## 2.6 Option B (JEPA) — deferred but referenced

JEPA pretraining (Phase F) is unblocked from the data curation work. The trainer exists, the CLI works, the dataset is ready. We are NOT executing it in the A+C track because:

- It produces a CS2-specific encoder, not a chat model. The chat path is the user-facing surface where quality is most visible.
- The encoder is most valuable as input to *other* downstream models (RAP, win-prob), not directly to the LLM chat.
- The 3× re-aggregation lift from §2.2 also benefits JEPA — running JEPA AFTER the re-aggregation is a strict Pareto improvement over running it now.

**Recommended sequencing:** run JEPA Phase F *after* the re-aggregation pass and *before* the LoRA fine-tune. The JEPA encoder can later become a feature extractor for an even more demo-grounded chat model in a Tier 4 multimodal version.

## 2.7 Option D restated — re-aggregation, not new demos

The original plan said "expand the demo corpus". After verification, the corpus is already ~110 demos on disk. The action is **not download more**, the action is **re-aggregate the existing 72 demos that are sitting in per-match dbs but not yet in production tables**.

See §2.2 for the action item and commands. This is the **first** thing to do after this roadmap is approved.

## 2.8 Session-by-session execution plan

Rough plan, ~6-9 sessions before we have `cs2coach:8b-v1` shipped.

| # | Session | Goal | Output | Blocking on |
|---|---|---|---|---|
| 1 | Re-aggregation | Run the §2.2 commands. Verify roundstats grows ~3×, experience bank grows ~3×. Patch any bugs surfaced. | Production DB with all 110 demos | — |
| 2 | Smoke test the chat | Run `init_knowledge_base` for v3 book. Launch Qt chat. Hit it with 30 questions. Note where retrieval misses, where the LLM hallucinates, where the answer is great. | A "weak link" report | Session 1 |
| 3 | Eval harness Stage 0 | Build `evals/cs2_coach_bench/`. Author 200 questions (50 in this session, 150 next). Build the rubric, the runner, the judge. | Eval harness skeleton | Session 2 |
| 4 | Eval harness Stage 0 part 2 | Finish 200 questions. Run baselines: vanilla Llama 3.1 8B, Llama+RAG, GPT-4o, Claude, Gemini. Save baseline reports. | Baseline numbers | Session 3 |
| 5 | Coach Book Option A part 1 | Restructure for new categories. Author ~500 entries (highest-priority gaps). | Book at ~650 entries | Session 1 |
| 6 | Coach Book Option A part 2 | Mine ~400 entries from per-match dbs and HLTV stats. Author ~450 hand-written. | Book at ~1500 entries | Session 5 |
| 7 | Dataset builder | Build `dataset_builder/`. Generate ~20k Q&A pairs from book + experience + HLTV + demos. Curate. Split. | `dataset/v1/` ready | Session 6 |
| 8 | LoRA training | Provision Runpod 4090. Push dataset. Train cs2coach-8b-v1. Pull adapter. Merge. Convert. Register. | `cs2coach:8b-v1` in Ollama | Session 7 |
| 9 | Re-eval and ship-decision | Run eval harness against `cs2coach:8b-v1`. Compare deltas. Decide ship or iterate. | Final report, ship/iterate decision | Session 8 |

## 2.9 Risks and what kills this project

| Risk | Likelihood | Mitigation |
|---|---|---|
| **Re-aggregation tools have hidden bugs on the 72 unprocessed demos** | Medium | Session 1 surfaces them; allocate extra time |
| **Dataset quality is too low to fine-tune meaningfully** | Medium-High | Stage 2 quality filter + GPT-4 grading + hand-authored seeds |
| **Cloud GPU costs balloon from iteration** | Low-Medium | Cap budget per session at $20; use Runpod spot instances |
| **Llama 3.1 8B is the wrong base model** | Low | Eval baseline against Qwen 2.5 7B, Phi-3-medium too |
| **Eval harness biased toward our content** | Medium | Use questions written BEFORE the book is expanded; have a separate "blind" question set |
| **We overfit to the eval and don't generalize** | Medium | Hold out 50 questions never seen during dataset building or grading |
| **Re-aggregation reveals demo corruption / parser bugs** | Low | demoparser2 is well-tested; if found, file upstream issue |
| **The user loses interest before Session 9** | Low | Each session ships a tangible artifact: better data, more book, working eval, etc. |
| **CSGO/CS2 mechanics drift mid-project** | Low | Roadmap explicitly aligns to current Premier season; re-validate book yearly |

## 2.10 Definition of "done"

The Macena CS2 Coach is the world's best on CS2 when **all** of these are true:

1. **Quantitative**: `cs2coach:8b-v1` beats vanilla Llama 3.1 8B by >25% on `cs2_coach_bench` total score.
2. **Quantitative**: `cs2coach:8b-v1` beats GPT-4o by >5% on the **CS2-currentness** and **pro-grounding** rubric dimensions.
3. **Quantitative**: `cs2coach:8b-v1` is within 10% of GPT-4o on the **tactical correctness** dimension and exceeds it on **specificity**.
4. **Qualitative**: 10 expert CS2 players, blind-evaluated on 30 questions each, prefer `cs2coach:8b-v1` answers over GPT-4o answers >60% of the time on CS2-specific questions.
5. **Operational**: the model runs locally on consumer hardware via Ollama, in <2s per response.
6. **Reproducible**: the dataset, training script, and eval harness are all in-repo with seeded RNGs and deterministic outputs.
7. **Visible**: the eval results are published as a markdown report in `docs/`, with frontier-model comparisons. This is what gets industry attention.

When all 7 are true, scope.gg, ESL, FACEIT, or any tier-1 CS2 product can integrate the model and immediately add real value to their users — and we have the receipts to prove it.

---

## Next session — first action

Run the §2.2 re-aggregation pass, verify the row counts triple, then smoke-test the chat with Llama 3.1 8B + the v3 book against ~30 questions. Note where retrieval misses and where the LLM hallucinates. That report becomes the starting point for Session 3 (the eval harness).

Everything in this roadmap is downstream of those two actions.
