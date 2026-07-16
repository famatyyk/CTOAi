import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from scripts.ops import otclient_equipment_capture_profile_doctor as doctor
from scripts.ops import otclient_equipment_shadow_snapshot as snapshot


def _use_temporary_local_profile(monkeypatch, root: Path) -> Path:
    target = root / ".ctoa-local" / "otclient" / "equipment-shadow-capture-profile.json"
    monkeypatch.setattr(snapshot, "ROOT", root)
    monkeypatch.setattr(snapshot, "DEFAULT_LOCAL_CAPTURE_PROFILE", target)
    return target


def test_doctor_blocks_tracked_unconfigured_template(monkeypatch, tmp_path: Path):
    template = tmp_path / "template.json"
    template.write_text(
        snapshot.DEFAULT_CAPTURE_PROFILE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(snapshot, "DEFAULT_CAPTURE_PROFILE", template)
    monkeypatch.setattr(
        snapshot, "DEFAULT_LOCAL_CAPTURE_PROFILE", tmp_path / "missing.json"
    )

    report = doctor.diagnose()

    assert report["status"] == "blocked"
    assert report["runtime_actions"] is False
    assert report["live_file_writes"] is False
    assert report["runtime_readiness_claimed"] is False
    assert "local_operator_override_missing" in report["blockers"]
    assert "operator_confirmation_missing" in report["blockers"]
    assert "exact_ids_missing" in report["blockers"]
    schema_path = (
        snapshot.ROOT / "schemas" / "equipment-capture-profile-doctor.schema.json"
    )
    Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).validate(
        report
    )


def test_doctor_accepts_only_exact_distinct_local_ids(monkeypatch, tmp_path: Path):
    local = tmp_path / "equipment-shadow-capture-profile.json"
    payload = json.loads(snapshot.DEFAULT_CAPTURE_PROFILE.read_text(encoding="utf-8"))
    payload.update(
        configured_by_operator=True,
        equipped_item_id=3051,
        candidate_item_id=3097,
        candidate_source_container_id=12,
        candidate_source_slot_index=3,
    )
    local.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(snapshot, "ROOT", tmp_path)
    monkeypatch.setattr(snapshot, "DEFAULT_LOCAL_CAPTURE_PROFILE", local)

    report = doctor.diagnose()

    assert report["status"] == "ready"
    assert report["blockers"] == []
    assert report["identifiers_present"] is True
    assert report["no_action_contract"] is True
    assert report["runtime_readiness_claimed"] is False


def test_initializer_exclusively_creates_exact_zero_id_profile(
    monkeypatch, tmp_path: Path
):
    target = _use_temporary_local_profile(monkeypatch, tmp_path)

    result = doctor.initialize_local_profile()

    expected = doctor.zero_id_skeleton()
    original = target.read_bytes()
    assert json.loads(original) == expected
    assert result == {
        "status": "initialized_unconfigured",
        "path": str(target),
        "sha256": snapshot.p9_replay.canonical_sha256(expected),
        "configured_by_operator": False,
        "runtime_readiness_claimed": False,
    }
    assert all(
        expected[key] == 0 for key in (*doctor.ZERO_KEYS, "candidate_source_slot_index")
    )
    assert all(expected[key] is False for key in snapshot.FALSE_FLAGS)
    assert not list(target.parent.glob(f".{target.name}.*.tmp"))

    with pytest.raises(FileExistsError, match="never overwrites"):
        doctor.initialize_local_profile()
    assert target.read_bytes() == original


def test_initializer_does_not_resolve_or_read_an_otclient(monkeypatch, tmp_path: Path):
    target = _use_temporary_local_profile(monkeypatch, tmp_path)

    def unexpected_profile_resolution(*_args, **_kwargs):
        raise AssertionError("initializer must not resolve runtime or client inputs")

    monkeypatch.setattr(
        snapshot, "resolve_capture_profile", unexpected_profile_resolution
    )

    doctor.initialize_local_profile()

    assert target.is_file()


def test_initializer_rejects_symlink_parent(monkeypatch, tmp_path: Path):
    target = _use_temporary_local_profile(monkeypatch, tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (tmp_path / ".ctoa-local").symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")

    with pytest.raises(ValueError, match="symlink or reparse point"):
        doctor.initialize_local_profile()

    assert not target.exists()


def test_initializer_rejects_symlink_target(monkeypatch, tmp_path: Path):
    target = _use_temporary_local_profile(monkeypatch, tmp_path)
    target.parent.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text("preserve", encoding="utf-8")
    try:
        target.symlink_to(outside)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"file symlinks unavailable: {exc}")

    with pytest.raises(ValueError, match="symlink or reparse point"):
        doctor.initialize_local_profile()

    assert outside.read_text(encoding="utf-8") == "preserve"


def test_initializer_rejects_reparse_parent_without_following_it(
    monkeypatch, tmp_path: Path
):
    _use_temporary_local_profile(monkeypatch, tmp_path)
    local_root = tmp_path / ".ctoa-local"
    local_root.mkdir()
    real_lstat = Path.lstat

    def lstat_with_reparse(path: Path):
        metadata = real_lstat(path)
        if path == local_root:
            return SimpleNamespace(
                st_mode=metadata.st_mode,
                st_file_attributes=0x400,
            )
        return metadata

    monkeypatch.setattr(Path, "lstat", lstat_with_reparse)

    with pytest.raises(ValueError, match="symlink or reparse point"):
        doctor.initialize_local_profile()


def test_initializer_refuses_any_non_fixed_target(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(snapshot, "ROOT", tmp_path)
    monkeypatch.setattr(
        snapshot,
        "DEFAULT_LOCAL_CAPTURE_PROFILE",
        tmp_path / ".ctoa-local" / "otclient" / "operator-selected.json",
    )

    with pytest.raises(ValueError, match="fixed .ctoa-local profile"):
        doctor.initialize_local_profile()


def test_init_cli_succeeds_without_claiming_readiness(
    monkeypatch, tmp_path: Path, capsys
):
    target = _use_temporary_local_profile(monkeypatch, tmp_path)
    reports: list[dict] = []
    monkeypatch.setattr(
        snapshot,
        "_write_atomic",
        lambda _path, _expected, payload: reports.append(payload),
    )

    exit_code = doctor.main(["--init-local"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert target.is_file()
    assert reports[0]["status"] == "blocked"
    assert reports[0]["runtime_readiness_claimed"] is False
    assert "remains unconfigured" in captured.err
    assert "no runtime readiness is claimed" in captured.err


def test_doctor_cli_can_allow_a_structurally_valid_blocked_report(
    monkeypatch, tmp_path: Path
):
    template = tmp_path / "template.json"
    template.write_text(
        snapshot.DEFAULT_CAPTURE_PROFILE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    monkeypatch.setattr(snapshot, "DEFAULT_CAPTURE_PROFILE", template)
    monkeypatch.setattr(
        snapshot, "DEFAULT_LOCAL_CAPTURE_PROFILE", tmp_path / "missing.json"
    )
    reports: list[dict] = []
    monkeypatch.setattr(
        snapshot,
        "_write_atomic",
        lambda _path, _expected, payload: reports.append(payload),
    )

    assert doctor.main([]) == 1
    assert doctor.main(["--allow-blocked"]) == 0
    assert [report["status"] for report in reports] == ["blocked", "blocked"]
    assert all(report["runtime_actions"] is False for report in reports)
