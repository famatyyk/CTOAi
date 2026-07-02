import json
from pathlib import Path
from types import SimpleNamespace

from scripts.ops import repo_hygiene_audit as module


def test_tracked_top_level_entries_returns_top_level_names(monkeypatch):
    monkeypatch.setattr(
        module.subprocess,
        'run',
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout='docs/file.md\nrunner/app.py\nREADME.md\n', stderr=''),
    )

    tracked = module._tracked_top_level_entries()

    assert tracked == {'docs', 'runner', 'README.md'}


def test_tracked_top_level_entries_returns_empty_set_on_git_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise module.subprocess.CalledProcessError(returncode=1, cmd=['git', 'ls-files'])

    monkeypatch.setattr(module.subprocess, 'run', fail)

    assert module._tracked_top_level_entries() == set()


def test_scan_top_level_ignores_untracked_local_outputs_and_flags_unknowns(tmp_path: Path, monkeypatch):
    for name in ['docs', 'mobile_console', 'build', 'node_modules', '.agents', '.codex', '_local_archive', 'mystery_dir', 'decompiled_sample']:
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    (tmp_path / 'analyze_enc3.py').write_text('print(1)\n', encoding='utf-8')
    (tmp_path / 'AGENTS.md').write_text('# Repository Guidelines\n', encoding='utf-8')
    (tmp_path / '.env.kingsvale').write_text('SECRET=local\n', encoding='utf-8')

    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module, '_tracked_top_level_entries', lambda: {'docs', 'mobile_console', 'analyze_enc3.py'})

    report = module._scan_top_level()

    assert report['status'] == 'REVIEW_REQUIRED'
    paths = {item['path']: item for item in report['findings']}
    assert 'AGENTS.md' not in paths
    assert 'build' not in paths
    assert 'node_modules' not in paths
    assert '.agents' not in paths
    assert '.codex' not in paths
    assert '_local_archive' not in paths
    assert '.env.kingsvale' not in paths
    assert paths['mystery_dir']['visibility'] == 'review'
    assert paths['analyze_enc3.py']['reason'] == 'top-level one-off or research artifact file'
    assert paths['decompiled_sample']['surface_action'] == 'remove-from-public-surface'
    assert report['summary']['private_count'] == 1
    assert report['summary']['review_count'] == 2


def test_main_writes_json_and_honors_fail_on_findings(tmp_path: Path, monkeypatch, capsys):
    report = {
        'repo_root': str(tmp_path),
        'findings': [{'path': 'mystery_dir', 'reason': 'unknown'}],
        'finding_count': 1,
        'summary': {'private_count': 0, 'public_count': 0, 'review_count': 1},
        'status': 'REVIEW_REQUIRED',
    }
    monkeypatch.setattr(module, '_scan_top_level', lambda: report)
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module.argparse.ArgumentParser, 'parse_args', lambda self: SimpleNamespace(json_out='runtime/repo-hygiene.json', fail_on_findings=True))

    exit_code = module.main()

    assert exit_code == 1
    out = capsys.readouterr().out
    assert '[repo-hygiene] status=REVIEW_REQUIRED findings=1' in out
    saved = json.loads((tmp_path / 'runtime/repo-hygiene.json').read_text(encoding='utf-8'))
    assert saved['finding_count'] == 1
