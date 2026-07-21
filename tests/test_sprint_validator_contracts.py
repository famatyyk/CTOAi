import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(
    params=[
        ("066", ["CTOA-329", "CTOA-330", "CTOA-331"]),
        ("067", ["CTOA-332", "CTOA-333", "CTOA-334"]),
        ("068", ["CTOA-335", "CTOA-336", "CTOA-337"]),
        ("069", ["CTOA-338", "CTOA-339", "CTOA-340"]),
    ]
)
def validator_case(request):
    sprint, task_ids = request.param
    module_path = PROJECT_ROOT / 'scripts' / 'ops' / f'sprint{sprint}_validate.py'
    spec = importlib.util.spec_from_file_location(f'sprint{sprint}_validate', module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return sprint, task_ids, module


def _write_validator_workspace(root: Path, sprint: str, task_ids: list[str]) -> None:
    sprint_upper = f'SPRINT-{sprint}'
    (root / 'workflows').mkdir(parents=True, exist_ok=True)
    (root / 'docs/history/sprints').mkdir(parents=True, exist_ok=True)
    (root / '.github/workflows').mkdir(parents=True, exist_ok=True)
    (root / '.vscode').mkdir(parents=True, exist_ok=True)
    (root / 'tests').mkdir(parents=True, exist_ok=True)

    focus_line = {
        '066': 'Sprint-066 packaging + release hardening',
        '067': 'Sprint-067 AI-layer consolidation + prompt/runtime governance',
        '068': 'Sprint-068 delivery/governance closure + validator CLI hardening',
        '069': 'Sprint-069 delivery continuity + CLI contract alignment',
    }[sprint]
    progress_lines = [f'Backlog: sprint-{sprint}', f'Source: workflows/backlog-sprint-{sprint}.yaml']
    if sprint == '066':
        progress_lines = ['# Sprint-066 Progress', '']

    backlog_lines = [
        f'backlog_id: sprint-{sprint}',
        f'focus: {focus_line}',
        'tasks:',
    ]
    for task_id in task_ids:
        backlog_lines.append(f'  - id: {task_id}')
    backlog_lines.append('')

    flow_lines = ['tasks:']
    for task_id in task_ids:
        flow_lines.extend(
            [
                f'  - id: {task_id}',
                '    on_start: start',
                '    on_complete: complete',
                '    on_fail: fail',
            ]
        )
    flow_lines.append('')

    (root / f'workflows/backlog-sprint-{sprint}.yaml').write_text('\n'.join(backlog_lines), encoding='utf-8')
    (root / f'workflows/sprint-{sprint}-delivery-flow.yaml').write_text('\n'.join(flow_lines), encoding='utf-8')
    (root / f'docs/history/sprints/{sprint_upper}.md').write_text(f'# {sprint_upper}\n', encoding='utf-8')
    (root / f'docs/history/sprints/{sprint_upper}-PROGRESS.md').write_text('\n'.join(progress_lines) + '\n', encoding='utf-8')
    (root / '.github/workflows/ctoa-pipeline.yml').write_text(
        '\n'.join(
            [
                f'Sprint-{sprint} delivery gate',
                f'scripts/ops/sprint{sprint}_validate.py --run-tests --json-out runtime/ci-artifacts/sprint-{sprint}-validation.json',
                f'Upload Sprint-{sprint} evidence',
                f'runtime/ci-artifacts/sprint-{sprint}-validation.json',
                f'runtime/ci-artifacts/sprint-{sprint}-wave1-summary.txt',
                f'docs/history/sprints/{sprint_upper}-PROGRESS.md',
                '',
            ]
        ),
        encoding='utf-8',
    )
    labels = [
        f'CTOA: Sprint-{sprint} Validate',
        f'CTOA: Sprint-{sprint} State Sync',
        f'CTOA: Sprint-{sprint} Refresh Progress Diagram',
        f'CTOA: Sprint-{sprint} Wave Summary UTF-8',
        f'CTOA: Sprint-{sprint} Quality Snapshot',
        f'CTOA: Sprint-{sprint} Wave-1 Run',
    ]
    (root / '.vscode/tasks.json').write_text('\n'.join(labels) + '\n', encoding='utf-8')
    (root / 'tests/test_response_guardrails.py').write_text('def test_placeholder():\n    assert True\n', encoding='utf-8')


def _failed_ids(report: dict[str, object]) -> list[str]:
    diagnostics = report['diagnostics']
    assert isinstance(diagnostics, dict)
    failed_ids = diagnostics['failed_ids']
    assert isinstance(failed_ids, list)
    return failed_ids


def test_sprint_validators_pass_for_complete_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, validator_case):
    sprint, task_ids, module = validator_case
    _write_validator_workspace(tmp_path, sprint, task_ids)
    monkeypatch.chdir(tmp_path)

    report = module.build_report(tmp_path, run_tests=False)

    assert report['status'] == 'PASS'
    assert _failed_ids(report) == []


def test_sprint_validators_flag_missing_local_tasks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, validator_case):
    sprint, task_ids, module = validator_case
    _write_validator_workspace(tmp_path, sprint, task_ids)
    (tmp_path / '.vscode/tasks.json').write_text(f'CTOA: Sprint-{sprint} Validate\n', encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    report = module.build_report(tmp_path, run_tests=False)

    assert report['status'] == 'FAIL'
    assert 'local_tasks' in _failed_ids(report)


def test_sprint066_quality_check_reports_pytest_failure(monkeypatch: pytest.MonkeyPatch):
    module_path = PROJECT_ROOT / 'scripts' / 'ops' / 'sprint066_validate.py'
    spec = importlib.util.spec_from_file_location('sprint066_validate', module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

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

def test_sprint066_main_writes_json_and_reports_fail(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys):
    module_path = PROJECT_ROOT / 'scripts' / 'ops' / 'sprint066_validate.py'
    spec = importlib.util.spec_from_file_location('sprint066_validate_main', module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    report = {
        'status': 'FAIL',
        'summary': '7/8 checks passed',
        'checks': [{'id': 'local_tasks', 'ok': False, 'hint': 'missing'}],
        'diagnostics': {'failed_ids': ['local_tasks'], 'failed_count': 1, 'critical_failed_ids': []},
    }
    monkeypatch.setattr(module, 'build_report', lambda root, run_tests: report)
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        'parse_args',
        lambda self: SimpleNamespace(root=str(tmp_path), run_tests=False, json_out='runtime/ci-artifacts/sprint-066-validation.json'),
    )

    exit_code = module.main()

    assert exit_code == 1
    saved = tmp_path / 'runtime/ci-artifacts/sprint-066-validation.json'
    assert saved.exists()
    out = capsys.readouterr().out
    assert '[sprint066_validate] FAIL - 7/8 checks passed' in out
    assert '[sprint066_validate] failed checks: local_tasks' in out
