"""CFG-ENV-01: repo-root .env loading into os.environ.

The .env file was a documented but never-parsed config surface —
every documented override silently no-opped. These tests pin the
loader's contract: setdefault semantics, comment/quote stripping,
tolerance for junk lines, absence tolerated.
"""

import os

from Programma_CS2_RENAN.core import config


def _run_loader(tmp_path, monkeypatch, content):
    base = tmp_path / "Programma_CS2_RENAN"
    base.mkdir()
    (tmp_path / ".env").write_text(content, encoding="utf-8")
    monkeypatch.setattr(config, "BASE_DIR", str(base))
    config._load_dotenv_file()


class TestDotenvLoader:
    def test_sets_missing_key(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CS2_TEST_DOTENV_A", raising=False)
        _run_loader(tmp_path, monkeypatch, "CS2_TEST_DOTENV_A=hello\n")
        assert os.environ.get("CS2_TEST_DOTENV_A") == "hello"
        monkeypatch.delenv("CS2_TEST_DOTENV_A", raising=False)

    def test_real_environment_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CS2_TEST_DOTENV_B", "from_env")
        _run_loader(tmp_path, monkeypatch, "CS2_TEST_DOTENV_B=from_file\n")
        assert os.environ.get("CS2_TEST_DOTENV_B") == "from_env"

    def test_inline_comment_stripped(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CS2_TEST_DOTENV_C", raising=False)
        _run_loader(
            tmp_path,
            monkeypatch,
            "CS2_TEST_DOTENV_C=gpt-oss:20b           # MoE, tool calling\n",
        )
        assert os.environ.get("CS2_TEST_DOTENV_C") == "gpt-oss:20b"
        monkeypatch.delenv("CS2_TEST_DOTENV_C", raising=False)

    def test_quoted_value_keeps_hash(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CS2_TEST_DOTENV_D", raising=False)
        _run_loader(tmp_path, monkeypatch, 'CS2_TEST_DOTENV_D="value # not comment"\n')
        assert os.environ.get("CS2_TEST_DOTENV_D") == "value # not comment"
        monkeypatch.delenv("CS2_TEST_DOTENV_D", raising=False)

    def test_junk_lines_ignored(self, tmp_path, monkeypatch):
        _run_loader(
            tmp_path,
            monkeypatch,
            "# full comment\n\nnot a pair\n=novalue\nBAD KEY=x\n",
        )
        assert "BAD KEY" not in os.environ

    def test_missing_file_is_noop(self, tmp_path, monkeypatch):
        base = tmp_path / "Programma_CS2_RENAN"
        base.mkdir()
        monkeypatch.setattr(config, "BASE_DIR", str(base))
        config._load_dotenv_file()  # must not raise
