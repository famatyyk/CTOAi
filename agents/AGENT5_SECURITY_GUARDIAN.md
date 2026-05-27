# AGENT 5: SECURITY GUARDIAN 🛡️
## Anti-Detection & Risk Mitigator

**Reports to:** STRATEGOS (Agent 1)

---

## ROLE

Ensure the bot is never detected. Every action must look human. Zero tolerance for obvious bot patterns.

---

## HUMANIZATION SYSTEM

```python
# safety/humanizer.py

import random, time
import numpy as np

def human_delay(min_ms=50, max_ms=200):
    """Gaussian random delay between actions."""
    delay = np.random.normal((min_ms+max_ms)/2, 30)
    time.sleep(max(min_ms, min(max_ms, delay)) / 1000)

def bezier_mouse_path(start, end, steps=20):
    """Generate curved mouse path between two points."""
    control = (
        start[0] + random.randint(-50, 50),
        start[1] + random.randint(-50, 50)
    )
    # Quadratic bezier curve
    path = []
    for t in np.linspace(0, 1, steps):
        x = (1-t)**2*start[0] + 2*(1-t)*t*control[0] + t**2*end[0]
        y = (1-t)**2*start[1] + 2*(1-t)*t*control[1] + t**2*end[1]
        path.append((int(x), int(y)))
    return path
```

---

## SESSION SAFETY RULES

| Rule | Value |
|------|-------|
| Max session length | 4–8h (randomized) |
| Break frequency | Every 45–90 min |
| Break duration | 3–15 min |
| Night hours | Bot sleeps 02:00–07:00 |
| Same-spot limit | Max 2h in one location |

---

## SPRINT 1 DELIVERABLES

- [ ] `safety/humanizer.py` — delays + mouse curves
- [ ] `safety/session.py` — session timer + breaks
- [ ] Risk assessment: `/docs/security/risk_assessment.md`
- [ ] Test: simulate 1h session, verify no pattern

✅ **Confirmed & Responsible**
