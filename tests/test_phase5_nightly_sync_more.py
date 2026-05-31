import importlib.util
from pathlib import Path
from types import SimpleNamespace

from urllib import error as urlerror

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    module_path = PROJECT_ROOT / 'scripts' / 'ops' / 'phase5_nightly_sync.py'
    spec = importlib.util.spec_from_file_location('phase5_nightly_sync_more', module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_key_path_prefers_env_then_userprofile(monkeypatch: pytest.MonkeyPatch):
    module = _load_module()
    monkeypatch.setenv('CTOA_VPS_KEY_PATH', 'C:/keys/custom')
    monkeypatch.setenv('USERPROFILE', 'C:/Users/tester')

    assert module._default_key_path() == Path('C:/keys/custom')

    monkeypatch.delenv('CTOA_VPS_KEY_PATH')
    assert module._default_key_path() == Path('C:/Users/tester/.ssh/ctoa_vps_auto_ed25519')


def test_run_raises_runtime_error_for_failed_checked_command(monkeypatch: pytest.MonkeyPatch):
    module = _load_module()
    monkeypatch.setattr(
        module.subprocess,
        'run',
        lambda *args, **kwargs: SimpleNamespace(returncode=2, stdout='bad stdout', stderr='bad stderr'),
    )

    with pytest.raises(RuntimeError, match='Command failed'):
        module._run(['fake', 'cmd'])


def test_post_json_handles_missing_url_and_http_error(monkeypatch: pytest.MonkeyPatch):
    module = _load_module()

    ok, detail = module._post_json('', {'x': 1})
    assert (ok, detail) == (False, 'missing_url')

    def raise_http(*args, **kwargs):
        raise urlerror.HTTPError('https://example.test', 503, 'down', None, None)

    monkeypatch.setattr(module.urlrequest, 'urlopen', raise_http)
    ok, detail = module._post_json('https://example.test', {'x': 1})
    assert (ok, detail) == (False, 'http_503')


def test_update_step9_closure_in_readme_appends_and_updates_timestamp(tmp_path: Path):
    module = _load_module()
    readme = tmp_path / 'README.md'
    readme.write_text('# Evidence\n', encoding='utf-8')

    created = module.update_step9_closure_in_readme(readme, '20260516T070000Z')
    updated = module.update_step9_closure_in_readme(readme, '20260517T070000Z')
    content = readme.read_text(encoding='utf-8')

    assert created is True
    assert updated is True
    assert content.count('## Phase 5 Step-9 Closure') == 1
    assert '- done_utc: 20260517T070000Z' in content


def test_main_returns_3_when_key_is_missing(monkeypatch: pytest.MonkeyPatch, capsys):
    module = _load_module()
    monkeypatch.setattr(module, 'parse_args', lambda: SimpleNamespace(key_path='C:/missing/key', local_evidence_dir='unused'))

    exit_code = module.main()

    assert exit_code == 3
    err = capsys.readouterr().err
    assert 'SSH key not found' in err


def test_main_returns_4_when_remote_listing_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    module = _load_module()
    key_path = tmp_path / 'key'
    key_path.write_text('dummy', encoding='utf-8')
    args = SimpleNamespace(
        key_path=str(key_path),
        local_evidence_dir=str(tmp_path / 'evidence'),
        host='host',
        user='user',
        ssh_timeout=20,
        remote_dir='/remote',
        checklist_json_out=str(tmp_path / 'checklist.json'),
        morning_brief_out=str(tmp_path / 'brief.md'),
        notify_env_file=str(tmp_path / 'notify.env'),
        discord_webhook_url='',
        slack_webhook_url='',
        auto_close_step9=False,
        sync_all=False,
        step9_plan_path=str(tmp_path / 'plan.md'),
        step9_closure_evidence_out=str(tmp_path / 'closure.md'),
        step9_evidence_readme_path=str(tmp_path / 'README.md'),
        checklist_script='unused',
        checklist_output='unused',
        target_runs=3,
        nightly_hour=2,
        nightly_minute=20,
        window_minutes=45,
        require_complete=False,
    )
    monkeypatch.setattr(module, 'parse_args', lambda: args)
    monkeypatch.setattr(module, 'list_remote_timestamps', lambda **kwargs: (_ for _ in ()).throw(RuntimeError('ssh failed')))

    exit_code = module.main()

    assert exit_code == 4
    err = capsys.readouterr().err
    assert 'Failed to list remote snapshots' in err
