# CTOA ↔ OTClient Integration Guide

**Complete integration documentation for CTOA AI Toolkit with OTClient native API**

---

## 🎯 Overview

CTOA now supports **native OTClient integration** using official API calls instead of screen automation. This provides:

- ✅ **Performance**: Direct API calls (no polling/OCR)
- ✅ **Reliability**: Event-driven architecture  
- ✅ **Legitimacy**: Uses official OTClient APIs
- ✅ **Community Support**: MIT licensed, open source

---

## 🏗️ Architecture

### **CTOA Generator System**
```
📁 CTOA AI Toolkit
├── 🤖 Generator Agent        → Creates OTClient-specific Lua templates
├── 🤖 Brain v2              → Schedules OTClient modules generation  
├── 📱 Mobile Console        → `/api/agents/otclient/generate` endpoint
├── 🎯 OTClient Templates    → Native API templates (5 new types)
└── 📝 OTClient Modules      → Physical .lua files in scripts/lua/otclient/
```

### **OTClient Integration Layer**
```lua
-- Traditional Approach (Screen Automation)
while true do
  local hp = captureHP()
  if hp < 65 then castSpell("exura") end
  wait(500)
end

-- CTOA OTClient Native Approach (Event-Driven)
local function onHealthChanged(localPlayer, health, maxHealth)
    local hpPercent = (health / maxHealth) * 100
    if hpPercent <= 65 then
        g_game.talk("exura")
    end
end
connect(LocalPlayer, { onHealthChanged = onHealthChanged })
```

---

## 🔧 Installation & Setup

### **Method 1: CTOA Mobile Console (Recommended)**
1. Open CTOA Mobile Console
2. Navigate to **Agents** → **OTClient Native**
3. Click **"Generate OTClient Pack"**
4. Follow installation instructions

### **Method 2: Manual Installation**
```bash
# Clone CTOA repository
git clone https://github.com/famatyyk/CTOAi.git
cd CTOAi

# Copy OTClient modules
cp scripts/lua/otclient/*.lua ~/.otclient/user_dir/ctoa_native/

# Add to your OTClient init.lua
echo 'dofile("user_dir/ctoa_native/ctoa_otclient_loader.lua")' >> ~/.otclient/init.lua
```

### **Method 3: OTClient Modules Directory**
```bash
# Copy to OTClient modules folder
cp scripts/lua/otclient/*.lua /path/to/otclient/modules/ctoa_native/

# Create module descriptor (otmod file)
cat > /path/to/otclient/modules/ctoa_native/ctoa_native.otmod << EOF
Module
  name: ctoa_native
  description: CTOA Native API Integration
  author: CTOA AI Toolkit
  website: github.com/famatyyk/CTOAi
  version: 1.0.0
  autoLoad: true
  autoLoadPriority: 1000
  scripts: [ ctoa_otclient_loader ]
EOF
```

---

## 🎮 Available Modules

### **Core Modules**

| Module | Purpose | OTClient API Used | File |
|--------|---------|-------------------|------|
| **Native Heal** | Smart HP/MP management | `LocalPlayer.onHealthChanged` | `ctoa_native_heal.lua` |
| **Native Combat** | Intelligent targeting | `g_game.attack()`, `g_map.getCreaturesInRange()` | `ctoa_native_combat.lua` |  
| **Native Loot** | Advanced item collection | `Container.onOpen`, `Map.onItemAppear` | `ctoa_native_loot.lua` |
| **OTC Manager** | Module coordination | Core loading system | `ctoa_otclient_loader.lua` |

### **Generated Templates** 
Via CTOA Generator Agent:

| Template ID | Category | Output | Server-Aware |
|-------------|----------|--------|--------------|
| `otclient_heal` | otclient | `otclient_heal.lua` | ❌ |
| `otclient_attack` | otclient | `otclient_attack.lua` | ✅ (uses monster data) |
| `otclient_walk` | otclient | `otclient_walk.lua` | ❌ |
| `otclient_loot` | otclient | `otclient_loot.lua` | ✅ (uses item data) |
| `otclient_manager` | otclient | `otclient_manager.lua` | ✅ (server-specific) |

---

## ⚙️ Configuration

### **Healing Module Configuration**
```lua
-- Edit ctoa_native_heal.lua
local HEAL_SETTINGS = {
    hp_critical = 30,    -- Emergency heal threshold (%)
    hp_low = 65,         -- Regular heal threshold (%)
    mana_low = 40,       -- Mana potion threshold (%)
    heal_spell = "exura",
    heal_critical_spell = "exura gran",
    mana_spell = "utani hur"
}
```

### **Combat Module Configuration**  
```lua
-- Edit ctoa_native_combat.lua
local PRIORITY_TARGETS = {
    "demon",       -- Highest priority (1)
    "dragon lord", -- Priority 2  
    "dragon",      -- Priority 3
    "cyclops",     -- Priority 4
    "dwarf"        -- Lowest priority (5)
}

local COMBAT_CONFIG = {
    attack_range = 8,        -- Maximum attack distance
    target_timeout = 30000,  -- 30s timeout per target
    auto_follow = true       -- Follow targets automatically
}
```

### **Loot Module Configuration**
```lua
-- Edit ctoa_native_loot.lua  
local VALUABLE_LOOT = {
    [3031] = true,  -- gold coin
    [3035] = true,  -- platinum coin
    [3043] = true,  -- crystal coin
    [3155] = true,  -- sudden death rune
    [3370] = true,  -- knight armor
    -- Add more Item IDs...
}

local LOOT_CONFIG = {
    auto_open_corpses = true,
    loot_range = 2,           -- Max distance to loot
    capacity_threshold = 50   -- Stop when capacity < 50
}
```

---

## 🔍 Monitoring & Debugging

### **Log Files**
All modules write to:
```
ctoa_local.log                 # Primary log file
user_dir/ctoa_local.log        # Fallback location  
```

### **Log Format**
```
2026-03-21 15:30:45 [CTOA-OTC-HEAL] Auto heal: exura (HP: 45%)
2026-03-21 15:30:47 [CTOA-OTC-COMBAT] New target: Dragon (priority: 3)  
2026-03-21 15:30:50 [CTOA-OTC-LOOT] Looted: Gold Coin x25
2026-03-21 15:30:52 [CTOA-OTC-MANAGER] Status: in_combat
```

### **Console Commands**
```lua
-- In OTClient console (Ctrl+T)
print(CTOA_Manager.status)           -- Check manager status
print(CTOA_Manager.modules)          -- List loaded modules

-- Reload modules
dofile("user_dir/ctoa_native/ctoa_native_heal.lua")
```

---

## 🔗 OTClient API Reference

### **Core APIs Used**

#### **Game Control**
```lua
g_game.talk(text)                    -- Say text/cast spells
g_game.attack(creature)              -- Attack creature
g_game.follow(creature)              -- Follow creature  
g_game.autoWalk(x, y, z)            -- Walk to position
g_game.move(item, toThing, count)    -- Move items
```

#### **Information Gathering**
```lua
g_game.getLocalPlayer()              -- Get player object
g_game.getAttackingCreature()        -- Current attack target
g_map.getCreaturesInRange(pos, range) -- Find nearby creatures
g_map.getTile(pos)                   -- Get map tile
```

#### **Event System**
```lua
connect(LocalPlayer, { onHealthChanged = function })
connect(LocalPlayer, { onManaChanged = function })
connect(Container, { onOpen = function })
connect(Map, { onItemAppear = function })
connect(Creature, { onDeath = function })
```

#### **Player Information**
```lua
player:getPosition()          -- Player position {x, y, z}
player:getHealthPercent()     -- HP percentage (0-100)
player:getManaPercent()       -- MP percentage (0-100) 
player:getFreeCapacity()      -- Available capacity
player:getInventoryItem(slot) -- Get inventory item
```

### **Advanced Features**
```lua
-- Timing & Events
g_clock.millis()              -- Current time in milliseconds
addEvent(callback, delay)     -- Schedule callback
cycleEvent(callback, interval) -- Repeat callback

-- UI Integration  
modules.game_console.addText(text, mode) -- Add console message
MessageModes.ModeStatus       -- Status message type

-- Item Database
ItemsDatabase:getItemInfo(id) -- Get item information
ItemsDatabase:getItemName(id) -- Get item name
```

---

## ⚡ Performance Optimizations

### **Event-Driven vs Polling**
```lua
-- ❌ BAD: Polling approach (high CPU)
macro(200, function()
    local hp = player:getHealthPercent()
    if hp < 65 then say("exura") end
end)

-- ✅ GOOD: Event-driven approach (efficient)
local function onHealthChanged(player, health, maxHealth)
    local hp = (health / maxHealth) * 100
    if hp < 65 then g_game.talk("exura") end
end
connect(LocalPlayer, { onHealthChanged = onHealthChanged })
```

### **Memory Management**
```lua
-- Cleanup events on disconnect
local function onGameEnd()
    disconnect(LocalPlayer, { onHealthChanged = onHealthChanged })
    -- Clear references
    currentTarget = nil
    lastPosition = nil
end
connect(g_game, { onGameEnd = onGameEnd })
```

---

## 🎯 CTOA Generator Integration

### **Server-Aware Generation**
CTOA automatically generates server-specific modules based on:

```python
# In generator_agent.py
def _tpl_otclient_attack(ctx: dict) -> str:
    monsters = ctx.get("monsters", [])[:8]  # Top 8 monsters from server data
    monster_list = "\n".join(f'    "{m.get("name", "Unknown")}",' for m in monsters)
    
    return f"""-- otclient_attack.lua  [CTOA Generated - OTClient Native]
local TARGET_LIST = {{
{monster_list}
}}
-- ... rest of template
"""
```

### **Template Categories**
```python
# In brain_v2.py - OTClient templates
{"id": "otclient_heal",    "category": "otclient", "requires": []},
{"id": "otclient_attack",  "category": "otclient", "requires": ["monsters"]},
{"id": "otclient_loot",    "category": "otclient", "requires": ["items"]}, 
{"id": "otclient_manager", "category": "otclient", "requires": [], "is_program": True},
```

### **Mobile Console API**
```bash
# Generate OTClient modules
curl -X POST http://localhost:8787/api/agents/otclient/generate \
  -H "Authorization: Bearer $CTOA_TOKEN"

# Response
{
  "ok": true,
  "client_type": "otclient_native", 
  "modules": [...],
  "generated_count": 4,
  "api_features": [
    "g_game.* native calls",
    "Event-driven (connect/disconnect)",
    "LocalPlayer callbacks",
    "Container/Map events", 
    "Performance optimized"
  ]
}
```

---

## 🔒 Security & Best Practices

### **Legitimate Use**
- ✅ **Open Source**: OTClient is MIT licensed
- ✅ **Official APIs**: Uses documented OTClient functions
- ✅ **Community Accepted**: No packet injection or memory manipulation

### **Server Compliance**
```lua
-- Always check server rules before using
-- Examples of compliant automation:
local function onLogin()
    -- Read and respect server automation policy
    print("[CTOA] Always follow server rules!")
end
```

### **Safety Features**
```lua
-- Built-in safety mechanisms
local function emergencyStop()
    if player:getHealthPercent() < 10 then
        g_game.talk("exura gran")  -- Emergency heal
        return true  -- Stop other actions
    end
    return false
end
```

---

## 🚀 Advanced Usage

### **Custom Module Development**
```lua
-- Create your own CTOA-compatible module
local MyCustomModule = {
    name = "custom_farming",
    enabled = true
}

function MyCustomModule:onThink()
    -- Your logic here
end

-- Register with CTOA Manager
if CTOA_Manager then
    CTOA_Manager:registerModule("custom_farming", MyCustomModule)
end
```

### **Multi-Server Support**
```lua
-- Server-specific configurations
local SERVER_CONFIGS = {
    ["mythibia.online"] = {
        targets = {"rat", "cave rat", "rotworm"}, 
        heal_threshold = 70
    },
    ["otland.net"] = {
        targets = {"demon", "dragon lord"},
        heal_threshold = 80
    }
}

local function getServerConfig()
    local serverName = g_game.getServerName() or "unknown"
    return SERVER_CONFIGS[serverName] or SERVER_CONFIGS["mythibia.online"]
end
```

---

## 🌐 Community Engagement Plan

### **OTClient Community Integration**
1. **Gitter Chat**: Join https://gitter.im/edubart/otclient
2. **GitHub Contributions**: Submit modules to edubart/otclient
3. **OTLand Forums**: Share CTOA modules and tutorials
4. **Reddit r/TibiaMMO**: Showcase legitimate automation approaches

### **Documentation Contributions**
```bash
# Submit CTOA modules to OTClient wiki
https://github.com/edubart/otclient/wiki

# Example contribution:
"AI-Generated Modules with CTOA Toolkit"
- How to use CTOA for legitimate automation
- Templates for common bot behaviors  
- Event-driven programming examples
```

---

## 🐛 Troubleshooting

### **Common Issues**

| Issue | Cause | Solution |
|-------|-------|----------|
| "Module not loading" | File path incorrect | Check `user_dir/ctoa_native/` exists |
| "API calls not working" | OTClient version | Update to latest OTClient build |
| "Events not firing" | Connection syntax | Use `connect(Object, { eventName = function })` |
| "High CPU usage" | Polling instead of events | Use event-driven approach |

### **Debug Commands**
```lua
-- In OTClient console
print("LocalPlayer available:", g_game.getLocalPlayer() ~= nil)
print("Game online:", g_game.isOnline())
print("Client version:", g_app.getVersion())

-- Test API calls
g_game.talk("test message")
local player = g_game.getLocalPlayer()
if player then
    print("Player HP:", player:getHealthPercent())
end
```

---

## 📚 Further Reading

- **OTClient Documentation**: https://github.com/edubart/otclient/wiki
- **CTOA AI Toolkit**: https://github.com/famatyyk/CTOAi
- **Lua API Reference**: OTClient source code `/src/client/luafunctions.cpp`
- **Community Discord**: https://discord.gg/otclient (if exists)

---

**🤖 Generated by CTOA AI Toolkit v1.0**  
*Last Updated: March 21, 2026*

---