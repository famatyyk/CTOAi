from pathlib import Path

import pytest

from scripts.ops import ctoa_chat_cli as cli


def test_extract_keywords_filters_short_and_stopwords():
    result = cli.extract_keywords("Jak zrobic plan refaktoru runner i docs w CTOAi?")
    assert "jak" not in result
    assert "runner" in result
    assert "docs" in result


def test_history_tail_handles_missing_file(tmp_path: Path):
    missing = tmp_path / "missing.jsonl"
    assert cli.history_tail(missing).startswith("[ctoa-chat] No history yet.")


def test_read_file_snippet_rejects_outside_repo():
    out = cli.read_file_snippet(r"C:\Windows\System32\drivers\etc\hosts")
    assert out.startswith("[ctoa-chat] Refusing to read outside repository root.")


def test_sanitize_test_tokens_rejects_unsafe_chars():
    with pytest.raises(ValueError):
        cli._sanitize_test_tokens(["tests/test_suite.py;rm"])


def test_sanitize_test_tokens_accepts_common_pytest_tokens():
    tokens = cli._sanitize_test_tokens(["tests/test_suite.py", "-q", "-k", "runner"])
    assert tokens == ["tests/test_suite.py", "-q", "-k", "runner"]


def test_apply_patch_rejects_outside_repo():
    out = cli.apply_patch_file(r"C:\Windows\Temp\a.patch")
    assert out.startswith("[ctoa-chat] Refusing to apply patch outside repository root.")


def test_extract_unified_diff_from_fenced_block():
    text = "Here is patch:\n```diff\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n```"
    diff = cli.extract_unified_diff(text)
    assert diff.startswith("--- a/a.txt")


def test_extract_unified_diff_returns_empty_without_patch():
    assert cli.extract_unified_diff("no patch here") == ""


def test_suggest_commit_message_handles_files():
    msg = cli.suggest_commit_message(["a.py", "b.py", "c.py", "d.py"])
    assert msg.startswith("chore: update ")
    assert "+1 more" in msg
