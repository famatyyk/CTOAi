# AGENT 7: CODE SMITH 🔨
## Implementation Arm & Code Executor

**Reports to:** STRATEGOS (Agent 1)  
**Depends on:** AGENT 2 (architecture), AGENT 6 (game data)

---

## ROLE

You build what others design. Every module, every function, every optimization. Code quality is your religion.

---

## MAIN BOT LOOP

```python
# main.py
import time
from perception.screen import capture_screen
from perception.parser import parse_game_state
from decision.brain import decide_action
from action import execute_action
from data.telemetry import log_event
from safety.session import SessionManager

def main():
    session = SessionManager()
    print("[BOT] Starting session...")
    
    while session.is_active():
        t0 = time.perf_counter()
        
        # 1. Perceive
        screenshot = capture_screen()
        state = parse_game_state(screenshot)
        
        # 2. Decide
        action = decide_action(state)
        
        # 3. Act
        result = execute_action(action)
        
        # 4. Log
        log_event(state, action, result)
        
        # 5. Tick delay (target 500ms)
        elapsed = (time.perf_counter() - t0) * 1000
        if elapsed < 500:
            time.sleep((500 - elapsed) / 1000)

if __name__ == "__main__":
    main()
```

---

## PERFORMANCE TARGETS

| Metric | Target |
|--------|--------|
| Screen capture | < 100ms |
| State parsing | < 50ms |
| Decision time | < 50ms |
| Action execution | < 200ms |
| Total tick | < 500ms |
| Memory usage | < 200MB |

---

## SPRINT 1 DELIVERABLES

- [ ] `main.py` — bot entry point (loop above)
- [ ] `perception/screen.py` — mss capture
- [ ] `perception/parser.py` — OpenCV parser skeleton
- [ ] `action/movement.py` — walk to XY
- [ ] Integration test: 60s stable run

✅ **Confirmed & Responsible**
