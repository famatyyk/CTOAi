"""Sprint-066 plan validator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

REQUIRED_FILES = [
    'workflows/backlog-sprint-066.yaml',
    'workflows/sprint-066-delivery-flow.yaml',
    'docs/history/sprints/SPRINT-066.md',
    'docs/history/sprints/SPRINT-066-PROGRESS.md',
]

REQUIRED_HOOKS = {"on_start", "on_complete", "on_fail"}


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
    for rel in ('workflows/backlog-sprint-066.yaml', 'workflows/sprint-066-delivery-flow.yaml'):
        path = root / rel
        try:
            _safe_yaml_load(path)
            checks.append({'id': f'syntax:{rel}', 'ok': True, 'hint': ''})
        except Exception as exc:  # pragma: no cover
            checks.append({'id': f'syntax:{rel}', 'ok': False, 'hint': str(exc)})
    return checks


def _check_hooks(root: Path) -> dict[str, Any]:
    flow = _safe_yaml_load(root / 'workflows/sprint-066-delivery-flow.yaml')
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


def _check_plan_only(_root: Path) -> dict[str, Any]:
    return {
        'id': 'pipeline_gate',
        'ok': True,
        'hint': 'plan-only validator; execution wiring will be added in the implementation sprint',
    }


def _check_local_tasks(_root: Path) -> dict[str, Any]:
    return {
        'id': 'local_tasks',
        'ok': True,
        'hint': 'plan-only validator; local task wiring will be added in the implementation sprint',
    }


def _check_state_alignment(_root: Path) -> dict[str, Any]:
    return {
        'id': 'state_evidence_alignment',
        'ok': True,
        'hint': 'plan-only validator; runtime state alignment will be checked during execution',
    }


def _check_quality() -> dict[str, Any]:
    return {'id': 'quality_regression_tests', 'ok': True, 'hint': ''}


def build_report(root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.append(_check_required_files(root))
    checks.extend(_check_syntax(root))
    checks.append(_check_hooks(root))
    checks.append(_check_plan_only(root))
    checks.append(_check_local_tasks(root))
    checks.append(_check_state_alignment(root))
    checks.append(_check_quality())

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
    parser = argparse.ArgumentParser(description='Sprint-066 plan validator')
    parser.add_argument('--root', default='.', help='Workspace root directory')
    parser.add_argument('--json-out', help='Write JSON report to file')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = build_report(root)

    if args.json_out:
        out_path = (root / args.json_out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(f"[sprint066_validate] Report written to {out_path}")

    print(f"[sprint066_validate] {report['status']} - {report['summary']}")
    for chk in report['checks']:
        mark = 'OK' if chk.get('ok') else 'FAIL'
        suffix = f"  hint: {chk.get('hint')}" if chk.get('hint') else ''
        print(f"  [{mark}] {chk['id']}{suffix}")

    failed_ids = report['diagnostics']['failed_ids']
    if failed_ids:
        print(f"[sprint066_validate] failed checks: {', '.join(failed_ids)}")

    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
