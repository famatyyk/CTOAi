"""Sprint-041 validator."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runner import process_safety  # noqa: E402

try:
    from scripts.ops.sprint_validator_engine import (
        SprintValidatorConfig,
        build_report as _engine_build_report,
        write_json_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct file execution fallback
    from sprint_validator_engine import (
        SprintValidatorConfig,
        build_report as _engine_build_report,
        write_json_report,
    )

REQUIRED_FILES = [
    'workflows/backlog-sprint-041.yaml',
    'workflows/sprint-041-delivery-flow.yaml',
    'scripts/ops/sprint041_validate.py',
    '.vscode/tasks.json',
    '.github/workflows/ctoa-pipeline.yml',
]
REQUIRED_YAML_FILES = [
    'workflows/backlog-sprint-041.yaml',
    'workflows/sprint-041-delivery-flow.yaml',
]
FOCUSED_REGRESSION_TEST_FILES = [
    'tests/test_response_guardrails.py',
    'tests/test_sprint029_validate.py',
    'tests/test_sprint041_dashboard_ergonomics.py',
    'tests/test_sprint041_live_dashboard_status_context_panel.py',
]


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    executable = process_safety.resolve_executable(cmd[0])
    result = process_safety.run_trusted([executable, *cmd[1:]], cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def _quality_check(root: Path, run_tests: bool) -> dict[str, object] | None:
    if not run_tests:
        return None

    commands = [
        [process_safety.resolve_python(), '-m', 'pytest', test_file, '-q']
        for test_file in FOCUSED_REGRESSION_TEST_FILES
    ]
    results = [_run(cmd, cwd=root) for cmd in commands]
    code = max(result[0] for result in results)
    output = '\n'.join(result[1] for result in results)
    output_tail = '\n'.join(output.splitlines()[-20:])

    return {
        'id': 'quality_regression_tests',
        'ok': code == 0,
        'hint': 'Focused quality regression tests failed' if code != 0 else '',
        'details': {
            'commands': [' '.join(cmd) for cmd in commands],
            'output_tail': output_tail,
        },
    }


def _config() -> SprintValidatorConfig:
    return SprintValidatorConfig(
        sprint_id='041',
        required_files=REQUIRED_FILES,
        required_yaml_files=REQUIRED_YAML_FILES,
        flow_file='workflows/sprint-041-delivery-flow.yaml',
        pipeline_file='.github/workflows/ctoa-pipeline.yml',
        pipeline_validator_snippet='scripts/ops/sprint041_validate.py',
        pipeline_artifact_snippet='runtime/ci-artifacts/sprint-041-validation.json',
        required_task_labels=[
            'CTOA: Sprint-041 Validate',
            'CTOA: Sprint-041 Wave-1 Run',
        ],
        quality_check=_quality_check,
    )


def validate(root: Path, run_tests: bool) -> dict[str, object]:
    return _engine_build_report(root, _config(), run_tests=run_tests)


def main() -> int:
    parser = argparse.ArgumentParser(description='Sprint-041 validator')
    parser.add_argument('--root', default='.', help='Workspace root directory')
    parser.add_argument('--json-out', help='Write JSON report to file')
    parser.add_argument('--run-tests', action='store_true', help='Run checks')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f'Root directory not found: {root}')

    report = validate(root, run_tests=args.run_tests)

    if args.json_out:
        out_path = write_json_report(root, args.json_out, report)
        print(f'[sprint041_validate] Report written to {out_path}')

    print(f"[sprint041_validate] {report['status']} - {report['summary']}")
    for chk in report['checks']:
        mark = 'OK' if chk.get('ok') else 'FAIL'
        hint = f"  hint: {chk['hint']}" if chk.get('hint') else ''
        print(f"  [{mark}] {chk['id']}{hint}")

    failed_ids = report.get('diagnostics', {}).get('failed_ids', [])
    if failed_ids:
        print(f"[sprint041_validate] failed checks: {', '.join(failed_ids)}")

    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
