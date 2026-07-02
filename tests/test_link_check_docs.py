import importlib.util
from pathlib import Path


def _load_link_check_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "ops" / "link_check_docs.py"
    spec = importlib.util.spec_from_file_location("link_check_docs", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_link_check_allows_root_relative_links_and_ignores_vendor_dirs(monkeypatch, tmp_path, capsys):
    module = _load_link_check_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (tmp_path / "README.md").write_text("# Root\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text("[root](README.md)\n", encoding="utf-8")
    (docs_dir / "broken.md").write_text("[missing](missing.md)\n", encoding="utf-8")

    ignored_dir = tmp_path / "web" / "node_modules" / "pkg"
    ignored_dir.mkdir(parents=True)
    (ignored_dir / "README.md").write_text("[ignored](missing.md)\n", encoding="utf-8")

    rc = module.main()
    output = capsys.readouterr().out

    assert rc == 1
    assert "docs/broken.md -> missing.md" in output
    assert "node_modules" not in output

