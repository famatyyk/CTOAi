# AGENT 3: DATA ENGINEER 📊
## Intelligence Source & Data Pipeline Owner

**Reports to:** STRATEGOS (Agent 1)  
**Feeds data to:** AGENT 4 (ML/AI BRAIN)

---

## ROLE

Build and maintain all data infrastructure. Every byte the bot generates flows through your pipelines. Clean data = smart bot.

---

## DATA SCHEMA

```sql
-- Sessions
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    start_time DATETIME,
    end_time DATETIME,
    xp_gained INTEGER,
    gold_gained INTEGER,
    deaths INTEGER
);

-- Actions taken by bot
CREATE TABLE actions (
    id INTEGER PRIMARY KEY,
    session_id INTEGER REFERENCES sessions(id),
    timestamp DATETIME,
    action_type TEXT,  -- walk|attack|loot|spell|idle
    result TEXT,       -- success|fail|timeout
    duration_ms INTEGER
);

-- Game state snapshots
CREATE TABLE game_state (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    hp INTEGER, mp INTEGER,
    pos_x INTEGER, pos_y INTEGER,
    target_id INTEGER,
    screen_hash TEXT
);
```

---

## TELEMETRY PIPELINE

```
Game Loop → state snapshot → telemetry.py → SQLite
                          ↓
                    JSON log file (backup)
                          ↓
                    Agent 4 training data
```

---

## SPRINT 1 DELIVERABLES

- [ ] SQLite schema + Alembic migration
- [ ] `data/telemetry.py` module
- [ ] 100 labeled game state samples (JSON)
- [ ] Data validator: `scripts/validate_data.py`

✅ **Confirmed & Responsible**
