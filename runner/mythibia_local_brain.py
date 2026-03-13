#!/usr/bin/env python3
"""Local brain that generates Mythibia scripts into user_dir.

Flow:
1) Read queue file from MythibiaV2 user_dir.
2) For NEW tasks, generate script files from built-in templates.
3) Mark tasks as GENERATED and write manifest.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

try:
    import yaml  # type: ignore
except Exception as ex:  # pragma: no cover
    raise SystemExit(f"Missing dependency pyyaml: {ex}")

MYTHIBIA_ROOT = Path(r"C:\Users\zycie\AppData\Roaming\Mythibia\MythibiaV2")
USER_DIR = MYTHIBIA_ROOT / "user_dir"
AI_DIR = USER_DIR / "ai_generated"
QUEUE_FILE = USER_DIR / "ai_agent_queue.yaml"
MANIFEST_FILE = AI_DIR / "manifest.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_queue() -> Dict:
    if QUEUE_FILE.exists():
        return yaml.safe_load(QUEUE_FILE.read_text(encoding="utf-8")) or {}

    bootstrap = {
        "version": 1,
        "updated_at": now_iso(),
        "tasks": [
            {
                "id": "MB-001",
                "status": "NEW",
                "template": "auto_heal_lua",
                "output": "auto_heal.lua",
            },
            {
                "id": "MB-002",
                "status": "NEW",
                "template": "auto_reconnect_lua",
                "output": "auto_reconnect.lua",
            },
            {
                "id": "MB-003",
                "status": "NEW",
                "template": "loot_filter_lua",
                "output": "loot_filter.lua",
            },
        ],
    }
    USER_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(yaml.safe_dump(bootstrap, sort_keys=False), encoding="utf-8")
    return bootstrap


def render(template_name: str) -> str:
    templates = {
        "auto_heal_lua": """-- AI generated: auto_heal.lua\n-- Dostosuj progi HP/Mana do swojej postaci.\n\nlocal hpThreshold = 55\nlocal spell = 'exura'\n\nmacro(200, 'AI Auto Heal', function()\n  local hp = hppercent()\n  if hp <= hpThreshold then\n    say(spell)\n  end\nend)\n""",
        "auto_reconnect_lua": """-- AI generated: auto_reconnect.lua\n-- Prosty reconnect i relog po disconnect.\n\nmacro(3000, 'AI Auto Reconnect', function()\n  if not g_game.isOnline() then\n    if modules and modules.client_entergame and modules.client_entergame.EnterGame then\n      modules.client_entergame.EnterGame.openWindow()\n    end\n  end\nend)\n""",
        "loot_filter_lua": """-- AI generated: loot_filter.lua\n-- Szablon filtrowania lootu (do rozbudowy).\n\nlocal wanted = {\n  [3031] = true, -- gold coin\n  [3043] = true, -- crystal coin\n}\n\nmacro(1000, 'AI Loot Filter Info', function()\n  -- Hook pod własny auto-loot.\n  -- To jest starter: trzyma whitelistę itemów.\nend)\n\nreturn wanted\n""",
    }
    if template_name not in templates:
        raise ValueError(f"Unknown template: {template_name}")
    return templates[template_name]


def generate() -> None:
    queue = ensure_queue()
    tasks: List[Dict] = queue.get("tasks", [])
    AI_DIR.mkdir(parents=True, exist_ok=True)

    manifest: Dict[str, Dict] = {
        "generated_at": now_iso(),
        "files": {},
    }

    changed = False
    for task in tasks:
        if str(task.get("status", "NEW")) != "NEW":
            continue

        template = str(task.get("template", "")).strip()
        output = str(task.get("output", "")).strip()
        if not template or not output:
            task["status"] = "FAILED"
            task["error"] = "missing template/output"
            changed = True
            continue

        content = render(template)
        out_file = AI_DIR / output
        out_file.write_text(content, encoding="utf-8")

        task["status"] = "GENERATED"
        task["updated_at"] = now_iso()
        task["output_abs"] = str(out_file)
        manifest["files"][output] = {
            "task_id": task.get("id"),
            "template": template,
            "updated_at": task["updated_at"],
        }
        changed = True

    if changed:
        queue["updated_at"] = now_iso()
        QUEUE_FILE.write_text(yaml.safe_dump(queue, sort_keys=False), encoding="utf-8")

    MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated files in: {AI_DIR}")


if __name__ == "__main__":
    generate()
