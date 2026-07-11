from __future__ import annotations

import logging

import numpy as np
import pytest

from runner.hybrid_bot import template_library as module


def _template(name: str, template_type: str = "creature") -> module.Template:
    return module.Template(
        name=name,
        template_type=template_type,
        image=np.zeros((4, 4, 3), dtype=np.uint8),
        original_size=(4, 4),
        resized_size=(4, 4),
        scale_factor=1.0,
        confidence_threshold=0.7,
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://user:secret@example.test/templates/rat.png",
        "https://example.test/templates/rat.png?token=secret",
        "https://example.test/templates/rat.png#secret",
        "https://example.test/templates/%2e%2e/rat.png",
        "https://example.test/templates%5crat.png",
        "http://localhost:8000/templates/rat.png",
        "http://127.0.0.1:8000/templates/rat.png",
        "http://10.0.0.4/templates/rat.png",
        "http://169.254.169.254/latest/meta-data",
        "http://template-service/templates/rat.png",
        "http://templates.local/templates/rat.png",
    ],
)
def test_template_server_url_rejects_unsafe_parts_before_urlopen(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    url: str,
) -> None:
    lib = module.TemplateLibrary(cache_dir=tmp_path, use_cache=False)

    def fail_urlopen(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("urlopen must not run for unsafe template URLs")

    monkeypatch.setattr(module, "urlopen", fail_urlopen)
    caplog.set_level(logging.ERROR, logger="hybrid_bot.template_library")

    assert lib._load_from_server(url, "creature", "rat") is None
    assert "secret" not in caplog.text


def test_template_library_rejects_unsafe_server_url_on_init(tmp_path) -> None:
    with pytest.raises(ValueError):
        module.TemplateLibrary(
            cache_dir=tmp_path,
            server_url="https://user:secret@example.test/templates",
        )


def test_template_library_rejects_private_server_url_on_init(tmp_path) -> None:
    with pytest.raises(ValueError):
        module.TemplateLibrary(
            cache_dir=tmp_path,
            server_url="http://127.0.0.1:8000/templates",
        )


@pytest.mark.parametrize("name", ["../escape", "creature/escape", "creature\\escape"])
def test_template_cache_rejects_traversal_names(tmp_path, name: str) -> None:
    lib = module.TemplateLibrary(cache_dir=tmp_path)

    assert lib.save_template(_template(name)) is False
    assert not list(tmp_path.rglob("*.png"))
    assert not (tmp_path.parent / "escape.png").exists()


def test_template_load_rejects_unsafe_creature_names_without_placeholder(
    tmp_path,
) -> None:
    lib = module.TemplateLibrary(cache_dir=tmp_path)

    assert lib.load_creatures(["../escape"]) == 0
    assert lib.creatures == {}


def test_template_load_allows_existing_space_separated_creature_names(tmp_path) -> None:
    lib = module.TemplateLibrary(cache_dir=tmp_path)

    assert lib.load_creatures(["cave spider"]) == 1
    assert "cave spider" in lib.creatures
