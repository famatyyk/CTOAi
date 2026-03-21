# 🚀 OTClient Quick Start - CTOA Native

**Get CTOA working with OTClient in 5 minutes**

---

## ⚡ 30-Second Setup

```bash
# 1. Clone CTOA
git clone https://github.com/famatyyk/CTOAi.git
cd CTOAi

# 2. Copy modules to OTClient
cp scripts/lua/otclient/*.lua ~/.otclient/user_dir/ctoa_native/

# 3. Add to init.lua  
echo 'dofile("user_dir/ctoa_native/ctoa_otclient_loader.lua")' >> ~/.otclient/init.lua

# 4. Start OTClient - modules auto-load!
```

---

## ✅ Verification

**In OTClient console (Ctrl+T):**
```lua
print(CTOA_OTCLIENT.loaded)  -- Should show: true
print(CTOA_OTCLIENT.modules) -- Should list: ctoa_native_heal, etc.
```

**Check logs:**
```bash
tail -f ~/.otclient/ctoa_local.log
# Should see: [CTOA-OTC] messages
```

---

## 🎯 What You Get

| Module | Auto-Activates On |
|--------|------------------|
| **ctoa_native_heal.lua** | HP drops below 65% → casts "exura" |
| **ctoa_native_combat.lua** | Finds closest monster → attacks automatically |  
| **ctoa_native_loot.lua** | Corpse opened → loots valuable items |
| **ctoa_otclient_loader.lua** | Game login → loads all modules |

---

## 🔧 Quick Config

**Edit healing thresholds:**
```lua
-- In ~/.otclient/user_dir/ctoa_native/ctoa_native_heal.lua
local HEAL_SETTINGS = {
    hp_critical = 30,  -- ← Change this
    hp_low = 65,       -- ← Change this
    heal_spell = "exura gran"  -- ← Change this
}
```

**Edit target priorities:**
```lua
-- In ~/.otclient/user_dir/ctoa_native/ctoa_native_combat.lua  
local PRIORITY_TARGETS = {
    "demon",     -- ← Add your monsters
    "dragon",    -- ← Higher in list = higher priority
    "cyclops"
}
```

---

## 🚨 Safety Notes

- ✅ **Uses official OTClient APIs** (legitimate)  
- ⚠️ **Always follow server rules** (check automation policy)
- 🔍 **Monitor logs** for issues (`ctoa_local.log`)
- 🛑 **Test in safe areas first**

---

## 🆘 Quick Fixes  

**Modules not loading?**
```bash
# Check file paths exist
ls ~/.otclient/user_dir/ctoa_native/
# Should show: ctoa_native_heal.lua, ctoa_native_combat.lua, etc.
```

**Not casting spells?**  
```lua
-- In OTClient console, test manually:
g_game.talk("exura")  -- Should cast heal
```

**No auto-attack?**
```lua  
-- Check if creatures detected:
local player = g_game.getLocalPlayer()
local pos = player:getPosition()
local creatures = g_map.getCreaturesInRange(pos, 8)
print("Creatures nearby:", #creatures)
```

---

## 🔗 Next Steps

1. **Full Documentation**: [OTCLIENT_INTEGRATION.md](OTCLIENT_INTEGRATION.md)
2. **CTOA Mobile Console**: `http://localhost:8787` → Generate custom modules
3. **Community**: Join https://gitter.im/edubart/otclient for help

---

**🤖 CTOA AI Toolkit - Making Tibia automation legitimate through open source APIs**