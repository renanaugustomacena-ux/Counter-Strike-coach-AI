"""Guides round (WP2) — localized guides win, English is the fallback."""

from __future__ import annotations

from Programma_CS2_RENAN.backend.knowledge_base.help_system import HelpSystem


def _docs(tmp_path):
    (tmp_path / "alpha.md").write_text("# Alpha\n\nenglish body\n", encoding="utf-8")
    (tmp_path / "beta.md").write_text("# Beta\n\nenglish only\n", encoding="utf-8")
    (tmp_path / "it").mkdir()
    (tmp_path / "it" / "alpha.md").write_text("# Alfa\n\ntesto italiano\n", encoding="utf-8")
    return HelpSystem(docs_dir=str(tmp_path))


def test_localized_topic_wins_and_missing_ones_fall_back_to_english(tmp_path):
    hs = _docs(tmp_path)

    it = {t["id"]: t for t in hs.get_all_topics(lang="it")}
    assert it["alpha"]["title"] == "Alfa" and "italiano" in it["alpha"]["content"]
    assert it["beta"]["title"] == "Beta" and "english only" in it["beta"]["content"]

    pt = {t["id"]: t for t in hs.get_all_topics(lang="pt")}
    assert pt["alpha"]["title"] == "Alpha"


def test_topic_ids_are_the_same_in_every_language(tmp_path):
    hs = _docs(tmp_path)
    assert {t["id"] for t in hs.get_all_topics()} == {"alpha", "beta"}
    assert {t["id"] for t in hs.get_all_topics(lang="it")} == {"alpha", "beta"}
    assert hs.available_languages() == {"en", "it"}


def test_get_topic_and_search_respect_the_language(tmp_path):
    hs = _docs(tmp_path)
    assert hs.get_topic("alpha", lang="it")["title"] == "Alfa"
    assert hs.get_topic("alpha")["title"] == "Alpha"
    assert [r["id"] for r in hs.search_topics("italiano", lang="it")] == ["alpha"]
    assert hs.search_topics("italiano") == []


def test_default_docs_dir_is_the_bundled_resource_folder():
    hs = HelpSystem()
    assert hs.docs_dir.replace("\\", "/").endswith("data/docs")
