"""Sprint-069 kickoff validator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runner import process_safety  # noqa: E402

REQUIRED_FILES = [
    'workflows/backlog-sprint-069.yaml',
    'workflows/sprint-069-delivery-flow.yaml',
    'docs/history/sprints/SPRINT-069.md',
    'docs/history/sprints/SPRINT-069-PROGRESS.md',
]

REQUIRED_TASK_LABELS = [
    'CTOA: Sprint-069 Validate',
    'CTOA: Sprint-069 State Sync',
    'CTOA: Sprint-069 Refresh Progress Diagram',
    'CTOA: Sprint-069 Wave Summary UTF-8',
    'CTOA: Sprint-069 Quality Snapshot',
    'CTOA: Sprint-069 Wave-1 Run',
]

REQUIRED_WORKFLOW_SNIPPETS = [
    'Sprint-069 delivery gate',
    'scripts/ops/sprint069_validate.py --run-tests --json-out runtime/ci-artifacts/sprint-069-validation.json',
    'Upload Sprint-069 evidence',
    'runtime/ci-artifacts/sprint-069-validation.json',
    'runtime/ci-artifacts/sprint-069-wave1-summary.txt',
    'docs/history/sprints/SPRINT-069-PROGRESS.md',
]

REQUIRED_HOOKS = {'on_start', 'on_complete', 'on_fail'}
REQUIRED_TASK_IDS = ['CTOA-338', 'CTOA-339', 'CTOA-340']


def _safe_yaml_load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def _check_required_files(root: Path) -> dict[str, Any]:
    missing = [rel for rel in REQUIRED_FILES if not (root / rel).exists()]
    return {
        'id': 'required_files',
        'ok': not missing,
        'hint': '' if not missing else f"missing files: {', '.join(missing)}",
    }


def _check_syntax(root: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for rel in ('workflows/backlog-sprint-069.yaml', 'workflows/sprint-069-delivery-flow.yaml'):
        path = root / rel
        try:
            _safe_yaml_load(path)
            checks.append({'id': f'syntax:{rel}', 'ok': True, 'hint': ''})
        except Exception as exc:
            checks.append({'id': f'syntax:{rel}', 'ok': False, 'hint': str(exc)})
    return checks


def _check_backlog_contract(root: Path) -> dict[str, Any]:
    backlog = _safe_yaml_load(root / 'workflows/backlog-sprint-069.yaml')
    tasks = backlog.get('tasks', []) if isinstance(backlog, dict) else []
    ids = [task.get('id') for task in tasks if isinstance(task, dict)]
    ok = isinstance(backlog, dict) and backlog.get('backlog_id') == 'sprint-069' and ids == REQUIRED_TASK_IDS
    hint = '' if ok else 'backlog_id must be sprint-069 and tasks must remain CTOA-338/339/340 in order'
    return {'id': 'backlog_contract', 'ok': ok, 'hint': hint}


def _check_hooks(root: Path) -> dict[str, Any]:
    flow = _safe_yaml_load(root / 'workflows/sprint-069-delivery-flow.yaml')
    tasks = flow.get('tasks', []) if isinstance(flow, dict) else []
    missing = []
    for task in tasks:
        if not REQUIRED_HOOKS.issubset(set(task.keys())):
            missing.append(task.get('id', '<unknown>'))
    return {
        'id': 'missing_hooks',
        'ok': not missing,
        'hint': '' if not missing else f"tasks missing hooks: {', '.join(missing)}",
    }


def _check_pipeline_gate(root: Path) -> dict[str, Any]:
    workflow = (root / '.github/workflows/ctoa-pipeline.yml').read_text(encoding='utf-8')
    missing = [snippet for snippet in REQUIRED_WORKFLOW_SNIPPETS if snippet not in workflow]
    ok = not missing
    return {'id': 'pipeline_gate', 'ok': ok, 'hint': '' if ok else f"missing workflow snippets: {', '.join(missing)}"}


def _check_local_tasks(root: Path) -> dict[str, Any]:
    tasks_json = (root / '.vscode/tasks.json').read_text(encoding='utf-8')
    missing = [label for label in REQUIRED_TASK_LABELS if label not in tasks_json]
    return {'id': 'local_tasks', 'ok': not missing, 'hint': '' if not missing else f"missing task labels: {', '.join(missing)}"}


def _check_plan_scope(root: Path) -> dict[str, Any]:
    backlog = _safe_yaml_load(root / 'workflows/backlog-sprint-069.yaml')
    focus = backlog.get('focus', '') if isinstance(backlog, dict) else ''
    ok = 'delivery continuity' in focus and 'CLI contract alignment' in focus
    return {
        'id': 'plan_scope',
        'ok': ok,
        'hint': '' if ok else 'focus should describe delivery continuity + CLI contract alignment',
    }


def _check_state_evidence_alignment(root: Path) -> dict[str, Any]:
    backlog = _safe_yaml_load(root / 'workflows/backlog-sprint-069.yaml')
    progress = root / 'docs/history/sprints/SPRINT-069-PROGRESS.md'
    mission = root / 'docs/history/sprints/SPRINT-069.md'
    ok = isinstance(backlog, dict) and backlog.get('backlog_id') == 'sprint-069' and progress.exists() and mission.exists()
    hint = '' if ok else 'backlog and sprint evidence must all point at sprint-069'
    return {'id': 'state_evidence_alignment', 'ok': ok, 'hint': hint}


def _check_progress_alignment(root: Path) -> dict[str, Any]:
    progress = (root / 'docs/history/sprints/SPRINT-069-PROGRESS.md').read_text(encoding='utf-8')
    normalized = progress.replace('\\\\', '/')
    source_ok = (
        'Source: workflows/backlog-sprint-069.yaml' in normalized
        or ('Source: ' in normalized and '/workflows/backlog-sprint-069.yaml' in normalized)
    )
    ok = 'Backlog: sprint-069' in normalized and source_ok
    return {
        'id': 'progress_alignment',
        'ok': ok,
        'hint': '' if ok else 'progress doc must point at sprint-069 backlog source',
    }


def _check_quality(run_tests: bool) -> dict[str, Any]:
    test_path = Path('tests/test_response_guardrails.py')
    if not run_tests:
        return {'id': 'quality_regression_tests', 'ok': test_path.exists(), 'hint': '' if test_path.exists() else 'missing tests/test_response_guardrails.py'}

    proc = process_safety.run_trusted(
        [process_safety.resolve_python(), '-m', 'pytest', 'tests/test_response_guardrails.py', '-q'],
        capture_output=True,
        text=True,
    )
    if proc.stdout:
        print(proc.stdout, end='')
    if proc.stderr:
        print(proc.stderr, end='', file=sys.stderr)
    return {'id': 'quality_regression_tests', 'ok': proc.returncode == 0, 'hint': '' if proc.returncode == 0 else 'pytest tests/test_response_guardrails.py -q failed'}


def build_report(root: Path, run_tests: bool) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.append(_check_required_files(root))
    checks.extend(_check_syntax(root))
    checks.append(_check_backlog_contract(root))
    checks.append(_check_hooks(root))
    checks.append(_check_pipeline_gate(root))
    checks.append(_check_local_tasks(root))
    checks.append(_check_plan_scope(root))
    checks.append(_check_state_evidence_alignment(root))
    checks.append(_check_progress_alignment(root))
    checks.append(_check_quality(run_tests))

    failed = [chk['id'] for chk in checks if not chk.get('ok')]
    status = 'PASS' if not failed else 'FAIL'
    return {
        'status': status,
        'summary': f"{len(checks) - len(failed)}/{len(checks)} checks passed",
        'checks': checks,
        'diagnostics': {
            'failed_count': len(failed),
            'failed_ids': failed,
            'critical_failed_ids': [],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Sprint-069 kickoff validator')
    parser.add_argument('--root', default='.', help='Workspace root directory')
    parser.add_argument('--run-tests', action='store_true', help='Run response guardrail regression test')
    parser.add_argument('--json-out', help='Write JSON report to file')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = build_report(root, args.run_tests)

    if args.json_out:
        out_path = (root / args.json_out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(f"[sprint069_validate] Report written to {out_path}")

    print(f"[sprint069_validate] {report['status']} - {report['summary']}")
    for chk in report['checks']:
        mark = 'OK' if chk.get('ok') else 'FAIL'
        suffix = f"  hint: {chk.get('hint')}" if chk.get('hint') else ''
        print(f"  [{mark}] {chk['id']}{suffix}")

    failed_ids = report['diagnostics']['failed_ids']
    if failed_ids:
        print(f"[sprint069_validate] failed checks: {', '.join(failed_ids)}")

    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())



