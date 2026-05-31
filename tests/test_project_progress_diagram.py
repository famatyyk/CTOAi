import importlib.util
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    module_path = PROJECT_ROOT / 'scripts' / 'ops' / 'project_progress_diagram.py'
    spec = importlib.util.spec_from_file_location('project_progress_diagram', module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_state_by_task_id_normalizes_invalid_status_and_backlog_mismatch():
    module = _load_module()

    mismatch = module._state_by_task_id({'backlog_id': 'other', 'tasks': [{'id': 'A', 'status': 'RELEASED'}]}, 'sprint-067')
    assert mismatch == {}

    state = {
        'backlog_id': 'sprint-067',
        'tasks': [
            {'id': 'A', 'status': 'RELEASED'},
            {'id': 'B', 'status': 'NOT_A_REAL_STATUS'},
            {'id': '', 'status': 'BLOCKED'},
            'ignored',
        ],
    }
    result = module._state_by_task_id(state, 'sprint-067')

    assert result == {'A': 'RELEASED', 'B': 'NEW'}


def test_generate_writes_markdown_with_percentages_and_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _load_module()
    backlog_path = tmp_path / 'workflows/backlog.yaml'
    state_path = tmp_path / 'runtime/task-state.yaml'
    output_path = tmp_path / 'docs/progress.md'
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    backlog_path.write_text(
        '\n'.join(
            [
                'backlog_id: sprint-067',
                'tasks:',
                '  - id: CTOA-332',
                '  - id: CTOA-333',
                '  - id: CTOA-334',
                '',
            ]
        ),
        encoding='utf-8',
    )
    state_path.write_text(
        '\n'.join(
            [
                'backlog_id: sprint-067',
                'tasks:',
                '  - id: CTOA-332',
                '    status: RELEASED',
                '  - id: CTOA-333',
                '    status: IN_PROGRESS',
                '',
            ]
        ),
        encoding='utf-8',
    )
    monkeypatch.setattr(module, '_now_iso', lambda: '2026-05-31T12:00:00Z')

    report = module.generate(backlog_path, state_path, output_path, 'CTOAi')

    assert report['backlog_id'] == 'sprint-067'
    assert report['total'] == 3
    assert report['released'] == 1
    content = output_path.read_text(encoding='utf-8')
    assert 'Completion: 33.3% (1/3 RELEASED)' in content
    assert '| IN_FLIGHT | 1 | 33.3% |' in content
    assert '| NEW | 1 | 33.3% |' in content
    assert 'Generated: 2026-05-31T12:00:00Z' in content


def test_generate_raises_when_backlog_tasks_is_not_a_list(tmp_path: Path):
    module = _load_module()
    backlog_path = tmp_path / 'workflows/backlog.yaml'
    output_path = tmp_path / 'docs/progress.md'
    backlog_path.parent.mkdir(parents=True, exist_ok=True)

    backlog_path.write_text('backlog_id: sprint-067\ntasks: invalid\n', encoding='utf-8')

    with pytest.raises(ValueError, match='tasks must be a list'):
        module.generate(backlog_path, None, output_path, 'CTOAi')
