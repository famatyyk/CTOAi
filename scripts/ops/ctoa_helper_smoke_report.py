#!/usr/bin/env python3
"""Build a coverage report from Solteria helper SmokeAll screenshots."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCREENSHOT_DIR = ROOT / "runtime" / "otclient_ui_preview"
EXPECTED_VIEWS = [
    "overview",
    "healing",
    "heal_friend",
    "conditions",
    "hunting",
    "hunting_magic",
    "cavebot",
    "equipment",
    "tools",
    "tools_pvp",
    "tools_hud",
    "tools_timer",
    "tools_diag",
    "scripting",
    "profile",
    "ui",
]

ZEROBOT_MODULE_MAP = {
    "overview": "ZeroBot shell / account overview",
    "healing": "Healing",
    "heal_friend": "Heal Friend",
    "conditions": "Conditions",
    "hunting": "Hunting / Targeting",
    "hunting_magic": "Hunting / Magic Shooter",
    "cavebot": "CaveBot",
    "equipment": "Equipment",
    "tools": "Tools / Helper",
    "tools_pvp": "Tools / PvP",
    "tools_hud": "Tools / HUD",
    "tools_timer": "Tools / Timer",
    "tools_diag": "Tools / Diagnostics",
    "scripting": "Scripting",
    "profile": "Settings / profiles / hotkeys",
    "ui": "Engine / hotkey / HUD",
}


@dataclass(frozen=True)
class ViewEvidence:
    view: str
    screenshot: str | None
    size_bytes: int | None


@dataclass(frozen=True)
class SmokeReport:
    run_id: str
    expected_count: int
    covered_count: int
    missing: list[str]
    modal_limited: bool
    acceptance_status: str
    views: list[ViewEvidence]


def _view_from_name(path: Path, run_id: str, prefix: str) -> str | None:
    pattern = rf"^{re.escape(prefix)}-(?P<view>.+)-{re.escape(run_id)}\d+\.png$"
    match = re.match(pattern, path.name)
    if not match:
        return None
    return match.group("view")


def collect_report(
    screenshot_dir: Path,
    run_id: str,
    *,
    modal_limited: bool = True,
    prefix: str = "solteria-helper-testenv",
) -> SmokeReport:
    found: dict[str, Path] = {}
    for path in sorted(screenshot_dir.glob(f"{prefix}-*-{run_id}*.png")):
        view = _view_from_name(path, run_id, prefix)
        if view in EXPECTED_VIEWS:
            found[view] = path

    def display_path(path: Path) -> str:
        try:
            return path.relative_to(ROOT).as_posix()
        except ValueError:
            return path.as_posix()

    views = [
        ViewEvidence(
            view=view,
            screenshot=display_path(found[view]) if view in found else None,
            size_bytes=found[view].stat().st_size if view in found else None,
        )
        for view in EXPECTED_VIEWS
    ]
    missing = [view.view for view in views if view.screenshot is None]
    return SmokeReport(
        run_id=run_id,
        expected_count=len(EXPECTED_VIEWS),
        covered_count=len(EXPECTED_VIEWS) - len(missing),
        missing=missing,
        modal_limited=modal_limited,
        acceptance_status="blocked_by_character_modal" if modal_limited else "ready_for_visual_review",
        views=views,
    )


def manifest_binding(manifest_path: Path) -> dict[str, str] | None:
    """Return content binding for the dev manifest used by this smoke run."""
    if not manifest_path.is_file():
        return None
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "path": str(manifest_path.resolve()),
        "created_at": str(payload.get("created_at") or ""),
        "sha256": digest,
    }


def render_markdown(report: SmokeReport) -> str:
    lines = [
        "# Solteria Helper SmokeAll Coverage",
        "",
        f"- Run id: `{report.run_id}`",
        f"- Coverage: `{report.covered_count}/{report.expected_count}`",
        f"- Modal-limited: `{str(report.modal_limited).lower()}`",
        f"- Acceptance status: `{report.acceptance_status}`",
        "",
    ]
    if report.missing:
        lines.append("## Missing")
        lines.append("")
        for view in report.missing:
            lines.append(f"- `{view}`")
        lines.append("")
    lines.append("## Views")
    lines.append("")
    for view in report.views:
        module = ZEROBOT_MODULE_MAP.get(view.view, view.view)
        if view.screenshot:
            lines.append(f"- `{view.view}` / {module}: [{Path(view.screenshot).name}]({view.screenshot}) ({view.size_bytes} bytes)")
        else:
            lines.append(f"- `{view.view}` / {module}: missing")
    lines.append("")
    lines.append("## ZeroBot Mapping")
    lines.append("")
    for view in EXPECTED_VIEWS:
        lines.append(f"- `{view}` -> {ZEROBOT_MODULE_MAP[view]}")
    lines.append("")
    lines.append("## Acceptance Note")
    lines.append("")
    if report.modal_limited:
        lines.append(
            "This report proves sandbox tab/subtab routing and screenshot generation. "
            "Full in-world visual acceptance still requires running SmokeAttachAll after entering a character, "
            "because Solteria's character modal can cover the helper before login."
        )
    else:
        lines.append(
            "This report proves all ZeroBot-like helper views were captured in-world without the Select Character modal."
        )
    return "\n".join(lines)


def render_html(report: SmokeReport) -> str:
    status_class = "ready" if not report.modal_limited else "blocked"
    cards: list[str] = []
    for view in report.views:
        module = ZEROBOT_MODULE_MAP.get(view.view, view.view)
        title = f"{view.view} / {module}"
        if view.screenshot:
            image = (
                f'<a href="{html.escape(view.screenshot)}">'
                f'<img src="{html.escape(view.screenshot)}" alt="{html.escape(title)}">'
                "</a>"
            )
            meta = f"{view.size_bytes} bytes"
        else:
            image = '<div class="missing">missing screenshot</div>'
            meta = "missing"
        cards.append(
            "\n".join(
                [
                    '<article class="card">',
                    f"<h2>{html.escape(title)}</h2>",
                    image,
                    f"<p>{html.escape(meta)}</p>",
                    "</article>",
                ]
            )
        )

    if report.modal_limited:
        note = (
            "This is a routing/screenshot proof only. Enter a character and run "
            "SmokeAttachAll to capture the helper in-world without the Select Character modal."
        )
    else:
        note = "All ZeroBot-like helper views were captured in-world without the Select Character modal."

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            "<title>Solteria Helper Visual Review</title>",
            "<style>",
            "body{margin:0;background:#121212;color:#eee;font:14px Arial,sans-serif;}",
            "header{position:sticky;top:0;background:#1d1d1d;border-bottom:1px solid #555;padding:14px 18px;z-index:2;}",
            "h1{font-size:18px;margin:0 0 8px 0;} p{margin:4px 0;color:#d8d8d8;}",
            ".status{display:inline-block;padding:3px 8px;border:1px solid #777;background:#2a2a2a;}",
            ".status.ready{border-color:#5f9d5f;color:#bdf0bd}.status.blocked{border-color:#b58c42;color:#f0c56a}",
            ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:14px;padding:14px;}",
            ".card{background:#202020;border:1px solid #555;padding:10px;}",
            ".card h2{font-size:14px;margin:0 0 8px 0;color:#f0c56a;}",
            ".card img{display:block;width:100%;height:auto;border:1px solid #444;background:#000;}",
            ".missing{height:180px;display:flex;align-items:center;justify-content:center;border:1px solid #633;background:#211;color:#f99;}",
            "</style>",
            "</head>",
            "<body>",
            "<header>",
            "<h1>Solteria Helper Visual Review</h1>",
            f"<p>Run id: <code>{html.escape(report.run_id)}</code></p>",
            f'<p>Coverage: <strong>{report.covered_count}/{report.expected_count}</strong> '
            f'<span class="status {status_class}">{html.escape(report.acceptance_status)}</span></p>',
            f"<p>{html.escape(note)}</p>",
            "</header>",
            '<main class="grid">',
            "\n".join(cards),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="20260705-035", help="Timestamp prefix used by SmokeAll screenshots")
    parser.add_argument("--screenshot-dir", type=Path, default=DEFAULT_SCREENSHOT_DIR)
    parser.add_argument("--prefix", default="solteria-helper-testenv", help="Screenshot filename prefix")
    parser.add_argument("--in-world", action="store_true", help="Mark report as not modal-limited")
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    parser.add_argument("--html-out", type=Path, default=None)
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=None,
        help="Current dev manifest to bind into the smoke evidence.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = collect_report(
        args.screenshot_dir.resolve(),
        args.run_id,
        modal_limited=not args.in_world,
        prefix=args.prefix,
    )
    suffix = "inworld" if args.in_world else "coverage"
    json_out = args.json_out or args.screenshot_dir / f"solteria-helper-smokeall-{suffix}-{args.run_id}.json"
    md_out = args.md_out or args.screenshot_dir / f"solteria-helper-smokeall-{suffix}-{args.run_id}.md"
    html_out = args.html_out or args.screenshot_dir / f"solteria-helper-smokeall-{suffix}-{args.run_id}.html"
    payload = asdict(report)
    if args.manifest_path is not None:
        binding = manifest_binding(args.manifest_path.resolve())
        if binding is None:
            raise SystemExit(f"Manifest path does not exist: {args.manifest_path}")
        payload["manifest"] = binding
    json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_out.write_text(render_markdown(report), encoding="utf-8")
    html_out.write_text(render_html(report), encoding="utf-8")
    print(f"[ctoa-helper-smoke-report] JSON: {json_out}")
    print(f"[ctoa-helper-smoke-report] MD: {md_out}")
    print(f"[ctoa-helper-smoke-report] HTML: {html_out}")
    print(f"[ctoa-helper-smoke-report] Coverage: {report.covered_count}/{report.expected_count}")
    if report.missing:
        print("[ctoa-helper-smoke-report] Missing: " + ", ".join(report.missing))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
