import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(params=['061', '062', '063', '064', '065'])
def validator_case(request):
    sprint = request.param
    module_path = PROJECT_ROOT / 'scripts' / 'ops' / f'sprint{sprint}_validate.py'
    spec = importlib.util.spec_from_file_location(f'sprint{sprint}_validate', module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return sprint, module


def _write_workspace(root: Path, sprint: str) -> None:
    sprint_upper = f'SPRINT-{sprint}'
    (root / 'workflows').mkdir(parents=True, exist_ok=True)
    (root / 'docs/history/sprints').mkdir(parents=True, exist_ok=True)
    (root / '.github/workflows').mkdir(parents=True, exist_ok=True)
    (root / '.vscode').mkdir(parents=True, exist_ok=True)
    (root / 'scripts/ops').mkdir(parents=True, exist_ok=True)

    (root / f'workflows/backlog-sprint-{sprint}.yaml').write_text(
        '\n'.join(
            [
                f'backlog_id: sprint-{sprint}',
                'tasks:',
                '  - id: CTOA-001',
                '  - id: CTOA-002',
                '',
            ]
        ),
        encoding='utf-8',
    )
    (root / f'workflows/sprint-{sprint}-delivery-flow.yaml').write_text(
        '\n'.join(
            [
                'tasks:',
                '  - id: CTOA-001',
                '    on_start: start',
                '    on_complete: complete',
                '    on_fail: fail',
                '  - id: CTOA-002',
                '    on_start: start',
                '    on_complete: complete',
                '    on_fail: fail',
                '',
            ]
        ),
        encoding='utf-8',
    )
    (root / f'docs/history/sprints/{sprint_upper}.md').write_text(f'# {sprint_upper}\nStatus: IN_PROGRESS\n', encoding='utf-8')
    (root / f'docs/history/sprints/{sprint_upper}-PROGRESS.md').write_text(f'# {sprint_upper} Progress\n', encoding='utf-8')
    (root / 'scripts/ops/project_progress_diagram.py').write_text('# placeholder\n', encoding='utf-8')
    (root / f'scripts/ops/sprint{sprint}_validate.py').write_text('# placeholder\n', encoding='utf-8')
    (root / 'scripts/ops/sprint_state_sync.py').write_text('# placeholder\n', encoding='utf-8')
    (root / 'scripts/ops/wave_summary_utf8.py').write_text('# placeholder\n', encoding='utf-8')
    (root / '.github/workflows/ctoa-pipeline.yml').write_text(
        '\n'.join(
            [
                f'scripts/ops/sprint{sprint}_validate.py',
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
        f'CTOA: Sprint-{sprint} Refresh Progress Diagram',
        f'CTOA: Sprint-{sprint} Quality Snapshot',
        f'CTOA: Sprint-{sprint} State Sync',
        f'CTOA: Sprint-{sprint} Wave Summary UTF-8',
        f'CTOA: Sprint-{sprint} Wave-1 Run',
    ]
    (root / '.vscode/tasks.json').write_text('\n'.join(labels) + '\n', encoding='utf-8')


def _failed_ids(report: dict[str, object]) -> list[str]:
    diagnostics = report['diagnostics']
    assert isinstance(diagnostics, dict)
    failed_ids = diagnostics['failed_ids']
    assert isinstance(failed_ids, list)
    return failed_ids


def test_legacy_sprint_validators_pass_for_complete_workspace(tmp_path: Path, validator_case):
    sprint, module = validator_case
    _write_workspace(tmp_path, sprint)

    report = module.validate(tmp_path, run_tests=False)

    assert report['status'] == 'PASS'
    assert _failed_ids(report) == []


def test_legacy_sprint_validators_flag_missing_local_tasks(tmp_path: Path, validator_case):
    sprint, module = validator_case
    _write_workspace(tmp_path, sprint)
    (tmp_path / '.vscode/tasks.json').write_text(f'CTOA: Sprint-{sprint} Validate\n', encoding='utf-8')

    report = module.validate(tmp_path, run_tests=False)

    assert report['status'] == 'FAIL'
    assert 'local_tasks' in _failed_ids(report)


def test_legacy_sprint_validator_quality_check_reports_pytest_failure(monkeypatch: pytest.MonkeyPatch):
    sprint = '061'
    module_path = PROJECT_ROOT / 'scripts' / 'ops' / f'sprint{sprint}_validate.py'
    spec = importlib.util.spec_from_file_location(f'sprint{sprint}_validate', module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(
        module,
        '_run',
        lambda cmd, cwd: (1, 'failed output\nboom\n'),
    )

    result = module.check_quality_regression_tests(PROJECT_ROOT)

    assert result['id'] == 'quality_regression_tests'
    assert result['ok'] is False
    assert result['hint'] == 'Focused quality regression tests failed'
    assert 'pytest' in result['details']['command']


def test_legacy_sprint_validators_flag_released_doc_state_mismatch(tmp_path: Path, validator_case):
    sprint, module = validator_case
    _write_workspace(tmp_path, sprint)
    sprint_upper = f'SPRINT-{sprint}'
    (tmp_path / f'docs/history/sprints/{sprint_upper}.md').write_text(f'# {sprint_upper}\nStatus: RELEASED\n', encoding='utf-8')
    (tmp_path / 'runtime').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'runtime/task-state.yaml').write_text(
        '\n'.join(
            [
                'backlog_id: other-sprint',
                'tasks:',
                '  - id: CTOA-001',
                '    status: IN_PROGRESS',
                '',
            ]
        ),
        encoding='utf-8',
    )

    report = module.validate(tmp_path, run_tests=False)

    assert report['status'] == 'FAIL'
    assert 'state_evidence_alignment' in _failed_ids(report)
