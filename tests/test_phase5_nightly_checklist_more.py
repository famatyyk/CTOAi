import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    module_path = PROJECT_ROOT / 'scripts' / 'ops' / 'phase5_nightly_checklist.py'
    spec = importlib.util.spec_from_file_location('phase5_nightly_checklist_more', module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_snapshot_timestamp_and_summary_handle_invalid_inputs(tmp_path: Path):
    module = _load_module()
    summary = tmp_path / 'summary.md'
    summary.write_text('# header\nbranch: main\ninvalid\nresult: PASS\n', encoding='utf-8')

    assert module._parse_snapshot_timestamp('phase5-drycheck-20260516T022020Z') is not None
    assert module._parse_snapshot_timestamp('phase5-drycheck-invalid') is None
    assert module._parse_summary(tmp_path / 'missing.md') == {}
    assert module._parse_summary(summary) == {'branch': 'main', 'result': 'PASS'}


def test_build_snapshot_record_and_evaluate_capture_all_alerts(tmp_path: Path):
    module = _load_module()
    snapshot = tmp_path / 'phase5-drycheck-20260516T033000Z'
    snapshot.mkdir(parents=True, exist_ok=True)
    (snapshot / 'summary.md').write_text(
        '\n'.join(
            [
                'branch: feature/test',
                'head: abc1234',
                'result: FAIL',
                'status: DIRTY',
                'mirror_policy: BROKEN',
                '',
            ]
        ),
        encoding='utf-8',
    )
    (snapshot / 'status-porcelain.txt').write_text(' M file.txt\n', encoding='utf-8')
    ts = module._parse_snapshot_timestamp(snapshot.name)
    assert ts is not None

    record = module._build_snapshot_record(snapshot, ts, nightly_hour=2, nightly_minute=20, window_minutes=45)
    evaluated = module._evaluate_nightly_record(record)

    assert evaluated['nightly_window_match'] is False
    assert evaluated['porcelain_empty'] is False
    assert evaluated['ok'] is False
    assert set(evaluated['alerts']) == {
        'result_not_pass',
        'status_not_clean',
        'branch_not_main',
        'mirror_policy_not_satisfied',
        'porcelain_not_empty',
    }


def test_determine_exit_code_and_main_write_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    module = _load_module()
    report = {
        'generated_utc': '20260516T070000Z',
        'overall_status': 'IN_PROGRESS',
        'target_runs': 3,
        'selected_nightly_runs': 1,
        'pending_runs': 2,
        'nightly_hour': 2,
        'nightly_minute': 20,
        'window_minutes': 45,
        'alerts_count': 0,
        'nightly_runs': [],
        'non_nightly_runs': [],
    }
    assert module.determine_exit_code(report, require_complete=False) == 0
    assert module.determine_exit_code(report, require_complete=True) == 2

    evidence_dir = tmp_path / 'evidence'
    output_path = tmp_path / 'checklist.md'
    json_out = tmp_path / 'checklist.json'
    monkeypatch.setattr(module, 'parse_args', lambda: SimpleNamespace(
        evidence_dir=str(evidence_dir),
        output=str(output_path),
        json_out=str(json_out),
        target_runs=3,
        nightly_hour=2,
        nightly_minute=20,
        window_minutes=45,
        require_complete=True,
    ))
    monkeypatch.setattr(module, 'build_report', lambda **kwargs: report)

    exit_code = module.main()

    assert exit_code == 2
    assert output_path.exists()
    assert json.loads(json_out.read_text(encoding='utf-8'))['overall_status'] == 'IN_PROGRESS'
    assert 'status=IN_PROGRESS' in capsys.readouterr().out
