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

## GAME CONSTANTS (UI Coordinates — Resolution-Aware)

Coordinates are **never hardcoded** — they are computed at runtime from the detected screen resolution using anchor ratios calibrated on 1280×720. Use `get_ui_coords()` to retrieve them for any display.

```python
# data/game/game_constants.py
import pyautogui

def get_screen_size() -> tuple[int, int]:
    """Return (width, height) of the primary monitor."""
    return pyautogui.size()

def get_ui_coords() -> dict:
    """Scale Tibia OTS UI coordinates to the current screen resolution.

    Anchor ratios calibrated on 1280×720 (Canary OTS default window).
    Multiply by actual (w/1280, h/720) to adapt to any display.
    """
    w, h = get_screen_size()
    sx, sy = w / 1280, h / 720
    return {
        "HP_BAR_POS":      (int(780 * sx), int(45 * sy)),
        "MP_BAR_POS":      (int(780 * sx), int(60 * sy)),
        "INVENTORY_BTN":   (int(1240 * sx), int(120 * sy)),
        "BATTLE_LIST_POS": (int(1180 * sx), int(200 * sy)),
        "MINIMAP_CENTER":  (int(1215 * sx), int(170 * sy)),
    }
```

> **Rule:** Agent 7 must call `get_ui_coords()` at bot startup — never use raw pixel constants in bot logic.

---

## SPRINT 1 DELIVERABLES

- [ ] `data/game/monsters.json` — top 20 monsters
- [ ] `data/game/hunt_routes.json` — 3 starter routes
- [ ] `data/game/game_constants.py` — UI coordinates
- [ ] OTS setup guide: `docs/OTS_SETUP.md`

✅ **Confirmed & Responsible**
