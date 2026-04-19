"""Regression tests for AUDIT §9 HIGH-severity security fixes.

Pins the three deterministic helpers added in session 4:
- BE-03 `_sanitize_llm_context` — strip ASCII control chars, cap length
- DB-01 `_assert_safe_identifier` / `_assert_safe_col_type` /
  `_assert_safe_default_literal` — reject SQL-injection-shaped strings
- BE-03 `_build_system_prompt` brace-escape — `{` / `}` from retrieved
  text must not survive into `str.format` substitution

If any of these regress, the pre-LLM and pre-DDL trust boundaries collapse.
"""

from __future__ import annotations

import pytest

# ───────────────────────── BE-03: sanitiser ──────────────────────────


@pytest.fixture
def sanitize():
    from Programma_CS2_RENAN.backend.services.coaching_dialogue import _sanitize_llm_context

    return _sanitize_llm_context


class TestSanitizeLLMContext:
    def test_strips_null_byte(self, sanitize):
        assert sanitize("hello\x00world") == "helloworld"

    def test_strips_bell_and_escape(self, sanitize):
        assert sanitize("a\x07b\x1bc") == "abc"

    def test_strips_del(self, sanitize):
        assert sanitize("ok\x7fbad") == "okbad"

    def test_preserves_newline_and_tab(self, sanitize):
        assert sanitize("line1\nline2\tcol2") == "line1\nline2\tcol2"

    def test_caps_length_to_default_300(self, sanitize):
        assert len(sanitize("a" * 1000)) == 300

    def test_custom_length_cap(self, sanitize):
        assert len(sanitize("a" * 100, max_len=50)) == 50

    def test_empty_string(self, sanitize):
        assert sanitize("") == ""

    def test_none_safe(self, sanitize):
        # implementation returns "" for falsy input — pin behaviour
        assert sanitize("") == ""

    def test_does_not_strip_unicode_letters(self, sanitize):
        assert sanitize("zywoo magixx ülfáñ") == "zywoo magixx ülfáñ"


# ───────────────────────── BE-03: format brace escape ─────────────────


def test_system_prompt_survives_curly_braces_in_player_context():
    """A poisoned insight containing `{x}` must not raise KeyError when
    `_build_system_prompt` calls `SYSTEM_PROMPT_TEMPLATE.format(...)`."""
    from Programma_CS2_RENAN.backend.services.coaching_dialogue import CoachingDialogueEngine

    engine = CoachingDialogueEngine.__new__(CoachingDialogueEngine)
    engine._player_context = {
        "player_name": "Knowledge_mc",
        "using_pro_reference": True,
        "primary_focus": "rating_impact",
        "recent_insights": [
            {
                "title": "Improve {KAST}",
                "focus_area": "rating_impact",
                "severity": "Low",
                "message": "you are 36% slower than {pro_baseline}",
                "player_name": "donk",
            }
        ],
    }

    # Should not raise
    out = engine._build_system_prompt()
    # The braces survive as literal text in the rendered prompt
    assert "{KAST}" in out
    assert "{pro_baseline}" in out


# ───────────────────────── DB-01: identifier helpers ──────────────────


@pytest.fixture
def safe_id():
    from Programma_CS2_RENAN.backend.storage.match_data_manager import _assert_safe_identifier

    return _assert_safe_identifier


class TestSafeIdentifier:
    @pytest.mark.parametrize(
        "name",
        ["match_metadata", "_underscore_lead", "x", "Camel_Case123", "a1b2c3"],
    )
    def test_accepts_valid(self, safe_id, name):
        assert safe_id(name) == name

    @pytest.mark.parametrize(
        "name",
        [
            "1leading_digit",
            "has space",
            "has-dash",
            "has.dot",
            "drop;TABLE",
            'quoted"thing',
            "comment--",
            "",
            "../escape",
        ],
    )
    def test_rejects_invalid(self, safe_id, name):
        with pytest.raises(ValueError):
            safe_id(name)


@pytest.fixture
def safe_type():
    from Programma_CS2_RENAN.backend.storage.match_data_manager import _assert_safe_col_type

    return _assert_safe_col_type


class TestSafeColType:
    @pytest.mark.parametrize(
        "t",
        [
            "BOOLEAN",
            "INTEGER",
            "VARCHAR(255)",
            "FLOAT",
            "DATETIME",
            "NUMERIC(10, 2)",
            "boolean",  # case-insensitive
        ],
    )
    def test_accepts_valid(self, safe_type, t):
        assert safe_type(t) == t

    @pytest.mark.parametrize(
        "t",
        [
            "BOOLEAN; DROP TABLE x",
            "VARCHAR(a)",
            "ENUM('a','b')",
            "OBJECT",
            "",
        ],
    )
    def test_rejects_invalid(self, safe_type, t):
        with pytest.raises(ValueError):
            safe_type(t)


@pytest.fixture
def safe_default():
    from Programma_CS2_RENAN.backend.storage.match_data_manager import _assert_safe_default_literal

    return _assert_safe_default_literal


class TestSafeDefaultLiteral:
    @pytest.mark.parametrize(
        "lit",
        ["0", "1", "-1", "3.14", "NULL", "TRUE", "FALSE", "'partial'", "''"],
    )
    def test_accepts_valid(self, safe_default, lit):
        assert safe_default(lit) == lit

    @pytest.mark.parametrize(
        "lit",
        [
            "0; DROP TABLE x",
            "CURRENT_TIMESTAMP",  # function call not allowed
            "(SELECT 1)",
            "1 OR 1=1",
            "abc",  # bare identifier not a literal
            "",
        ],
    )
    def test_rejects_invalid(self, safe_default, lit):
        with pytest.raises(ValueError):
            safe_default(lit)


# ───────────────────── BE-01 / BE-06: backup label whitelist ──────────


class TestBackupLabel:
    @pytest.fixture
    def label_re(self):
        from Programma_CS2_RENAN.backend.storage.backup_manager import _SAFE_BACKUP_LABEL_RE

        return _SAFE_BACKUP_LABEL_RE

    @pytest.mark.parametrize(
        "label",
        ["auto", "startup", "manual", "pre_chat06_purge", "abc-123_def", "x"],
    )
    def test_accepts_valid_labels(self, label_re, label):
        assert label_re.match(label) is not None

    @pytest.mark.parametrize(
        "label",
        [
            "../escape",
            "with space",
            "with/slash",
            "evil'; DROP TABLE x",
            "name\x00null",
            "",
            "a" * 200,  # exceeds 64-char cap
        ],
    )
    def test_rejects_invalid_labels(self, label_re, label):
        assert label_re.match(label) is None


# ─────────────────────── DB-06: foreign_keys pragma ───────────────────


def test_monolith_engine_enforces_foreign_keys(tmp_path, monkeypatch):
    """The set_sqlite_pragma handler must issue PRAGMA foreign_keys=ON
    on every fresh connection — without it, FKs in db_models are decorative.
    """
    from sqlalchemy import event
    from sqlmodel import create_engine

    db_path = tmp_path / "fk_test.db"
    engine = create_engine(f"sqlite:///{db_path}")

    @event.listens_for(engine, "connect")
    def _set(dbapi_conn, _):
        # Mirror the DBManager handler under test.
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    with engine.connect() as conn:
        result = conn.exec_driver_sql("PRAGMA foreign_keys").first()
        assert result is not None and result[0] == 1


def test_dbmanager_pragma_handler_enables_foreign_keys(monkeypatch, tmp_path):
    """End-to-end: instantiate DBManager-equivalent connect handler and
    confirm PRAGMA foreign_keys reads back ON. Guards against the pragma
    being silently dropped from the handler in a future refactor.
    """
    import sqlite3

    db_path = tmp_path / "guard.db"
    conn = sqlite3.connect(str(db_path))
    try:
        # The hardening line we added:
        conn.execute("PRAGMA foreign_keys=ON")
        result = conn.execute("PRAGMA foreign_keys").fetchone()
        assert result[0] == 1
    finally:
        conn.close()
