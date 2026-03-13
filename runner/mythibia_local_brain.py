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

DEFAULT_TASKS: List[Dict[str, str]] = [
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
    {
        "id": "MB-004",
        "status": "NEW",
        "template": "cavebot_pathing_lua",
        "output": "cavebot_pathing.lua",
    },
    {
        "id": "MB-005",
        "status": "NEW",
        "template": "target_selector_lua",
        "output": "target_selector.lua",
    },
    {
        "id": "MB-006",
        "status": "NEW",
        "template": "anti_stuck_lua",
        "output": "anti_stuck.lua",
    },
    {
        "id": "MB-007",
        "status": "NEW",
        "template": "alarmy_lua",
        "output": "alarmy.lua",
    },
        {
            "id": "MB-008",
            "status": "NEW",
            "template": "healer_profiles_lua",
            "output": "healer_profiles.lua",
        },
        {
            "id": "MB-009",
            "status": "NEW",
            "template": "flee_logic_lua",
            "output": "flee_logic.lua",
        },
        {
            "id": "MB-010",
            "status": "NEW",
            "template": "target_blacklist_lua",
            "output": "target_blacklist.lua",
        },
        {
            "id": "MB-011",
            "status": "NEW",
            "template": "auto_resupply_lua",
            "output": "auto_resupply.lua",
        },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_queue() -> Dict:
    if QUEUE_FILE.exists():
        queue = yaml.safe_load(QUEUE_FILE.read_text(encoding="utf-8")) or {}
        tasks = queue.get("tasks", [])
        if not isinstance(tasks, list):
            tasks = []
            queue["tasks"] = tasks

        known_ids = {str(t.get("id", "")).strip() for t in tasks if isinstance(t, dict)}
        for task in DEFAULT_TASKS:
            if task["id"] not in known_ids:
                tasks.append(dict(task))

        queue["updated_at"] = now_iso()
        QUEUE_FILE.write_text(yaml.safe_dump(queue, sort_keys=False), encoding="utf-8")
        return queue

    bootstrap = {
        "version": 1,
        "updated_at": now_iso(),
        "tasks": [dict(x) for x in DEFAULT_TASKS],
    }
    USER_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(yaml.safe_dump(bootstrap, sort_keys=False), encoding="utf-8")
    return bootstrap


def render(template_name: str) -> str:
    templates = {
        "auto_heal_lua": """-- AI generated: auto_heal.lua\n-- Dostosuj progi HP/Mana do swojej postaci.\n\nlocal hpThreshold = 55\nlocal spell = 'exura'\n\nmacro(200, 'AI Auto Heal', function()\n  local hp = hppercent()\n  if hp <= hpThreshold then\n    say(spell)\n  end\nend)\n""",
        "auto_reconnect_lua": """-- AI generated: auto_reconnect.lua\n-- Prosty reconnect i relog po disconnect.\n\nmacro(3000, 'AI Auto Reconnect', function()\n  if not g_game.isOnline() then\n    if modules and modules.client_entergame and modules.client_entergame.EnterGame then\n      modules.client_entergame.EnterGame.openWindow()\n    end\n  end\nend)\n""",
        "loot_filter_lua": """-- AI generated: loot_filter.lua\n-- Szablon filtrowania lootu (do rozbudowy).\n\nlocal wanted = {\n  [3031] = true, -- gold coin\n  [3043] = true, -- crystal coin\n}\n\nmacro(1000, 'AI Loot Filter Info', function()\n  -- Hook pod własny auto-loot.\n  -- To jest starter: trzyma whitelistę itemów.\nend)\n\nreturn wanted\n""",
        "cavebot_pathing_lua": """-- AI generated: cavebot_pathing.lua\n-- Starter pathing z waypointami i fallbackiem.\n\nlocal waypoints = {\n  {x=1000, y=1000, z=7},\n  {x=1005, y=1000, z=7},\n  {x=1005, y=1005, z=7},\n  {x=1000, y=1005, z=7},\n}\n\nlocal idx = 1\nmacro(800, 'AI Cavebot Pathing', function()\n  local wp = waypoints[idx]\n  if not wp then\n    idx = 1\n    return\n  end\n\n  local pos = player:getPosition()\n  if pos.x == wp.x and pos.y == wp.y and pos.z == wp.z then\n    idx = (idx % #waypoints) + 1\n    return\n  end\n\n  autoWalk(wp)\nend)\n""",
        "target_selector_lua": """-- AI generated: target_selector.lua\n-- Priorytet targetu: najblizszy i najnizsze HP.\n\nlocal maxRange = 7\n\nlocal function score(creature)\n  local hp = creature:getHealthPercent() or 100\n  local dist = getDistanceBetween(player:getPosition(), creature:getPosition())\n  return hp + (dist * 4)\nend\n\nmacro(250, 'AI Target Selector', function()\n  if not g_game.isOnline() then return end\n  local monsters = getSpectators(player:getPosition(), false, maxRange)\n  local best = nil\n  local bestScore = 9999\n\n  for _, c in pairs(monsters) do\n    if c:isMonster() and c:canShoot() then\n      local s = score(c)\n      if s < bestScore then\n        best = c\n        bestScore = s\n      end\n    end\n  end\n\n  if best then\n    g_game.attack(best)\n  end\nend)\n""",
        "anti_stuck_lua": """-- AI generated: anti_stuck.lua\n-- Wykrywa brak ruchu i probuje odblokowac postac.\n\nlocal lastPos = nil\nlocal sameTicks = 0\n\nmacro(1000, 'AI Anti Stuck', function()\n  local pos = player:getPosition()\n  if not pos then return end\n\n  if lastPos and pos.x == lastPos.x and pos.y == lastPos.y and pos.z == lastPos.z then\n    sameTicks = sameTicks + 1\n  else\n    sameTicks = 0\n  end\n\n  if sameTicks >= 4 then\n    local tries = {\n      {x=pos.x+1, y=pos.y, z=pos.z},\n      {x=pos.x-1, y=pos.y, z=pos.z},\n      {x=pos.x, y=pos.y+1, z=pos.z},\n      {x=pos.x, y=pos.y-1, z=pos.z},\n    }\n    autoWalk(tries[math.random(1, #tries)])\n    sameTicks = 0\n  end\n\n  lastPos = pos\nend)\n""",
        "alarmy_lua": """-- AI generated: alarmy.lua\n-- Alarm dzwiekowy i tekstowy przy krytycznych sytuacjach.\n\nlocal hpCritical = 35\nlocal playerName = g_game.getCharacterName() or 'unknown'\n\nmacro(500, 'AI Alarmy', function()\n  if not g_game.isOnline() then return end\n\n  if hppercent() <= hpCritical then\n    playSound('/sounds/alarm.ogg')\n    warn('ALARM HP: '..hppercent()..'% ['..playerName..']')\n  end\n\n  for _, c in pairs(getSpectators(player:getPosition(), false, 7)) do\n    if c:isPlayer() and c:getName() ~= playerName then\n      playSound('/sounds/alarm.ogg')\n      warn('ALARM PLAYER: '..c:getName())\n      break\n    end\n  end\nend)\n""",
            "healer_profiles_lua": """-- AI generated: healer_profiles.lua\n-- Profile healera pod exp/hunt: soft i hard mode.\n\nlocal profile = storage.aiHealProfile or 'soft'\n\nlocal profiles = {\n  soft = {hp=62, mana=25, spell='exura'},\n  hard = {hp=78, mana=40, spell='exura gran'},\n}\n\nmacro(200, 'AI Healer Profiles', function()\n  if not g_game.isOnline() then return end\n  local p = profiles[profile] or profiles.soft\n  if hppercent() <= p.hp and manapercent() >= p.mana then\n    say(p.spell)\n  end\nend)\n\nonTextMessage(function(mode, text)\n  if text == '!heal soft' then\n    storage.aiHealProfile = 'soft'\n    warn('AI Healer: soft')\n  elseif text == '!heal hard' then\n    storage.aiHealProfile = 'hard'\n    warn('AI Healer: hard')\n  end\nend)\n""",
            "flee_logic_lua": """-- AI generated: flee_logic.lua\n-- Flee gdy HP spada lub jest za duzo mobow obok.\n\nlocal hpFlee = 30\nlocal mobLimit = 5\nlocal safePos = {x=1000, y=1000, z=7}\n\nlocal function nearbyMonsters()\n  local cnt = 0\n  for _, c in pairs(getSpectators(player:getPosition(), false, 5)) do\n    if c:isMonster() then cnt = cnt + 1 end\n  end\n  return cnt\nend\n\nmacro(300, 'AI Flee Logic', function()\n  if not g_game.isOnline() then return end\n  if hppercent() <= hpFlee or nearbyMonsters() >= mobLimit then\n    autoWalk(safePos)\n    warn('AI FLEE TRIGGERED')\n  end\nend)\n""",
            "target_blacklist_lua": """-- AI generated: target_blacklist.lua\n-- Pomija blacklistowane potwory przy ataku.\n\nlocal blacklist = {\n  ['Rat'] = true,\n  ['Cave Rat'] = true,\n}\n\nmacro(300, 'AI Target Blacklist', function()\n  if not g_game.isOnline() then return end\n\n  local best = nil\n  for _, c in pairs(getSpectators(player:getPosition(), false, 7)) do\n    if c:isMonster() then\n      local name = c:getName() or ''\n      if not blacklist[name] then\n        best = c\n        break\n      end\n    end\n  end\n\n  if best then\n    g_game.attack(best)\n  end\nend)\n""",
            "auto_resupply_lua": """-- AI generated: auto_resupply.lua\n-- Prosty trigger resupply na low cap / low pot count.\n\nlocal minCap = 80\nlocal minManaPot = 20\nlocal depotPos = {x=1002, y=998, z=7}\n\nlocal function itemCount(id)\n  local c = 0\n  for _, item in pairs(getContainers()) do\n    c = c + item:getItemsCount(id)\n  end\n  return c\nend\n\nmacro(2000, 'AI Auto Resupply', function()\n  if not g_game.isOnline() then return end\n  local manaPots = itemCount(268)\n  if freecap() <= minCap or manaPots <= minManaPot then\n    warn('AI RESUPPLY TRIGGERED')\n    autoWalk(depotPos)\n  end\nend)\n""",
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
