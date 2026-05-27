# AGENT 4: ML/AI BRAIN 🧠
## Intelligence Core & Decision Engine

**Reports to:** STRATEGOS (Agent 1)  
**Depends on:** AGENT 3 (DATA ENGINEER) for training data

---

## ROLE

Build the brain that decides what the bot does every tick. Start with rules, evolve to ML.

---

## DECISION ARCHITECTURE

```
Game State (from perception/)
        ↓
   Rule Engine       ← Safety overrides (HP < 30% → flee)
        ↓
  Decision Tree      ← Hunt strategy (which monster? which area?)
        ↓
   RL Q-Agent        ← Optimizes action sequences over time
        ↓
   Action Output     → action/ layer executes
```

---

## HYBRID MODEL

### Phase 1: Rule Engine (Sprint 1)
```python
# decision/rules.py
RULES = [
    {"condition": "hp < 30", "action": "flee_to_depot"},
    {"condition": "mp < 20", "action": "use_mana_potion"},
    {"condition": "target_dead", "action": "loot"},
    {"condition": "bag_full", "action": "go_to_depot"},
]
```

### Phase 2: Q-Learning (Sprint 2-3)
- State space: (hp%, mp%, monster_count, loot_value)
- Actions: attack | flee | loot | idle | potion
- Reward: +xp gained, +gold, -death penalty

---

## SPRINT 1 DELIVERABLES

- [ ] `decision/rules.py` — priority rule engine
- [ ] `decision/brain.py` — main decision loop
- [ ] Q-table skeleton in `decision/ml_model.py`
- [ ] Benchmark: 70%+ correct on 100 test states

✅ **Confirmed & Responsible**
