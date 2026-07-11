"""File path guardrails for hybrid bot runtime artifacts."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

_WINDOWS_UNSAFE_FILENAME_CHARS = set('<>:"|?*')


def resolve_output_dir(output_dir: Path | str) -> Path:
    """Resolve and create an operator-selected output directory."""
    path = Path(output_dir or ".").expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise ValueError("Output path must be a directory")
    return path


def safe_child_path(
    base_dir: Path,
    relative_path: Path | str,
    *,
    allowed_suffixes: set[str] | None = None,
    create_parent: bool = False,
    must_exist: bool = False,
) -> Path:
    """Resolve a safe child file under an already trusted base directory."""
    raw = str(relative_path or "").strip()
    if not raw or "\\" in raw:
        raise ValueError("Unsafe metrics path")

    rel = PurePosixPath(raw)
    if rel.is_absolute() or not rel.parts:
        raise ValueError("Unsafe metrics path")

    for part in rel.parts:
        if (
            part in {"", ".", ".."}
            or any(ord(ch) < 32 for ch in part)
            or any(ch in _WINDOWS_UNSAFE_FILENAME_CHARS for ch in part)
        ):
            raise ValueError("Unsafe metrics path")

    base_resolved = base_dir.resolve()
    candidate = base_resolved.joinpath(*rel.parts)
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base_resolved)
    except ValueError as exc:
        raise ValueError("Metrics path escapes output directory") from exc

    if candidate.exists() and candidate.is_symlink():
        raise ValueError("Metrics path must not be a symlink")
    if allowed_suffixes and candidate.suffix.lower() not in allowed_suffixes:
        raise ValueError("Metrics path has an unsupported extension")
    if must_exist and not candidate.is_file():
        raise FileNotFoundError(f"Metrics file not found: {candidate}")
    if create_parent:
        candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate
