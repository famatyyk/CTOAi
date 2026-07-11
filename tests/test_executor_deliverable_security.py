from pathlib import Path

import pytest

from runner.agents import executor as module


def test_write_deliverable_writes_repo_relative_file(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)

    path = module.write_deliverable("docs/out.md", "Title", "Body")

    assert path == tmp_path / "docs" / "out.md"
    assert path.read_text(encoding="utf-8").startswith("# Title\n\nGenerated: ")
    assert "Body" in path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "path_str",
    [
        "",
        "../escape.md",
        "docs/../../escape.md",
        "/tmp/escape.md",
        "C:/temp/escape.md",
        "docs\\escape.md",
        "docs/bad:name.md",
        "docs/bad\nname.md",
    ],
)
def test_write_deliverable_rejects_unsafe_paths_before_write(
    tmp_path: Path, monkeypatch, path_str: str
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)

    with pytest.raises(
        ValueError, match="Unsafe deliverable path|escapes repository root"
    ):
        module.write_deliverable(path_str, "Title", "Body")

    assert list(tmp_path.rglob("*")) == []


def test_write_deliverable_rejects_existing_symlink(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(module, "ROOT", tmp_path)
    target = tmp_path / "target.md"
    target.write_text("existing\n", encoding="utf-8")
    link = tmp_path / "link.md"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Symlink creation is not available in this environment")

    with pytest.raises(ValueError, match="must not be a symlink"):
        module.write_deliverable("link.md", "Title", "Body")

    assert target.read_text(encoding="utf-8") == "existing\n"
