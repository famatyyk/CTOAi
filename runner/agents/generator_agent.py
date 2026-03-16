#!/usr/bin/env python3
"""Generator Agent – renders Lua/Python templates for QUEUED modules.

For each QUEUED module:
  1. Load server game_data from DB (monsters, items, etc.)
  2. Render the template string with server context
  3. Write output file to /opt/ctoa/generated/{server_slug}/{output_file}
  4. Update module status to GENERATED

Run: python3 -m runner.agents.generator_agent
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runner.agents import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [generator] %(levelname)s %(message)s",
)
log = logging.getLogger("generator")

OUTPUT_BASE = Path(os.environ.get("CTOA_GENERATED_DIR", "/opt/ctoa/generated"))
MAX_RETRIES = 3


def _server_ctx(server_id: int) -> dict[str, Any]:
    """Build template context from game_data and server row."""
    srv = db.query_one("SELECT url, name, game_type FROM servers WHERE id=%s", (server_id,)) or {}
    ctx: dict[str, Any] = {
        "server_url":  srv.get("url", ""),
        "server_name": srv.get("name", "Server"),
        "game_type":   srv.get("game_type", "tibia-ot"),
        "monsters":    [],
        "items":       [],
        "players":     [],
        "highscores":  [],
        "server_info": {},
    }
    rows = db.query_all(
        "SELECT data_type, raw FROM game_data WHERE server_id=%s ORDER BY fetched_at DESC",
        (server_id,),
    )
    seen: set[str] = set()
    for row in rows:
        dt = row["data_type"]
        if dt in seen:
            continue
        seen.add(dt)
        raw = row["raw"]
        if isinstance(raw, str):
            raw = json.loads(raw)
        ctx[dt] = raw
    return ctx


def _safe_lua_string(s: object) -> str:
    txt = "" if s is None else str(s)
    return txt.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _render(template_id: str, ctx: dict) -> str:
    """Dispatch to the correct template renderer."""
    fn = _TEMPLATES.get(template_id)
    if fn is None:
        raise ValueError(f"Unknown template: {template_id!r}")
    return fn(ctx)


# ─── Template functions ───────────────────────────────────────────────────────

def _tpl_auto_heal(ctx: dict) -> str:
    return """-- auto_heal.lua  [CTOA Generated]
-- Heals character when HP drops below threshold.

local HEAL_THRESHOLD = 55  -- % of max HP
local HEAL_SPELL     = "exura"
local CHECK_DELAY_MS = 350

local lastHeal = 0

local function onThink()
    local now = os.time() * 1000
    if (now - lastHeal) < CHECK_DELAY_MS then return end
    local hp    = Player.getHpPercent()
    if hp <= HEAL_THRESHOLD then
        Player.say(HEAL_SPELL)
        lastHeal = now
    end
end

register("onThink", onThink)
"""


def _tpl_auto_reconnect(ctx: dict) -> str:
    return """-- auto_reconnect.lua  [CTOA Generated]
-- Automatically reconnects when character goes offline.

local CHECK_INTERVAL = 5000  -- ms
local MAX_OFFLINE_SEC = 30
local lastOnline = os.time()

local function onThink()
    if Player.isOnline() then
        lastOnline = os.time()
        return
    end
    if (os.time() - lastOnline) >= MAX_OFFLINE_SEC then
        Game.reconnect()
        lastOnline = os.time()
    end
end

register("onThink", onThink)
"""


def _tpl_loot_filter(ctx: dict) -> str:
    items = ctx.get("items", [])
    item_names = [_safe_lua_string(i["name"]) for i in items[:20] if i.get("name")]
    if not item_names:
        item_names = ["Gold Coin", "Platinum Coin", "Crystal Coin",
                      "Dragon Scale Mail", "Demon Helmet"]
    whitelist_lua = "\n".join(f'    "{n}",' for n in item_names)
    return f"""-- loot_filter.lua  [CTOA Generated – server: {_safe_lua_string(ctx['server_name'])}]
-- Picks up only whitelisted items.

local WHITELIST = {{
{whitelist_lua}
}}

local function isWanted(name)
    for _, v in ipairs(WHITELIST) do
        if v:lower() == name:lower() then return true end
    end
    return false
end

local function onItemFound(item)
    if isWanted(item.name) then
        Player.pickupItem(item)
    end
end

register("onItemFound", onItemFound)
"""


def _tpl_cavebot_pathing(ctx: dict) -> str:
    return """-- cavebot_pathing.lua  [CTOA Generated]
-- Loops through waypoints using autoWalk.

local WAYPOINTS = {
    {x=0, y=0, z=7, action="walk"},
    -- add your waypoints here
}

local currentWP = 1
local walking   = false

local function onThink()
    if walking then return end
    local wp = WAYPOINTS[currentWP]
    Player.autoWalk(wp.x, wp.y, wp.z)
    walking = true
    currentWP = (currentWP % #WAYPOINTS) + 1
end

local function onWalkFinished()
    walking = false
end

register("onThink",        onThink)
register("onWalkFinished", onWalkFinished)
"""


def _tpl_target_selector(ctx: dict) -> str:
    return """-- target_selector.lua  [CTOA Generated]
-- Scores targets: lower HP% + closer distance wins.

local function scoreCreature(c)
    local dist = math.abs(c.x - Player.x) + math.abs(c.y - Player.y)
    return (c.hpPercent or 100) + dist * 4
end

local function onThink()
    if Player.hasTarget() then return end
    local best, bestScore = nil, math.huge
    for _, c in ipairs(Creature.getAll()) do
        if c.isMonster and c.isAttackable then
            local s = scoreCreature(c)
            if s < bestScore then best, bestScore = c, s end
        end
    end
    if best then Player.attack(best) end
end

register("onThink", onThink)
"""


def _tpl_anti_stuck(ctx: dict) -> str:
    return """-- anti_stuck.lua  [CTOA Generated]
-- Detects same position for N ticks → escapes in random direction.

local STUCK_TICKS = 4
local stuckCount  = 0
local lastPos     = {x=0, y=0, z=0}
local DIRS        = {0, 1, 2, 3}  -- N E S W

local function onThink()
    local pos = Player.getPosition()
    if pos.x == lastPos.x and pos.y == lastPos.y then
        stuckCount = stuckCount + 1
    else
        stuckCount = 0
        lastPos    = pos
    end
    if stuckCount >= STUCK_TICKS then
        local dir = DIRS[math.random(#DIRS)]
        Player.walk(dir)
        stuckCount = 0
    end
end

register("onThink", onThink)
"""


def _tpl_alarmy(ctx: dict) -> str:
    return """-- alarmy.lua  [CTOA Generated]
-- Sound + warning on critical HP or player nearby.

local HP_CRIT    = 25
local WARN_RANGE = 7

local lastWarn = 0

local function onThink()
    local now = os.time()
    if (now - lastWarn) < 10 then return end

    if Player.getHpPercent() <= HP_CRIT then
        Game.playSound("alarm.wav")
        Player.say("!alarm crit_hp")
        lastWarn = now
        return
    end

    for _, c in ipairs(Creature.getAll()) do
        if c.isPlayer and c.name ~= Player.name then
            local d = math.abs(c.x - Player.x) + math.abs(c.y - Player.y)
            if d <= WARN_RANGE then
                Game.playSound("alert.wav")
                Player.say("!alarm player_near " .. c.name)
                lastWarn = now
                return
            end
        end
    end
end

register("onThink", onThink)
"""


def _tpl_healer_profiles(ctx: dict) -> str:
    return """-- healer_profiles.lua  [CTOA Generated]
-- Soft / hard healing profiles switchable via chat command.

local PROFILES = {
    soft = {hpPct=65, spell="exura"},
    hard = {hpPct=80, spell="exura gran"},
}
local active = "soft"
local delay  = 400
local last   = 0

local function onChat(msg)
    if msg:match("^!heal (%a+)$") then
        local p = msg:match("^!heal (%a+)$")
        if PROFILES[p] then active = p end
    end
end

local function onThink()
    local now = os.time() * 1000
    if (now - last) < delay then return end
    local prof = PROFILES[active]
    if Player.getHpPercent() <= prof.hpPct then
        Player.say(prof.spell)
        last = now
    end
end

register("onThink", onThink)
register("onChat",  onChat)
"""


def _tpl_flee_logic(ctx: dict) -> str:
    return """-- flee_logic.lua  [CTOA Generated]
-- Flees to safePos when HP critical or too many mobs nearby.

local HP_FLEE   = 30
local MOB_LIMIT = 5
local SAFE_POS  = {x=100, y=100, z=7}  -- update for your map

local fleeing = false

local function onThink()
    if fleeing then return end
    local mobs = 0
    for _, c in ipairs(Creature.getAll()) do
        if c.isMonster then mobs = mobs + 1 end
    end
    if Player.getHpPercent() <= HP_FLEE or mobs >= MOB_LIMIT then
        fleeing = true
        Player.autoWalk(SAFE_POS.x, SAFE_POS.y, SAFE_POS.z)
    end
end

local function onWalkFinished()
    fleeing = false
end

register("onThink",        onThink)
register("onWalkFinished", onWalkFinished)
"""


def _tpl_target_blacklist(ctx: dict) -> str:
    monsters = ctx.get("monsters", [])
    blacklist = [m["name"] for m in monsters[:10] if m.get("hp", 9999) < 50]
    if not blacklist:
        blacklist = ["Rat", "Cave Rat", "Bug"]
    entries = "\n".join(f'    ["{_safe_lua_string(n)}"] = true,' for n in blacklist)
    return f"""-- target_blacklist.lua  [CTOA Generated – server: {_safe_lua_string(ctx['server_name'])}]
-- Skip monsters on the blacklist.

local BLACKLIST = {{
{entries}
}}

local function onTarget(creature)
    if BLACKLIST[creature.name] then
        Player.clearTarget()
        return false
    end
    return true
end

register("onTarget", onTarget)
"""


def _tpl_auto_resupply(ctx: dict) -> str:
    return """-- auto_resupply.lua  [CTOA Generated]
-- Walks to depot when capacity or mana-pot count is low.

local MIN_CAP       = 200
local MIN_MANA_POTS = 20
local DEPOT_POS     = {x=200, y=200, z=7}  -- update for your map

local going = false

local function onThink()
    if going then return end
    local cap   = Player.getFreeCapacity()
    local pots  = Player.getItemCount("Mana Potion")
    if cap < MIN_CAP or pots < MIN_MANA_POTS then
        going = true
        Player.autoWalk(DEPOT_POS.x, DEPOT_POS.y, DEPOT_POS.z)
    end
end

local function onWalkFinished()
    going = false
end

register("onThink",        onThink)
register("onWalkFinished", onWalkFinished)
"""


def _tpl_server_blacklist(ctx: dict) -> str:
    monsters = ctx.get("monsters", [])
    # Blacklist weakest mobs (hp < 100) to save time
    weak = sorted([m for m in monsters if isinstance(m.get("hp"), int) and m["hp"] < 100], key=lambda m: m["hp"])
    names = [m["name"] for m in weak[:15]]
    if not names:
        names = ["Rat", "Bug", "Rotworm"]
    entries = "\n".join(f'    ["{_safe_lua_string(n)}"] = true,' for n in names)
    return f"""-- server_blacklist.lua  [CTOA Generated – {_safe_lua_string(ctx['server_name'])}]
-- Skips low-value monsters discovered from server API.

local SKIP = {{
{entries}
}}

local function onTarget(c)
    if SKIP[c.name] then Player.clearTarget(); return false end
    return true
end

register("onTarget", onTarget)
"""


def _tpl_server_loot_map(ctx: dict) -> str:
    items = ctx.get("items", [])
    top = sorted(items, key=lambda i: i.get("weight", 0), reverse=True)[:20]
    entries = "\n".join(f'    "{_safe_lua_string(i["name"])}",' for i in top if i.get("name"))
    if not entries:
        entries = '    "Gold Coin",'
    return f"""-- server_loot_map.lua  [CTOA Generated – {_safe_lua_string(ctx['server_name'])}]
-- High-value item list from server API.

local LOOT_LIST = {{
{entries}
}}

local function onItemFound(item)
    for _, n in ipairs(LOOT_LIST) do
        if item.name:lower() == n:lower() then
            Player.pickupItem(item); return
        end
    end
end

register("onItemFound", onItemFound)
"""


def _tpl_highscore_scout(ctx: dict) -> str:
    hs = ctx.get("highscores", [])[:5]
    lines = "\n".join(f'    -- #{h["rank"]} {h["name"]} lv{h["level"]}' for h in hs)
    return f"""-- highscore_scout.lua  [CTOA Generated – {_safe_lua_string(ctx['server_name'])}]
-- Tracks top players from server highscores.
-- Snapshot at generation time:
{lines or "    -- (no highscore data)"}

local TOP_PLAYERS = {{
{chr(10).join(f"    {chr(34)}{_safe_lua_string(h.get('name','?'))}{chr(34)}," for h in hs)}}}

local function onSeeCreature(c)
    if c.isPlayer then
        for _, n in ipairs(TOP_PLAYERS) do
            if c.name == n then
                Game.addEvent("HighScorePlayer: " .. c.name, "info")
            end
        end
    end
end

register("onSeeCreature", onSeeCreature)
"""


def _tpl_server_stats(ctx: dict) -> str:
    si = ctx.get("server_info", {})
    return f"""-- server_stats.lua  [CTOA Generated – {_safe_lua_string(ctx['server_name'])}]
-- Shows server stats in console on login.

local SERVER = {{
    name    = "{_safe_lua_string(str(si.get('name', ctx['server_name'])))}",
    pvpType = "{_safe_lua_string(str(si.get('pvp_type', 'unknown')))}",
    expRate = {float(si.get('rate_exp', 1))},
    maxLvl  = {int(si.get('max_level', 0))},
    online  = {int(si.get('online', 0))},
}}

local function onLogin()
    Game.addEvent(string.format("[%s] PvP: %s | Exp×%g | Online: %d",
        SERVER.name, SERVER.pvpType, SERVER.expRate, SERVER.online), "info")
end

register("onLogin", onLogin)
"""


def _tpl_player_tracker(ctx: dict) -> str:
    players = ctx.get("players", [])[:10]
    names = [p["name"] for p in players if p.get("name")]
    entries = "\n".join(f'    "{_safe_lua_string(n)}",' for n in names)
    return f"""-- player_tracker.lua  [CTOA Generated – {_safe_lua_string(ctx['server_name'])}]
-- Alert when tracked players come online.

local WATCH = {{
{entries or '    -- no players loaded'}
}}

local KNOWN_ONLINE = {{}}

local function onThink()
    for _, name in ipairs(WATCH) do
        local online = Game.isPlayerOnline(name)
        if online and not KNOWN_ONLINE[name] then
            Game.playSound("alert.wav")
            Game.addEvent("TRACKED: " .. name .. " is now online!", "warn")
            KNOWN_ONLINE[name] = true
        elseif not online then
            KNOWN_ONLINE[name] = nil
        end
    end
end

register("onThink", onThink)
"""


def _tpl_hunt_orchestrator(ctx: dict) -> str:
    return """-- hunt_orchestrator.lua  [CTOA Generated – PROGRAM]
-- Master hunt controller: integrates healer, flee, targeting and anti-stuck.
-- Priority queue: flee > heal > target > cavebot > anti_stuck

local STATE = "idle"
local COOLDOWNS = {}
local FLOOR_INTERVAL = 200  -- ms

local function cd(key, ms)
    local now = os.time() * 1000
    if (now - (COOLDOWNS[key] or 0)) < ms then return true end
    COOLDOWNS[key] = now
    return false
end

-- ── Healer module
local HEAL_HP   = 65
local HEAL_HARD = 80
local function tryHeal()
    if cd("heal", 400) then return false end
    local hp = Player.getHpPercent()
    if hp <= HEAL_HP then
        Player.say(hp <= 40 and "exura gran" or "exura")
        return true
    end
    return false
end

-- ── Flee module
local FLEE_HP   = 30
local FLEE_MOBS = 5
local SAFE_POS  = {x=100, y=100, z=7}
local function tryFlee()
    if cd("flee", 1000) then return false end
    local mobs = 0
    for _, c in ipairs(Creature.getAll()) do if c.isMonster then mobs=mobs+1 end end
    if Player.getHpPercent() <= FLEE_HP or mobs >= FLEE_MOBS then
        Player.autoWalk(SAFE_POS.x, SAFE_POS.y, SAFE_POS.z)
        STATE = "fleeing"
        return true
    end
    return false
end

-- ── Targeting
local function tryTarget()
    if cd("target", 300) or Player.hasTarget() then return false end
    local best, bs = nil, math.huge
    for _, c in ipairs(Creature.getAll()) do
        if c.isMonster and c.isAttackable then
            local s = c.hpPercent + (math.abs(c.x-Player.x)+math.abs(c.y-Player.y))*4
            if s < bs then best, bs = c, s end
        end
    end
    if best then Player.attack(best) end
    return best ~= nil
end

-- ── Anti-stuck
local lastPos = {x=0,y=0,z=0}
local stuckCt = 0
local function tryAntiStuck()
    local pos = Player.getPosition()
    if pos.x==lastPos.x and pos.y==lastPos.y then
        stuckCt = stuckCt+1
    else stuckCt=0; lastPos=pos end
    if stuckCt >= 4 then
        Player.walk(math.random(0,3)); stuckCt=0
    end
end

-- ── Main loop
local function onThink()
    if cd("main", FLOOR_INTERVAL) then return end
    if tryFlee()   then return end
    if tryHeal()   then end
    if tryTarget() then end
    tryAntiStuck()
end

local function onWalkFinished()
    if STATE == "fleeing" then STATE = "idle" end
end

register("onThink",        onThink)
register("onWalkFinished", onWalkFinished)
"""


def _tpl_economy_bot(ctx: dict) -> str:
    items = ctx.get("items", [])
    valuable = [i for i in items if i.get("weight", 0) < 5 and i.get("name")][:10]
    picks = "\n".join(f'    "{_safe_lua_string(i["name"])}",' for i in valuable)
    return f"""-- economy_bot.lua  [CTOA Generated – PROGRAM]
-- Automated economy agent: picks valuable light items, manages depot trips.

local PICKS = {{
{picks or '    "Gold Coin",'}
}}
local MIN_CAP  = 150
local DEPOT    = {{x=200, y=200, z=7}}
local going    = false

local function wantItem(name)
    for _, n in ipairs(PICKS) do if n:lower()==name:lower() then return true end end
    return false
end

local function onItemFound(item)
    if wantItem(item.name) then Player.pickupItem(item) end
end

local function onThink()
    if going then return end
    if Player.getFreeCapacity() < MIN_CAP then
        going = true
        Player.autoWalk(DEPOT.x, DEPOT.y, DEPOT.z)
    end
end

local function onWalkFinished() going = false end

register("onItemFound",    onItemFound)
register("onThink",        onThink)
register("onWalkFinished", onWalkFinished)
"""


def _tpl_pvp_guard(ctx: dict) -> str:
    return """-- pvp_guard.lua  [CTOA Generated – PROGRAM]
-- PvP guard: detects hostile players and activates defense sequence.

local SAFE_DIST = 5
local last      = 0

local function onThink()
    local now = os.time()
    if (now - last) < 3 then return end
    for _, c in ipairs(Creature.getAll()) do
        if c.isPlayer and c.name ~= Player.name then
            local d = math.abs(c.x-Player.x) + math.abs(c.y-Player.y)
            if d <= SAFE_DIST then
                -- ring the alarm + equip shield
                Game.playSound("alarm.wav")
                Player.equipItem("Shield")
                Player.say("exura")
                last = now
                return
            end
        end
    end
end

register("onThink", onThink)
"""


def _tpl_depot_manager(ctx: dict) -> str:
    return """-- depot_manager.lua  [CTOA Generated]
-- Opens depot at destination and deposits all non-essential items.

local KEEP = {"Gold Coin", "Mana Potion", "Health Potion", "Rune"}
local DEPOT_POS = {x=200, y=200, z=7}

local function shouldKeep(name)
    for _, k in ipairs(KEEP) do
        if name:lower():find(k:lower()) then return true end
    end
    return false
end

local function onReachDepot()
    for _, item in ipairs(Player.getItems()) do
        if not shouldKeep(item.name) then
            Game.depositItem(item)
        end
    end
end

register("onReachDepot", onReachDepot)
"""


def _tpl_gold_tracker(ctx: dict) -> str:
    return """-- gold_tracker.lua  [CTOA Generated]
-- Tracks gold earned per session and logs to console every 5 minutes.

local sessionStart = os.time()
local goldStart    = Player.getMoney()
local lastReport   = os.time()

local function onThink()
    local now = os.time()
    if (now - lastReport) < 300 then return end
    local elapsed = now - sessionStart
    local earned  = Player.getMoney() - goldStart
    local perHour = elapsed > 0 and math.floor(earned / elapsed * 3600) or 0
    Game.addEvent(string.format("Gold/h: %d | Total: %d | Time: %dm",
        perHour, earned, math.floor(elapsed/60)), "info")
    lastReport = now
end

register("onThink", onThink)
"""


def _tpl_bank_automation(ctx: dict) -> str:
    return """-- bank_automation.lua  [CTOA Generated]
-- Auto-deposits gold to bank when above threshold.

local GOLD_LIMIT = 50000
local BANK_POS   = {x=201, y=201, z=7}

local going = false

local function onThink()
    if going then return end
    if Player.getMoney() >= GOLD_LIMIT then
        going = true
        Player.autoWalk(BANK_POS.x, BANK_POS.y, BANK_POS.z)
    end
end

local function onReachBank()
    Player.depositMoney(Player.getMoney() - 1000)  -- keep 1000gp
    going = false
end

register("onThink",     onThink)
register("onReachBank", onReachBank)
"""


def _tpl_human_delay(ctx: dict) -> str:
    return """-- human_delay.lua  [CTOA Generated]
-- Injects random delays to mimic human behaviour and reduce detection.

local BASE_DELAY = 300
local VARIANCE   = 150

local function humanDelay()
    return BASE_DELAY + math.random(-VARIANCE, VARIANCE)
end

-- Patch Player.say to add human delay
local _origSay = Player.say
function Player.say(msg)
    local d = humanDelay()
    os.execute("sleep " .. (d / 1000))
    _origSay(msg)
end

-- Export for other modules
HumanDelay = humanDelay
"""


def _tpl_break_scheduler(ctx: dict) -> str:
    return """-- break_scheduler.lua  [CTOA Generated]
-- Schedules random breaks to simulate human play patterns.

local MIN_PLAY   = 25 * 60   -- 25 min in seconds
local MAX_PLAY   = 55 * 60
local MIN_BREAK  = 3  * 60
local MAX_BREAK  = 12 * 60

local nextBreak  = os.time() + math.random(MIN_PLAY, MAX_PLAY)
local onBreak    = false
local breakEnd   = 0

local function onThink()
    local now = os.time()
    if onBreak then
        if now >= breakEnd then
            onBreak   = false
            nextBreak = now + math.random(MIN_PLAY, MAX_PLAY)
            Game.addEvent("Break ended – resuming", "info")
        end
        return
    end
    if now >= nextBreak then
        onBreak  = true
        breakEnd = now + math.random(MIN_BREAK, MAX_BREAK)
        Game.addEvent(string.format("Break started – %dm", math.floor((breakEnd-now)/60)), "info")
        Game.logout()
    end
end

register("onThink", onThink)
"""


def _tpl_login_randomizer(ctx: dict) -> str:
    return """-- login_randomizer.lua  [CTOA Generated]
-- Randomises login time within a window to avoid pattern detection.

local WINDOW_START_H = 9   -- 09:00
local WINDOW_END_H   = 23  -- 23:00

local function inWindow()
    local h = tonumber(os.date("%H"))
    return h >= WINDOW_START_H and h < WINDOW_END_H
end

local function onDisconnect()
    if not inWindow() then
        Game.addEvent("Outside login window – not reconnecting", "info")
        return
    end
    local delay = math.random(30, 300)  -- 30s–5min
    Game.addEvent("Reconnecting in " .. delay .. "s", "info")
    os.execute("sleep " .. delay)
    Game.reconnect()
end

register("onDisconnect", onDisconnect)
"""


def _tpl_rune_maker(ctx: dict) -> str:
    return """-- rune_maker.lua  [CTOA Generated]
-- Auto-creates runes when mana is above threshold and blank runes are available.

local MIN_MANA_PCT = 90
local RUNE_SPELL   = "adori gran"
local BLANK_RUNE   = "Blank Rune"
local delay        = 800
local last         = 0

local function onThink()
    local now = os.time() * 1000
    if (now - last) < delay then return end
    if Player.getManaPercent() < MIN_MANA_PCT then return end
    if Player.getItemCount(BLANK_RUNE) < 1 then return end
    Player.say(RUNE_SPELL)
    last = now
end

register("onThink", onThink)
"""


def _tpl_combo_spells(ctx: dict) -> str:
    return """-- combo_spells.lua  [CTOA Generated]
-- Executes a spell combo when HP/mana conditions are met.

local COMBO = {
    {spell="exori", manaMin=60, hpMin=50, cd=1000},
    {spell="exori gran", manaMin=80, hpMin=70, cd=2000},
}
local cds = {}

local function onThink()
    local now  = os.time() * 1000
    local mana = Player.getManaPercent()
    local hp   = Player.getHpPercent()
    for _, c in ipairs(COMBO) do
        if mana >= c.manaMin and hp >= c.hpMin and (now-(cds[c.spell]or 0)) >= c.cd then
            Player.say(c.spell)
            cds[c.spell] = now
            return
        end
    end
end

register("onThink", onThink)
"""


def _tpl_area_spell_ctrl(ctx: dict) -> str:
    return """-- area_spell_ctrl.lua  [CTOA Generated]
-- Fires area-of-effect spell only when enough monsters are nearby.

local AOE_SPELL    = "exori mas"
local MIN_MOBS     = 4
local AOE_RANGE    = 3
local MANA_MIN_PCT = 70
local last         = 0
local DELAY_MS     = 1500

local function countNearbyMobs(range)
    local n = 0
    for _, c in ipairs(Creature.getAll()) do
        if c.isMonster then
            local d = math.max(math.abs(c.x-Player.x), math.abs(c.y-Player.y))
            if d <= range then n = n+1 end
        end
    end
    return n
end

local function onThink()
    local now = os.time() * 1000
    if (now-last) < DELAY_MS then return end
    if Player.getManaPercent() < MANA_MIN_PCT then return end
    if countNearbyMobs(AOE_RANGE) >= MIN_MOBS then
        Player.say(AOE_SPELL)
        last = now
    end
end

register("onThink", onThink)
"""


def _tpl_exp_tracker(ctx: dict) -> str:
    return """-- exp_tracker.lua  [CTOA Generated]
-- Tracks experience gain per session with hourly projection.

local startExp  = Player.getExperience()
local startTime = os.time()
local lastLog   = os.time()
local LOG_INT   = 120  -- log every 2 min

local function onThink()
    local now = os.time()
    if (now - lastLog) < LOG_INT then return end
    lastLog        = now
    local elapsed  = now - startTime
    local gained   = Player.getExperience() - startExp
    local perHour  = elapsed > 0 and math.floor(gained / elapsed * 3600) or 0
    Game.addEvent(string.format("EXP/h: %s | Gained: %s | %dm session",
        perHour, gained, math.floor(elapsed/60)), "info")
end

register("onThink", onThink)
"""


def _tpl_session_log(ctx: dict) -> str:
    return """-- session_log.lua  [CTOA Generated]
-- Writes a session summary to a local log file on logout.

local LOG_FILE   = "session_log.txt"
local startTime  = os.time()
local startExp   = Player.getExperience()
local startGold  = Player.getMoney()

local function onLogout()
    local elapsed = os.time() - startTime
    local summary = string.format(
        "[%s] Duration: %dm | EXP: +%d | Gold: +%d\\n",
        os.date("%Y-%m-%d %H:%M"), math.floor(elapsed/60),
        Player.getExperience()-startExp, Player.getMoney()-startGold
    )
    local f = io.open(LOG_FILE, "a")
    if f then f:write(summary); f:close() end
    Game.addEvent("Session saved to " .. LOG_FILE, "info")
end

register("onLogout", onLogout)
"""


def _tpl_respawn_optimizer(ctx: dict) -> str:
    monsters = ctx.get("monsters", [])
    top_exp = sorted(monsters, key=lambda m: m.get("exp", 0), reverse=True)[:5]
    entries = "\n".join(
        f'    {{name="{_safe_lua_string(m["name"])}", exp={m.get("exp",0)}, hp={m.get("hp",0)}}},'
        for m in top_exp
    )
    return f"""-- respawn_optimizer.lua  [CTOA Generated – {_safe_lua_string(ctx['server_name'])}]
-- Ranks available respawns by exp/hp ratio.

local RESPAWNS = {{
{entries or '    {name="Unknown", exp=0, hp=100},'}
}}

local function bestRespawn()
    local best, bs = nil, 0
    for _, r in ipairs(RESPAWNS) do
        local score = r.hp > 0 and (r.exp / r.hp) or 0
        if score > bs then best, bs = r, score end
    end
    return best
end

local function onLogin()
    local b = bestRespawn()
    if b then
        Game.addEvent("Best respawn: " .. b.name .. " (exp/hp=" ..
            string.format("%.2f", b.exp/b.hp) .. ")", "info")
    end
end

register("onLogin", onLogin)
"""


# ─── Template dispatch table ──────────────────────────────────────────────────
_TEMPLATES: dict[str, Any] = {
    "auto_heal":         _tpl_auto_heal,
    "auto_reconnect":    _tpl_auto_reconnect,
    "loot_filter":       _tpl_loot_filter,
    "cavebot_pathing":   _tpl_cavebot_pathing,
    "target_selector":   _tpl_target_selector,
    "anti_stuck":        _tpl_anti_stuck,
    "alarmy":            _tpl_alarmy,
    "healer_profiles":   _tpl_healer_profiles,
    "flee_logic":        _tpl_flee_logic,
    "target_blacklist":  _tpl_target_blacklist,
    "auto_resupply":     _tpl_auto_resupply,
    "server_blacklist":  _tpl_server_blacklist,
    "server_loot_map":   _tpl_server_loot_map,
    "highscore_scout":   _tpl_highscore_scout,
    "server_stats_lua":  _tpl_server_stats,
    "player_tracker":    _tpl_player_tracker,
    "hunt_orchestrator": _tpl_hunt_orchestrator,
    "economy_bot":       _tpl_economy_bot,
    "pvp_guard":         _tpl_pvp_guard,
    "depot_manager":     _tpl_depot_manager,
    "gold_tracker":      _tpl_gold_tracker,
    "bank_automation":   _tpl_bank_automation,
    "human_delay":       _tpl_human_delay,
    "break_scheduler":   _tpl_break_scheduler,
    "login_randomizer":  _tpl_login_randomizer,
    "rune_maker":        _tpl_rune_maker,
    "combo_spells":      _tpl_combo_spells,
    "area_spell_ctrl":   _tpl_area_spell_ctrl,
    "exp_tracker":       _tpl_exp_tracker,
    "session_log":       _tpl_session_log,
    "respawn_optimizer": _tpl_respawn_optimizer,
}


def _slug(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", url.lower().split("//")[-1])[:40]


def generate_module(mod: dict) -> None:
    server_id  = mod["server_id"]
    task_id    = mod["task_id"]
    template   = mod["template"]
    output_file = mod["output_file"] or f"{template}.lua"

    srv = db.query_one("SELECT url FROM servers WHERE id=%s", (server_id,)) if server_id else None
    slug = _slug(srv["url"]) if srv else "generic"
    out_dir = OUTPUT_BASE / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / output_file

    ctx = _server_ctx(server_id) if server_id else {
        "server_url": "", "server_name": "Generic", "game_type": "tibia-ot",
        "monsters": [], "items": [], "players": [], "highscores": [], "server_info": {},
    }

    code = _render(template, ctx)
    out_path.write_text(code, encoding="utf-8")

    db.execute(
        """
        UPDATE modules
        SET status='GENERATED', output_path=%s, generated_at=now()
        WHERE task_id=%s
        """,
        (str(out_path), task_id),
    )
    # Update daily_stats
    today = datetime.now(timezone.utc).date().isoformat()
    db.execute(
        """
        INSERT INTO daily_stats (dt, modules_generated)
        VALUES (%s, 1)
        ON CONFLICT (dt) DO UPDATE
          SET modules_generated = daily_stats.modules_generated + 1
        """,
        (today,),
    )
    log.info("Generated %s → %s", task_id, out_path)


def run_once() -> None:
    mods = db.query_all(
        "SELECT id, server_id, task_id, template, output_file FROM modules "
        "WHERE status='QUEUED' AND retry_count < %s ORDER BY id LIMIT 20",
        (MAX_RETRIES,),
    )
    if not mods:
        log.info("No QUEUED modules to generate")
        return

    ok = err = 0
    for mod in mods:
        try:
            generate_module(mod)
            ok += 1
        except Exception as exc:
            err += 1
            log.error("Generator error for %s: %s", mod["task_id"], exc)
            db.execute(
                "UPDATE modules SET status='FAILED', retry_count=retry_count+1, test_log=%s WHERE task_id=%s",
                (str(exc)[:2000], mod["task_id"]),
            )

    db.log_run("generator_agent", "ok", f"generated {ok}, failed {err}")


if __name__ == "__main__":
    run_once()
