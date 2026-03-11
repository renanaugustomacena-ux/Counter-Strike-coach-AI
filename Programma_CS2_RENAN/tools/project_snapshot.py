#!/usr/bin/env python3
"""Compact project state snapshot — all key facts in <60 lines of output."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from _infra import path_stabilize

PROJECT_ROOT, SOURCE_ROOT = path_stabilize()

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.project_snapshot")

VERSION = "1.0"

# ─── Packages to probe ────────────────────────────────────────────────────────
CRITICAL_DEPS = [
    "sqlmodel",
    "kivymd",
    "demoparser2",
    "ncps",
    "numpy",
    "psutil",
    "scikit-learn",
    "torch",
]

KEY_TABLES = [
    "playermatchstats",
    "roundstats",
    "coachinginsight",
    "coachingexperience",
    "playerprofile",
]


# ─── Safe wrapper ─────────────────────────────────────────────────────────────


def _safe(fn, fallback=None):
    try:
        return fn()
    except Exception as e:
        logger.warning("%s failed: %s", fn.__name__, e)
        return fallback if fallback is not None else {"error": str(e)}


# ─── Collectors ───────────────────────────────────────────────────────────────


def collect_git():
    def _run(cmd):
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
        )
        return r.stdout.strip() if r.returncode == 0 else ""

    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if not branch:
        return {"error": "git unavailable"}

    status_raw = _run(["git", "status", "--porcelain"])
    lines = [l for l in status_raw.splitlines() if l.strip()] if status_raw else []
    modified = sum(1 for l in lines if not l.startswith("?"))
    untracked = sum(1 for l in lines if l.startswith("?"))

    log_line = _run(["git", "log", "-1", "--format=%h %s"])
    commit_hash = log_line.split(" ", 1)[0] if log_line else "?"
    commit_msg = log_line.split(" ", 1)[1] if " " in log_line else ""
    if len(commit_msg) > 40:
        commit_msg = commit_msg[:37] + "..."

    dirty = modified > 0 or untracked > 0
    return {
        "branch": branch,
        "modified": modified,
        "untracked": untracked,
        "commit": commit_hash,
        "msg": commit_msg,
        "dirty": dirty,
    }


def collect_runtime():
    py = platform.python_version()
    plat = sys.platform
    data = {"python": py, "platform": plat, "torch": None, "cuda": None}
    try:
        import torch

        data["torch"] = torch.__version__
        if torch.cuda.is_available():
            data["cuda"] = torch.cuda.get_device_name(0)
        else:
            data["cuda"] = "cpu"
    except ImportError:
        data["torch"] = "not_installed"
        data["cuda"] = "n/a"
    return data


def collect_db():
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy import text

    from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database

    init_database()
    db = get_db_manager()

    result = {
        "connected": False,
        "wal": False,
        "timeout": None,
        "counts": {},
        "ingest": {},
        "coach": {},
    }

    with db.get_session() as s:
        check = s.exec(text("SELECT 1")).first()
        result["connected"] = check is not None and check[0] == 1

        wal = s.exec(text("PRAGMA journal_mode")).first()
        result["wal"] = wal is not None and wal[0].lower() == "wal"

        bt = s.exec(text("PRAGMA busy_timeout")).first()
        result["timeout"] = bt[0] if bt else None

    # Table counts
    insp = sa_inspect(db.engine)
    all_tables = insp.get_table_names()

    allowed = set(all_tables)
    with db.get_session() as s:
        for t in KEY_TABLES:
            if t in allowed:
                row = s.exec(text(f"SELECT COUNT(*) FROM [{t}]")).first()
                result["counts"][t] = row[0] if row else 0
            else:
                result["counts"][t] = -1

        # Ingestion status
        if "ingestiontask" in all_tables:
            rows = s.exec(text("SELECT status, COUNT(*) FROM ingestiontask GROUP BY status")).all()
            ingest = {}
            for status, cnt in rows:
                key = status.lower() if status else "unknown"
                ingest[key] = cnt
            result["ingest"] = ingest

        # Coach state
        if "coachstate" in all_tables:
            row = s.exec(text("SELECT * FROM coachstate LIMIT 1")).first()
            if row:
                keys = row._fields if hasattr(row, "_fields") else row.keys()
                coach = dict(zip(keys, row))
                result["coach"] = {
                    "status": str(coach.get("status", "?")),
                    "heartbeat": str(coach.get("heartbeat", "")),
                    "epoch": coach.get("current_epoch", 0),
                    "loss": coach.get("train_loss"),
                }

    return result


def collect_checkpoints():
    from Programma_CS2_RENAN.core.config import MODELS_DIR

    models_path = Path(MODELS_DIR)
    ckpts = []
    if models_path.exists():
        for ext in ("**/*.pt", "**/*.pth"):
            for f in models_path.glob(ext):
                stat = f.stat()
                age_days = (time.time() - stat.st_mtime) / 86400
                rel = f.relative_to(models_path)
                ckpts.append(
                    {
                        "name": str(rel).replace("\\", "/"),
                        "mb": round(stat.st_size / (1024 * 1024), 1),
                        "age_days": round(age_days, 1),
                    }
                )
    return {"files": ckpts, "total": len(ckpts)}


def collect_manifest():
    manifest_path = SOURCE_ROOT / "core" / "integrity_manifest.json"
    if not manifest_path.exists():
        return {"error": "manifest not found"}

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    hashes = manifest.get("hashes", {})
    tracked = len(hashes)
    match_count = 0
    drift = []

    for rel_path, expected_hash in hashes.items():
        full = PROJECT_ROOT / rel_path
        if not full.exists():
            drift.append(rel_path.split("/")[-1])
            continue
        sha = hashlib.sha256(full.read_bytes()).hexdigest()
        if sha == expected_hash:
            match_count += 1
        else:
            drift.append(rel_path.split("/")[-1])

    return {"tracked": tracked, "match": match_count, "drift": drift}


def collect_deps():
    result = {}
    for pkg in CRITICAL_DEPS:
        try:
            result[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            result[pkg] = "not_installed"
    return result


def collect_config():
    from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
    from Programma_CS2_RENAN.core.config import (
        CS2_PLAYER_NAME,
        DATABASE_URL,
        MATCH_DATA_PATH,
        MODELS_DIR,
        SETTINGS_PATH,
    )

    # Match data stats
    match_path = Path(MATCH_DATA_PATH)
    match_count = 0
    match_bytes = 0
    if match_path.exists():
        for f in match_path.iterdir():
            if f.name.startswith("match_") and f.name.endswith(".db"):
                match_count += 1
                match_bytes += f.stat().st_size

    # DB path extraction
    db_path = DATABASE_URL.replace("sqlite:///", "")
    settings_ok = os.path.exists(SETTINGS_PATH)

    return {
        "dim": METADATA_DIM,
        "db_path": os.path.relpath(db_path, str(PROJECT_ROOT)).replace("\\", "/"),
        "settings": settings_ok,
        "player": CS2_PLAYER_NAME,
        "match_dbs": match_count,
        "match_gb": round(match_bytes / (1024**3), 1),
    }


# ─── Formatting ───────────────────────────────────────────────────────────────


def _fmt_size(mb):
    if mb >= 1024:
        return f"{mb / 1024:.1f}GB"
    return f"{mb:.1f}MB"


def _fmt_age(days):
    if days < 1:
        return f"{days * 24:.0f}h"
    return f"{days:.0f}d"


def format_compact(data):
    SEP = " \u25aa "
    lines = []
    lines.append(f"── project_snapshot v{VERSION} {'─' * 38}")
    lines.append("")

    # Git
    g = data.get("git", {})
    if "error" in g:
        lines.append(f"git    {g['error']}")
    else:
        dirty = "dirty" if g.get("dirty") else "clean"
        lines.append(
            f"git    {g['branch']} \u25aa {g['modified']}M {g['untracked']}U "
            f"\u25aa {g['commit']} \"{g['msg']}\" \u25aa {dirty}"
        )

    # Runtime
    r = data.get("runtime", {})
    cuda_str = r.get("cuda") or "n/a"
    torch_str = r.get("torch") or "n/a"
    lines.append(
        f"rt     py{r.get('python', '?')} \u25aa torch{torch_str} \u25aa cuda:{cuda_str} \u25aa {r.get('platform', '?')}"
    )

    # DB
    d = data.get("db", {})
    if "error" in d:
        lines.append(f"db     {d['error']}")
    else:
        wal = "on" if d.get("wal") else "off"
        timeout_s = f"{d['timeout'] // 1000}s" if d.get("timeout") else "?"
        conn = "connected" if d.get("connected") else "disconnected"
        lines.append(f"db     WAL:{wal} \u25aa timeout:{timeout_s} \u25aa {conn}")

        # Counts
        counts = d.get("counts", {})
        count_parts = [f"{k}:{v}" for k, v in counts.items() if v >= 0]
        if count_parts:
            # Split into rows of ~3 each
            row = "       "
            for i, part in enumerate(count_parts):
                if i > 0:
                    row += " \u25aa "
                row += part
            lines.append(row)

        # Ingest
        ingest = d.get("ingest", {})
        if ingest:
            total = sum(ingest.values())
            q = ingest.get("queued", 0)
            p = ingest.get("processing", 0)
            done = ingest.get("done", 0)
            e = ingest.get("error", 0)
            lines.append(f"       ingest: {q}q/{p}p/{done}d/{e}e ({total} total)")

        # Coach
        coach = d.get("coach", {})
        if coach:
            status = coach.get("status", "?")
            epoch = coach.get("epoch", 0)
            loss = coach.get("loss")
            loss_str = f"{loss:.4f}" if loss is not None else "\u2014"
            lines.append(f"       coach: {status} \u25aa epoch:{epoch} \u25aa loss:{loss_str}")

    # Checkpoints
    ckpt = data.get("checkpoints", {})
    files = ckpt.get("files", [])
    if files:
        parts = []
        for c in files[:4]:
            parts.append(f"{c['name']} {_fmt_size(c['mb'])} {_fmt_age(c['age_days'])}")
        lines.append(f"ckpt   {SEP.join(parts)}")
        if ckpt["total"] > 4:
            lines.append(f"       {ckpt['total']} total")
    else:
        lines.append("ckpt   none")

    # Manifest
    m = data.get("manifest", {})
    if "error" in m:
        lines.append(f"manif  {m['error']}")
    else:
        drift_str = ", ".join(m.get("drift", [])) if m.get("drift") else "none"
        lines.append(
            f"manif  {m['tracked']} tracked \u25aa {m['match']} match \u25aa {len(m.get('drift', []))} drift: {drift_str}"
        )

    # Deps
    deps = data.get("deps", {})
    if deps:
        parts = [f"{k}:{v}" for k, v in deps.items()]
        # Two rows of 4
        lines.append(f"deps   {SEP.join(parts[:4])}")
        if len(parts) > 4:
            lines.append(f"       {SEP.join(parts[4:])}")

    # Config
    c = data.get("config", {})
    if c:
        settings_str = "ok" if c.get("settings") else "missing"
        lines.append(
            f"conf   dim:{c.get('dim', '?')} \u25aa db:{c.get('db_path', '?')} "
            f"\u25aa settings:{settings_str} \u25aa player:{c.get('player', '?')}"
        )
        lines.append(
            f"       match_data: {c.get('match_dbs', 0)} DBs \u25aa {c.get('match_gb', 0)}GB"
        )

    elapsed = data.get("elapsed_s", 0)
    lines.append("")
    lines.append(f"── {elapsed:.1f}s elapsed ──")
    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Compact project state snapshot")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress console header/footer")
    args = parser.parse_args()

    t0 = time.time()

    data = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git": _safe(collect_git, {"error": "git unavailable"}),
        "runtime": _safe(collect_runtime, {}),
        "db": _safe(collect_db, {"error": "db unavailable"}),
        "checkpoints": _safe(collect_checkpoints, {"files": [], "total": 0}),
        "manifest": _safe(collect_manifest, {"error": "manifest unavailable"}),
        "deps": _safe(collect_deps, {}),
        "config": _safe(collect_config, {}),
    }

    data["elapsed_s"] = round(time.time() - t0, 1)

    if args.json:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(format_compact(data))

    return 0


if __name__ == "__main__":
    sys.exit(main())
