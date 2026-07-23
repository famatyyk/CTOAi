from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _requirements(path: Path) -> list[str]:
    return [
        line.split("#", 1)[0].strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.split("#", 1)[0].strip()
    ]


def test_bot_image_uses_only_the_headless_opencv_variant() -> None:
    base = _requirements(ROOT / "requirements.txt")
    bot = _requirements(ROOT / "requirements-bot.txt")

    assert any(item.startswith("opencv-python-headless") for item in base)
    assert any(item.startswith("opencv-python-headless") for item in bot)
    assert not any(item.startswith("opencv-python>=") for item in [*base, *bot])
