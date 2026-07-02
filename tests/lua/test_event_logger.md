# Test Event Logger

## Cases
- verify output has timestamp, hp, mana, exp
- verify position included when available
- verify no runtime error on missing optional fields
- verify numeric fallbacks for hp/mana/exp when state fields are missing
- verify JSONL output is stable enough for line-based logging
