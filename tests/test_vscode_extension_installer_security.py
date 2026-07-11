from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "windows" / "install-ctoa-vscode-extensions.ps1"


def _script_text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_vscode_extension_installer_uses_separator_aware_child_path_guard():
    script = _script_text()

    assert "function Assert-ChildPath" in script
    assert "$rootPrefix = $resolvedRoot.TrimEnd($trimChars) + [System.IO.Path]::DirectorySeparatorChar" in script
    assert "$resolvedCandidate.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)" in script
    assert "Refusing to write outside ExtensionsRoot" in script


def test_vscode_extension_installer_uses_literal_paths_for_recursive_replace():
    script = _script_text()

    assert "Test-Path -LiteralPath $source" in script
    assert "Test-Path -LiteralPath $resolvedTarget" in script
    assert "Remove-Item -LiteralPath $resolvedTarget -Recurse -Force" in script
    assert "Copy-Item -LiteralPath $source -Destination $resolvedTarget -Recurse -Force" in script
    assert "Remove-Item $target -Recurse -Force" not in script
    assert "Copy-Item $source $target -Recurse -Force" not in script
