#!/usr/bin/env python3
"""
Convert raw OTClient/Tibia source files into instruction-following JSONL pairs
for fine-tuning qwen2.5-coder with LoRA/Unsloth.

Usage: python build_dataset.py --raw ../data/raw/ --output ../data/dataset.jsonl
"""
import json, re, argparse, random
from pathlib import Path

# System prompt embedded in every training example
SYSTEM = (
    "Jestes ekspertem od OTClient, vBot, Tibia bota i Lua skryptow. "
    "Piszesz kod, wyjasnisz architekture, debugujesz problemy zwiazane z OpenTibia. "
    "Odpowiadaj zwiezle i daj dzialajacy kod kiedy to mozliwe."
)

# Templates for generating instruction pairs from raw code files
CODE_TEMPLATES = [
    ("Wyjasnij co robi ten kod {ext}:\n\n```{lang}\n{code}\n```",
     "Ten kod {purpose}. {explanation}"),
    ("Jak poprawic ten fragment {ext}?\n\n```{lang}\n{code}\n```",
     "Mozna poprawic przez: {improvements}"),
    ("Napisz dokumentacje dla tego modulu:\n\n```{lang}\n{code}\n```",
     "## Dokumentacja\n\n{doc}"),
    ("Czy widzisz bledy w tym kodzie?\n\n```{lang}\n{code}\n```",
     "Analiza kodu: {analysis}"),
]

LUA_SNIPPETS_TEMPLATES = [
    {
        "instruction": "Jak w vBot/OTClient zrobic auto-loot dla konkretnych itemow?",
        "response": """Przyklad auto-loot w Lua dla vBot:

```lua
local lootItems = {2148, 2152, 7369}  -- ids itemow do zbierania

local function autoLoot()
    local containers = g_game.getContainers()
    for _, container in pairs(containers) do
        for slot = 0, container:getCapacity() - 1 do
            local item = container:getItem(slot)
            if item and table.contains(lootItems, item:getId()) then
                -- przesuniecie do glownego kontenera
                g_game.move(item, player:getInventoryItem(INVENTORY_BACKPACK), 1)
            end
        end
    end
end

local lootTimer = cycleEvent(autoLoot, 500)
```

Dodaj `lootTimer` do cleanup listy w `onLogout`."""
    },
    {
        "instruction": "Jak wykryc czy postac jest w walce w OTClient Lua?",
        "response": """```lua
local function isInCombat()
    return player:getSkull() ~= SKULL_NONE
        or player:getCondition(CONDITION_INFIGHT) ~= nil
end

-- Alternatywnie przez icons
local function isInCombatByIcon()
    local icons = player:getIcons()
    return bit32.band(icons, ICON_SWORDS) ~= 0
end
```

`CONDITION_INFIGHT` jest bardziej niezawodne - aktywne przez 60s po ostatnim ataku."""
    },
    {
        "instruction": "Jak zrobic pathfinding do konkretnej pozycji w OTClient?",
        "response": """```lua
local function walkTo(targetPos)
    local path = g_map.findPath(player:getPosition(), targetPos, 20, 0)
    if not path then
        print("Brak sciezki do " .. tostring(targetPos))
        return false
    end
    
    local walkTimer
    local step = 1
    
    walkTimer = cycleEvent(function()
        if step > #path then
            removeEvent(walkTimer)
            return
        end
        
        local dir = path[step]
        g_game.walk(dir)
        step = step + 1
    end, 400)
    
    return true
end

-- Uzycie:
walkTo({x=1000, y=1000, z=7})
```

Odstep 400ms odzwierciedla typowa szybkosc chodzenia postaci."""
    },
    {
        "instruction": "Jak zbudowac system spell-casting w OTClient z cooldownem?",
        "response": """```lua
local spells = {
    heal = {name = "exura", cooldown = 1000, lastCast = 0},
    mana  = {name = "exura gran", cooldown = 2000, lastCast = 0},
}

local function castSpell(spellKey)
    local spell = spells[spellKey]
    if not spell then return end
    
    local now = g_clock.millis()
    if now - spell.lastCast < spell.cooldown then return end
    
    g_game.talk(spell.name)
    spell.lastCast = now
end

-- Auto-heal loop
local healTimer = cycleEvent(function()
    local hp = player:getHealth()
    local maxHp = player:getMaxHealth()
    if hp / maxHp < 0.7 then
        castSpell("heal")
    end
end, 200)
```"""
    },
]


def ext_to_lang(ext: str) -> str:
    return {"lua": "lua", "cpp": "cpp", "h": "cpp", "py": "python", "md": "markdown"}.get(ext, ext)


def chunk_code(content: str, max_chars: int = 1200) -> list[str]:
    lines = content.splitlines()
    chunks, cur = [], []
    cur_len = 0
    for line in lines:
        if cur_len + len(line) > max_chars and cur:
            chunks.append("\n".join(cur))
            cur, cur_len = [], 0
        cur.append(line)
        cur_len += len(line) + 1
    if cur:
        chunks.append("\n".join(cur))
    return chunks


def make_code_example(file_path: Path, content: str) -> dict | None:
    ext = file_path.suffix.lstrip(".")
    lang = ext_to_lang(ext)
    chunks = chunk_code(content)
    if not chunks:
        return None
    chunk = random.choice(chunks[:3])  # bias toward beginning of file
    if len(chunk) < 80:
        return None

    fname = file_path.name
    instruction = f"Wyjasnij ten fragment kodu z pliku `{fname}`:\n\n```{lang}\n{chunk}\n```"
    response = f"To jest fragment kodu {lang.upper()} z projektu OTClient/Tibia.\n\nAnalizujac strukture: kod implementuje logike zwiazana z `{fname}`. Kluczowe elementy to patterny typowe dla silnika OTClient."

    return {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": instruction},
            {"role": "assistant", "content": response},
        ]
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(Path(__file__).parent.parent / "data" / "raw"))
    ap.add_argument("--output", default=str(Path(__file__).parent.parent / "data" / "dataset.jsonl"))
    ap.add_argument("--max", type=int, default=5000, help="Max examples to generate")
    args = ap.parse_args()

    raw_dir = Path(args.raw)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    examples = []

    # 1. Hardcoded Lua/vBot expert snippets (high quality)
    for snip in LUA_SNIPPETS_TEMPLATES:
        examples.append({
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": snip["instruction"]},
                {"role": "assistant", "content": snip["response"]},
            ]
        })

    # 2. Auto-generated from raw source files
    if raw_dir.exists():
        all_files = list(raw_dir.rglob("*"))
        code_files = [f for f in all_files if f.is_file() and f.suffix.lstrip(".") in {"lua", "cpp", "h", "py"}]
        random.shuffle(code_files)
        print(f"Found {len(code_files)} source files in {raw_dir}")

        for fpath in code_files[:args.max]:
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                ex = make_code_example(fpath, content)
                if ex:
                    examples.append(ex)
            except Exception:
                pass

    random.shuffle(examples)
    print(f"Total examples: {len(examples)}")

    with open(out_path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"Dataset written to: {out_path}")
    print(f"Format: ShareGPT messages (system/user/assistant)")
    print(f"Ready for Unsloth fine-tuning on Google Colab T4")


if __name__ == "__main__":
    main()
