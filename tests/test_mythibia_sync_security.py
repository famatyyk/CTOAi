from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ops" / "sync-mythibia-client.ps1"


def _script_text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_unsafe_runtime_bootstrap_requires_second_env_approval():
    script = _script_text()

    assert "[switch]$UnsafeRuntimeBootstrap" in script
    assert "function Assert-UnsafeRuntimeBootstrapApproved" in script
    assert "CTOA_ALLOW_UNSAFE_RUNTIME_BOOTSTRAP" in script
    assert "Assert-UnsafeRuntimeBootstrapApproved" in script.split("function Ensure-UnsafeRuntimeBootstrap", 1)[1]


def test_unsafe_runtime_bootstrap_paths_are_clientroot_scoped():
    script = _script_text()

    assert "function Resolve-ClientChildPath" in script
    unsafe_body = script.split("function Ensure-UnsafeRuntimeBootstrap", 1)[1].split("function Remove-UnsafeRuntimeBootstrapArtifacts", 1)[0]
    cleanup_body = script.split("function Remove-UnsafeRuntimeBootstrapArtifacts", 1)[1].split("function New-LuaStubContent", 1)[0]

    assert "Join-Path $ClientRoot 'modules\\ctoa_bootstrap'" not in unsafe_body
    assert "Join-Path $ClientRoot '_tmp_unpack\\modules\\ctoa_bootstrap'" not in unsafe_body
    assert "Resolve-ClientChildPath -ClientRoot $ClientRoot -RelativePath 'modules\\ctoa_bootstrap'" in unsafe_body
    assert "Resolve-ClientChildPath -ClientRoot $ClientRoot -RelativePath '_tmp_unpack\\modules\\ctoa_bootstrap'" in unsafe_body
    assert "Resolve-ClientChildPath -ClientRoot $ClientRoot -RelativePath 'unsafe_runtime_bootstrap_report.txt'" in unsafe_body
    assert "Remove-Item -LiteralPath $target -Recurse -Force" in cleanup_body
    assert "Test-Path -LiteralPath $target" in cleanup_body


def test_default_flow_removes_unsafe_runtime_bootstrap_artifacts():
    script = _script_text()
    dispatch = script.split("$unsafeResult = $null", 1)[1].split("$trainerState = Ensure-TrainerEnabled", 1)[0]

    assert "if ($UnsafeRuntimeBootstrap.IsPresent)" in dispatch
    assert "Ensure-UnsafeRuntimeBootstrap" in dispatch
    assert "else" in dispatch
    assert "Remove-UnsafeRuntimeBootstrapArtifacts -ClientRoot $clientRoot" in dispatch
