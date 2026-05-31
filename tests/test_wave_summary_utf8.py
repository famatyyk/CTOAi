import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    module_path = PROJECT_ROOT / 'scripts' / 'ops' / 'wave_summary_utf8.py'
    spec = importlib.util.spec_from_file_location('wave_summary_utf8', module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_state_release_counts_reports_alignment_and_mismatch():
    module = _load_module()
    backlog = {'tasks': [{'id': 'A'}, {'id': 'B'}]}
    state = {'backlog_id': 'sprint-067', 'tasks': [{'id': 'A', 'status': 'RELEASED'}, {'id': 'B', 'status': 'IN_PROGRESS'}]}

    released, total, alignment = module._state_release_counts(state, backlog, 'sprint-067')
    assert (released, total, alignment) == (1, 2, 'aligned')

    released, total, alignment = module._state_release_counts(state, backlog, 'sprint-066')
    assert (released, total, alignment) == (1, 2, 'mismatch:sprint-067')


def test_generate_summary_uses_defaults_when_inputs_missing(tmp_path: Path, monkeypatch):
    module = _load_module()
    validation_json = tmp_path / 'validation.json'
    hygiene_json = tmp_path / 'hygiene.json'
    state_yaml = tmp_path / 'state.yaml'
    backlog_yaml = tmp_path / 'backlog.yaml'
    output = tmp_path / 'summary.txt'
    backlog_yaml.write_text(
        '\n'.join(
            [
                'backlog_id: sprint-067',
                'tasks:',
                '  - id: CTOA-332',
                '  - id: CTOA-333',
                '',
            ]
        ),
        encoding='utf-8',
    )
    monkeypatch.setattr(module, '_now_iso', lambda: '2026-05-31T12:00:00Z')

    out_path = module.generate_summary(
        sprint_id='067',
        validation_json=validation_json,
        output=output,
        repo_hygiene_json=hygiene_json,
        state_yaml=state_yaml,
        backlog_yaml=backlog_yaml,
    )

    assert out_path == output
    content = output.read_text(encoding='utf-8')
    assert 'validation_status: UNKNOWN' in content
    assert 'repo_hygiene_status: UNKNOWN' in content
    assert 'runtime_release: 0/2' in content
    assert 'runtime_alignment: mismatch:unknown' in content
    assert 'generated_at: 2026-05-31T12:00:00Z' in content


def test_main_writes_summary_and_returns_zero(tmp_path: Path, monkeypatch, capsys):
    module = _load_module()
    validation_json = tmp_path / 'validation.json'
    hygiene_json = tmp_path / 'hygiene.json'
    state_yaml = tmp_path / 'state.yaml'
    backlog_yaml = tmp_path / 'backlog.yaml'
    output = tmp_path / 'summary.txt'

    validation_json.write_text(json.dumps({'status': 'PASS', 'summary': '11/11 checks passed'}), encoding='utf-8')
    hygiene_json.write_text(json.dumps({'status': 'PASS'}), encoding='utf-8')
    state_yaml.write_text(
        '\n'.join(
            [
                'backlog_id: sprint-067',
                'tasks:',
                '  - id: CTOA-332',
                '    status: RELEASED',
                '',
            ]
        ),
        encoding='utf-8',
    )
    backlog_yaml.write_text(
        '\n'.join(
            [
                'backlog_id: sprint-067',
                'tasks:',
                '  - id: CTOA-332',
                '',
            ]
        ),
        encoding='utf-8',
    )
    monkeypatch.setattr(module.argparse.ArgumentParser, 'parse_args', lambda self: SimpleNamespace(
        sprint_id='067',
        validation_json=str(validation_json),
        output=str(output),
        repo_hygiene_json=str(hygiene_json),
        state_yaml=str(state_yaml),
        backlog_yaml=str(backlog_yaml),
    ))

    exit_code = module.main()

    assert exit_code == 0
    assert output.exists()
    assert '[wave_summary_utf8] wrote' in capsys.readouterr().out
