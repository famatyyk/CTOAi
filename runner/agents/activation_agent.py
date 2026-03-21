#!/usr/bin/env python3
"""Activation Agent – prepares live VPS assets for auto-approved servers.

Flow:
  1. Pick READY servers whose latest catalog_signal is auto_approved.
  2. Skip servers that already have an activation manifest recorded.
  3. Create live target directory with:
     - bot-profile.json
     - character-plan.json
    - bot-bootstrap.lua
     - deploy-live.sh
     - live-manifest.json
  4. Store activation metadata in game_data as activation_manifest.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runner.agents import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [activation] %(levelname)s %(message)s",
)
log = logging.getLogger("activation")

LIVE_TARGETS_DIR = Path(os.environ.get("CTOA_LIVE_TARGETS_DIR", "/opt/ctoa/runtime/live-targets"))
BOT_LIVE_ROOT = Path(os.environ.get("CTOA_BOT_LIVE_ROOT", str(Path(__file__).resolve().parents[2] / "runtime" / "bot-live")))
SYNC_HOOK = Path(os.environ.get("CTOA_LIVE_TARGETS_SYNC_SCRIPT", str(Path(__file__).resolve().parents[2] / "scripts" / "ops" / "sync-live-targets.py")))
BOT_API_BASE = os.environ.get("CTOA_BOT_API_BASE", "http://127.0.0.1:8787")
DEFAULT_CHARACTER_PREFIX = os.environ.get("CTOA_CHARACTER_PREFIX", "ctoa")
MAX_TARGETS_PER_RUN = int(os.environ.get("CTOA_ACTIVATION_LIMIT", "5"))
AUTO_DEPLOY = os.environ.get("CTOA_ACTIVATION_AUTO_DEPLOY", "true").strip().lower() == "true"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:50] or "server"


def _targets() -> list[dict[str, Any]]:
    return db.query_all(
        """
        WITH latest_signal AS (
            SELECT DISTINCT ON (g.server_id)
                g.server_id,
                g.raw,
                g.fetched_at
            FROM game_data g
            WHERE g.data_type='catalog_signal'
            ORDER BY g.server_id, g.fetched_at DESC
        )
        SELECT s.id, s.url, s.name, s.game_type, ls.raw AS signal
        FROM servers s
        JOIN latest_signal ls ON ls.server_id=s.id
        WHERE s.status='READY'
          AND COALESCE((ls.raw->>'auto_approved')::boolean, FALSE)=TRUE
          AND NOT EXISTS (
              SELECT 1 FROM game_data g2
              WHERE g2.server_id=s.id AND g2.data_type='activation_manifest'
          )
        ORDER BY COALESCE((ls.raw->>'score')::int, 0) DESC, s.id DESC
        LIMIT %s
        """,
        (MAX_TARGETS_PER_RUN,),
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _persist_manifest(server_id: int, manifest: dict[str, Any]) -> None:
    db.execute(
        "INSERT INTO game_data (server_id, data_type, raw, fetched_at) VALUES (%s, %s, %s::jsonb, now())",
        (server_id, "activation_manifest", json.dumps(manifest, ensure_ascii=True)),
    )


def _run_sync_hook() -> dict[str, Any]:
    if not AUTO_DEPLOY:
        return {"ok": False, "skipped": True, "reason": "auto deploy disabled"}
    if not SYNC_HOOK.exists():
        return {"ok": False, "skipped": True, "reason": f"missing hook: {SYNC_HOOK}"}

    proc = subprocess.run(
        [
            sys.executable,
            str(SYNC_HOOK),
            "--source",
            str(LIVE_TARGETS_DIR),
            "--target",
            str(BOT_LIVE_ROOT),
        ],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=120,
        check=False,
    )
    payload: dict[str, Any] = {
        "ok": proc.returncode == 0,
        "code": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }
    if proc.stdout.strip():
        try:
            payload["report"] = json.loads(proc.stdout)
        except Exception:
            pass
    return payload


def _character_plan(server_slug: str) -> dict[str, Any]:
    names = [
        f"{DEFAULT_CHARACTER_PREFIX}-{server_slug}-knight",
        f"{DEFAULT_CHARACTER_PREFIX}-{server_slug}-mage",
    ]
    return {
        "strategy": "seed-two-characters",
        "characters": [
            {"name": names[0][:28], "vocation": "knight", "purpose": "farm-main"},
            {"name": names[1][:28], "vocation": "sorcerer", "purpose": "loot-scout"},
        ],
        "note": "Provisioning plan only; external account/character creation must be executed by the connected bot runtime.",
    }


def _bot_profile(server: dict[str, Any], signal: dict[str, Any], target_dir: Path) -> dict[str, Any]:
    return {
        "server_id": server["id"],
        "server_url": server["url"],
        "server_name": server.get("name") or server["url"],
        "game_type": server.get("game_type") or "unknown",
        "activation_mode": "auto-approved-live",
        "signal": {
            "score": signal.get("score", 0),
            "tags": signal.get("tags", []),
            "source": signal.get("source", ""),
            "population_hint": signal.get("population_hint", 0),
        },
        "bot_api_base": BOT_API_BASE,
        "artifacts_dir": str(target_dir),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def _deploy_script(server_slug: str) -> str:
    return """#!/usr/bin/env bash
set -eu

TARGET_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "[CTOA-LIVE] activating target: {slug}"
echo "[CTOA-LIVE] profile: $TARGET_DIR/bot-profile.json"
echo "[CTOA-LIVE] character plan: $TARGET_DIR/character-plan.json"
echo "[CTOA-LIVE] next step: point connected bot runtime at bot-profile.json and sync generated files"
""".format(slug=server_slug)


def _bootstrap_lua(server_name: str, bot_profile_path: Path) -> str:
        return f"""-- CTOA live bootstrap for {server_name}
-- Generated by activation_agent.

local profilePath = [[{str(bot_profile_path).replace('\\', '/')}]]

print(string.format("[CTOA-LIVE] bootstrap loaded for {server_name}"))
print(string.format("[CTOA-LIVE] profile: %s", profilePath))

macro(30000, "CTOA Live Heartbeat", function()
    print(string.format("[CTOA-LIVE] heartbeat :: {server_name}"))
end)
"""


def run_once() -> None:
    targets = _targets()
    if not targets:
        log.info("No auto-approved READY servers to activate")
        return

    activated = 0
    activated_server_ids: list[int] = []
    for server in targets:
        signal = server.get("signal") or {}
        if not isinstance(signal, dict):
            signal = {}

        server_slug = _slug(str(server.get("name") or server.get("url") or server.get("id")))
        target_dir = LIVE_TARGETS_DIR / server_slug

        bot_profile = _bot_profile(server, signal, target_dir)
        character_plan = _character_plan(server_slug)
        manifest = {
            "server_id": server["id"],
            "server_url": server["url"],
            "server_slug": server_slug,
            "target_dir": str(target_dir),
            "files": [
                str(target_dir / "bot-profile.json"),
                str(target_dir / "character-plan.json"),
                str(target_dir / "bot-bootstrap.lua"),
                str(target_dir / "deploy-live.sh"),
                str(target_dir / "live-manifest.json"),
            ],
            "signal": signal,
            "activated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "status": "ready-for-live-sync",
        }

        _write_json(target_dir / "bot-profile.json", bot_profile)
        _write_json(target_dir / "character-plan.json", character_plan)
        _write_text(target_dir / "bot-bootstrap.lua", _bootstrap_lua(server_slug, target_dir / "bot-profile.json"))
        _write_text(target_dir / "deploy-live.sh", _deploy_script(server_slug))
        _write_json(target_dir / "live-manifest.json", manifest)
        _persist_manifest(int(server["id"]), manifest)

        activated += 1
        activated_server_ids.append(int(server["id"]))
        log.info("Activated live target server #%s -> %s", server["id"], target_dir)

    deploy_result = _run_sync_hook() if activated > 0 else {"ok": False, "skipped": True, "reason": "no activations"}
    if activated > 0 and deploy_result.get("ok"):
        for server_id in activated_server_ids:
            row = db.query_one(
                "SELECT raw FROM game_data WHERE server_id=%s AND data_type='activation_manifest' ORDER BY fetched_at DESC LIMIT 1",
                (server_id,),
            ) or {}
            raw_manifest = row.get("raw")
            manifest: dict[str, Any] = raw_manifest if isinstance(raw_manifest, dict) else {}
            manifest["status"] = "deployed-live-target"
            manifest["deploy_result"] = deploy_result.get("report") or {
                "code": deploy_result.get("code"),
            }
            _persist_manifest(server_id, manifest)

    db.log_run("activation_agent", "ok", f"activated {activated} live targets | deploy_ok={deploy_result.get('ok')}")


if __name__ == "__main__":
    run_once()