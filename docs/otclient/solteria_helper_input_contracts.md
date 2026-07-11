# Solteria Helper Input Contracts

- Status: `passed`
- Checks: `16` / `16`
- Failed: `0`
- Next action: Run ModuleStaticGates, then sandbox SmokeAttachModules before any runtime bridge consumes input decisions.

## Rule

Hotkey and modal modules may parse, normalize, describe, and decide. They must not bind keys, create widgets, execute commands, dispatch plans, or promote live runtime behavior.

## Hotkey Fixtures

| Fixture | Status | Expected | Evidence |
|---|---:|---|---|
| `modifier_order_normalizes_ctrl_h` | `passed` | `{"input": " ctrl + h ", "normalized": "Ctrl+H", "reason": "ok", "valid": true}` | parser trims input, normalizes single-character keys, and emits ordered modifiers |
| `command_alias_maps_to_meta_function_key` | `passed` | `{"input": "command+f12", "normalized": "Meta+F12", "reason": "ok", "valid": true}` | command/cmd/win aliases map to Meta and F1-F24 are accepted |
| `empty_hotkey_is_rejected` | `passed` | `{"input": "", "normalized": "", "reason": "empty", "valid": false}` | empty input has an explicit fail-closed reason |
| `modifier_only_hotkey_is_rejected` | `passed` | `{"input": "Ctrl+Alt", "normalized": "", "reason": "missing_key", "valid": false}` | modifier-only input has no executable key and is rejected |
| `invalid_function_key_is_rejected` | `passed` | `{"input": "F25", "normalized": "", "reason": "invalid_key", "valid": false}` | function key range is bounded to F1-F24 |
| `multiple_keys_are_rejected` | `passed` | `{"input": "Ctrl+A+B", "normalized": "", "reason": "multiple_keys", "valid": false}` | a second non-modifier key fails closed |
| `reserved_keys_are_rejected` | `passed` | `{"input": "Escape", "normalized": "", "reason": "reserved_key", "valid": false}` | reserved UI keys cannot become helper bindings |
| `binding_decision_reports_changed_allowed_choice` | `passed` | `{"allowed": ["Ctrl+H", "Ctrl+J"], "allowed_result": true, "changed": true, "current": "Ctrl+H", "input": "Ctrl+J", "normalized": "Ctrl+J", "reason": "changed"}` | bindingDecision reports normalized value, previous value, and changed state without binding keys |
| `binding_decision_rejects_disallowed_choice` | `passed` | `{"allowed": ["Ctrl+H", "Ctrl+J"], "allowed_result": false, "current": "Ctrl+H", "input": "Ctrl+K", "normalized": "Ctrl+K", "reason": "not_allowed"}` | bindingDecision enforces explicit allow-list before the shell may bind |

## Modal Fixtures

| Fixture | Status | Expected | Evidence |
|---|---:|---|---|
| `request_builds_bounded_confirmation` | `passed` | `{"action": "cavebot_delete", "context": "wp 1", "expires_at_ms": 5500, "message": "Confirm cavebot delete: wp 1", "now_ms": 1000, "ttl_ms": 4500}` | request creates a bounded confirmation payload and readable action text |
| `pending_state_expires_after_ttl` | `passed` | `{"action": "cavebot_delete", "expired_at_ms": 6000, "pending_after_expiry": false, "pending_at_ms": 5000, "pending_before_expiry": true}` | isPending is time-bounded and action-specific |
| `guarded_action_requires_confirmation` | `passed` | `{"action": "cavebot_delete", "allowed": false, "confirm": false, "reason": "confirmation_required"}` | guarded destructive actions fail closed without confirm=true |
| `confirmed_guarded_action_is_allowed` | `passed` | `{"action": "cavebot_delete", "allowed": true, "confirm": true, "reason": "confirmed"}` | confirmation payload is required before a guarded action can proceed |
| `expired_guarded_action_is_blocked` | `passed` | `{"action": "cavebot_delete", "allowed": false, "confirm": true, "decision_text": "confirmation expired", "reason": "expired"}` | expired confirmations are denied and have explicit operator text |
| `unguarded_action_stays_allowed_without_runtime_shortcut` | `passed` | `{"action": "tab_switch", "allowed": true, "confirm": false, "reason": "unguarded_action"}` | unprotected UI intents remain allowed while the module still cannot execute runtime actions |
| `decision_text_covers_allow_deny_states` | `passed` | `{"confirmed": "confirmed: cavebot delete", "expired": "confirmation expired", "required": "confirmation required: cavebot delete"}` | decisionText turns modal states into stable operator text |

## Verification

```powershell
.\.venv\Scripts\python.exe scripts\ops\otclient_input_contract_fixtures.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows\solteria_helper_test_env.ps1 -Action InputContractsStaticSmoke
```
