import ast
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
FINETUNE_PATH = ROOT / "training" / "kaggle-notebook" / "ctoa_finetune.py"
COLAB_NOTEBOOK_PATH = ROOT / "training" / "finetune_colab.ipynb"
COLLECT_GITHUB_PATH = ROOT / "training" / "scripts" / "collect_github.py"
BUILD_DATASET_PATH = ROOT / "training" / "scripts" / "build_dataset.py"


def load_collect_github_module():
    spec = importlib.util.spec_from_file_location("collect_github", COLLECT_GITHUB_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_finetune_requires_pinned_huggingface_revision() -> None:
    source = FINETUNE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    from_pretrained_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "from_pretrained"
    ]

    assert len(from_pretrained_calls) == 3
    for call in from_pretrained_calls:
        keyword_names = {keyword.arg for keyword in call.keywords}
        assert "revision" in keyword_names
        assert "trust_remote_code" in keyword_names

    assert "CTOA_TRAINING_MODEL_REVISION" in source
    assert "40-character Hugging Face git commit SHA" in source
    assert "assert DATASET_PATH" not in source


def test_colab_notebook_requires_pinned_huggingface_revision() -> None:
    notebook = json.loads(COLAB_NOTEBOOK_PATH.read_text(encoding="utf-8"))
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )

    assert "FastLanguageModel.from_pretrained" in source
    assert "CTOA_TRAINING_MODEL_REVISION" in source
    assert "40-character Hugging Face commit SHA" in source
    assert "revision=model_revision" in source
    assert "trust_remote_code=trust_remote_code" in source


def test_collect_github_rejects_untrusted_api_urls_before_urlopen(monkeypatch) -> None:
    module = load_collect_github_module()

    def fail_urlopen(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("urlopen must not run for invalid GitHub API URLs")

    monkeypatch.setattr(module.urllib.request, "urlopen", fail_urlopen)

    with pytest.raises(ValueError):
        module.gh_get("file:///etc/passwd", "token")
    with pytest.raises(ValueError):
        module.gh_get("https://api.github.com.evil.test/repos/owner/repo", "token")
    with pytest.raises(ValueError):
        module.gh_get("https://user:pass@api.github.com/repos/owner/repo", "token")
    with pytest.raises(ValueError):
        module.gh_get(
            "https://api.github.com/repos/owner/repo?access_token=secret-token", "token"
        )
    with pytest.raises(ValueError):
        module.gh_get("https://api.github.com/repos/owner/repo/../other", "token")
    with pytest.raises(ValueError):
        module.gh_get("https://api.github.com/repos/owner/repo/%2e%2e/other", "token")
    with pytest.raises(ValueError):
        module.gh_get("https://api.github.com/repos/owner/repo/%2e%2e%2fother", "token")
    with pytest.raises(ValueError):
        module.gh_get("https://api.github.com/repos/owner/repo/modules%5cinit", "token")


def test_collect_github_allows_only_recursive_tree_query() -> None:
    module = load_collect_github_module()

    assert (
        module._validate_github_api_url(
            "https://api.github.com/repos/owner/repo/git/trees/main?recursive=1"
        )
        == "https://api.github.com/repos/owner/repo/git/trees/main?recursive=1"
    )
    with pytest.raises(ValueError):
        module._validate_github_api_url(
            "https://api.github.com/repos/owner/repo/git/trees/main?recursive=true"
        )
    with pytest.raises(ValueError):
        module._validate_github_api_url(
            "https://api.github.com/repos/owner/repo?recursive=1"
        )


def test_collect_github_builds_only_trusted_raw_urls() -> None:
    module = load_collect_github_module()

    raw_url = module._build_raw_url("edubart", "otclient", "main", "modules/game.lua")

    assert (
        raw_url
        == "https://raw.githubusercontent.com/edubart/otclient/main/modules/game.lua"
    )
    with pytest.raises(ValueError):
        module._build_raw_url("edubart", "otclient", "main", "../secret.lua")
    with pytest.raises(ValueError):
        module._build_raw_url("edu/bart", "otclient", "main", "modules/game.lua")
    with pytest.raises(ValueError):
        module._validate_github_raw_url(
            "https://raw.githubusercontent.com/owner/repo/main/%2e%2e/secret.lua"
        )
    with pytest.raises(ValueError):
        module._validate_github_raw_url(
            "https://raw.githubusercontent.com/owner/repo/main/%2e%2e%2fsecret.lua"
        )
    with pytest.raises(ValueError):
        module._validate_github_raw_url(
            "https://raw.githubusercontent.com/owner/repo/main/modules%5csecret.lua"
        )


def test_collect_github_dataset_filename_blocks_path_traversal() -> None:
    module = load_collect_github_module()

    assert module._safe_dataset_filename("src/foo/bar.lua") == "src__foo__bar.lua"
    with pytest.raises(ValueError):
        module._safe_dataset_filename("src/../secret.lua")
    with pytest.raises(ValueError):
        module._safe_dataset_filename("src\\..\\secret.lua")
    with pytest.raises(ValueError):
        module._safe_dataset_filename("src/%2e%2e/secret.lua")
    with pytest.raises(ValueError):
        module._safe_dataset_filename("src/%2e%2e%2fsecret.lua")


def test_build_dataset_uses_deterministic_non_security_rng_and_visible_errors() -> None:
    source = BUILD_DATASET_PATH.read_text(encoding="utf-8")

    assert "rng = random.Random(args.seed)" in source
    assert "rng.choice" in source
    assert "rng.shuffle" in source
    assert "random.choice" not in source
    assert "random.shuffle" not in source
    assert "except Exception" not in source
    assert "pass  # skip" not in source
