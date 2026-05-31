"""Sprint-067 kickoff validator."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REQUIRED_FILES = [
    'workflows/backlog-sprint-067.yaml',
    'workflows/sprint-067-delivery-flow.yaml',
    'docs/history/sprints/SPRINT-067.md',
    'docs/history/sprints/SPRINT-067-PROGRESS.md',
]

REQUIRED_TASK_LABELS = [
    'CTOA: Sprint-067 Validate',
    'CTOA: Sprint-067 State Sync',
    'CTOA: Sprint-067 Refresh Progress Diagram',
    'CTOA: Sprint-067 Wave Summary UTF-8',
    'CTOA: Sprint-067 Quality Snapshot',
    'CTOA: Sprint-067 Wave-1 Run',
]

REQUIRED_WORKFLOW_SNIPPETS = [
    'Sprint-067 delivery gate',
    'scripts/ops/sprint067_validate.py --run-tests --json-out runtime/ci-artifacts/sprint-067-validation.json',
    'Upload Sprint-067 evidence',
    'runtime/ci-artifacts/sprint-067-validation.json',
    'runtime/ci-artifacts/sprint-067-wave1-summary.txt',
    'docs/history/sprints/SPRINT-067-PROGRESS.md',
]

REQUIRED_HOOKS = {'on_start', 'on_complete', 'on_fail'}
REQUIRED_TASK_IDS = ['CTOA-332', 'CTOA-333', 'CTOA-334']


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
    for rel in ('workflows/backlog-sprint-067.yaml', 'workflows/sprint-067-delivery-flow.yaml'):
        path = root / rel
        try:
            _safe_yaml_load(path)
            checks.append({'id': f'syntax:{rel}', 'ok': True, 'hint': ''})
        except Exception as exc:
            checks.append({'id': f'syntax:{rel}', 'ok': False, 'hint': str(exc)})
    return checks


def _check_backlog_contract(root: Path) -> dict[str, Any]:
    backlog = _safe_yaml_load(root / 'workflows/backlog-sprint-067.yaml')
    tasks = backlog.get('tasks', []) if isinstance(backlog, dict) else []
    ids = [task.get('id') for task in tasks if isinstance(task, dict)]
    ok = isinstance(backlog, dict) and backlog.get('backlog_id') == 'sprint-067' and ids == REQUIRED_TASK_IDS
    hint = '' if ok else 'backlog_id must be sprint-067 and tasks must remain CTOA-332/333/334 in order'
    return {'id': 'backlog_contract', 'ok': ok, 'hint': hint}


def _check_hooks(root: Path) -> dict[str, Any]:
    flow = _safe_yaml_load(root / 'workflows/sprint-067-delivery-flow.yaml')
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
    backlog = _safe_yaml_load(root / 'workflows/backlog-sprint-067.yaml')
    focus = backlog.get('focus', '') if isinstance(backlog, dict) else ''
    ok = 'AI-layer consolidation' in focus and 'prompt/runtime governance' in focus
    return {
        'id': 'plan_scope',
        'ok': ok,
        'hint': '' if ok else 'focus should describe AI-layer consolidation + prompt/runtime governance',
    }


def _check_state_evidence_alignment(root: Path) -> dict[str, Any]:
    backlog = _safe_yaml_load(root / 'workflows/backlog-sprint-067.yaml')
    progress = root / 'docs/history/sprints/SPRINT-067-PROGRESS.md'
    mission = root / 'docs/history/sprints/SPRINT-067.md'
    ok = isinstance(backlog, dict) and backlog.get('backlog_id') == 'sprint-067' and progress.exists() and mission.exists()
    hint = '' if ok else 'backlog and sprint evidence must all point at sprint-067'
    return {'id': 'state_evidence_alignment', 'ok': ok, 'hint': hint}


def _check_progress_alignment(root: Path) -> dict[str, Any]:
    progress = (root / 'docs/history/sprints/SPRINT-067-PROGRESS.md').read_text(encoding='utf-8')
    ok = 'Backlog: sprint-067' in progress and 'Source: workflows/backlog-sprint-067.yaml' in progress
    return {
        'id': 'progress_alignment',
        'ok': ok,
        'hint': '' if ok else 'progress doc must point at sprint-067 backlog source',
    }


def _check_quality(run_tests: bool) -> dict[str, Any]:
    test_path = Path('tests/test_response_guardrails.py')
    if not run_tests:
        return {'id': 'quality_regression_tests', 'ok': test_path.exists(), 'hint': '' if test_path.exists() else 'missing tests/test_response_guardrails.py'}

    proc = subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_response_guardrails.py', '-q'], capture_output=True, text=True)
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
    parser = argparse.ArgumentParser(description='Sprint-067 kickoff validator')
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
        print(f"[sprint067_validate] Report written to {out_path}")

    print(f"[sprint067_validate] {report['status']} - {report['summary']}")
    for chk in report['checks']:
        mark = 'OK' if chk.get('ok') else 'FAIL'
        suffix = f"  hint: {chk.get('hint')}" if chk.get('hint') else ''
        print(f"  [{mark}] {chk['id']}{suffix}")

    failed_ids = report['diagnostics']['failed_ids']
    if failed_ids:
        print(f"[sprint067_validate] failed checks: {', '.join(failed_ids)}")

    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
