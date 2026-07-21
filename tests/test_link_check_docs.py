from pathlib import Path

from scripts.ops import link_check_docs


def test_iter_markdown_files_excludes_runtime_and_dependency_trees(tmp_path: Path):
    docs_file = tmp_path / "docs" / "guide.md"
    runtime_file = tmp_path / "runtime" / "report.md"
    dependency_file = tmp_path / "web" / "node_modules" / "package" / "README.md"
    for path in (docs_file, runtime_file, dependency_file):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Document\n", encoding="utf-8")

    assert list(link_check_docs.iter_markdown_files(tmp_path)) == [docs_file]


def test_find_broken_links_checks_relative_targets_and_ignores_uris(tmp_path: Path):
    source = tmp_path / "docs" / "guide.md"
    existing = tmp_path / "README.md"
    source.parent.mkdir(parents=True)
    existing.write_text("# Repository\n", encoding="utf-8")
    source.write_text(
        "[ok](../README.md) [web](https://example.com) "
        "[plugin](plugin://github@example) [missing](missing.md)\n",
        encoding="utf-8",
    )

    assert link_check_docs.find_broken_links(tmp_path) == [
        "docs/guide.md -> missing.md"
    ]


def test_find_broken_links_handles_encoded_paths_titles_and_anchors(tmp_path: Path):
    source = tmp_path / "docs" / "guide.md"
    target = tmp_path / "docs" / "My Guide.md"
    source.parent.mkdir(parents=True)
    target.write_text("# Section\n", encoding="utf-8")
    source.write_text(
        '[guide](My%20Guide.md#section "title") [local](#section)\n',
        encoding="utf-8",
    )

    assert link_check_docs.find_broken_links(tmp_path) == []


def test_repository_markdown_links_are_valid():
    assert link_check_docs.find_broken_links(link_check_docs.ROOT) == []
