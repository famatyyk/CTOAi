import json
from pathlib import Path
from types import SimpleNamespace

from scripts.ops import repo_hygiene_migration_plan as module


def test_classify_routes_known_and_unknown_paths():
    assert module.classify('.env', 'sensitive')['batch'] == 1
    assert module.classify('decompiled_lua', 'artifact')['action'] == 'move-to-private-storage'
    assert module.classify('sprint-061-notes.md', 'history')['target'] == 'docs/history/sprints/sprint-061-notes.md'
    assert module.classify('mystery-dir', 'odd finding')['action'] == 'manual-review'


def test_load_findings_and_write_markdown(tmp_path: Path):
    findings_path = tmp_path / 'findings.json'
    findings_path.write_text(json.dumps({'findings': [{'path': 'logs', 'reason': 'generated'}]}), encoding='utf-8')

    findings = module.load_findings(findings_path)
    plan = module.build_plan(findings)
    output = tmp_path / 'plan.md'
    module.write_markdown(plan, output)

    assert findings == [{'path': 'logs', 'reason': 'generated'}]
    markdown = output.read_text(encoding='utf-8')
    assert '# Repo Migration Batch Plan' in markdown
    assert '## Batch 1 (1 items)' in markdown
    assert '| MIG-001 | logs | review | Unclassified | untrack-and-ignore | local-only (ignored) | high |' in markdown


def test_main_writes_json_and_markdown(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    input_path = tmp_path / 'runtime/repo-hygiene/latest.json'
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text(
        json.dumps(
            {
                'findings': [
                    {
                        'path': 'decompiled_lua',
                        'reason': 'artifact',
                        'visibility': 'private',
                        'package_tier': 'Studio',
                        'surface_action': 'remove-from-public-surface',
                    }
                ]
            }
        ),
        encoding='utf-8',
    )
    monkeypatch.setattr(
        module.argparse.ArgumentParser,
        'parse_args',
        lambda self: SimpleNamespace(
            input='runtime/repo-hygiene/latest.json',
            json_out='runtime/repo-hygiene/migration-plan.json',
            md_out='docs/REPO_MIGRATION_BATCH_PLAN.md',
        ),
    )

    exit_code = module.main()

    assert exit_code == 0
    saved = json.loads((tmp_path / 'runtime/repo-hygiene/migration-plan.json').read_text(encoding='utf-8'))
    assert saved['status'] == 'READY'
    assert saved['batch_count'] == 1
    assert (tmp_path / 'docs/REPO_MIGRATION_BATCH_PLAN.md').exists()
    out = capsys.readouterr().out
    assert '[repo-migration-plan] status=READY findings=1 batches=1' in out
