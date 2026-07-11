import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    module_path = PROJECT_ROOT / 'scripts' / 'ops' / 'sprint067_validate.py'
    spec = importlib.util.spec_from_file_location('sprint067_validate', module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_valid_workspace(root: Path) -> None:
    (root / 'workflows').mkdir(parents=True, exist_ok=True)
    (root / 'docs/history/sprints').mkdir(parents=True, exist_ok=True)
    (root / '.github/workflows').mkdir(parents=True, exist_ok=True)
    (root / '.vscode').mkdir(parents=True, exist_ok=True)
    (root / 'tests').mkdir(parents=True, exist_ok=True)

    (root / 'workflows/backlog-sprint-067.yaml').write_text(
        '\n'.join(
            [
                'backlog_id: sprint-067',
                'focus: Sprint-067 AI-layer consolidation + prompt/runtime governance',
                'tasks:',
                '  - id: CTOA-332',
                '  - id: CTOA-333',
                '  - id: CTOA-334',
                '',
            ]
        ),
        encoding='utf-8',
    )
    (root / 'workflows/sprint-067-delivery-flow.yaml').write_text(
        '\n'.join(
            [
                'tasks:',
                '  - id: CTOA-332',
                '    on_start: start',
                '    on_complete: complete',
                '    on_fail: fail',
                '  - id: CTOA-333',
                '    on_start: start',
                '    on_complete: complete',
                '    on_fail: fail',
                '  - id: CTOA-334',
                '    on_start: start',
                '    on_complete: complete',
                '    on_fail: fail',
                '',
            ]
        ),
        encoding='utf-8',
    )
    (root / 'docs/history/sprints/SPRINT-067.md').write_text('# Sprint-067\n', encoding='utf-8')
    (root / 'docs/history/sprints/SPRINT-067-PROGRESS.md').write_text(
        'Backlog: sprint-067\nSource: workflows/backlog-sprint-067.yaml\n',
        encoding='utf-8',
    )
    (root / '.github/workflows/ctoa-pipeline.yml').write_text(
        '\n'.join(
            [
                'Sprint-067 delivery gate',
                'scripts/ops/sprint067_validate.py --run-tests --json-out runtime/ci-artifacts/sprint-067-validation.json',
                'Upload Sprint-067 evidence',
                'runtime/ci-artifacts/sprint-067-validation.json',
                'runtime/ci-artifacts/sprint-067-wave1-summary.txt',
                'docs/history/sprints/SPRINT-067-PROGRESS.md',
                '',
            ]
        ),
        encoding='utf-8',
    )
    (root / '.vscode/tasks.json').write_text(
        '\n'.join(
            [
                'CTOA: Sprint-067 Validate',
                'CTOA: Sprint-067 State Sync',
                'CTOA: Sprint-067 Refresh Progress Diagram',
                'CTOA: Sprint-067 Wave Summary UTF-8',
                'CTOA: Sprint-067 Quality Snapshot',
                'CTOA: Sprint-067 Wave-1 Run',
                '',
            ]
        ),
        encoding='utf-8',
    )
    (root / 'tests/test_response_guardrails.py').write_text('def test_placeholder():\n    assert True\n', encoding='utf-8')


def _failed_ids(report: dict[str, object]) -> list[str]:
    diagnostics = report['diagnostics']
    assert isinstance(diagnostics, dict)
    failed_ids = diagnostics['failed_ids']
    assert isinstance(failed_ids, list)
    return failed_ids


def test_build_report_passes_for_complete_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _load_module()
    _write_valid_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    report = module.build_report(tmp_path, run_tests=False)

    assert report['status'] == 'PASS'
    assert report['summary'] == '11/11 checks passed'
    assert _failed_ids(report) == []


def test_build_report_flags_missing_local_tasks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _load_module()
    _write_valid_workspace(tmp_path)
    (tmp_path / '.vscode/tasks.json').write_text('CTOA: Sprint-067 Validate\n', encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    report = module.build_report(tmp_path, run_tests=False)

    assert report['status'] == 'FAIL'
    assert 'local_tasks' in _failed_ids(report)


def test_build_report_flags_missing_pipeline_gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _load_module()
    _write_valid_workspace(tmp_path)
    (tmp_path / '.github/workflows/ctoa-pipeline.yml').write_text('Upload Sprint-067 evidence\n', encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    report = module.build_report(tmp_path, run_tests=False)

    assert report['status'] == 'FAIL'
    assert 'pipeline_gate' in _failed_ids(report)


def test_build_report_flags_misaligned_progress_doc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _load_module()
    _write_valid_workspace(tmp_path)
    (tmp_path / 'docs/history/sprints/SPRINT-067-PROGRESS.md').write_text('Backlog: sprint-067\n', encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    report = module.build_report(tmp_path, run_tests=False)

    assert report['status'] == 'FAIL'
    assert 'progress_alignment' in _failed_ids(report)


def test_check_quality_reports_pytest_failure(monkeypatch: pytest.MonkeyPatch):
    module = _load_module()

    monkeypatch.setattr(module.Path, 'exists', lambda self: True)
    monkeypatch.setattr(module.process_safety, 'resolve_python', lambda: '/trusted/python')
    monkeypatch.setattr(
        module.process_safety,
        'run_trusted',
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout='failed output\n', stderr='boom\n'),
    )

    result = module._check_quality(run_tests=True)

    assert result['id'] == 'quality_regression_tests'
    assert result['ok'] is False
    assert 'pytest tests/test_response_guardrails.py -q failed' in result['hint']

def test_main_writes_json_and_returns_nonzero_for_failed_report(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    module = _load_module()
    report = {
        'status': 'FAIL',
        'summary': '10/11 checks passed',
        'checks': [{'id': 'progress_alignment', 'ok': False, 'hint': 'mismatch'}],
        'diagnostics': {'failed_ids': ['progress_alignment'], 'failed_count': 1, 'critical_failed_ids': []},
    }
    monkeypatch.setattr(module, 'build_report', lambda root, run_tests: report)
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        'parse_args',
        lambda self: SimpleNamespace(root=str(tmp_path), run_tests=False, json_out='runtime/ci-artifacts/sprint-067-validation.json'),
    )

    exit_code = module.main()

    assert exit_code == 1
    saved = tmp_path / 'runtime/ci-artifacts/sprint-067-validation.json'
    assert saved.exists()
    out = capsys.readouterr().out
    assert '[sprint067_validate] FAIL - 10/11 checks passed' in out
    assert '[sprint067_validate] failed checks: progress_alignment' in out
