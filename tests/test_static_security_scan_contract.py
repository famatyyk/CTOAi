import py_compile
from pathlib import Path
import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_non_security_sha1_fingerprints_are_marked_explicitly() -> None:
    checked_paths = [
        ROOT / "scripts" / "ops" / "assemble_overlap_graph_variants.py",
        ROOT / "scripts" / "ops" / "assemble_window_aware_variants.py",
        ROOT / "scripts" / "ops" / "capture_runtime_loader_transform_live.py",
    ]

    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        assert "hashlib.sha1(" in text, str(path)
        assert "usedforsecurity=False" in text, str(path)
        assert ".sha1(data).hexdigest()" not in text, str(path)
        assert ".sha1(ch).hexdigest()" not in text, str(path)
        assert ".sha1(part).hexdigest()" not in text, str(path)


def test_bandit_scope_legacy_python_tools_compile() -> None:
    checked_paths = [
        ROOT / "scripts" / "ops" / "capture_runtime_loader_transform_live.py",
        ROOT / "scripts" / "ops" / "depack_top_candidates.py",
        ROOT / "scripts" / "ops" / "triage_entropy_carves.py",
    ]

    for path in checked_paths:
        py_compile.compile(str(path), doraise=True)


def test_pre_commit_bandit_scope_covers_operator_surfaces() -> None:
    payload = yaml.safe_load(
        (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    )
    hooks = [
        hook
        for repo in payload.get("repos", [])
        for hook in repo.get("hooks", [])
        if hook.get("id") == "bandit"
    ]
    assert hooks, "bandit hook must stay configured"
    args = hooks[0].get("args", [])
    for path in ("runner", "mobile_console", "scripts", "desktop_console", "bot"):
        assert path in args
