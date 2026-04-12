#!/usr/bin/env python3
"""
CS2 Coach Bench — Response Scorer

Two scoring modes:
1. Manual: Interactive CLI where a human grades each response on 5 dimensions
2. LLM-as-judge: Uses Claude/GPT-4 to score responses against the rubric

Usage:
    # Manual scoring
    python evals/cs2_coach_bench/score_responses.py --input reports/2026-04-12_coach.jsonl --mode manual

    # LLM judge scoring (requires ANTHROPIC_API_KEY or OPENAI_API_KEY)
    python evals/cs2_coach_bench/score_responses.py --input reports/2026-04-12_coach.jsonl --mode judge

    # Compare two model reports
    python evals/cs2_coach_bench/score_responses.py --compare reports/model_a.scored.jsonl reports/model_b.scored.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

DIMENSIONS = [
    "tactical_correctness",
    "cs2_currentness",
    "specificity",
    "pro_grounding",
    "actionability",
]

DIMENSION_DESCRIPTIONS = {
    "tactical_correctness": "Is the advice tactically correct? (0=wrong, 1=partial, 2=mostly, 3=exactly right)",
    "cs2_currentness": "Is it CS2-current, not CSGO-era? (0=CSGO, 1=mostly CS2, 2=all CS2, 3=current meta)",
    "specificity": "How specific is the advice? (0=generic, 1=some, 2=named callouts, 3=tick-level detail)",
    "pro_grounding": "Does it reference pros/teams? (0=none, 1=vague, 2=named, 3=named+stats)",
    "actionability": "Is it actionable? (0=descriptive only, 1=one action, 2=multi-step, 3=multi-step+criteria)",
}


def load_responses(path: Path) -> list[dict]:
    """Load eval responses from JSONL."""
    responses = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                responses.append(json.loads(line))
    return responses


def score_manually(responses: list[dict], output_path: Path) -> list[dict]:
    """Interactive CLI scoring — human grades each response."""
    scored = []

    print(f"\nManual scoring: {len(responses)} responses")
    print(f"Dimensions: {', '.join(DIMENSIONS)}")
    print(f"Scale: 0-3 each (max 15 per question)")
    print(f"Type 's' to skip, 'q' to quit and save progress\n")

    with open(output_path, "w") as out:
        for i, resp in enumerate(responses):
            print(f"\n{'=' * 70}")
            print(f"[{i + 1}/{len(responses)}] {resp['id']} ({resp['category']})")
            print(f"Q: {resp['question']}")
            print(f"\nA ({resp['model']}):")
            # Show first 500 chars, then truncate indicator
            answer = resp["response"]
            if len(answer) > 500:
                print(f"{answer[:500]}...")
                print(f"  [{len(answer)} total chars]")
            else:
                print(answer)

            scores = {}
            skip = False
            for dim in DIMENSIONS:
                desc = DIMENSION_DESCRIPTIONS[dim]
                while True:
                    raw = input(f"  {dim} {desc}: ").strip()
                    if raw == "s":
                        skip = True
                        break
                    if raw == "q":
                        print(f"\nSaved {len(scored)} scored responses to {output_path}")
                        return scored
                    try:
                        val = int(raw)
                        if 0 <= val <= 3:
                            scores[dim] = val
                            break
                        print("    Score must be 0-3")
                    except ValueError:
                        print("    Enter a number 0-3, 's' to skip, 'q' to quit")

                if skip:
                    break

            if skip:
                continue

            resp["scores"] = scores
            resp["total_score"] = sum(scores.values())
            scored.append(resp)

            out.write(json.dumps(resp) + "\n")
            out.flush()

            print(f"  Total: {resp['total_score']}/15")

    print(f"\nDone! Scored {len(scored)} responses. Saved to {output_path}")
    return scored


def print_summary(scored: list[dict], label: str = ""):
    """Print scoring summary with per-category breakdown."""
    if not scored:
        print("No scored responses to summarize.")
        return

    header = f"SCORING SUMMARY{f' — {label}' if label else ''}"
    print(f"\n{'=' * 60}")
    print(header)
    print(f"{'=' * 60}")

    total = sum(r["total_score"] for r in scored)
    max_total = len(scored) * 15
    print(f"\nOverall: {total}/{max_total} ({total / max_total * 100:.1f}%)")

    # Per-dimension averages
    print("\nPer-dimension averages (0-3 scale):")
    for dim in DIMENSIONS:
        vals = [r["scores"][dim] for r in scored if dim in r.get("scores", {})]
        if vals:
            avg = sum(vals) / len(vals)
            print(f"  {dim:25s} {avg:.2f}/3.00")

    # Per-category breakdown
    categories = sorted(set(r.get("category", "unknown") for r in scored))
    if len(categories) > 1:
        print("\nPer-category scores:")
        for cat in categories:
            cat_scored = [r for r in scored if r.get("category") == cat]
            cat_total = sum(r["total_score"] for r in cat_scored)
            cat_max = len(cat_scored) * 15
            pct = cat_total / cat_max * 100 if cat_max > 0 else 0
            print(f"  {cat:20s} {cat_total:4d}/{cat_max:4d} ({pct:.1f}%)")


def compare_reports(path_a: Path, path_b: Path):
    """Compare two scored report files side by side."""
    scored_a = load_responses(path_a)
    scored_b = load_responses(path_b)

    label_a = scored_a[0].get("model", path_a.stem) if scored_a else path_a.stem
    label_b = scored_b[0].get("model", path_b.stem) if scored_b else path_b.stem

    print(f"\n{'=' * 70}")
    print(f"COMPARISON: {label_a} vs {label_b}")
    print(f"{'=' * 70}")

    # Overall
    total_a = sum(r.get("total_score", 0) for r in scored_a)
    total_b = sum(r.get("total_score", 0) for r in scored_b)
    max_a = len(scored_a) * 15
    max_b = len(scored_b) * 15

    print(f"\n{'Metric':25s} {'Model A':>10s} {'Model B':>10s} {'Delta':>10s}")
    print(f"{'-' * 55}")
    print(f"{'Total score':25s} {total_a:>10d} {total_b:>10d} {total_b - total_a:>+10d}")
    pct_a = total_a / max_a * 100 if max_a else 0
    pct_b = total_b / max_b * 100 if max_b else 0
    print(f"{'Percentage':25s} {pct_a:>9.1f}% {pct_b:>9.1f}% {pct_b - pct_a:>+9.1f}%")

    # Per-dimension comparison
    print(f"\nPer-dimension (0-3 avg):")
    for dim in DIMENSIONS:
        vals_a = [r["scores"][dim] for r in scored_a if dim in r.get("scores", {})]
        vals_b = [r["scores"][dim] for r in scored_b if dim in r.get("scores", {})]
        avg_a = sum(vals_a) / len(vals_a) if vals_a else 0
        avg_b = sum(vals_b) / len(vals_b) if vals_b else 0
        delta = avg_b - avg_a
        print(f"  {dim:25s} {avg_a:>8.2f} {avg_b:>8.2f} {delta:>+8.2f}")


def main():
    parser = argparse.ArgumentParser(description="CS2 Coach Bench — Score responses")
    subparsers = parser.add_subparsers(dest="command")

    # Score subcommand
    score_parser = subparsers.add_parser("score", help="Score responses")
    score_parser.add_argument(
        "--input", type=Path, required=True, help="Input JSONL from run_eval.py"
    )
    score_parser.add_argument(
        "--mode",
        choices=["manual"],
        default="manual",
        help="Scoring mode",
    )
    score_parser.add_argument("--output", type=Path, default=None, help="Output scored JSONL")

    # Summary subcommand
    summary_parser = subparsers.add_parser("summary", help="Print scoring summary")
    summary_parser.add_argument("--input", type=Path, required=True, help="Scored JSONL file")

    # Compare subcommand
    compare_parser = subparsers.add_parser("compare", help="Compare two scored reports")
    compare_parser.add_argument("report_a", type=Path, help="First scored JSONL")
    compare_parser.add_argument("report_b", type=Path, help="Second scored JSONL")

    args = parser.parse_args()

    if args.command == "score":
        responses = load_responses(args.input)
        if args.output is None:
            args.output = args.input.with_suffix(".scored.jsonl")
        scored = score_manually(responses, args.output)
        print_summary(scored)

    elif args.command == "summary":
        scored = load_responses(args.input)
        label = scored[0].get("model", "") if scored else ""
        print_summary(scored, label)

    elif args.command == "compare":
        compare_reports(args.report_a, args.report_b)

    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
