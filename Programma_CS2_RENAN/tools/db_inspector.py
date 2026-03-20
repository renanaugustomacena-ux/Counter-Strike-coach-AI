#!/usr/bin/env python3
"""Compact database diagnostics — full DB state without manual queries."""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from _infra import path_stabilize

PROJECT_ROOT, SOURCE_ROOT = path_stabilize()

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.db_inspector")

VERSION = "1.0"
SEP = " \u25aa "


def _validate_table_name(name: str, allowed: set) -> str:
    """Validate table name against whitelist to prevent SQL injection."""
    if name not in allowed:
        raise ValueError(f"Table name '{name}' not in allowed set")
    return name


# ─── Safe wrapper ─────────────────────────────────────────────────────────────


def _safe(fn, fallback=None):
    try:
        return fn()
    except Exception as e:
        logger.warning("%s failed: %s", fn.__name__, e)
        return fallback if fallback is not None else {"error": str(e)}


# ─── DB access ────────────────────────────────────────────────────────────────


def _get_db():
    from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database

    init_database()
    return get_db_manager()


# ─── Collectors ───────────────────────────────────────────────────────────────


def collect_connectivity():
    from sqlalchemy import text

    from Programma_CS2_RENAN.core.config import DATABASE_URL

    db = _get_db()
    result = {"connected": False, "wal": None, "sync": None, "timeout": None, "db_mb": None}

    with db.get_session() as s:
        check = s.exec(text("SELECT 1")).first()
        result["connected"] = check is not None and check[0] == 1

        wal = s.exec(text("PRAGMA journal_mode")).first()
        result["wal"] = wal[0] if wal else None

        sync = s.exec(text("PRAGMA synchronous")).first()
        sync_map = {0: "OFF", 1: "NORMAL", 2: "FULL", 3: "EXTRA"}
        result["sync"] = sync_map.get(sync[0], str(sync[0])) if sync else None

        bt = s.exec(text("PRAGMA busy_timeout")).first()
        result["timeout"] = f"{bt[0] // 1000}s" if bt and bt[0] else "0s"

    db_path = DATABASE_URL.replace("sqlite:///", "")
    if os.path.exists(db_path):
        result["db_mb"] = round(os.path.getsize(db_path) / (1024 * 1024), 1)

    return result


def collect_tables():
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy import text

    db = _get_db()
    insp = sa_inspect(db.engine)
    all_tables = insp.get_table_names()

    table_counts = []
    allowed = set(all_tables)
    with db.get_session() as s:
        for t in all_tables:
            try:
                _validate_table_name(t, allowed)
                row = s.exec(text(f"SELECT COUNT(*) FROM [{t}]")).first()
                count = row[0] if row else 0
            except Exception:
                count = -1
            table_counts.append({"name": t, "rows": count})

    table_counts.sort(key=lambda x: x["rows"], reverse=True)
    return {"total": len(all_tables), "tables": table_counts}


def collect_storage():
    from Programma_CS2_RENAN.core.config import DATABASE_URL, HLTV_DATABASE_URL, MATCH_DATA_PATH

    result = {"main": {}, "hltv": {}, "match_data": {}}

    # Main DB
    db_path = DATABASE_URL.replace("sqlite:///", "")
    if os.path.exists(db_path):
        result["main"] = {
            "path": os.path.basename(db_path),
            "mb": round(os.path.getsize(db_path) / (1024 * 1024), 1),
        }

    # HLTV DB
    hltv_path = HLTV_DATABASE_URL.replace("sqlite:///", "")
    if os.path.exists(hltv_path):
        result["hltv"] = {
            "path": os.path.basename(hltv_path),
            "mb": round(os.path.getsize(hltv_path) / (1024 * 1024), 2),
        }

    # Match data directory
    match_path = Path(MATCH_DATA_PATH)
    if match_path.exists():
        dbs = [
            f
            for f in match_path.iterdir()
            if f.name.startswith("match_") and f.name.endswith(".db")
        ]
        sizes = [f.stat().st_size for f in dbs]
        total_bytes = sum(sizes)
        result["match_data"] = {
            "count": len(dbs),
            "total_gb": round(total_bytes / (1024**3), 1),
            "min_mb": round(min(sizes) / (1024**2), 1) if sizes else 0,
            "max_mb": round(max(sizes) / (1024**2), 1) if sizes else 0,
            "avg_mb": round((total_bytes / len(dbs)) / (1024**2), 1) if dbs else 0,
        }
    else:
        result["match_data"] = {"count": 0, "total_gb": 0}

    return result


def collect_ingestion():
    from sqlalchemy import text

    db = _get_db()
    result = {"statuses": {}, "total": 0, "oldest_queued": None, "last_error": None}

    with db.get_session() as s:
        rows = s.exec(text("SELECT status, COUNT(*) FROM ingestiontask GROUP BY status")).all()
        for status, cnt in rows:
            key = status.lower() if status else "unknown"
            result["statuses"][key] = cnt
        result["total"] = sum(result["statuses"].values())

        # Oldest queued
        try:
            oq = s.exec(
                text(
                    "SELECT created_at FROM ingestiontask WHERE status='queued' "
                    "ORDER BY created_at ASC LIMIT 1"
                )
            ).first()
            if oq and oq[0]:
                result["oldest_queued"] = str(oq[0])
        except Exception as e:
            logger.debug("collect_ingestion oldest_queued query suppressed: %s", e)

        # Last error message
        try:
            le = s.exec(
                text(
                    "SELECT error_message FROM ingestiontask WHERE status='error' "
                    "ORDER BY updated_at DESC LIMIT 1"
                )
            ).first()
            if le and le[0]:
                msg = str(le[0])
                result["last_error"] = msg[:80] + "..." if len(msg) > 80 else msg
        except Exception as e:
            logger.debug("collect_ingestion last_error query suppressed: %s", e)

    return result


def collect_coach_state():
    from sqlalchemy import text

    db = _get_db()
    result = {}

    with db.get_session() as s:
        row = s.exec(text("SELECT * FROM coachstate LIMIT 1")).first()
        if row:
            keys = row._fields if hasattr(row, "_fields") else row.keys()
            data = dict(zip(keys, row))
            result = {
                "status": str(data.get("status", "?")),
                "heartbeat": str(data.get("heartbeat", "")),
                "epoch": data.get("current_epoch", 0),
                "target_epoch": data.get("target_epochs", 0),
                "loss": data.get("train_loss"),
                "matches": data.get("total_matches_processed", 0),
                "hunter": str(data.get("hunter_status", "?")),
                "digester": str(data.get("digester_status", "?")),
                "teacher": str(data.get("teacher_status", "?")),
            }

    return result


def collect_alembic():
    from sqlalchemy import inspect as sa_inspect
    from sqlalchemy import text

    db = _get_db()
    insp = sa_inspect(db.engine)
    tables = insp.get_table_names()

    if "alembic_version" not in tables:
        return {"version": None, "note": "no alembic_version table"}

    with db.get_session() as s:
        row = s.exec(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
        return {"version": row[0] if row else None}


def collect_splits():
    from sqlalchemy import text

    db = _get_db()
    result = {"splits": {}, "pro_user": {}}

    with db.get_session() as s:
        # Dataset split distribution
        try:
            rows = s.exec(
                text("SELECT dataset_split, COUNT(*) FROM playermatchstats GROUP BY dataset_split")
            ).all()
            for split, cnt in rows:
                result["splits"][split or "null"] = cnt
        except Exception as e:
            logger.debug(
                "collect_splits query suppressed: %s", e
            )  # F8-23/F8-24: log instead of silent suppress

        # Pro vs user
        try:
            rows = s.exec(
                text("SELECT is_pro, COUNT(*) FROM playermatchstats GROUP BY is_pro")
            ).all()
            for is_pro, cnt in rows:
                key = "pro" if is_pro else "user"
                result["pro_user"][key] = cnt
        except Exception as e:
            logger.debug("collect_splits pro/user query suppressed: %s", e)  # F8-23/F8-24

    return result


def collect_table_schema(table_name):
    from sqlalchemy import inspect as sa_inspect

    db = _get_db()
    insp = sa_inspect(db.engine)

    tables = insp.get_table_names()
    if table_name not in tables:
        return {"error": f"table '{table_name}' not found"}

    columns = []
    for col in insp.get_columns(table_name):
        columns.append(
            {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "default": str(col.get("default")) if col.get("default") else None,
                "primary_key": False,
            }
        )

    # Mark PKs
    pk = insp.get_pk_constraint(table_name)
    pk_cols = pk.get("constrained_columns", []) if pk else []
    for c in columns:
        if c["name"] in pk_cols:
            c["primary_key"] = True

    # Foreign keys
    fks = insp.get_foreign_keys(table_name)
    fk_list = []
    for fk in fks:
        fk_list.append(
            {
                "columns": fk.get("constrained_columns", []),
                "ref_table": fk.get("referred_table", "?"),
                "ref_columns": fk.get("referred_columns", []),
            }
        )

    # Indexes
    indexes = []
    for idx in insp.get_indexes(table_name):
        indexes.append(
            {
                "name": idx.get("name", "?"),
                "columns": idx.get("column_names", []),
                "unique": idx.get("unique", False),
            }
        )

    # Row count
    from sqlalchemy import text

    with db.get_session() as s:
        _validate_table_name(table_name, set(insp.get_table_names()))
        row = s.exec(text(f"SELECT COUNT(*) FROM [{table_name}]")).first()
        row_count = row[0] if row else 0

    return {
        "table": table_name,
        "columns": columns,
        "fks": fk_list,
        "indexes": indexes,
        "rows": row_count,
    }


# ─── Formatting ───────────────────────────────────────────────────────────────


def format_compact(data, table_detail=None):
    lines = []
    lines.append(f"── db_inspector v{VERSION} {'─' * 40}")
    lines.append("")

    # Connectivity
    c = data.get("connectivity", {})
    if "error" in c:
        lines.append(f"conn   {c['error']}")
    else:
        wal_str = c.get("wal", "?")
        sync_str = c.get("sync", "?")
        timeout_str = c.get("timeout", "?")
        db_mb = c.get("db_mb", "?")
        conn_str = "ok" if c.get("connected") else "FAILED"
        lines.append(
            f"conn   WAL:{wal_str}{SEP}sync:{sync_str}{SEP}timeout:{timeout_str}{SEP}db:{db_mb}MB{SEP}{conn_str}"
        )

    # Tables
    t = data.get("tables", {})
    if "error" not in t:
        tables = t.get("tables", [])
        lines.append(f"\ntables ({t.get('total', 0)} total, by row count desc)")
        # Display in rows of 3
        row_parts = []
        for tbl in tables:
            row_parts.append(f"{tbl['name']}:{tbl['rows']}")
            if len(row_parts) == 3:
                lines.append(f"       {SEP.join(row_parts)}")
                row_parts = []
        if row_parts:
            lines.append(f"       {SEP.join(row_parts)}")

    # Storage
    s = data.get("storage", {})
    if "error" not in s:
        main = s.get("main", {})
        hltv = s.get("hltv", {})
        md = s.get("match_data", {})
        lines.append("")
        main_str = f"{main.get('path', '?')}:{main.get('mb', '?')}MB" if main else "n/a"
        hltv_str = f"{hltv.get('path', '?')}:{hltv.get('mb', '?')}MB" if hltv else "n/a"
        lines.append(f"store  {main_str}{SEP}{hltv_str}")
        if md.get("count", 0) > 0:
            lines.append(f"       match_data/: {md['count']} DBs{SEP}{md['total_gb']}GB total")
            lines.append(
                f"       range: {md['min_mb']}MB(min) \u2014 {md['max_mb']}MB(max) \u2014 {md['avg_mb']}MB(avg)"
            )

    # Ingestion
    ig = data.get("ingestion", {})
    if "error" not in ig:
        st = ig.get("statuses", {})
        total = ig.get("total", 0)
        q = st.get("queued", 0)
        p = st.get("processing", 0)
        d = st.get("done", 0)
        e = st.get("error", 0)
        lines.append(
            f"\ningest queued:{q}{SEP}processing:{p}{SEP}done:{d}{SEP}error:{e}{SEP}total:{total}"
        )
        if ig.get("oldest_queued"):
            lines.append(f"       oldest_queued: {ig['oldest_queued']}")
        if ig.get("last_error"):
            lines.append(f"       last_error: \"{ig['last_error']}\"")

    # Coach
    co = data.get("coach", {})
    if co and "error" not in co:
        status = co.get("status", "?")
        epoch = co.get("epoch", 0)
        target = co.get("target_epoch", 0)
        loss = co.get("loss")
        loss_str = f"{loss:.4f}" if loss is not None else "\u2014"
        matches = co.get("matches", 0)
        lines.append(
            f"\ncoach  {status}{SEP}epoch:{epoch}/{target}{SEP}loss:{loss_str}{SEP}matches:{matches}"
        )
        hunter = co.get("hunter", "?")
        digester = co.get("digester", "?")
        teacher = co.get("teacher", "?")
        lines.append(f"       daemons: hunter={hunter} digester={digester} teacher={teacher}")

    # Alembic
    al = data.get("alembic", {})
    if "error" not in al:
        ver = al.get("version") or "none"
        lines.append(f"\nalembic {ver}")

    # Splits
    sp = data.get("splits", {})
    if "error" not in sp:
        splits = sp.get("splits", {})
        pu = sp.get("pro_user", {})
        if splits:
            split_parts = [f"{k}:{v}" for k, v in splits.items()]
            total = sum(splits.values())
            lines.append(f"\nsplits {SEP.join(split_parts)} total:{total}")
        if pu:
            pu_parts = [f"{k}:{v}" for k, v in pu.items()]
            lines.append(f"       {SEP.join(pu_parts)}")

    # Table detail
    if table_detail and "error" not in table_detail:
        lines.append("")
        lines.append(f"── schema: {table_detail['table']} {'─' * 30}")
        lines.append("")
        cols = table_detail.get("columns", [])
        lines.append(f"columns ({len(cols)})")
        for col in cols:
            pk = "PK" if col.get("primary_key") else ""
            null = "NOT NULL" if not col.get("nullable") else "nullable"
            default = f"default:{col['default']}" if col.get("default") else ""
            parts = [s for s in [pk, null, default] if s]
            flags = SEP.join(parts) if parts else ""
            lines.append(f"  {col['name']:<20s}{str(col['type']):<15s}{flags}")

        idxs = table_detail.get("indexes", [])
        if idxs:
            lines.append(f"\nindexes ({len(idxs)})")
            for idx in idxs:
                uniq = "UNIQUE" if idx.get("unique") else ""
                cols_str = ", ".join(idx.get("columns", []))
                lines.append(f"  {idx['name']:<30s}{uniq}({cols_str})")

        fks = table_detail.get("fks", [])
        lines.append(f"\nfk     {'none' if not fks else ''}")
        for fk in fks:
            src = ", ".join(fk.get("columns", []))
            ref = fk.get("ref_table", "?")
            ref_cols = ", ".join(fk.get("ref_columns", []))
            lines.append(f"  ({src}) -> {ref}({ref_cols})")

        lines.append(f"rows   {table_detail.get('rows', 0)}")

    elapsed = data.get("elapsed_s", 0)
    lines.append("")
    lines.append(f"── {elapsed:.1f}s elapsed ──")
    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Compact database diagnostics")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress console header/footer")
    parser.add_argument("--table", type=str, default=None, help="Show schema for specific table")
    args = parser.parse_args()

    t0 = time.time()

    data = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "connectivity": _safe(collect_connectivity, {"error": "db unavailable"}),
        "tables": _safe(collect_tables, {"error": "tables unavailable"}),
        "storage": _safe(collect_storage, {"error": "storage unavailable"}),
        "ingestion": _safe(collect_ingestion, {"error": "ingestion unavailable"}),
        "coach": _safe(collect_coach_state, {}),
        "alembic": _safe(collect_alembic, {"error": "alembic unavailable"}),
        "splits": _safe(collect_splits, {"error": "splits unavailable"}),
    }

    table_detail = None
    if args.table:
        table_detail = _safe(
            lambda: collect_table_schema(args.table), {"error": f"table '{args.table}' unavailable"}
        )
        data["table_detail"] = table_detail

    data["elapsed_s"] = round(time.time() - t0, 1)

    if args.json:
        print(json.dumps(data, indent=2, default=str))
    else:
        print(format_compact(data, table_detail))

    return 0


if __name__ == "__main__":
    sys.exit(main())
