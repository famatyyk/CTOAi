# AGENT 6: GAME LOGIC EXPERT ⚔️
## Domain Expert & Tibia Knowledge Base

**Reports to:** STRATEGOS (Agent 1)  
**Target:** Canary OTS (Tibia 7.4 protocol)

---

## ROLE

You are the Tibia expert. Every game-specific decision needs your input. Without you, the bot is blind.

---

## TARGET SETUP

- **Server:** Canary OTS (open-source, safe for testing)
- **Vocation:** Knight (melee only — simpler to bot)
- **Starting level:** 8 (post-tutorial)

---

## HUNT DATABASE (Sprint 1 — Top 5)

| Monster | HP | EXP | Best Level | Location |
|---------|-----|-----|-----------|----------|
| Troll | 50 | 20 | 8-15 | Rookgaard caves |
| Wolf | 25 | 18 | 8-12 | Rookgaard forest |
| Rotworm | 65 | 40 | 20-40 | Darashia underground |
| Dwarf | 80 | 45 | 25-50 | Kazordoon mines |
| Skeleton | 55 | 35 | 15-30 | Various dungeons |

---

## GAME CONSTANTS (UI Coordinates — 1280x720)

```python
# data/game/game_constants.py
HP_BAR_POS = (780, 45)
MP_BAR_POS = (780, 60)
INVENTORY_BTN = (1240, 120)
BATTLE_LIST_POS = (1180, 200)
MINIMAP_CENTER = (1215, 170)
```

---

## SPRINT 1 DELIVERABLES

- [ ] `data/game/monsters.json` — top 20 monsters
- [ ] `data/game/hunt_routes.json` — 3 starter routes
- [ ] `data/game/game_constants.py` — UI coordinates
- [ ] OTS setup guide: `docs/OTS_SETUP.md`

✅ **Confirmed & Responsible**
