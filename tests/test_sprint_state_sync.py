import importlib.util
import json
from pathlib import Path

import pytest
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    module_path = PROJECT_ROOT / 'scripts' / 'ops' / 'sprint_state_sync.py'
    spec = importlib.util.spec_from_file_location('sprint_state_sync', module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_init_state_from_backlog_applies_defaults_and_skips_invalid_items(monkeypatch: pytest.MonkeyPatch):
    module = _load_module()
    monkeypatch.setattr(module, '_now_iso', lambda: '2026-05-31T12:00:00Z')

    state = module._init_state_from_backlog(
        {
            'backlog_id': 'sprint-067',
            'tasks': [
                {'id': 'CTOA-332', 'title': 'Registry', 'domain': ['agents'], 'assignees': ['queen-ctoa']},
                'ignored',
            ],
        }
    )

    assert state['backlog_id'] == 'sprint-067'
    assert state['history'] == []
    assert len(state['tasks']) == 1
    task = state['tasks'][0]
    assert task['status'] == 'NEW'
    assert task['ticks_in_status'] == 0
    assert task['updated_at'] == '2026-05-31T12:00:00Z'
    assert task['priority'] == 'P1'
    assert task['type'] == 'code'


def test_preview_release_counts_raises_for_missing_or_empty_backlog(tmp_path: Path):
    module = _load_module()
    backlog_path = tmp_path / 'workflows/backlog.yaml'
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_path.write_text('{}\n', encoding='utf-8')

    with pytest.raises(FileNotFoundError, match='Missing or empty backlog'):
        module._preview_release_counts(backlog_path)


def test_synchronize_state_initializes_and_releases_all_tasks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _load_module()
    timestamps = iter([
        '2026-05-31T12:00:00Z',
        '2026-05-31T12:00:01Z',
        '2026-05-31T12:00:02Z',
        '2026-05-31T12:00:03Z',
        '2026-05-31T12:00:04Z',
        '2026-05-31T12:00:05Z',
        '2026-05-31T12:00:06Z',
        '2026-05-31T12:00:07Z',
    ])
    monkeypatch.setattr(module, '_now_iso', lambda: next(timestamps))

    backlog_path = tmp_path / 'workflows/backlog.yaml'
    state_path = tmp_path / 'runtime/task-state.yaml'
    evidence_dir = tmp_path / 'runtime/ci-artifacts'
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_path.write_text(
        '\n'.join(
            [
                'backlog_id: sprint-067',
                'tasks:',
                '  - id: CTOA-332',
                '    title: Registry',
                '  - id: CTOA-333',
                '    title: Runtime',
                '',
            ]
        ),
        encoding='utf-8',
    )

    released, total, backlog_id = module.synchronize_state(
        backlog_path,
        state_path,
        'wave1 complete',
        evidence_dir=evidence_dir,
    )

    assert (released, total, backlog_id) == (2, 2, 'sprint-067')
    payload = yaml.safe_load(state_path.read_text(encoding='utf-8'))
    assert payload['backlog_id'] == 'sprint-067'
    assert payload['last_tick_at'] == '2026-05-31T12:00:06Z'
    assert payload['history'][-1]['reason'] == 'wave1 complete'
    assert [task['status'] for task in payload['tasks']] == ['RELEASED', 'RELEASED']
    assert payload['tasks'][0]['notes'][-1]['status'] == 'RELEASED'
    assert list((tmp_path / 'runtime').glob('.*.tmp')) == []


def test_sprint_state_sync_atomic_writer_uses_unique_temp_and_fsync():
    module = _load_module()
    source = Path(module.__file__).read_text(encoding='utf-8')

    assert 'path.with_suffix(path.suffix + ".tmp")' not in source
    assert 'uuid.uuid4().hex' in source
    assert 'os.fsync(fh.fileno())' in source

    evidence_json = evidence_dir / 'sprint-067-release-evidence-pack.json'
    evidence_md = evidence_dir / 'sprint-067-release-evidence-pack.md'
    assert evidence_json.exists()
    assert evidence_md.exists()
    evidence = json.loads(evidence_json.read_text(encoding='utf-8'))
    assert evidence['schema_version'] == 'ctoa.release_evidence_pack.v1'
    assert evidence['backlog_id'] == 'sprint-067'
    assert evidence['release']['released_count'] == 2


def test_synchronize_state_reuses_matching_state_and_adds_missing_task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = _load_module()
    timestamps = iter([
        '2026-05-31T12:10:00Z',
        '2026-05-31T12:10:01Z',
        '2026-05-31T12:10:02Z',
        '2026-05-31T12:10:03Z',
        '2026-05-31T12:10:04Z',
        '2026-05-31T12:10:05Z',
        '2026-05-31T12:10:06Z',
    ])
    monkeypatch.setattr(module, '_now_iso', lambda: next(timestamps))

    backlog_path = tmp_path / 'workflows/backlog.yaml'
    state_path = tmp_path / 'runtime/task-state.yaml'
    evidence_dir = tmp_path / 'runtime/ci-artifacts'
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    backlog_path.write_text(
        '\n'.join(
            [
                'backlog_id: sprint-067',
                'tasks:',
                '  - id: CTOA-332',
                '    title: Registry',
                '  - id: CTOA-333',
                '    title: Runtime',
                '',
            ]
        ),
        encoding='utf-8',
    )
    state_path.write_text(
        '\n'.join(
            [
                'backlog_id: sprint-067',
                'last_tick_at: null',
                'tasks:',
                '  - id: CTOA-332',
                '    title: Registry',
                '    priority: P2',
                '    type: code',
                '    domain: []',
                '    assignees: []',
                '    deliverables: []',
                '    status: IN_PROGRESS',
                '    ticks_in_status: 5',
                '    updated_at: old',
                '    notes: []',
                'history: []',
                '',
            ]
        ),
        encoding='utf-8',
    )

    released, total, backlog_id = module.synchronize_state(
        backlog_path,
        state_path,
        'wave1 complete',
        evidence_dir=evidence_dir,
    )

    assert (released, total, backlog_id) == (2, 2, 'sprint-067')
    payload = yaml.safe_load(state_path.read_text(encoding='utf-8'))
    assert len(payload['tasks']) == 2
    existing = next(task for task in payload['tasks'] if task['id'] == 'CTOA-332')
    added = next(task for task in payload['tasks'] if task['id'] == 'CTOA-333')
    assert existing['priority'] == 'P2'
    assert existing['status'] == 'RELEASED'
    assert added['title'] == 'Runtime'
    assert added['status'] == 'RELEASED'

