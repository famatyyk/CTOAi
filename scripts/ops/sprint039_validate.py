"""Sprint-039 validator."""

from __future__ import annotations

import argparse
from pathlib import Path

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
    'workflows/backlog-sprint-039.yaml',
    'workflows/sprint-039-delivery-flow.yaml',
    'scripts/ops/sprint039_validate.py',
    '.vscode/tasks.json',
    '.github/workflows/ctoa-pipeline.yml',
]
REQUIRED_YAML_FILES = [
    'workflows/backlog-sprint-039.yaml',
    'workflows/sprint-039-delivery-flow.yaml',
]


def _config() -> SprintValidatorConfig:
    return SprintValidatorConfig(
        sprint_id='039',
        required_files=REQUIRED_FILES,
        required_yaml_files=REQUIRED_YAML_FILES,
        flow_file='workflows/sprint-039-delivery-flow.yaml',
        pipeline_file='.github/workflows/ctoa-pipeline.yml',
        pipeline_validator_snippet='scripts/ops/sprint039_validate.py',
        pipeline_artifact_snippet='runtime/ci-artifacts/sprint-039-validation.json',
        required_task_labels=[
            'CTOA: Sprint-039 Validate',
            'CTOA: Sprint-039 Wave-1 Run',
        ],
    )


def validate(root: Path) -> dict[str, object]:
    return _engine_build_report(root, _config(), run_tests=False)


def main() -> int:
    parser = argparse.ArgumentParser(description='Sprint-039 validator')
    parser.add_argument('--root', default='.', help='Workspace root directory')
    parser.add_argument('--json-out', help='Write JSON report to file')
    parser.add_argument('--run-tests', action='store_true', help='Reserved for compatibility')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f'Root directory not found: {root}')

    report = validate(root)

    if args.json_out:
        out_path = write_json_report(root, args.json_out, report)
        print(f'[sprint039_validate] Report written to {out_path}')

    print(f"[sprint039_validate] {report['status']} - {report['summary']}")
    for chk in report['checks']:
        mark = 'OK' if chk.get('ok') else 'FAIL'
        hint = f"  hint: {chk['hint']}" if chk.get('hint') else ''
        print(f"  [{mark}] {chk['id']}{hint}")

    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
