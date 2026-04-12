#!/usr/bin/env python3
"""
CS2 Coach Bench — Eval Runner

Runs the 200-question benchmark against a model backend and saves responses
with latency metrics.

Usage:
    # Full coaching pipeline (RAG + Experience Bank + LLM)
    python evals/cs2_coach_bench/run_eval.py --model coach

    # Raw LLM only (no RAG, isolates model knowledge)
    python evals/cs2_coach_bench/run_eval.py --model ollama:llama3.1:8b

    # Limit to N questions (for quick tests)
    python evals/cs2_coach_bench/run_eval.py --model coach --limit 10

    # Filter by category
    python evals/cs2_coach_bench/run_eval.py --model coach --category map_tactics
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

QUESTIONS_FILE = Path(__file__).parent / "questions.jsonl"
REPORTS_DIR = Path(__file__).parent / "reports"


def load_questions(
    path: Path = QUESTIONS_FILE,
    category: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Load questions from JSONL, optionally filtering by category."""
    questions = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            q = json.loads(line)
            if category and q.get("category") != category:
                continue
            questions.append(q)
            if limit and len(questions) >= limit:
                break
    return questions


def create_coach_backend():
    """Create the full coaching pipeline backend (RAG + Experience Bank + LLM)."""
    from Programma_CS2_RENAN.backend.services.coaching_dialogue import CoachingDialogueEngine
    from Programma_CS2_RENAN.backend.storage.database import init_database

    init_database()
    engine = CoachingDialogueEngine()
    engine.start_session(player_name="eval_player")
    return engine


def create_ollama_backend(model_name: str):
    """Create a raw Ollama LLM backend (no RAG, no experience bank)."""
    from Programma_CS2_RENAN.backend.services.llm_service import LLMService

    return LLMService(model=model_name)


CS2_SYSTEM_PROMPT = (
    "You are an expert Counter-Strike 2 tactical coach. "
    "Answer questions about CS2 tactics, economy, mechanics, professional "
    "players, and competitive play. Be specific, actionable, and accurate. "
    "Reference professional players and teams when relevant. "
    "Only discuss CS2 (2023+), not CSGO."
)


def query_model(backend, question: str, model_type: str) -> tuple[str, float]:
    """Send a question to the model and return (response, latency_ms)."""
    start = time.monotonic()

    if model_type == "coach":
        response = backend.respond(question)
    elif model_type.startswith("ollama:"):
        response = backend.chat(
            messages=[{"role": "user", "content": question}],
            system_prompt=CS2_SYSTEM_PROMPT,
        )
    else:
        response = f"[ERROR] Unknown model type: {model_type}"

    latency_ms = (time.monotonic() - start) * 1000
    return response, latency_ms


def run_eval(
    model_type: str,
    output_path: Path,
    category: str | None = None,
    limit: int | None = None,
) -> dict:
    """Run the full evaluation and save results."""
    questions = load_questions(category=category, limit=limit)
    if not questions:
        print("ERROR: No questions loaded")
        return {"error": "no questions"}

    print(f"Loaded {len(questions)} questions")
    print(f"Model: {model_type}")
    print(f"Output: {output_path}")
    print()

    # Create backend
    if model_type == "coach":
        print("Initializing coaching pipeline (RAG + Experience Bank + LLM)...")
        backend = create_coach_backend()
    elif model_type.startswith("ollama:"):
        ollama_model = model_type.split(":", 1)[1]
        print(f"Initializing Ollama with model: {ollama_model}")
        backend = create_ollama_backend(ollama_model)
    else:
        print(f"ERROR: Unknown model type '{model_type}'")
        print("Supported: 'coach', 'ollama:<model_name>'")
        return {"error": f"unknown model: {model_type}"}

    # Run questions
    results = []
    total_latency = 0
    errors = 0

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as out:
        for i, q in enumerate(questions):
            qid = q["id"]
            question = q["question"]

            try:
                response, latency_ms = query_model(backend, question, model_type)
            except Exception as e:
                response = f"[ERROR] {e}"
                latency_ms = 0
                errors += 1

            result = {
                "id": qid,
                "category": q.get("category", "unknown"),
                "difficulty": q.get("difficulty", "unknown"),
                "model": model_type,
                "question": question,
                "response": response,
                "latency_ms": round(latency_ms, 1),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            results.append(result)
            total_latency += latency_ms

            out.write(json.dumps(result) + "\n")
            out.flush()

            # Progress
            status = "OK" if not response.startswith("[ERROR") else "ERR"
            print(
                f"  [{i + 1}/{len(questions)}] {qid:10s} {status} "
                f"({latency_ms:.0f}ms, {len(response)} chars)"
            )

    # Summary
    avg_latency = total_latency / len(questions) if questions else 0
    summary = {
        "model": model_type,
        "total_questions": len(questions),
        "errors": errors,
        "avg_latency_ms": round(avg_latency, 1),
        "total_latency_s": round(total_latency / 1000, 1),
        "output_file": str(output_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    print(f"\n{'=' * 60}")
    print(f"EVAL COMPLETE: {len(questions)} questions, {errors} errors")
    print(f"Avg latency: {avg_latency:.0f}ms")
    print(f"Total time: {total_latency / 1000:.1f}s")
    print(f"Output: {output_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="CS2 Coach Bench — run eval against a model backend"
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Model backend: 'coach' (full pipeline) or 'ollama:<model>' (raw LLM)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSONL path (default: reports/<date>_<model>.jsonl)",
    )
    parser.add_argument(
        "--category",
        choices=["map_tactics", "economy", "mid_round", "pro_knowledge", "mechanics"],
        default=None,
        help="Filter to a single category",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit to N questions (for quick tests)",
    )
    args = parser.parse_args()

    if args.output is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
        model_slug = args.model.replace(":", "_").replace("/", "_")
        args.output = REPORTS_DIR / f"{date_str}_{model_slug}.jsonl"

    summary = run_eval(
        model_type=args.model,
        output_path=args.output,
        category=args.category,
        limit=args.limit,
    )

    return 0 if summary.get("errors", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
