from scripts.ops import ctoa_helper_ui_preview as preview


def test_as_int_evaluates_limited_numeric_expressions() -> None:
    variables = {"left": 10, "right": 40, "gap": 6}

    assert preview.as_int("left + right - gap", fallback=-1, variables=variables) == 44
    assert preview.as_int("math.floor((left + right) / 2)", fallback=-1, variables=variables) == 25
    assert preview.as_int("-left + 50", fallback=-1, variables=variables) == 40


def test_as_int_rejects_non_numeric_expressions_without_eval() -> None:
    variables = {"left": 10}

    assert preview.as_int("__import__('os').system('whoami')", fallback=123, variables=variables) == 123
    assert preview.as_int("open('x')", fallback=123, variables=variables) == 123
    assert preview.as_int("floor(left, 2)", fallback=123, variables=variables) == 123


def test_helper_ui_preview_source_does_not_use_eval() -> None:
    source = preview.Path(preview.__file__).read_text(encoding="utf-8")

    assert "eval(" not in source
