# Engine Brain Symbol Map

Generated at: `2026-07-11T09:26:31+00:00`

This is a lightweight map for navigation, not a full source dump.

## `agents/definitions.py`

- L24: def _normalize_agent(agent)
- L39: def _read_registry_payload(registry_path)
- L46: def _load_registry(registry_path)
- L58: def validate_registry_consistency(registry_path)
- L103: def get_agent_config(agent_id)
- L108: def list_agents()
- L113: def get_agents_for_task(task_id)
- L122: def _load_toolkit_registry(registry_path)
- L134: def list_toolkit_agents(registry_path)
- L139: def get_toolkit_agent_config(agent_id, registry_path)
- L144: class APICostOptimizerAgent
- L147: def __init__(self)
- L164: def score_action_risk(self, tool_name, payload)
- L172: def registry_config(self)

## `agents/toolkit/ctoai_foundry_agent/app.py`

- L31: class IncidentInput
- L39: class AgentResponse
- L49: class CTOAIFoundryRouter
- L52: def __init__(self)
- L73: def _append_evidence(self, kind, payload)
- L83: def _chat(self, model, prompt)
- L103: def triage(self, incident)
- L126: def finalize(self, incident, triage)
- L171: def invoke(self, incident)
- L181: def health()
- L186: def invoke(payload)
- L190: def run_cli()
- L203: def main()

## `alembic/env.py`

- L15: def _db_url()
- L29: def run_migrations_offline()
- L37: def run_migrations_online()

## `alembic/versions/20260521_0001_sprint0_baseline.py`

- L20: def upgrade()
- L25: def downgrade()

## `api/main.py`

- L32: def _env_bool(name, default)
- L39: def _env_int(name, default)
- L49: def _is_production_env()
- L57: def _is_weak_secret(secret)
- L85: def _backend_kind(url)
- L134: def _api_self_register_enabled()
- L138: def _api_self_register_code()
- L142: def _validate_api_security_config()
- L217: def _safety_telemetry_snapshot()
- L235: def _sanitize_assistant_content(content)
- L254: def _friendly_model_error(exc)
- L291: class Message
- L296: class ChatRequest
- L306: class OpenAIChatRequest
- L316: class RegisterRequest
- L324: class LoginRequest
- L329: class BootstrapRequest
- L335: class InviteRequest
- L340: class AcceptInviteRequest
- L344: class RoleUpdateRequest
- L348: def _estimate_chars(messages)
- L352: def _is_complex(messages)
- L357: def _low_quality(content, user_chars)
- L369: def _utc_now_iso()
- L373: def _atomic_write_json(path, payload)
- L408: def _display_path(path_value)
- L431: def _redact_release_evidence_text(value)
- L445: def _public_release_evidence_value(value, key)
- L462: def _public_audit_value(value, key)
- L479: def _read_release_evidence_payload(path)
- L495: def _hash_password(password)
- L499: def _verify_password(password, hashed)
- L506: def _sanitize_username(username)
- L515: def _seed_password(env_name)
- L522: def _seed_accounts()
- L555: def _default_account_seed_blocked()
- L559: def _read_auth_store_payload(path)
- L578: def _load_auth_store()
- L620: def _save_auth_store(store)
- L624: def _append_activity(store)
- L647: def _b64url_encode(data)
- L651: def _b64url_decode(data)
- L656: def _jwt_encode(payload)
- L667: def _jwt_decode(token)
- L692: def _issue_token(user)
- L703: def _extract_bearer(authorization)
- L716: def _first_forwarded_ip(value)
- L726: def _client_ip_from_request(request)
- L736: def _rate_limit_group(path)
- L746: def _rate_limit_for_group(group)
- L754: def _consume_rate_limit(ip, group, now_ts)
- L799: def _audit_actor_from_request(request)
- L813: def _append_audit_http(request, status, actor, meta)
- L839: async def security_middleware(request, call_next)
- L881: def _current_user(authorization)
- L904: def _require_roles(user, allowed)
- L909: def _select_models(req)
- L982: async def _call_model(model_name, backend_url, backend_key, messages, temperature, max_tokens)
- L1016: async def _execute_chat(req)
- L1104: def _safe_chat_route_info(route_info)
- L1120: def _require_chat_debug_route_user(user)
- L1130: def health()
- L1135: def status()
- L1156: def bootstrap(req)
- L1204: def register(req, authorization)
- L1270: def login(req)
- L1294: def me(authorization)
- L1300: def create_invite(req, authorization)
- L1337: def accept_invite(req, authorization)
- L1385: def community_members(authorization)
- L1405: def set_member_role(username, req, authorization)
- L1446: def community_feed(authorization)
- L1455: def community_invites(authorization)
- L1466: def release_evidence()
- L1547: async def chat(req, authorization)
- L1566: async def chat_completions(req, authorization)
- L1608: async def safety_metrics(authorization)
- L1622: async def safety_telemetry(authorization)
- L1631: async def safety_status()

## `api/startup_guard.py`

- L7: def _env_bool(name, default)
- L14: def _is_production_env()
- L18: def validate_early_security_config()

## `bot/action/__init__.py`

- L18: def set_current_state(state)
- L22: def _select_target()
- L32: def _attack_with_rotation()
- L38: def _follow_route()
- L63: def execute_action(action)

## `bot/action/combat.py`

- L24: def _can_act()
- L28: def attack_target()
- L36: def use_hp_potion()
- L43: def use_strong_hp_potion()
- L50: def use_mp_potion()
- L57: def use_antidote()

## `bot/action/input_backend.py`

- L24: def _noop_press(_key)
- L28: def _noop_click(_x, _y)
- L38: def _load_pydirectinput()
- L54: def _load_pyautogui()
- L79: def is_available()
- L83: def backend_name()
- L87: def _is_tibia_active_window()
- L104: def _can_dispatch_input()
- L112: def press(key)
- L118: def click(x, y)

## `bot/action/loot.py`

- L9: def loot_corpse()

## `bot/action/movement.py`

- L19: def _auto_follow_key()
- L23: def _auto_follow_interval_ms()
- L27: def _auto_follow_stuck_ms()
- L31: def _auto_follow_refresh_ms()
- L35: def walk_to(x, y)
- L46: def idle_move()
- L55: def _state_position_tuple(state)
- L72: def auto_follow(state)

## `bot/action/spell_rotation.py`

- L36: def _default_config()
- L51: def _load_config()
- L75: def _active_client_profile_lower()
- L79: def _merge_rotation_config(cfg)
- L113: def _active_window_title_lower()
- L129: def _detect_profession(level, cfg)
- L163: def cast_rotation_spell(level, profession_override)

## `bot/config/runtime_profile.py`

- L28: def _set_config_error(code, message, exc)
- L37: def last_config_error()
- L41: def _load_config()
- L93: def active_profile_name()
- L101: def _profile_values()
- L118: def _raw_value(key, default)
- L125: def get_str(key, default)
- L132: def get_int(key, default)
- L140: def get_float(key, default)
- L148: def get_bool(key, default)
- L160: def get_list(key, default)
- L175: def config_path()
- L179: def reload_config()
- L186: def _write_json_atomic(path, payload)
- L203: def save_profile_values(profile, updates)

## `bot/connection/ots_config.py`

- L11: def _env(key, default)
- L16: class OTSConfig
- L38: def is_configured(self)
- L41: def summary(self)
- L49: def _parse_region(s)
- L60: def get_config()
- L69: def _load_dotenv()

## `bot/dashboard/app.py`

- L42: def health()
- L46: def scheduler_status()
- L56: def stats()
- L71: def metrics()
- L103: def index()

## `bot/decision/brain.py`

- L19: def decide_action(state)

## `bot/decision/hunt_strategy.py`

- L21: def best_target_from_nearby(state)
- L42: def get_active_route(level, max_risk)
- L49: def get_potion_thresholds()
- L62: def next_waypoint(level)

## `bot/decision/ml_model.py`

- L76: def _load()
- L110: def save_qtable()
- L128: def _epsilon()
- L134: def _state_key(state)
- L144: def _row(table, key)
- L150: def predict_action(state)
- L172: def update_q(state, action, reward, next_state)
- L212: def compute_reward(prev_state, action, result, curr_state)

## `bot/decision/rules.py`

- L24: def _auto_follow_enabled()
- L29: class Rule
- L51: def evaluate_rules(state)

## `bot/main.py`

- L43: def _manual_action(state)
- L51: def _record_loop_telemetry(tick, elapsed_ms, stage, ok, details)
- L62: def run()
- L76: def _shutdown(sig, frame)
- L86: def _print_stats()

## `bot/overlay/macro_overlay.py`

- L32: def _now_iso()
- L36: def _default_config()
- L98: def _ensure_defaults(data)
- L110: def _load_config()
- L124: def _save_config(data)
- L130: def _normalize_macro(entry, index)
- L143: def _normalize_preset(entry, index)
- L153: def _pretty_age(remaining)
- L161: def _parse_steps(text)
- L170: def _normalize_step(step)
- L179: class MacroOverlayApp
- L180: def __init__(self, root)
- L264: def _build_editor(self, parent)
- L326: def _build_help(self, parent)
- L338: def _build_presets(self, parent)
- L357: def _field(self, parent, label, variable, row, col, width)
- L374: def _refresh_list(self)
- L384: def _selected_macro(self)
- L390: def _load_selected(self, index)
- L406: def _on_select(self, _event)
- L412: def _update_preview(self)
- L420: def _append_log(self, message)
- L427: def _refresh_timer(self)
- L436: def _collect_macro(self)
- L457: def _save_current(self)
- L472: def _run_steps(self, steps)
- L487: def _preview_steps(self, label, steps)
- L494: def _fire_preset(self, name, group, cooldown_ms, steps)
- L513: def worker()
- L528: def _fire_macro(self, macro)
- L555: def _fire_current(self)
- L558: def worker()
- L571: def _reset_current_cd(self)
- L578: def _new_macro(self)
- L584: def _duplicate_macro(self)
- L593: def _delete_macro(self)
- L604: def _reload(self)
- L613: def _tick(self)
- L619: def run()

## `bot/overlay/status_overlay.py`

- L41: class RailSwitch
- L44: def __init__(self, master)
- L69: def set_state(self, enabled)
- L73: def _on_click(self, _event)
- L78: def _draw(self)
- L122: class OverlayApp
- L123: def __init__(self, root)
- L382: def refresh(self)
- L412: def _toggle_pin(self)
- L415: def _set_alpha(self, value)
- L421: def _start_drag(self, event)
- L425: def _drag(self, event)
- L430: def _reload_config(self)
- L440: def _render_module_row(self, parent, label, key, enabled)
- L457: def _paint_module_switch(self, key, enabled)
- L463: def _module_auto_follow(self)
- L466: def _module_spell_rotation(self)
- L469: def _module_focus_guard(self)
- L472: def _sync_module_buttons(self)
- L481: def _toggle_module(self, key, desired_state)
- L494: def _save_follow_key(self)
- L504: def _save_follow_timing(self)
- L527: def _start_bot(self)
- L552: def _stop_bot(self)
- L569: def _open_macro_pad(self)
- L589: def _refresh_diagnostics(self)
- L609: def _on_close(self)
- L613: def _read_state(self)
- L623: def run()

## `bot/perception/memory_reader.py`

- L65: class _PROCESSENTRY32
- L81: class TibiaMemoryReader
- L84: def __init__(self, process_name)
- L91: def attach(self)
- L114: def detach(self)
- L124: def read_position(self)
- L133: def read_hp(self)
- L141: def read_mp(self)
- L149: def read_level(self)
- L152: def read_exp(self)
- L155: def read_all(self)
- L167: def _find_pid(self)
- L195: def _read_bytes(self, address, size)
- L210: def _read_int32(self, address)
- L216: def _read_int64(self, address)
- L227: def get_reader()

## `bot/perception/parser.py`

- L68: def _parse_region(raw)
- L78: def _scale_region(region, frame)
- L103: def _load_calibration()
- L145: def _bgr_range(mean_bgr, tolerance)
- L182: def _rescale_from_pct(pct, max_value)
- L186: def _stabilize_resource_value(current, current_max, prev, prev_max)
- L209: def _bar_percentage(frame, region, low, high)
- L239: def _has_target(frame, region)
- L247: def _target_hp_pct(frame, region)
- L254: def _template_target_match(frame)
- L273: def _ocr_reader()
- L285: def _ocr_extract_ratios(frame)
- L318: def reload_calibration()
- L336: def parse_game_state(screenshot_pixels, prev_state)

## `bot/perception/screen.py`

- L18: def _capture_window_pixels()
- L27: def capture_screen(region)
- L40: def capture_region_pixels(region)

## `bot/perception/state.py`

- L7: class Position
- L14: class GameState
- L31: def hp_pct(self)
- L35: def mp_pct(self)
- L38: def is_low_hp(self, threshold)
- L41: def is_low_mp(self, threshold)

## `bot/perception/window.py`

- L40: def _window_title_patterns()
- L45: def _active_window_title_hint()
- L58: class _BITMAPINFOHEADER
- L74: class _BITMAPINFO
- L82: class WindowHandle
- L88: def width(self)
- L92: def height(self)
- L96: def left(self)
- L100: def top(self)
- L104: def find_tibia_window()
- L115: def _enum_cb(hwnd, _lParam)
- L193: def capture_window(handle)
- L283: def bring_to_front(handle)

## `bot/safety/humanizer.py`

- L25: def human_delay(min_ms, max_ms)
- L33: def reaction_delay()
- L38: def combat_pause()
- L56: def think_pause()
- L64: def loot_delay()
- L69: def potion_delay()
- L79: def bezier_path(start, end, steps)
- L94: def misclick_jitter(x, y)
- L99: def move_mouse_human(start, end)
- L119: def random_afk_twitch()

## `bot/safety/nonsecurity_random.py`

- L18: def random()
- L22: def randint(left, right)
- L26: def uniform(left, right)
- L30: def gauss(mean, sigma)
- L34: def choice(items)
- L38: def shuffle(items)

## `bot/safety/scheduler.py`

- L33: def _env_int(key, default)
- L40: class SessionScheduler
- L43: def __init__(self, active_start, active_end, session_min_h, session_max_h, break_min_m, break_max_m)
- L68: def should_run(self)
- L100: def tick(self)
- L107: def session_elapsed_s(self)
- L113: def status(self)
- L134: def _in_active_window(self, dt)
- L144: def _plan_session(self)
- L166: def _start_break(self)
- L186: def get_scheduler()

## `bot/safety/session.py`

- L23: class SessionManager
- L24: def __init__(self)
- L33: def is_active(self)
- L47: def stop(self)
- L50: def _take_break(self)
- L59: def _is_night()

## `ctoa.ps1`

- L20: function Get-CliVpsHost
- L31: function Get-PythonExe
- L39: function Resolve-ControlCenterUrl
- L91: function Invoke-FromRoot
- L111: function Invoke-FromRootCapture
- L141: function Get-CommandDictionary
- L168: function Show-Help
- L248: function Get-GitExe
- L262: function Get-NpmExe
- L273: function Get-WorktreeSummary
- L295: function Show-Next
- L318: function Open-ControlCenter
- L373: function Resolve-Sprint
- L387: function Invoke-ValidateSprint
- L407: function Invoke-Nightly
- L424: function Invoke-Up
- L438: function Invoke-Test
- L449: function Invoke-Doctor
- L462: function Invoke-DevProfile
- L467: function Invoke-OpsProfile
- L472: function Invoke-ProdProfile
- L482: function Invoke-VpsAction
- L522: function Invoke-VpsActionCapture
- L570: function Invoke-RunnerCommand
- L582: function Invoke-ReportCommand
- L595: function Invoke-MobileCommand
- L607: function Invoke-LogsCommand
- L621: function Invoke-StatusSnapshot
- L701: function Invoke-DashboardSnapshot
- L705: function Invoke-ReportNow
- L709: function Invoke-OtProfileBuilder
- L723: function Invoke-OtHelperPreview
- L733: function Invoke-OtHelperMockup
- L743: function Invoke-OtHelperDeploy
- L764: function Invoke-OtTestLoop
- L779: function Invoke-EngineBrain
- L810: function Get-ValueOrDefault
- L822: function Show-Menu

## `ctoa_ui_prefs.lua`

- L13: lua hud

## `docs/site/script.js`

- L21: symbol createIdeaId
- L28: symbol encodeSecret
- L32: symbol nowTs
- L36: symbol isPrivateIpv4Host
- L49: symbol isLocalDevHost
- L54: symbol normalizeApiBase
- L79: symbol inferSameOriginApiBase
- L86: symbol getApiBase
- L91: symbol setApiBase
- L100: symbol syncApiBaseInputs
- L112: symbol getApiToken
- L116: symbol setApiSession
- L134: symbol getConsoleUrl
- L145: symbol apiRequest
- L178: symbol loadJson
- L191: symbol saveJson
- L195: symbol loadSessionJson
- L208: symbol saveSessionJson
- L212: symbol canUseIdeasBackend
- L216: symbol loadIdeas
- L220: symbol saveIdeas
- L226: symbol refreshIdeasFromBackend
- L236: symbol addIdea
- L267: symbol removeIdea
- L278: symbol clearIdeas
- L287: symbol formatDate
- L298: symbol updateIdeaCount
- L315: symbol downloadJsonFile
- L327: symbol renderIdeas
- L386: symbol setupIdeaForm
- L435: symbol getDefaultAdminState
- L443: symbol loadAdminState
- L448: symbol saveAdminState
- L452: symbol loadAdminStateFromBackend
- L470: symbol getAdminUsers
- L480: symbol saveAdminUsers
- L485: symbol getUserRecord
- L491: symbol isAdminLocked
- L496: symbol getLockSecondsLeft
- L501: symbol resetAuthFailures
- L506: symbol markAuthFailure
- L516: symbol isAdminLoggedIn
- L528: symbol getAdminSession
- L535: symbol isOwnerSession
- L540: symbol setAdminLoggedIn
- L552: symbol clearAdminSessionState
- L558: symbol applyAdminState
- L607: symbol setupAdminDrawerHover
- L654: symbol showAuthModal
- L672: symbol setupAdminAuth
- L975: symbol setupMenuPanels
- L1200: symbol setupDecks

## `mobile_console/app.py`

- L48: def generate_latest()
- L98: def _is_production_env()
- L106: def _is_windows_host()
- L108: def _command_exists(name)
- L112: def _read_orchestrator_loop_pid()
- L122: def _windows_orchestrator_state()
- L136: def _service_is_active(unit)
- L150: def _disk_probe()
- L171: def _lab_tasks_probe()
- L189: def _require_http_url(url)
- L196: def _require_local_runtime_api_base_url(url, label)
- L218: def _require_local_runtime_proxy_path(path, label)
- L243: def _private_intel_targets_allowed()
- L252: def _is_private_or_local_intel_host(hostname)
- L269: def _safe_proxy_error(exc)
- L273: def _intel_api_health_probe()
- L306: def _intel_api_proxy(path, timeout)
- L363: def _ctoa_api_proxy(path, timeout)
- L412: def _load_json_file(path)
- L429: def _is_production_env()
- L433: def _read_generated_manifest_json(path)
- L450: def _atomic_local_state_temp_path(path)
- L454: def _remove_local_state_temp(path)
- L461: def _atomic_write_local_json(path, payload)
- L475: def _atomic_write_text(path, text)
- L488: def _atomic_write_bytes(path, data)
- L501: def _read_local_json_bounded(path, max_bytes)
- L515: def _read_text_bounded(path, max_bytes)
- L527: def _read_tail_text_bounded(path, lines, max_bytes)
- L543: def _read_json_bounded(path, max_bytes)
- L558: def _normalize_package_tier(value)
- L565: def _is_windows_host()
- L573: def _prom_get_or_create_counter(name, documentation, labels)
- L586: def _prom_get_or_create_histogram(name, documentation, labels)
- L626: async def enforce_mobile_console_capability(request, call_next)
- L642: async def collect_http_metrics(request, call_next)
- L663: class CommandRequest
- L669: class ServerRegisterRequest
- L673: class IntelMissionRequest
- L681: class GuardedActionRequest
- L686: class QueueJobRequest
- L689: class AuthLoginRequest
- L694: class AdminSettingsPayload
- L700: class IdeaCreatePayload
- L704: class LiveDashboardProfilePayload
- L709: class RegisterAccountPayload
- L715: class SelfRegisterPayload
- L721: class ChangePasswordPayload
- L725: class ChangeRolePayload
- L747: def _default_admin_settings()
- L755: def _normalize_admin_settings(payload)
- L765: def _read_admin_settings()
- L775: def _write_admin_settings(payload)
- L782: def _normalize_idea_item(payload, fallback_author)
- L804: def _read_idea_parking()
- L823: def _write_idea_parking(ideas)
- L848: def _mobile_token()
- L853: def _full_access()
- L857: def _self_register_enabled()
- L866: def _self_register_code()
- L870: def _session_cookie_secure()
- L879: def _safe_command_specs()
- L924: def _allowed_commands()
- L928: def _normalize_user(username)
- L932: def _admin_credentials()
- L946: def _validate_security_config()
- L976: def _extract_bearer(authorization)
- L985: def _create_session(username, role)
- L999: def _get_session(token)
- L1012: def _delete_session(token)
- L1019: def _delete_sessions_for_user(username)
- L1031: def _try_auth_context(x_ctoa_token, authorization, x_ctoa_session, ctoa_session)
- L1065: def _token_valid(x_ctoa_token, authorization, x_ctoa_session, ctoa_session)
- L1079: def _csrf_required(request, ctx)
- L1087: def _verify_csrf(request, ctx, x_csrf_token)
- L1096: def require_authenticated(request, x_ctoa_token, authorization, x_ctoa_session, x_csrf_token, ctoa_session)
- L1116: def require_operator(ctx)
- L1123: def require_owner(ctx)
- L1130: def _slice_command_output(value)
- L1134: def _redact_audit_text(value, max_length)
- ... 92 more symbols omitted

## `mobile_console/services/admin_settings_service.py`

- L6: class AdminSettingsService
- L9: def __init__(self, read_settings, write_settings)
- L17: def get(self)
- L20: def save(self, payload)

## `mobile_console/services/ideas_service.py`

- L8: class IdeasService
- L11: def __init__(self, read_items, write_items, normalize_item)
- L21: def list_items(self)
- L24: def add(self, text, author)
- L41: def delete(self, idea_id)
- L50: def clear(self)

## `mobile_console/static/app.js`

- L14: symbol getToken
- L18: symbol getSessionToken
- L22: symbol setToken
- L26: symbol api
- L49: symbol refreshOwnerUi
- L65: symbol applyRoleState
- L73: symbol setRoleBadge
- L142: symbol checkAuthAuto
- L397: symbol clearElement
- L403: symbol createTextElement
- L412: symbol appendText
- L416: symbol safeStatusKey
- L421: symbol createStatusBadge
- L441: symbol createEmptyTrend
- L445: symbol renderReasonGroup
- L463: symbol renderTimeline
- L493: symbol bindTrendToggles
- L506: symbol statusClassFromSeverity
- L513: symbol appendEmptyTableRow
- L523: symbol renderTrendBars
- L554: symbol createTrendToggle
- L564: symbol appendReasonGroup
- L572: symbol renderTrendSummary
- L634: symbol renderDashboardStatusContext
- L850: symbol fetchAgentLog

## `mobile_console/static/dashboard_helpers.js`

- L2: symbol escapeHtml
- L11: symbol badgeStatus

## `prompts/braver_templates.py`

- L11: class _SafeFormatDict
- L12: def __missing__(self, key)
- L138: def get_template(template_type)
- L143: def normalize_component_name(component)
- L148: def render_template(template_type, component)
- L155: def get_all_components()

## `runner/agents/activation_agent.py`

- L43: def _slug(value)
- L47: def _targets()
- L75: def _write_json(path, payload)
- L80: def _write_text(path, text)
- L85: def _persist_manifest(server_id, manifest)
- L92: def _run_sync_hook()
- L127: def _character_plan(server_slug)
- L142: def _bot_profile(server, signal, target_dir)
- L161: def _deploy_script(server_slug)
- L173: def _bootstrap_lua(server_name, bot_profile_path)
- L189: def run_once()

## `runner/agents/brain_v2.py`

- L89: def _get_daily_counts()
- L104: def _existing_task_ids(server_id)
- L112: def _available_data_types(server_id)
- L120: def plan_for_server(server_id)
- L167: def run_once()

## `runner/agents/catalog_agent.py`

- L110: def _catalog_profile()
- L118: def _parse_window_hours(window, fallback_start, fallback_end)
- L135: def _hour_in_window(hour, start, end)
- L141: def _source_allowed_now(source_url, profile)
- L170: def _source_priority(source_url)
- L178: def _default_sources()
- L185: def _fetch_text(url)
- L213: def _is_candidate_url(url)
- L232: def _extract_candidates(source_url, body)
- L260: def _count_players_hint(text)
- L274: def _score_candidate(source_url, context)
- L320: def _upsert_server(url)
- L336: def _write_signal(server_id, source_url, score, tags, pop_hint, context, detail)
- L364: def _enrich_existing_servers()
- L444: def run_once()

## `runner/agents/db.py`

- L39: class DbConnectConfig
- L48: def _connect_config()
- L62: def _sanitize_db_error(exc)
- L72: def get_pool()
- L82: def get_conn()
- L96: def query_one(sql, params)
- L104: def query_all(sql, params)
- L111: def execute(sql, params)
- L117: def log_run(agent, status, message)

## `runner/agents/executor.py`

- L40: def now_iso()
- L44: def _safe_repo_relative_path(path_str)
- L71: def write_deliverable(path_str, title, body)
- L83: def get_llm_provider()
- L95: def invoke_llm_for_task(task_id, prompt, context)
- L123: class TrackAAgent
- L133: def execute(task_id, deliverables)
- L173: def create_runbook_disk_emergency()
- L285: def create_validation_checklist()
- L418: def create_consistency_report()
- L451: class TrackBAgent
- L461: def execute(task_id, deliverables)
- L487: def enhance_weekly_report()
- L493: class TrackCAgent
- L503: def execute(task_id, deliverables)
- L537: def create_drift_checker()
- L642: class TrackDAgent
- L652: def execute(task_id, deliverables)
- L678: def create_sprint_governance()
- L861: def execute_agent_for_task(task)

## `runner/agents/generator_agent.py`

- L36: def _now_iso()
- L40: def _safe_output_path(base_dir, output_file)
- L70: def _safe_output_dir(base_dir, relative_dir)
- L76: def _write_run_manifest(run_started_at, generated, failed)
- L117: def _server_ctx(server_id)
- L152: def _safe_lua_string(s)
- L157: def _render(template_id, ctx)
- L168: def _tpl_auto_heal(ctx)
- L192: def _tpl_auto_reconnect(ctx)
- L215: def _tpl_loot_filter(ctx)
- L251: def _tpl_cavebot_pathing(ctx)
- L280: def _tpl_target_selector(ctx)
- L305: def _tpl_anti_stuck(ctx)
- L333: def _tpl_alarmy(ctx)
- L370: def _tpl_healer_profiles(ctx)
- L404: def _tpl_flee_logic(ctx)
- L435: def _tpl_target_blacklist(ctx)
- L460: def _tpl_auto_resupply(ctx)
- L489: def _tpl_server_blacklist(ctx)
- L516: def _tpl_server_loot_map(ctx)
- L543: def _tpl_highscore_scout(ctx)
- L568: def _tpl_server_stats(ctx)
- L590: def _tpl_player_tracker(ctx)
- L620: def _tpl_hunt_orchestrator(ctx)
- L710: def _tpl_economy_bot(ctx)
- L749: def _tpl_pvp_guard(ctx)
- L778: def _tpl_depot_manager(ctx)
- L804: def _tpl_gold_tracker(ctx)
- L827: def _tpl_bank_automation(ctx)
- L854: def _tpl_human_delay(ctx)
- L878: def _tpl_break_scheduler(ctx)
- L913: def _tpl_login_randomizer(ctx)
- L940: def _tpl_rune_maker(ctx)
- L963: def _tpl_combo_spells(ctx)
- L990: def _tpl_area_spell_ctrl(ctx)
- L1026: def _tpl_exp_tracker(ctx)
- L1050: def _tpl_session_log(ctx)
- L1075: def _tpl_respawn_optimizer(ctx)
- L1146: def _slug(url)
- L1153: def generate_module(mod)
- L1220: def run_once()

## `runner/agents/ingest_agent.py`

- L36: def _fetch_json(url)
- L64: def _normalise_monsters(data)
- L81: def _normalise_items(data)
- L98: def _normalise_players(data)
- L114: def _normalise_highscores(data)
- L131: def _normalise_server_info(data)
- L157: def _detect_type(path)
- L165: def ingest_server(server_id, base_url)
- L219: def run_once()

## `runner/agents/orchestrator.py`

- L42: def run_pipeline()

## `runner/agents/publisher_agent.py`

- L44: def _criteria_met(today_str)
- L73: def _collect_validated()
- L80: def _create_zip(today_str, mods)
- L92: def _write_manifest(today_str, mods, zip_path)
- L113: def _git_commit_release(manifest_path, tag)
- L135: def _gh_release(tag, zip_path, manifest_path)
- L159: def run_once()

## `runner/agents/routing.py`

- L6: def select_track(domain)

## `runner/agents/scout_agent.py`

- L157: def _fetch(url)
- L198: def _safe_slug(url)
- L202: def _dedupe_paths(paths)
- L213: def _infer_profile(base_url)
- L221: def _force_generic_hosts()
- L226: def _probe_paths(server_id, base_url, paths, source, probed, deadline)
- L273: def scout_server(server_id, base_url)
- L379: def run_once()

## `runner/agents/validator_agent.py`

- L44: def _luac_check(path)
- L64: def _bracket_balance(src)
- L76: def _py_compile_check(path)
- L90: def validate_lua(path, src)
- L131: def validate_python(path, src)
- L157: def validate_module(mod)
- L210: def run_once()

## `runner/alert_rules.py`

- L104: def check_generation_failed_spike(reason_counts, max_fails)

## `runner/close_on_gate.py`

- L14: def github_api(method, url, token, payload)
- L36: def parse_waiting_task_ids(issue_body)
- L58: def main()

## `runner/daily_insights.py`

- L22: def parse_iso(ts)
- L31: def load_yaml(path)
- L41: def github_api(method, url, token, payload)
- L63: def build_daily_comment(backlog, state)
- L148: def comment_daily_insight(comment_body)
- L178: def main()

## `runner/drift_checker.py`

- L28: def now_iso()
- L32: def check_service_status(service)
- L65: def main()

## `runner/generated_manifest_safety.py`

- L9: def _is_relative_to(path, root)
- L17: def resolve_latest_manifest_path(manifests_dir, latest_payload)
- L50: def iter_safe_manifest_files(manifests_dir)
- L95: def public_manifest_path(manifest_path, manifests_dir)

## `runner/generator_validator_samples.py`

- L28: def now_iso()
- L32: def load_latest_manifest(manifests_dir)
- L58: def build_generator_sample(latest_manifest)
- L98: def build_validator_sample(latest_manifest)
- L136: def write_json(path, payload)
- L141: def write_markdown(path, generator_payload, validator_payload)
- L161: def main()

## `runner/health_metrics.py`

- L33: def now_iso()
- L37: def _atomic_temp_path(path)
- L41: def _remove_temp_path(path)
- L48: def _atomic_write_json(path, payload)
- L62: def _read_proc_stat_totals()
- L74: def read_cpu_percent(sample_seconds)
- L117: def read_memory_percent()
- L164: def read_disk_percent(path)
- L171: def read_uptime_human()
- L192: def read_load_average()
- L199: def check_processes(processes_to_check)
- L229: def _run_tool(name, args)
- L251: def collect_metrics()
- L320: def check_thresholds(metrics)
- L340: def format_health_dashboard(metrics, alerts)
- L394: def publish_to_github(dashboard_md)
- L424: def persist_snapshot(metrics, alerts)
- L432: def print_live_line(metrics, alerts)
- L444: def maybe_run_disk_cleanup(metrics, now_ts, enabled, threshold, cooldown_seconds, command, last_run_ts)
- L499: def run_once(publish)
- L512: def run_watch(interval, samples, publish, cpu_sustain, disk_auto_cleanup, disk_cleanup_threshold, disk_cleanup_cooldown, disk_cleanup_cmd)
- L569: def build_parser()
- L620: def main()

## `runner/health_trend.py`

- L15: def parse_iso(ts)
- L22: def read_rows(path)
- L39: def avg(values)
- L45: def summarize_window(rows, since)
- L100: def print_window(label, summary)
- L115: def main()

## `runner/http_safety.py`

- L46: def env_enabled(name)
- L50: def require_http_url(url)
- L58: def require_github_repository(repo)
- L75: def require_github_api_url(url)
- L107: def require_loopback_http_url(url)
- L125: def _reject_token_query(parsed, label)
- L131: def _is_ip_literal(host)
- L139: def _reject_private_discovery_host(host, label)
- L163: def require_public_discovery_url(url)
- L179: def _reject_url_secret_parts(parsed, label)
- L191: def require_model_backend_url(url)
- L205: def require_azure_service_url(url)
- L217: def _require_strict_path_parts(parsed, label)
- L232: def require_notify_webhook_url(url)
- L250: def require_discord_webhook_url(url)
- L264: def discovery_ssl_context(insecure_env_name)

## `runner/hybrid_bot/bot_runner.py`

- L36: class BotConfig
- L49: class ActionExecutor
- L52: def __init__(self, send_command)
- L61: def execute(self, action, parameters)
- L105: class HybridBotRunner
- L123: def __init__(self, config, screenshot_provider, command_executor)
- L144: def command_callback(cmd)
- L172: async def run(self)
- L189: async def _tick(self)
- L266: def _capture_frame(self)
- L276: def _collect_perception(self, frame)
- L287: def _apply_state_updates(self, position, health, creatures)
- L312: def _decide_and_execute(self)
- L319: def _emit_tick_telemetry(self, decision)
- L327: def stop(self)
- L335: def set_waypoints(self, waypoints)
- L341: def start_hunting_location(self, name)
- L348: def _print_final_report(self)
- L363: def get_status(self)

## `runner/hybrid_bot/cli.py`

- L37: async def cmd_run(args)
- L74: def cmd_benchmark(args)
- L115: def cmd_export(args)
- L129: def main()

## `runner/hybrid_bot/clock.py`

- L8: def utc_now()

## `runner/hybrid_bot/command_executor.py`

- L27: class _FallbackKey
- L36: class _FallbackButton
- L48: class CommandExecutor
- L74: def __init__(self, base_delay_ms, typing_delay_ms, enable_delays)
- L101: def execute(self, command)
- L181: async def execute_async(self, command)
- L187: def _type_spell(self, spell_name)
- L197: def _press_key(self, key)
- L219: def _press_named_key(self, key_name)
- L226: def _press_combo(self, combo)
- L249: def _resolve_key(self, key_name)
- L278: def _attack_target(self)
- L300: def _wait(self)
- L305: def _reconnect(self)
- L324: def _apply_delay(self)
- L333: def set_delaying(self, enable)
- L338: def get_stats(self)
- L349: class BatchCommandExecutor
- L361: def __init__(self, executor)
- L366: def add(self, command, duration_ms)
- L376: async def execute(self)
- L395: def clear(self)

## `runner/hybrid_bot/file_safety.py`

- L10: def resolve_output_dir(output_dir)
- L19: def safe_child_path(base_dir, relative_path)

## `runner/hybrid_bot/gameplay_engine.py`

- L27: class GameplayMode
- L35: class CombatStats
- L45: def dps(self)
- L50: def increment_kill(self, xp_gain, loot_value)
- L57: class CombatEngine
- L60: def __init__(self, player_level)
- L72: def _build_priority_queue(self)
- L82: def choose_target(self, visible_creatures)
- L129: def should_flee(self, health_percent, critical_threshold)
- L134: class MovementEngine
- L137: def __init__(self, max_distance_before_recall)
- L150: def set_home(self, x, y, z)
- L155: def set_hunting_path(self, waypoints)
- L161: def get_next_waypoint(self, current_x, current_y)
- L179: def should_recall_home(self, current_x, current_y)
- L191: class LootEngine
- L194: def __init__(self, max_backpack_items, skip_items)
- L210: def should_pickup_loot(self, item_name)
- L223: def should_drop_loot(self, backpack_items)
- L228: class HealingEngine
- L231: def __init__(self)
- L241: def should_cast_heal(self, health_percent, heal_threshold)
- L252: def should_cast_buff(self, buff_name)
- L259: def record_heal(self)
- L263: def record_buff(self, buff_name)
- L268: class GameplayEngine
- L275: def __init__(self, mode, player_level)
- L296: def make_decision(self, player_state, visible_creatures, time_delta)
- L344: def set_mode(self, mode)
- L349: def get_stats(self)

## `runner/hybrid_bot/interactive_mode.py`

- L31: class InteractiveCommand
- L52: class InteractiveState
- L59: def update_activity(self)
- L64: class KeyboardListener
- L71: def __init__(self)
- L76: async def start(self, command_queue)
- L88: def on_key_press(key)
- L106: def _map_key_to_command(self, key)
- L142: def stop(self)
- L151: class InteractiveMode
- L158: def __init__(self, command_executor, screenshot_callback)
- L184: async def run(self)
- L212: async def _handle_command(self, command)
- L279: async def _periodic_update(self)
- L284: def _print_status(self)
- L301: def _print_session_stats(self)

## `runner/hybrid_bot/metrics.py`

- L29: class MetricsSnapshot
- L58: class SessionMetrics
- L77: def __post_init__(self)
- L82: class MetricsCollector
- L92: def __init__(self, output_dir, snapshot_interval_seconds, disable_file_output)
- L136: def record_snapshot(self, location, duration_seconds, xp_gained, monsters_killed, loot_value_gold, supplies_cost_gold, player_health_percent, player_level, distance_traveled_sqm, notes)
- L195: def _append_snapshot_to_file(self, snapshot)
- L204: def _append_event_to_file(self, event)
- L214: def load_snapshots_from_file(self, filepath)
- L234: def record_event(self, name, duration_ms, ok, error, details)
- L256: def get_session_summary(self)
- L293: def get_location_stats(self, location)
- L314: def print_session_report(self)
- L350: def export_metrics_csv(self, output_file)
- L377: def compare_with_manual_metrics(bot_metrics, manual_xp_per_hour, manual_balance_per_hour)

## `runner/hybrid_bot/pathfinding.py`

- L24: class SQMType
- L38: class Coordinate
- L44: def distance_to(self, other)
- L50: class PathNode
- L58: def __post_init__(self)
- L61: def __lt__(self, other)
- L64: def __hash__(self)
- L67: def __eq__(self, other)
- L74: class PathSegment
- L83: class Pathfinder
- L95: def __init__(self, player_level, sqm_cost_map, base_movement_ms)
- L120: def find_path(self, start, goal, sqm_terrain, max_iterations)
- L207: def _get_neighbors(self, pos)
- L225: def _is_valid_position(self, pos)
- L230: def _calculate_move_cost(self, sqm_type)
- L236: def _reconstruct_path(self, node, sqm_terrain)
- L263: def estimate_travel_time_ms(self, segments)
- L268: class WaypointBuffer
- L276: def __init__(self, waypoints)
- L281: def get_current_waypoint(self)
- L287: def advance(self)
- L294: def reset(self)
- L298: def distance_to_current(self, pos)
- L308: def generate_terrain_map(map_data)

## `runner/hybrid_bot/performance_profiler.py`

- L28: class TimingSnapshot
- L39: def to_dict(self)
- L52: class PerformanceStats
- L82: def update(self, snapshot)
- L116: def print_report(self)
- L144: class PerformanceProfiler
- L162: def __init__(self, output_dir)
- L176: class TimingContext
- L179: def __init__(self, profiler, timer_name)
- L184: def __enter__(self)
- L188: def __exit__(self, exc_type, exc_val, exc_tb)
- L206: def measure(self, timer_name)
- L218: def record_snapshot(self)
- L225: def get_stats(self)
- L229: def export_to_json(self, filename)
- L245: def print_report(self)

## `runner/hybrid_bot/prompt_logic.py`

- L25: class Action
- L40: class GameState
- L58: class Decision
- L67: class PromptLogic
- L79: def __init__(self, use_llm, model_name)
- L102: def decide_action_heuristic(self, state)
- L169: def decide_action_with_llm(self, state)
- L208: def make_decision(self, state)
- L228: def _build_state_prompt(self, state)
- L253: def _get_system_prompt(self)
- L275: def _parse_llm_response(self, response)
- L300: def prompt_training_mode(level, current_xp_percent)
- L309: def prompt_hunting_profit(balance_per_hour)
- L318: def prompt_resource_management(supplies_cost, loot_value)

## `runner/hybrid_bot/screenshot_provider.py`

- L36: class ScreenshotProvider
- L46: def __init__(self, window_title, monitor_index, use_mss, game_window_bounds)
- L73: def _initialize_capture_method(self)
- L92: def capture(self)
- L111: def _capture_mss(self)
- L142: def _capture_pil(self)
- L163: def get_bounds(self)
- L179: def set_bounds(self, bounds)
- L184: def close(self)
- L193: def find_tibia_window()

## `runner/hybrid_bot/state_manager.py`

- L26: class PlayerState
- L41: def position(self)
- L45: def is_alive(self)
- L49: def is_critical(self)
- L54: class TargetState
- L64: def position(self)
- L68: def is_valid(self)
- L73: class LocationMetrics
- L83: def elapsed_minutes(self)
- L87: def xp_per_hour(self)
- L92: def balance_per_hour(self)
- L98: def supplies_per_hour(self)
- L103: class StateManager
- L114: def __init__(self, initial_level)
- L129: def update_player_state(self, x, y, z, hp_percent, mp_percent, is_poisoned, is_paralyzed)
- L148: def update_target(self, name, x, y, distance, is_engaged, health_percent)
- L165: def clear_target(self)
- L169: def update_inventory(self, items)
- L175: def start_location(self, name)
- L187: def record_monster_kill(self, xp_gain, loot_value)
- L194: def record_supply_cost(self, cost)
- L200: def should_heal(self)
- L204: def is_critical_health(self)
- L208: def should_rotate_location(self)
- L218: def is_inventory_full(self, capacity_percent_threshold)
- L228: def snapshot(self)
- L252: def print_summary(self)
- L276: def get_location_history(self)

## `runner/hybrid_bot/template_library.py`

- L38: def _safe_template_component(value, label)
- L52: def _require_template_source_url(url)
- L68: class Template
- L80: class TemplateLibrary
- L93: def __init__(self, cache_dir, server_url, use_cache)
- L123: def load_creatures(self, creature_names)
- L146: def _load_creature(self, name)
- L183: def load_minimap_sections(self, world_bounds, section_size)
- L230: def _cache_file(self, tpl_type, name)
- L241: def _load_from_disk(self, path, tpl_type, name)
- L277: def _load_from_server(self, url, tpl_type, name)
- L321: def save_template(self, template)
- L334: def get_creature(self, name)
- L338: def get_minimap_section(self, x, y, z)
- L343: def get_all_creatures(self)
- L349: def get_stats(self)
- L366: def print_stats(self)
- L401: def create_default_library(cache_dir)

## `runner/hybrid_bot/vision_layer.py`

- L29: def _vision_deps_available()
- L34: class GPSPosition
- L43: class HealthState
- L51: class Creature
- L65: class VisionLayer
- L75: def __init__(self, templates_dir)
- L92: def _load_templates(self)
- L112: def detect_position_from_minimap(self, minimap_screenshot)
- L169: def detect_health_from_healthbar(self, healthbar_region)
- L226: def detect_creatures_from_sprites(self, game_screen, creature_db)
- L285: def detect_engagement_from_target_window(self, target_window)
- L318: def extract_healthbar_region(game_screen, ui_layout)
- L345: def extract_minimap_region(game_screen, ui_layout)
- L366: def extract_target_window(game_screen, ui_layout)

## `runner/issue_sync.py`

- L20: def github_api(method, url, token, payload)
- L42: def load_backlog()
- L50: def make_issue_title(task)
- L54: def make_issue_body(backlog_id, task)
- L84: def list_open_issues(base, token)
- L101: def group_backlog_issues_by_task_id(open_issues)
- L116: def split_primary_and_duplicates(issues_by_task_id)
- L133: def main()

## `runner/llm_providers/__init__.py`

- L11: class LLMProvider
- L15: def complete(self, system_prompt, user_prompt, temperature, max_tokens)
- L26: def health(self)
- L31: def get_provider()

## `runner/llm_providers/azure_foundry.py`

- L19: class AzureFoundryProvider
- L22: def __init__(self)
- L39: def health(self)
- L43: def complete(self, system_prompt, user_prompt, temperature, max_tokens)

## `runner/llm_providers/local_model.py`

- L15: class LocalModelProvider
- L18: def __init__(self)
- L30: def health(self)
- L40: def complete(self, system_prompt, user_prompt, temperature, max_tokens)

## `runner/mythibia_local_brain.py`

- L98: def now_iso()
- L102: def ensure_queue()
- L129: def render(template_name)
- L148: def generate()

## `runner/pipeline/scheduler.py`

- L6: def count_active_tasks(tasks, active_states)
- L10: def build_new_task_candidates(tasks, priority_rank)

## `runner/process_safety.py`

- L18: class ExecutableUnavailableError
- L27: def _resolve_candidate(value)
- L42: def resolve_executable(name)
- L75: def resolve_git()
- L81: def resolve_python()
- L90: def run_trusted(command)
- L97: def start_trusted(command)

## `runner/queue_worker.py`

- L29: def _redis_url_for_log(raw_url)
- L55: def _parse_job_payload(payload_raw)
- L65: def _setup_logging()
- L77: def _run_action(action)
- L100: def main()

## `runner/response_guardrails.py`

- L29: def validate_response(text)
- L51: def is_response_compliant(text)
- L55: def validate_operational_structure(text)
- L68: def is_operational_structure_compliant(text)

## `runner/runner.py`

- L33: def _default_ci_artifacts_dir(root)
- L71: def now_iso()
- L75: def _atomic_temp_path(path)
- L79: def _remove_temp_path(path)
- L86: def load_yaml(path)
- L94: def save_yaml(path, payload)
- L107: def save_json(path, payload)
- L123: def load_backlog()
- L129: def init_state(backlog)
- L161: def load_state(backlog)
- L201: def status_rank(status)
- L208: def priority_rank(priority)
- L213: def transition_task(task, new_status, reason)
- L233: def tick(backlog, state, invoke_agents)
- L279: def approve_task(state, task_id)
- L294: def execute_task_agent(task, backlog)
- L322: def estimate_next_approval_eta_hours(tasks)
- L341: def build_execution_summary(backlog, state)
- L391: def build_report(backlog, state)
- L501: def github_api(method, url, token, payload)
- L523: def upsert_live_issue(markdown)
- L561: def main()

## `runner/status_sync.py`

- L32: def parse_iso(ts)
- L41: def load_state()
- L51: def github_api(method, url, token, payload)
- L73: def ensure_status_labels(base, token)
- L92: def task_map(state)
- L104: def backlog_issue_map(open_issues)
- L115: def list_open_issues(base, token)
- L132: def desired_status_label(task)
- L137: def normalize_alert_mode(value)
- L144: def sync_status_labels(base, token, tasks, issues)
- L175: def build_sla_alert(tasks, issues, threshold_hours, alert_mode)
- L241: def update_live_issue_sla_section(base, token, live_issue_number, body)
- L276: def main()

## `runner/tibia_sources.py`

- L65: def utc_now()
- L70: class CollectedSource
- L81: class RawSnapshot
- L95: class NormalizedRecord
- L102: class UpdateEvent
- L112: class SourceCollector
- L113: def fetch(self, source_kind, cursor)
- L117: class SourceParser
- L118: def parse(self, snapshot)
- L122: class ClientAdapter
- L123: def detect(self)
- L127: class HttpTibiaCollector
- L130: def __init__(self)
- L133: def fetch(self, source_kind, cursor)
- L138: def _fetch(self, source_kind, url)
- L213: class _AnchorParser
- L214: def __init__(self)
- L220: def handle_starttag(self, tag, attrs)
- L229: def handle_data(self, data)
- L233: def handle_endtag(self, tag)
- L243: class LinkRecordParser
- L246: def __init__(self, archive_root)
- L249: def parse(self, snapshot)
- L275: class SnapshotArchive
- L276: def __init__(self, root)
- L285: def ingest(self, collected, parser)
- L357: def _record_diff_events(self, previous, current, records)
- L413: def _records_for(self, snapshot)
- L442: def latest(self, source_kind)
- L450: def _diff_events(self, previous, current)
- L492: def _append_events(self, events)
- L502: def _write_inventory(self)
- L587: def _latest_parser_error(self, source_kind)
- L595: def _recent_events(self, limit)
- L611: def source_definition(source_kind)
- L618: def collected_from_file(source_kind, path)
- L634: def _validate_source_url(url)
- L642: def _blocked_reason(status_code, content)
- L650: def _timestamp_slug(value)
- L655: def _safe_archive_path(root, relative)
- L664: def _temporary_path(path)
- L668: def _atomic_write_bytes(path, content)
- L681: def _atomic_write_json(path, payload)
- L686: def _next_action(status)

## `runner/weekly_report.py`

- L27: def github_api(method, url, token, payload)
- L49: def iso_week_key(now)
- L54: def parse_date(ts)
- L58: def _read_latency_kpi()
- L122: def build_weekly_comment(repo, token)
- L207: def main()

## `runtime_context.py`

- L13: def is_truthy_env(value)
- L17: def is_falsey_env(value)
- L21: def is_windows_host()
- L25: def is_production_env()
- L30: def normalize_package_tier(value)
- L37: def load_json_file(path)
- L45: def current_package_tier(product_manifest_file, product_user_config_file, default)
- L63: def mobile_console_enabled(product_manifest_file, product_user_config_file)
- L86: def default_generated_dir(root)
- L90: def default_ci_artifacts_dir(root)

## `scoring/tool_advisor.py`

- L78: def score_tool(tool_id, agent_weights, context)
- L123: def rank_tools_for_task(task_type, agent_weights, context)
- L136: def get_tool_config(tool_id)
- L140: def list_available_tools()

## `scripts/calibrate_colors.py`

- L24: def _require_cv2()
- L33: def _require_numpy()
- L42: def _load_config()
- L51: def _save_config(data)
- L56: def cmd_screenshot(args)
- L76: def cmd_sample(args)
- L124: def cmd_verify(args)
- L148: def main()

## `scripts/calibrate_memory.py`

- L52: class _PROCESSENTRY32
- L67: class _MEMORY_BASIC_INFORMATION
- L79: def find_pid(name)
- L98: def open_process(pid)
- L103: def read_int32(handle, addr)
- L113: def scan_value(handle, target, prev_candidates)
- L160: def verify_offsets(handle)
- L167: def export_offsets(updates)
- L187: def main()

## `scripts/enc3_analyze.py`

- L9: def show_context(offset, before, after, label)
- L24: def null_strings(region_bytes)

## `scripts/enc3_disasm.py`

- L27: def file_to_rva(foff)
- L34: def rva_to_file(rva)

## `scripts/enc3_format.py`

- L23: def hex4(off)
- L24: def u32(off)

## `scripts/enc3_recover_func.py`

- L27: def rva_to_file(rva)
- L35: def file_to_rva(foff)
- L42: def va_to_file(va)
- L46: def in_text(va)

## `scripts/example_strategos_local_ai.py`

- L20: class StrategosLocalAI
- L23: def __init__(self)
- L27: def assess_sprint_blocker(self, blocker_desc, affected_agents)
- L52: def generate_daily_assignments(self, tasks)
- L81: def evaluate_qa_report(self, qa_results)
- L101: class Agent7LocalAIIntegration
- L104: def __init__(self)
- L108: def generate_performance_profile(self)
- L130: def refactor_legacy_module(self, module_description)
- L150: def example_strategos_flow()
- L188: def example_agent7_flow()

## `scripts/lua/auto_heal.lua`

- L12: lua readPercent
- L25: lua pickHealReason
- L45: lua AutoHeal.shouldCast
- L55: lua AutoHeal.nextAction

## `scripts/lua/ctoa_hotkey_status.lua`

- L7: lua appendLog
- L17: lua readWsadWalking
- L34: lua emitStatus
- L41: lua onThink

## `scripts/lua/ctoa_path_probe.lua`

- L15: lua tryAppend
- L23: lua writeProbe
- L38: lua onThink

## `scripts/lua/emergency_heal.lua`

- L8: lua onThink

## `scripts/lua/event_logger.lua`

- L7: lua safeNumber
- L15: lua getStateValue
- L26: lua normalizePosition
- L38: lua encodeJson
- L66: lua EventLogger.build
- L83: lua EventLogger.log
- L87: lua EventLogger.toJsonLine

## `scripts/lua/loot_filter.lua`

- L3: lua hasValue
- L7: lua countValue
- L18: lua LootFilter.filter
- L35: lua LootFilter.shouldStack
- L39: lua LootFilter.shouldLoot
- L52: lua LootFilter.classify

## `scripts/lua/module_reporter.lua`

- L8: lua appendLog
- L18: lua logLine
- L22: lua onThink

## `scripts/lua/otclient/ctoa_ed_profile.lua`

- L5: lua modules
- L6: lua healing
- L9: lua spell_rotation
- L14: lua heal_friend
- L15: lua conditions
- L16: lua equipment
- L17: lua scripting
- L18: lua tools
- L23: lua rotation_spells
- L30: lua feature_flags
- L32: lua hud

## `scripts/lua/otclient/ctoa_ek_profile.lua`

- L14: lua modules
- L28: lua healing
- L36: lua spell_rotation
- L62: lua heal_friend
- L69: lua friend_whitelist
- L82: lua conditions
- L99: lua equipment
- L115: lua scripting
- L127: lua tools
- L144: lua friendly_summon_name_fragments
- L151: lua ignored_names
- L165: lua priority_names
- L182: lua rotation_spells
- L221: lua exeta_spells
- L255: lua cavebot_waypoints
- L256: lua feature_flags
- L265: lua hud

## `scripts/lua/otclient/ctoa_helper_action_catalog.lua`

- L136: lua copyList
- L144: lua copyAction
- L158: lua ActionCatalog.requiredGates
- L162: lua ActionCatalog.all
- L170: lua ActionCatalog.domains
- L182: lua ActionCatalog.byAction
- L201: lua ActionCatalog.classify
- L210: lua ActionCatalog.summary
- L217: lua ActionCatalog.contract

## `scripts/lua/otclient/ctoa_helper_cavebot_observer.lua`

- L7: lua numberValue
- L13: lua Observer.normalizeObservation
- L21: lua position
- L33: lua Observer.observe
- L41: lua Observer.attach
- L45: lua dependencies
- L47: lua metadata
- L56: lua Observer.contract

## `scripts/lua/otclient/ctoa_helper_cavebot_runtime.lua`

- L6: lua boolValue
- L10: lua numberValue
- L18: lua runtimeBlockedReason
- L40: lua CavebotRuntime.plan
- L66: lua CavebotRuntime.summary
- L76: lua CavebotRuntime.decisionText
- L91: lua CavebotRuntime.adapterSummary
- L110: lua CavebotRuntime.adapterStatusText
- L118: lua CavebotRuntime.adapterStatusSummary
- L123: lua CavebotRuntime.movementCapability
- L146: lua CavebotRuntime.probeSnapshot
- L162: lua CavebotRuntime.probeSummary
- L176: lua CavebotRuntime.probeReport
- L184: lua CavebotRuntime.pathText
- L198: lua CavebotRuntime.movementBlockedReason
- L215: lua CavebotRuntime.walkPreflight
- L238: lua CavebotRuntime.testWalkPlan
- L261: lua CavebotRuntime.walkingStatus
- L270: lua data
- L278: lua CavebotRuntime.retryDecision
- L285: lua trace_data
- L297: lua trace_data
- L305: lua status_data
- L311: lua CavebotRuntime.statusText
- L384: lua CavebotRuntime.traceText
- L423: lua CavebotRuntime.contract

## `scripts/lua/otclient/ctoa_helper_client_reporter.lua`

- L10: lua safeCall
- L23: lua firstValue
- L33: lua normalizedId
- L45: lua sortedLoadedModules
- L57: lua runtimeCoreSnapshot
- L79: lua tasks
- L83: lua jsonEscape
- L95: lua isArray
- L111: lua encodeJson
- L145: lua Reporter.detect
- L176: lua Reporter.snapshot
- L188: lua Reporter.resolvePath
- L206: lua Reporter.writeSnapshot
- L237: lua Reporter.intervalMs
- L241: lua Reporter.contract

## `scripts/lua/otclient/ctoa_helper_combat_observer.lua`

- L10: lua numberValue
- L24: lua textValue
- L32: lua normalizeTarget
- L45: lua normalizeSpectators
- L55: lua CombatObserver.normalizeObservation
- L82: lua CombatObserver.observe
- L92: lua CombatObserver.attach
- L104: lua dependencies
- L108: lua metadata
- L130: lua CombatObserver.contract

## `scripts/lua/otclient/ctoa_helper_combat_runtime.lua`

- L6: lua boolValue
- L10: lua runtimeBlockedReason
- L28: lua CombatRuntime.plan
- L63: lua CombatRuntime.summary
- L72: lua CombatRuntime.adapterSummary
- L81: lua CombatRuntime.magicSummary
- L98: lua CombatRuntime.msLeftText
- L106: lua CombatRuntime.runeReady
- L125: lua monsterCountForRange
- L137: lua directionalSpell
- L142: lua CombatRuntime.bestDirectionalFacing
- L158: lua CombatRuntime.recordDirectionalHit
- L168: lua CombatRuntime.rotationSpellRows
- L194: lua CombatRuntime.spellReadiness
- L215: lua CombatRuntime.rotationSpell
- L244: lua CombatRuntime.stanceAction
- L262: lua CombatRuntime.offensiveAction
- L308: lua CombatRuntime.actionStatusText
- L341: lua CombatRuntime.targetingStatusText
- L362: lua CombatRuntime.nextActionText
- L380: lua CombatRuntime.waitReason
- L425: lua CombatRuntime.decisionState
- L445: lua CombatRuntime.decisionStateSummary
- L464: lua CombatRuntime.contract

## `scripts/lua/otclient/ctoa_helper_conditions.lua`

- L6: lua boolText
- L10: lua hasBitFlag
- L23: lua collectNumericFlags
- L33: lua Conditions.flagText
- L53: lua Conditions.snapshot
- L94: lua Conditions.apiProbe
- L119: lua Conditions.observe
- L133: lua Conditions.plan
- L172: lua Conditions.summary
- L188: lua Conditions.contract

## `scripts/lua/otclient/ctoa_helper_decision_pipeline.lua`

- L24: lua componentReady
- L28: lua copyTable
- L36: lua componentsSnapshot
- L45: lua missingComponents
- L56: lua adapterHandoff
- L73: lua DecisionPipeline.components
- L77: lua DecisionPipeline.evaluate
- L124: lua DecisionPipeline.summary
- L136: lua DecisionPipeline.blockers
- L140: lua append
- L156: lua DecisionPipeline.contract

## `scripts/lua/otclient/ctoa_helper_decision_trace.lua`

- L6: lua copyList
- L14: lua missingGates
- L25: lua DecisionTrace.record
- L47: lua DecisionTrace.queue
- L75: lua DecisionTrace.summary
- L87: lua DecisionTrace.contract

## `scripts/lua/otclient/ctoa_helper_diagnostics.lua`

- L6: lua Diagnostics.boolText
- L10: lua Diagnostics.trimText
- L15: lua Diagnostics.posText
- L22: lua Diagnostics.hasApi
- L26: lua Diagnostics.apiText
- L30: lua Diagnostics.valueText
- L43: lua unavailableRuntimeCoreSnapshot
- L59: lua Diagnostics.runtimeCoreSnapshot
- L73: lua Diagnostics.runtimeCoreText
- L81: lua Diagnostics.apiSnapshotText
- L91: lua Diagnostics.apiProbeSnapshot
- L156: lua Diagnostics.apiProbeText
- L170: lua Diagnostics.probeDeferredPlan
- L191: lua Diagnostics.magicApiProbeText
- L212: lua Diagnostics.featureFlagsText
- L220: lua Diagnostics.appendLog
- L238: lua Diagnostics.exportPath
- L248: lua Diagnostics.bufferText
- L253: lua Diagnostics.movementText
- L258: lua Diagnostics.magicLootText
- L264: lua Diagnostics.snapshotUiRows
- L275: lua Diagnostics.tableCount
- L286: lua Diagnostics.firstTableValue
- L296: lua Diagnostics.smokeCommandValue
- L312: lua Diagnostics.smokeCommandExists
- L334: lua Diagnostics.parseSmokeCommandText
- L358: lua Diagnostics.smokeCommandTarget
- L390: lua Diagnostics.smokeTabLabel
- L401: lua Diagnostics.smokeTabStatusText
- L405: lua Diagnostics.smokeCommandStatusText
- L417: lua Diagnostics.smokeCommandBlockedText
- L421: lua Diagnostics.smokeCommandFailedText
- L425: lua Diagnostics.recordSnapshot
- L451: lua Diagnostics.exportBuffer
- L480: lua Diagnostics.contract

## `scripts/lua/otclient/ctoa_helper_dispatch_guard.lua`

- L25: lua append
- L29: lua isRuntimeAction
- L34: lua policyStatus
- L41: lua hasPolicyReady
- L45: lua planModule
- L52: lua DispatchGuard.classify
- L65: lua DispatchGuard.decision
- L104: lua DispatchGuard.summary
- L113: lua DispatchGuard.contract

## `scripts/lua/otclient/ctoa_helper_domain_contract.lua`

- L20: lua copyTable
- L28: lua descriptorCopy
- L38: lua DomainContract.schemaVersion
- L42: lua DomainContract.lanes
- L50: lua DomainContract.lane
- L60: lua DomainContract.observationEnvelope
- L73: lua DomainContract.planEnvelope
- L89: lua DomainContract.summaryEnvelope
- L102: lua DomainContract.validateEnvelope
- L120: lua DomainContract.contract

## `scripts/lua/otclient/ctoa_helper_equipment.lua`

- L6: lua boolText
- L10: lua Equipment.slotText
- L45: lua Equipment.snapshot
- L57: lua Equipment.apiProbe
- L77: lua Equipment.observe
- L91: lua Equipment.plan
- L137: lua Equipment.summary
- L154: lua Equipment.contract

## `scripts/lua/otclient/ctoa_helper_equipment_observer.lua`

- L7: lua numberValue
- L13: lua slot
- L18: lua Observer.normalizeObservation
- L26: lua slots
- L33: lua Observer.observe
- L41: lua Observer.attach
- L45: lua dependencies
- L47: lua metadata
- L56: lua Observer.contract

## `scripts/lua/otclient/ctoa_helper_feature_flags.lua`

- L107: lua copyFlag
- L121: lua valueAtPath
- L139: lua FeatureFlags.all
- L147: lua FeatureFlags.safeFalseKeys
- L157: lua FeatureFlags.byKey
- L176: lua FeatureFlags.audit
- L194: lua FeatureFlags.summary
- L202: lua FeatureFlags.toolsSummary
- L226: lua FeatureFlags.contract

## `scripts/lua/otclient/ctoa_helper_heal_friend.lua`

- L6: lua HealFriend.whitelistContainsName
- L19: lua HealFriend.scan
- L60: lua HealFriend.observe
- L84: lua HealFriend.plan
- L143: lua HealFriend.statusText
- L156: lua HealFriend.decisionText
- L167: lua HealFriend.summary
- L182: lua HealFriend.contract

## `scripts/lua/otclient/ctoa_helper_hotkeys.lua`

- L27: lua trim
- L34: lua Hotkeys.trim
- L38: lua Hotkeys.normalizeKeyName
- L61: lua Hotkeys.normalize
- L69: lua Hotkeys.parse
- L76: lua modifiers
- L148: lua Hotkeys.isAllowed
- L161: lua Hotkeys.bindingDecision
- L191: lua Hotkeys.display
- L199: lua Hotkeys.actionbarSlotText
- L206: lua Hotkeys.contract

## `scripts/lua/otclient/ctoa_helper_hud.lua`

- L11: lua Hud.startText
- L15: lua Hud.disarmedText
- L19: lua Hud.position
- L27: lua Hud.state
- L44: lua Hud.visibilityText
- L58: lua Hud.runtimeText
- L72: lua Hud.uiSummary
- L85: lua Hud.operatorSummary
- L100: lua Hud.contract

## `scripts/lua/otclient/ctoa_helper_loot_observer.lua`

- L7: lua numberValue
- L13: lua Observer.normalizeObservation
- L28: lua Observer.observe
- L36: lua Observer.attach
- L40: lua dependencies
- L42: lua metadata
- L51: lua Observer.contract

## `scripts/lua/otclient/ctoa_helper_loot_runtime.lua`

- L6: lua boolValue
- L10: lua numberValue
- L18: lua runtimeBlockedReason
- L43: lua LootRuntime.plan
- L77: lua LootRuntime.summary
- L87: lua LootRuntime.adapterSummary
- L105: lua LootRuntime.contract

## `scripts/lua/otclient/ctoa_helper_modal.lua`

- L15: lua trim
- L22: lua actionText
- L30: lua Modal.request
- L50: lua Modal.isPending
- L62: lua Modal.isExpired
- L70: lua Modal.confirm
- L81: lua Modal.cancel
- L92: lua Modal.decision
- L128: lua Modal.decisionText
- L147: lua Modal.statusText
- L158: lua Modal.buttonText
- L169: lua Modal.contract
- L177: lua guarded_actions

## `scripts/lua/otclient/ctoa_helper_module_status.lua`

- L35: lua copyList
- L43: lua truthy
- L47: lua moduleStatus
- L61: lua normalizeOne
- L78: lua ModuleStatus.defaultOrder
- L82: lua ModuleStatus.normalize
- L100: lua ModuleStatus.snapshot
- L134: lua ModuleStatus.summary
- L142: lua ModuleStatus.contract

## `scripts/lua/otclient/ctoa_helper_modules.lua`

- L138: lua copyList
- L146: lua Registry.getSupportModules
- L159: lua Registry.validateSupportModules
- L181: lua Registry.bootSnapshot
- L226: lua Registry.bootSummary
- L235: lua Registry.getModuleLanes
- L239: lua Registry.getShortLabels
- L243: lua Registry.laneEnabled
- L269: lua Registry.laneRuntimeText
- L287: lua Registry.registrySummary
- L304: lua Registry.readinessTag
- L324: lua Registry.readinessRow
- L339: lua Registry.contract

## `scripts/lua/otclient/ctoa_helper_operator_summary.lua`

- L6: lua callText
- L16: lua moduleSummary
- L26: lua OperatorSummary.title
- L34: lua autosaveState
- L41: lua OperatorSummary.healing
- L46: lua OperatorSummary.healFriend
- L51: lua OperatorSummary.conditions
- L56: lua OperatorSummary.equipment
- L61: lua OperatorSummary.scripting
- L66: lua OperatorSummary.targeting
- L71: lua OperatorSummary.magic
- L76: lua OperatorSummary.tools
- L91: lua OperatorSummary.profile
- L104: lua OperatorSummary.ui
- L109: lua OperatorSummary.bridgeText
- L121: lua OperatorSummary.contract

## `scripts/lua/otclient/ctoa_helper_otclient_observation_adapter.lua`

- L6: lua call
- L21: lua boolCall
- L30: lua hasMethod
- L34: lua clockMillis
- L44: lua distanceBetween
- L54: lua targetSnapshot
- L70: lua spectatorSnapshot
- L94: lua cooldownActive
- L103: lua Adapter.combatSnapshot
- L122: lua Adapter.recoverySnapshot
- L141: lua Adapter.cavebotSnapshot
- L163: lua Adapter.lootSnapshot
- L189: lua inventorySlot
- L202: lua Adapter.equipmentSnapshot
- L210: lua slots
- L220: lua Adapter.attach
- L229: lua Adapter.attachAll
- L263: lua Adapter.contract
- L266: lua guarded_globals

## `scripts/lua/otclient/ctoa_helper_plan_queue.lua`

- L8: lua copyDecision
- L27: lua boundedLimit
- L38: lua PlanQueue.normalize
- L42: lua PlanQueue.enqueue
- L55: lua PlanQueue.trim
- L67: lua PlanQueue.summary
- L75: lua PlanQueue.contract

## `scripts/lua/otclient/ctoa_helper_planner.lua`

- L27: lua weightFor
- L34: lua domainValue
- L45: lua normalizedPlan
- L75: lua Planner.collect
- L106: lua Planner.best
- L118: lua Planner.summary
- L127: lua Planner.summaryEnvelope
- L144: lua Planner.contract

## `scripts/lua/otclient/ctoa_helper_profile_persistence.lua`

- L19: lua profile
- L33: lua ui_prefs
- L49: lua healing
- L70: lua heal_friend
- L90: lua conditions
- L107: lua equipment
- L123: lua scripting
- L135: lua tools
- L210: lua copyList
- L218: lua copyTable
- L229: lua saveDefaults
- L233: lua exportSection
- L245: lua ProfilePersistence.profileCandidates
- L249: lua ProfilePersistence.uiPrefsCandidates
- L253: lua ProfilePersistence.saveDefaults
- L257: lua ProfilePersistence.resolveSavePath
- L284: lua ProfilePersistence.fallbackSavePath
- L293: lua ProfilePersistence.saveText
- L298: lua ProfilePersistence.loadSuccessText
- L305: lua ProfilePersistence.loadFailureText
- L312: lua booleanPref
- L316: lua nonEmptyText
- L323: lua ProfilePersistence.uiPrefsPlan
- L328: lua config_updates
- L329: lua hud_updates
- L330: lua helper_updates
- L376: lua ProfilePersistence.dirtyState
- L389: lua ProfilePersistence.exportProfile
- L409: lua ProfilePersistence.exportUiPrefs
- L421: lua hud
- L429: lua ProfilePersistence.contract

## `scripts/lua/otclient/ctoa_helper_profile_schema.lua`

- L55: lua spell
- L56: lua critical_spell
- L57: lua potion_name
- L58: lua mana_potion_name
- L59: lua hotkey
- L60: lua rune_name
- L61: lua sio_spell
- L62: lua heal_friend_priority
- L63: lua magic_priority
- L64: lua ui_hotkey
- L65: lua theme_preset
- L66: lua tool_timeout_ms
- L67: lua timer_interval_ms
- L68: lua tool_range
- L75: lua spells
- L87: lua spells
- L99: lua spells
- L111: lua profile
- L112: lua ui_prefs
- L113: lua healing
- L134: lua modules
- L148: lua heal_friend
- L168: lua conditions
- L185: lua equipment
- L201: lua scripting
- L213: lua tools
- L286: lua hud
- L287: lua rotation
- L288: lua heal_spell
- L289: lua waypoint
- L290: lua feature_flags
- L293: lua copyList
- L301: lua copyTable
- L312: lua isArrayTable
- L316: lua ProfileSchema.mergeTable
- L334: lua luaQuote
- L338: lua nestedOrderForKey
- L351: lua ProfileSchema.serializeLua
- L394: lua shortValue
- L403: lua ProfileSchema.requiredSections
- L407: lua ProfileSchema.sectionOrder
- L411: lua ProfileSchema.safeFalseKeys
- L415: lua ProfileSchema.optionList
- L419: lua ProfileSchema.rotationPresets
- L423: lua ProfileSchema.keyOrder
- L427: lua ProfileSchema.valueIndex
- L436: lua ProfileSchema.cycleValue
- L446: lua ProfileSchema.fieldGeometry
- L463: lua ProfileSchema.stepValue
- L474: lua profileVersion
- L489: lua setPath
- L507: lua ProfileSchema.currentVersion
- L511: lua ProfileSchema.currentSchema
- L515: lua ProfileSchema.profileVersion
- L519: lua ProfileSchema.migrationPlan
- L562: lua ProfileSchema.migrate
- L593: lua ProfileSchema.summary
- L602: lua ProfileSchema.profileSchemaSuffix
- L610: lua ProfileSchema.autosaveLabel
- L618: lua ProfileSchema.titleSummary
- L629: lua ProfileSchema.healingSummary
- L648: lua ProfileSchema.profileSummary
- L666: lua ProfileSchema.rotationPresetIds
- L676: lua ProfileSchema.rotationPresetLabel
- L686: lua ProfileSchema.rotationSummary
- L715: lua ProfileSchema.spellLabel
- L733: lua ProfileSchema.potionLabel
- L745: lua ProfileSchema.runeLabel
- L758: lua ProfileSchema.healFriendPriorityLabel
- L765: lua ProfileSchema.magicPriorityLabel
- L772: lua ProfileSchema.themePresetLabel
- L785: lua ProfileSchema.onOffLabel
- L789: lua ProfileSchema.contract

## `scripts/lua/otclient/ctoa_helper_recovery_observer.lua`

- L10: lua numberValue
- L18: lua percentage
- L27: lua RecoveryObserver.normalizeObservation
- L50: lua RecoveryObserver.observe
- L60: lua RecoveryObserver.attach
- L72: lua dependencies
- L76: lua metadata
- L97: lua RecoveryObserver.contract

## `scripts/lua/otclient/ctoa_helper_recovery_runtime.lua`

- L6: lua numberValue
- L10: lua percentValue
- L19: lua RecoveryRuntime.normalizeVitals
- L55: lua RecoveryRuntime.jitterThreshold
- L69: lua RecoveryRuntime.selectHealingSpell
- L95: lua RecoveryRuntime.potionStatusText
- L100: lua RecoveryRuntime.spellStatusText
- L104: lua RecoveryRuntime.actionGap
- L117: lua RecoveryRuntime.summary
- L124: lua RecoveryRuntime.contract

## `scripts/lua/otclient/ctoa_helper_route.lua`

- L6: lua clampIndex
- L20: lua distanceChebyshev
- L29: lua advanceIndex
- L36: lua Route.position
- L49: lua Route.label
- L60: lua Route.posKey
- L67: lua Route.add
- L83: lua Route.clear
- L92: lua Route.select
- L106: lua Route.delete
- L122: lua Route.move
- L140: lua Route.editorAction
- L168: lua Route.retryStatus
- L175: lua Route.retryBlocked
- L183: lua Route.progress
- L208: lua Route.activeTarget
- L255: lua Route.stats
- L287: lua Route.selectedSummary
- L299: lua Route.uiState
- L312: lua Route.deleteRequest
- L322: lua Route.contract

## `scripts/lua/otclient/ctoa_helper_runtime_core.lua`

- L25: lua numberValue
- L36: lua copyTable
- L47: lua safeNow
- L63: lua sortedCopy
- L74: lua RuntimeCore.registerModule
- L96: lua RuntimeCore.moduleSnapshot
- L105: lua RuntimeCore.moduleHealth
- L124: lua RuntimeCore.subscribe
- L137: lua RuntimeCore.publish
- L157: lua RuntimeCore.registerTask
- L184: lua RuntimeCore.setTaskEnabled
- L193: lua RuntimeCore.taskSnapshot
- L203: lua RuntimeCore.runDue
- L244: lua RuntimeCore.metricsSnapshot
- L248: lua RuntimeCore.statusSnapshot
- L292: lua RuntimeCore.contract

## `scripts/lua/otclient/ctoa_helper_runtime_policy.lua`

- L15: lua player_methods
- L16: lua player_states
- L17: lua globals
- L18: lua literals
- L20: lua state_flags
- L21: lua globals
- L22: lua fallbacks
- L24: lua tile_methods
- L25: lua tile_flags
- L26: lua globals
- L27: lua fallbacks
- L29: lua tile_has_flags
- L30: lua globals
- L31: lua literals
- L35: lua boolValue
- L39: lua copyTable
- L50: lua globalValues
- L58: lua policyStateValues
- L66: lua collectNumericFlags
- L84: lua hasBitFlag
- L97: lua gateValue
- L104: lua append
- L108: lua RuntimePolicy.requiredGates
- L116: lua RuntimePolicy.protectionZonePolicy
- L120: lua RuntimePolicy.resolvedProtectionZonePolicy
- L131: lua RuntimePolicy.protectionZoneDecision
- L152: lua RuntimePolicy.snapshot
- L170: lua RuntimePolicy.decision
- L209: lua RuntimePolicy.summary
- L217: lua RuntimePolicy.contract

## `scripts/lua/otclient/ctoa_helper_runtime_readiness.lua`

- L21: lua append
- L25: lua truthy
- L29: lua componentReady
- L36: lua gateReady
- L43: lua RuntimeReadiness.requiredComponents
- L51: lua RuntimeReadiness.requiredGates
- L59: lua RuntimeReadiness.snapshot
- L87: lua RuntimeReadiness.decision
- L109: lua RuntimeReadiness.summary
- L117: lua RuntimeReadiness.contract

## `scripts/lua/otclient/ctoa_helper_sandbox_handoff.lua`

- L39: lua copyStep
- L52: lua gateReady
- L57: lua SandboxHandoff.steps
- L65: lua SandboxHandoff.snapshot
- L85: lua SandboxHandoff.next
- L108: lua SandboxHandoff.summary
- L117: lua SandboxHandoff.contract

## `scripts/lua/otclient/ctoa_helper_scripting.lua`

- L6: lua Scripting.policySnapshot
- L20: lua Scripting.plan
- L53: lua Scripting.summary
- L66: lua Scripting.contract

## `scripts/lua/otclient/ctoa_helper_targeting.lua`

- L14: lua lowered
- L21: lua Targeting.normalizedName
- L36: lua Targeting.isIgnoredName
- L50: lua Targeting.hasBlockingNpcIcon
- L64: lua friendlySummonFragments
- L72: lua Targeting.isFriendlySummonName
- L90: lua Targeting.isFriendlySummonCandidate
- L104: lua Targeting.priorityRank
- L115: lua Targeting.scoreCandidate
- L130: lua Targeting.bestCandidate
- L143: lua Targeting.creatureTypeDecision
- L163: lua Targeting.decision
- L227: lua Targeting.summary
- L237: lua Targeting.configSummary
- L249: lua Targeting.contract

## `scripts/lua/otclient/ctoa_helper_timer_runtime.lua`

- L6: lua boolValue
- L10: lua numberValue
- L18: lua runtimeBlockedReason
- L39: lua TimerRuntime.plan
- L72: lua TimerRuntime.summary
- L81: lua TimerRuntime.dispatch
- L118: lua TimerRuntime.contract

## `scripts/lua/otclient/ctoa_helper_ui.lua`

- L116: lua Ui.configureLayout
- L125: lua Ui.shortText
- L134: lua Ui.fitText
- L143: lua Ui.setWidgetText
- L149: lua Ui.styleWidget
- L177: lua Ui.setWidgetChecked
- L183: lua Ui.getWidgetChecked
- L190: lua Ui.showWidget
- L201: lua Ui.createWidget
- L251: lua Ui.styleTabState
- L264: lua Ui.styleTabRail
- L274: lua Ui.styleRaisedCard
- L284: lua Ui.styleInsetValue
- L294: lua Ui.styleGroupedFrame
- L304: lua Ui.styleSubtabState
- L317: lua Ui.styleMiniButton
- L330: lua Ui.styleActionButton
- L361: lua Ui.styleRuntimeBadge
- L375: lua Ui.styleRuleCard
- L386: lua Ui.styleMetricRow
- L396: lua Ui.styleMetricLabel
- L405: lua Ui.styleMetricValue
- L414: lua Ui.styleSettingState
- L435: lua Ui.styleStateValue
- L452: lua Ui.styleProfileField
- L473: lua Ui.styleVectorRow
- L498: lua Ui.styleSectionBody
- L508: lua Ui.styleTableHeader
- L518: lua Ui.styleTableHeaderLabel
- L527: lua Ui.styleFooterStrip
- L537: lua Ui.styleFooterStripLabel
- L545: lua Ui.styleSummaryStrip
- L555: lua Ui.styleSummaryStripLabel
- L563: lua Ui.styleSectionBandTitle
- L578: lua Ui.styleSectionBandSubtitle
- L587: lua Ui.styleSectionBandDivider
- L597: lua Ui.stylePriorityBadge
- L610: lua Ui.styleLabel
- L629: lua Ui.styleWindowRoot
- L639: lua Ui.styleWindowFrame
- L675: lua Ui.styleWindowTitleLabel
- L702: lua Ui.styleToggleButton
- L714: lua Ui.styleCheckBox
- L726: lua Ui.styleSidebarCard
- L738: lua Ui.styleOverviewAvatarFrame
- L748: lua Ui.styleOverviewAvatar
- L757: lua Ui.styleOverviewAvatarName
- L766: lua Ui.styleOverviewHpBar
- L775: lua Ui.styleOverviewEquipSlot
- L785: lua Ui.styleControlName
- L793: lua Ui.settingRowGeometry
- L811: lua Ui.metricCardGeometry
- L827: lua Ui.metricTextPlan
- L843: lua Ui.setMetricText
- L857: lua Ui.profileFieldGeometry
- L871: lua Ui.vectorStepGeometry
- L905: lua adapterStyle
- L910: lua adapterProfileFieldGeometry
- L920: lua Ui.addProfileCycleRow
- L952: lua refresh
- L994: lua Ui.addProfileStepRow
- L1027: lua setValue
- L1064: lua Ui.addVectorStepRow
- L1112: lua clampValue
- L1122: lua refresh
- L1173: lua Ui.addSettingRow
- L1204: lua Ui.addToggleSettingRow
- L1211: lua valueText
- L1233: lua Ui.sectionBodyGeometry
- L1242: lua Ui.sidebarTabs
- L1260: lua Ui.sidebarGeometry
- L1294: lua Ui.huntingSubtabs
- L1302: lua Ui.subtabContentY
- L1306: lua Ui.toolsSubtabs
- L1318: lua Ui.toolsTableHeaders
- L1327: lua Ui.cavebotDelayChoices
- L1331: lua Ui.cavebotReachChoices
- L1335: lua Ui.msText
- L1339: lua Ui.cavebotActionSpecs
- L1357: lua Ui.renderOverviewPanel
- ... 13 more symbols omitted

## `scripts/lua/otclient/ctoa_helper_vocation_profiles.lua`

- L27: lua safeCall
- L35: lua slug
- L43: lua VocationProfiles.normalize
- L54: lua VocationProfiles.detect
- L73: lua VocationProfiles.fileName
- L78: lua VocationProfiles.label
- L83: lua VocationProfiles.characterName
- L87: lua VocationProfiles.candidates
- L103: lua VocationProfiles.contract
- L107: lua supported

## `scripts/lua/otclient/ctoa_ms_profile.lua`

- L5: lua modules
- L6: lua healing
- L9: lua spell_rotation
- L14: lua heal_friend
- L15: lua conditions
- L16: lua equipment
- L17: lua scripting
- L18: lua tools
- L23: lua rotation_spells
- L30: lua feature_flags
- L32: lua hud

## `scripts/lua/otclient/ctoa_native_combat.lua`

- L17: lua ignored_names
- L26: lua priority_names
- L45: lua probe_log
- L48: lua appendLog
- L59: lua helperConfig
- L73: lua nowMs
- L85: lua localPlayer
- L97: lua getPosition
- L109: lua pcallBool
- L121: lua pcallOptionalBool
- L134: lua pcallWithArg
- L146: lua pcallNumber
- L158: lua hasAnyState
- L170: lua hasBitFlag
- L183: lua collectNumericFlags
- L201: lua isInProtectionZone
- L281: lua safeGameCall
- L293: lua clearCombatState
- L309: lua chebyshevDistance
- L316: lua normalizedName
- L328: lua appendIgnoredNames
- L336: lua mergedIgnoredNames
- L343: lua isIgnoredName
- L357: lua isMonsterCreature
- L395: lua isValidTarget
- L418: lua getPriorityNameRank
- L429: lua candidateScore
- L441: lua getSpectators
- L461: lua findBestTarget
- L485: lua currentAttackTarget
- L497: lua currentTargetId
- L509: lua probeValue
- L522: lua logCreatureProbe
- L556: lua retargetNow
- L587: lua onThink
- L631: lua onCreatureDeath
- L638: lua init

## `scripts/lua/otclient/ctoa_native_heal.lua`

- L29: lua appendLog
- L49: lua nowMs
- L61: lua mergeSettings
- L72: lua helperConfig
- L100: lua localPlayer
- L112: lua percent
- L119: lua readVitals
- L167: lua isInProtectionZone
- L184: lua castSpell
- L194: lua pressHotkey
- L204: lua chooseHealSpell
- L211: lua maybeRecover
- L253: lua onHealthChanged
- L257: lua onManaChanged
- L261: lua onThink
- L268: lua init

## `scripts/lua/otclient/ctoa_native_helper.lua`

- L25: lua modules
- L31: lua healing
- L36: lua spell_rotation
- L49: lua heal_friend
- L52: lua friend_whitelist
- L57: lua conditions
- L65: lua equipment
- L73: lua scripting
- L80: lua tools
- L88: lua friendly_summon_name_fragments
- L96: lua ignored_names
- L101: lua priority_names
- L120: lua last_spell_casts
- L121: lua rotation_spells
- L134: lua exeta_spells
- L175: lua cavebot_waypoints
- L176: lua feature_flags
- L195: lua moduleCall
- L205: lua moduleValue
- L213: lua rebuildModuleLaneIndex
- L214: lua MODULE_LANE_INDEX
- L239: lua widgets
- L240: lua sections
- L293: lua classic
- L316: lua graphite
- L339: lua amber
- L362: lua emerald
- L483: lua displayProfileName
- L517: lua profileSchemaValue
- L525: lua profileSchemaTable
- L533: lua profilePersistenceValue
- L541: lua profilePersistenceTable
- L546: lua normalizeHelperHotkey
- L557: lua hotkeyBindingDecision
- L572: lua helperNowMs
- L584: lua modalRequest
- L600: lua appendLog
- L619: lua status
- L631: lua mergeTable
- L639: lua reportClientCapabilities
- L683: lua loadProfile
- L727: lua applySafeBootRuntimeGuard
- L758: lua runtimeArmingBlockedReason
- L765: lua requestRuntimeSessionArm
- L774: lua loadUiPrefs
- L816: lua applyThemePreset
- L832: lua applyWindowPlacement
- L849: lua applyUiPrefs
- L855: lua setThemePreset
- L862: lua setCompactMode
- L869: lua serializeLua
- L877: lua exportProfile
- L890: lua exportUiPrefs
- L935: lua getSmokeCommandPath
- L954: lua getDiagnosticsExportPath
- L968: lua removeSmokeCommand
- L976: lua readSmokeCommand
- L989: lua applySmokeCommand
- L1067: lua processSmokeCommand
- L1116: lua markProfileDirty
- L1161: lua setLastPotionStatus
- L1170: lua setHudText
- L1176: lua throttledRuntimeStatus
- L1189: lua defer
- L1211: lua addToSection
- L1223: lua setSectionVisible
- L1230: lua createWidget
- L1238: lua sendHotkey
- L1253: lua resolveActionbarSlot
- L1263: lua sendActionbarSlot
- L1271: lua castSpell
- L1279: lua hasAttackTarget
- L1283: lua getAttackTarget
- L1295: lua isGameOnline
- L1305: lua getLocalPlayer
- L1317: lua getThingPosition
- L1329: lua distanceChebyshev
- L1336: lua normalizedCreatureName
- L1352: lua isIgnoredCreatureName
- L1370: lua creatureHasBlockingNpcIcon
- ... 125 more symbols omitted

## `scripts/lua/otclient/ctoa_native_loot.lua`

- L36: lua appendLog
- L56: lua nowMs
- L68: lua helperLootConfig
- L87: lua localPlayer
- L99: lua itemId
- L111: lua itemCount
- L123: lua itemName
- L139: lua lootRule
- L144: lua isValuableLoot
- L148: lua freeCapacity
- L160: lua hasCapacityForItem
- L168: lua isCorpseContainer
- L187: lua getContainerItems
- L200: lua getOpenContainers
- L212: lua destinationForLoot
- L233: lua lootScore
- L241: lua moveItem
- L274: lua sortedValuableItems
- L287: lua scanContainer
- L306: lua onContainerOpen
- L317: lua distance
- L324: lua getPosition
- L336: lua onItemAppear
- L350: lua scanOpenContainers
- L365: lua onThink
- L381: lua init

## `scripts/lua/otclient/ctoa_otclient_loader.lua`

- L7: lua modules
- L16: lua bootLog
- L33: lua log
- L43: lua fileExists
- L55: lua resolveModuleDir
- L67: lua isOnline
- L71: lua loadModule
- L85: lua loadHelperFromFilesystem
- L104: lua supportManifest
- L121: lua loadSupportModules
- L146: lua loadSupportModulesFromFilesystem
- L185: lua loadHelperOnly
- L218: lua scheduleHelperLoad
- L231: lua onGameStart
- L243: lua onGameEnd

## `scripts/lua/otclient/ctoa_rp_profile.lua`

- L5: lua modules
- L6: lua healing
- L9: lua spell_rotation
- L14: lua heal_friend
- L15: lua conditions
- L16: lua equipment
- L17: lua scripting
- L18: lua tools
- L23: lua rotation_spells
- L30: lua feature_flags
- L32: lua hud

## `scripts/lua/pathing_helper.lua`

- L7: lua normalizeWaypoint
- L22: lua PathingHelper.normalizeRoute
- L38: lua PathingHelper.nextWaypoint
- L55: lua PathingHelper.retryBlocked

## `scripts/lua/proximity_watch.lua`

- L8: lua onThink

## `scripts/lua/safety_interrupt.lua`

- L7: lua SafetyInterrupt.shouldInterrupt
- L11: lua SafetyInterrupt.nextAction

## `scripts/lua/status_beacon.lua`

- L7: lua onThink

## `scripts/lua/supply_manager.lua`

- L7: lua asNumber
- L15: lua SupplyManager.checkSupplies
- L36: lua SupplyManager.shouldRefill
- L42: lua SupplyManager.nextAction

## `scripts/lua/target_priority.lua`

- L10: lua asNumber
- L18: lua normalizeTarget
- L36: lua TargetPriority.score
- L50: lua TargetPriority.pick
- L72: lua TargetPriority.normalize

## `scripts/lua/telemetry_exporter.lua`

- L3: lua escape
- L9: lua TelemetryExporter.toJsonLine

## `scripts/ops/analyze-enc3.ps1`

- L13: function Get-ShannonEntropy
- L39: function Find-ZlibOffsets
- L52: function Test-SimpleXorZlib

## `scripts/ops/api_cost_report.py`

- L27: class CostRecord
- L41: def _read_json_or_jsonl(path)
- L63: def _read_jsonl_records(path)
- L79: def _configured_path(env_name, fallback)
- L84: def _configured_path_from(env_names, fallback)
- L92: def _configured_optional_path(env_name)
- L97: def _extract_records(payload)
- L111: def _nested_get(payload, keys, default)
- L125: def _as_int(value)
- L138: def _as_float(value)
- L151: def _timestamp_to_day(value)
- L161: def _load_pricing(path)
- L179: def _extract_cost_record(raw, path, index, pricing)
- L230: def load_cost_records(runs_dir, pricing)
- L251: def load_eval_artifact_summary(dataset_path, prompt_variants_dir)
- L285: def _sum_by(records, field)
- L313: def build_report(records, runs_dir, anomaly_threshold, dataset_path, prompt_variants_dir)
- L389: def _build_recommendations(records, anomalies, records_with_cost, reduction_pct, eval_artifacts)
- L419: def render_markdown(report)
- L455: def _build_parser()
- L482: def main()

## `scripts/ops/assemble_by_handle_offset.py`

- L12: def load_events()
- L24: def get_dump_file(ev)
- L32: def get_handle(ev)
- L40: def get_offset(ev)
- L55: def get_size(ev)
- L63: def get_ts(ev)
- L71: def main()

## `scripts/ops/assemble_io_dense_stream.py`

- L13: def entropy(data)
- L28: def headers(data)

## `scripts/ops/assemble_overlap_graph_variants.py`

- L21: def entropy(data)
- L36: def headers(data)
- L53: def sha1(data)
- L57: def find_best_overlap(a, b, min_ov, max_ov)
- L65: def rolling_hashes(data, window, stride)
- L78: def jaccard(a, b)
- L88: def edge_score(overlap, jac)
- L93: def dedup_blocks(stream, block)
- L108: def merge_ordered_chunks(chunks)
- L124: def build_clusters(node_ids, outgoing, best_out)
- L165: def order_cluster(cluster, outgoing, incoming_weight)
- L195: def main()

## `scripts/ops/assemble_window_aware_variants.py`

- L16: def entropy(data)
- L31: def headers(data)
- L48: def find_best_overlap(a, b, min_ov, max_ov)
- L56: def merge_overlap(chunks)
- L72: def dedup_chunks(chunks)
- L84: def dedup_blocks(stream, block)

## `scripts/ops/auto_trainer.py`

- L41: def _now()
- L45: def _rows(sql, params)
- L49: def _row(sql, params)
- L53: def _quality_state()
- L75: def _failed_templates(limit)
- L84: def _recent_runs(limit)
- L92: def _success_ratio(runs, agent)
- L100: def _recommendations(quality, failed, runs)
- L140: def _render_markdown(quality, failed, runs, rec)
- L177: def _write_reports(markdown, payload)
- L193: def main()

## `scripts/ops/azure-alerts-runner.ps1`

- L14: function Import-DotEnvFile
- L41: function Resolve-PythonExecutable
- L55: function Test-LoopbackHost
- L65: function Assert-AzureListenerExposure
- L81: function Invoke-AzureAlertsPipeline

## `scripts/ops/azure_activity_webhook_listener.py`

- L17: def parse_args()
- L54: def _is_loopback_host(host)
- L68: def _assert_safe_listener_config(args)
- L79: class _Handler
- L82: def _write_json(self, code, payload)
- L90: def do_POST(self)
- L146: def log_message(self, format)
- L150: def main()

## `scripts/ops/bootstrap_sprints_029_040.py`

- L24: class SprintWindow
- L29: def _sprint_label(sprint)
- L33: def _sprint_dir_name(sprint)
- L37: def _backlog_path(sprint)
- L41: def _flow_path(sprint)
- L45: def _validator_path(sprint)
- L49: def _experiments_dir(sprint)
- L53: def _window_for_sprint(sprint)
- L59: def _write_yaml(path, payload)
- L65: def _build_backlog_payload(window)
- L123: def _build_flow_payload(window)
- L183: def _validator_code(sprint)
- L361: def _write_experiment_md(path, task_id, status, objective)
- L379: def _update_tasks_json()
- L420: def _update_pipeline()
- L450: def bootstrap()
- L480: def main()

## `scripts/ops/bridge_replacement_readiness.py`

- L26: def tracked_files()
- L31: def scan()
- L61: def main()

## `scripts/ops/capture_io_dense_live.py`

- L26: def entropy(data)
- L41: def headers(data)
- L52: def rd32(c, addr)
- L59: def rb(c, addr, size)
- L68: def resolve_symbol(c, names)
- L98: def flush(status, summary)
- L106: def record_error(context, exc)
- L110: def clear_breakpoint(addr, context)
- L117: def add_dump(item)
- L124: def dump_blob(kind, blob, meta)
- L144: def dump_region(c, kind, base, size, meta)
- L189: def arm_exec_watch(base, size, source)

## `scripts/ops/capture_loader_exec_aggressive.py`

- L23: def entropy(data)
- L38: def headers(data)
- L49: def rd32(c, addr)
- L56: def rmem(c, addr, size)
- L65: def has_exec(p)
- L95: def record_error(context, exc)
- L98: def clear_breakpoint(addr, context)
- L104: def dump_region(kind, base, size, extra)
- L127: def arm_exec(base, size, source, protect)

## `scripts/ops/capture_loader_exec_aggressive_live.py`

- L24: def entropy(data)
- L39: def headers(data)
- L50: def rd32(c, addr)
- L57: def rmem(c, addr, size)
- L66: def has_exec(p)
- L80: def flush_report(status, extra_summary)
- L113: def record_error(context, exc)
- L117: def clear_breakpoint(addr, context)
- L124: def dump_region(kind, base, size, extra)
- L148: def arm_exec(base, size, source, protect)

## `scripts/ops/capture_loader_exec_burst.py`

- L23: def entropy(data)
- L38: def headers(data)
- L49: def rd32(c, addr)
- L56: def rmem(c, addr, size)
- L65: def has_exec(prot)
- L101: def record_error(context, exc)
- L104: def clear_breakpoint(addr, context)
- L110: def write_dump(kind, base, size, trigger_addr, extra)
- L134: def arm_exec_breakpoints(base, size, source, protect)

## `scripts/ops/capture_ntreadfile_stream.py`

- L21: def entropy(data)
- L36: def detect_headers(data)
- L47: def rd32(c, addr)
- L54: def read_bytes(c, addr, size)
- L63: def read_u64_ptr(c, ptr)
- L73: def build_by_offset(segments)
- L110: def build_by_order(segments)

## `scripts/ops/capture_post_transform_mapview.py`

- L20: def entropy(data)
- L35: def detect_headers(data)
- L52: def rd32(c, addr)
- L59: def read_ptr(c, ptr)
- L65: def read_size_t_ptr(c, ptr)
- L71: def read_mem(c, addr, size)

## `scripts/ops/capture_post_transform_protect.py`

- L22: def entropy(data)
- L37: def detect_headers(data)
- L48: def rd32(c, addr)
- L55: def read_mem(c, addr, size)

## `scripts/ops/capture_runtime_crypto_decompress_live.py`

- L23: def entropy(data)
- L38: def headers(data)
- L58: def rd32(c, addr)
- L65: def rb(c, addr, size)
- L74: def resolve_symbol(c, names)
- L102: def flush(status, summary)
- L110: def record_error(context, exc)
- L114: def clear_breakpoint(addr, context)
- L121: def dump_blob(kind, blob, meta)
- L142: def capture_return_for_rtl(c, esp)
- L196: def capture_return_for_bcrypt(c, esp)
- L257: def capture_return_for_crypt(c, esp)
- L306: def capture_return_for_ncrypt(c, esp)

## `scripts/ops/capture_runtime_loader_transform_live.py`

- L40: def record_error(stage, error)
- L50: def _pid_alive(pid)
- L62: def _read_lock_pid()
- L87: def _release_lock()
- L108: def has_exec(prot)
- L114: def entropy(data)
- L129: def printable_ratio(data)
- L140: def dump_score(size, ent, hdrs, pr)
- L168: def bounded_region_size(size, fallback)
- L174: def sample_prefix(c, base, size)
- L181: def headers(data)
- L201: def sha1_fingerprint(data)
- L205: def rd32(c, addr)
- L212: def rb(c, addr, size)
- L221: def resolve_symbol(c, names)
- L252: def flush(status, summary)
- L260: def dump_blob(kind, blob, meta)
- L300: def dump_region(c, kind, base, size, meta)
- L381: def alloc_shape_key(size, prot, alloc_type)
- L385: def track_alloc_region(base, size, prot, source, alloc_type)
- L417: def clear_alloc_breakpoints(base)
- L430: def refresh_hot_alloc_watchers()
- L449: def maybe_dump_first_touch(base, reason, trigger)
- L467: def poll_alloc_region_diffs(trigger_eip)
- L482: def remember_recent_move(dest, size, source)
- L490: def match_recent_move(base, size)
- L509: def add_write_volume(base, size, source)
- L534: def rank_exec_watch_pages(base, size)
- L549: def arm_exec_watch(base, size, source)
- L575: def wait_return_and_regs(ret_addr)

## `scripts/ops/ci_executive_report.py`

- L39: class WorkflowMetric
- L49: def _fetch_json(url, token)
- L64: def fetch_runs(owner, repo, token, min_cutoff)
- L99: def slice_window(runs, cutoff)
- L108: def metric_for_workflow(runs, workflow_name)
- L135: def weighted_score(metrics)
- L150: def identify_risks(metrics_7d, score_7d, score_30d)
- L181: def remediation_actions(metrics_7d)
- L204: def render_markdown(generated_at, owner_repo, windows, by_window, scores)
- L277: def parse_args()
- L296: def main()

## `scripts/ops/client_profile_router.py`

- L8: def resolve_client_profile(client_path)
- L21: def main()

## `scripts/ops/control_center_p6_plugin_handoff_smoke.py`

- L52: def display_path(path, root)
- L59: def plugin_display_path(path)
- L67: def workspace_path(root, value)
- L71: def assert_inside_workspace(root, path)
- L78: def safe_file_stat(path)
- L88: def read_text_bounded(path, max_bytes)
- L104: def read_json_object(path)
- L111: def add_check(checks, name, ok, evidence, blocker)
- L128: def checks_from_payload(payload)
- L135: def check_by_name(checks, name)
- L142: def installed_cache_version(check)
- L149: def plugin_mcp_server(payload)
- L157: def plugin_mcp_absolute_script_ready(plugin_root, payload)
- L179: def allowed_tools(payload)
- L201: def blocked_classes(payload)
- L209: def summary(payload)
- L214: def build_report(root)
- L486: def render_markdown(report)
- L527: def write_outputs(root, report, json_out, md_out)
- L538: def main()

## `scripts/ops/control_center_p7_cockpit_smoke.py`

- L51: def display_path(path, root)
- L58: def workspace_path(root, value)
- L62: def assert_inside_workspace(root, path)
- L69: def safe_file_stat(path)
- L79: def read_text_bounded(path, max_bytes)
- L95: def read_json_object(path)
- L102: def read_jsonl_tail(path)
- L141: def add_check(checks, name, ok, evidence, blocker)
- L158: def tool_names(items)
- L168: def enabled_safe_write_tools(payload)
- L179: def action_id_for_record(record)
- L183: def mcp_tool_for_action(action_id)
- L187: def audit_records_by_action(records)
- L217: def build_report(root)
- L449: def render_markdown(report)
- L488: def write_outputs(root, report, json_out, md_out)
- L499: def main()

## `scripts/ops/control_center_p7_evidence_review.py`

- L34: def display_path(path, root)
- L41: def workspace_path(root, value)
- L45: def assert_inside_workspace(root, path)
- L52: def safe_file_stat(path)
- L62: def read_text_bounded(path, max_bytes)
- L78: def read_json_object(path)
- L85: def read_jsonl_tail(path)
- L121: def add_check(checks, name, passed, evidence, blocker)
- L138: def latest_confirmed_evidence_refresh(records)
- L153: def p7_cockpit_evidence_audit(payload)
- L163: def summary(payload)
- L168: def build_report(root)
- L345: def render_markdown(report)
- L378: def write_outputs(root, report, json_out, md_out)
- L389: def main()

## `scripts/ops/control_center_p7_safe_write_dry_run_smoke.py`

- L50: def display_path(path, root)
- L57: def workspace_path(root, value)
- L61: def assert_inside_workspace(root, path)
- L68: def safe_file_stat(path)
- L78: def read_text_bounded(path, max_bytes)
- L89: def read_jsonl_tail(path)
- L111: def plugin_command(plugin_root)
- L130: def mcp_messages(root)
- L163: def parse_mcp_responses(stdout)
- L176: def tool_text_payload(response)
- L191: def latest_record_by_audit_id(records)
- L200: def finalizable_bootstrap_preflight(preflight)
- L213: def add_check(checks, name, passed, evidence, blocker)
- L230: def build_report(root, plugin_root)
- L425: def render_markdown(report)
- L460: def write_outputs(root, report, json_out, md_out)
- L471: def main()

## `scripts/ops/core_guard.py`

- L21: def sha256_file(path)
- L29: def read_protected_paths()
- L43: def write_manifest(paths)
- L66: def parse_manifest()
- L82: def check_manifest(paths)
- L120: def main()

## `scripts/ops/ctoa-vps.ps1`

- L70: function Get-RequiredEnv
- L78: function Get-OptionalEnv
- L86: function Assert-VpsUser
- L100: function Assert-VpsHost
- L154: function Resolve-ServerUrl
- L167: function Assert-RemoteScriptText
- L184: function ConvertTo-RemoteSqlLiteral
- L189: function Assert-CtoaServerUrl
- L210: function Resolve-CtoaServerUrlList
- L221: function Assert-CtoaServerStatus
- L229: function Assert-CtoaServiceName
- L237: function Assert-CtoaGitRef
- L258: function Assert-CtoaIntegerRange
- L269: function Assert-CtoaUtcTime
- L277: function Get-RemoteTarget
- L287: function Get-KeyPath
- L294: function Get-LocalRootWrapperScript
- L303: function Invoke-RemoteRootWrapper
- L320: function Ensure-RemoteRootWrapper
- L323: function Invoke-WithSshRetry
- L351: function Invoke-SshCommand
- L363: function Invoke-SshScript
- L376: function Assert-GithubPatValue
- L389: function Assert-EnvSecretValue
- L405: function Write-RemoteGithubPat
- L451: function Write-RemoteGsEnvKeys
- L547: function Invoke-RemoteSyntaxValidation
- L577: function Invoke-RemoteVerify
- L610: function Get-SetupScript

## `scripts/ops/ctoa_env_doctor.py`

- L21: def _check_git()
- L40: def _origin_url()
- L44: def _check_origin(expected_origin)
- L70: def _check_worktree_clean()
- L87: def _check_upstream_sync()
- L118: def _check_ssh_access(expected_origin)
- L137: def run_doctor(expected_origin)
- L158: def _print_human(report)
- L172: def main()

## `scripts/ops/ctoa_full_workspace_audit.py`

- L89: class FileRecord
- L100: def _run_git(args)
- L122: def _rel(path)
- L126: def _is_git_internal(path)
- L134: def _category(rel_path, tracked)
- L161: def _safe_file_stat(path)
- L171: def _file_kind(mode)
- L189: def _same_file_stat(expected, opened)
- L197: def _sha256_for_file(path, category, max_hash_bytes, file_stat)
- L223: def build_inventory(max_hash_bytes)
- L305: def _audit_gate(inventory)
- L360: def _load_validation_evidence(path)
- L391: def _validation_gate(validation)
- L421: def _mb(value)
- L425: def _audit_findings(inventory)
- L476: def render_audit_markdown(inventory, validation_evidence)
- L603: def render_plans_markdown(inventory)
- L698: def parse_args()
- L708: def main()

## `scripts/ops/ctoa_helper_smoke_report.py`

- L56: class ViewEvidence
- L63: class SmokeReport
- L73: def _view_from_name(path, run_id, prefix)
- L81: def collect_report(screenshot_dir, run_id)
- L94: def display_path(path)
- L120: def render_markdown(report)
- L165: def render_html(report)
- L238: def parse_args()
- L250: def main()

## `scripts/ops/ctoa_helper_ui_mockup_v4.py`

- L253: def main()

## `scripts/ops/ctoa_helper_ui_preview.py`

- L36: class Widget
- L47: def right(self)
- L51: def bottom(self)
- L55: def clean_text(raw, widget_id)
- L128: def split_lua_args(arg_text)
- L180: def _eval_numeric_expr(expr)
- L181: def visit(node)
- L210: def as_int(value, fallback, variables)
- L231: def section_from_args(args)
- L257: def section_from_id(widget_id, fallback)
- L310: def lua_table_field(table_source, field)
- L315: def width_from_args(fn, args, fallback, variables)
- L345: def extract_layout_variables(source)
- L407: def extract_window(source)
- L420: def extract_widgets(source)
- L600: def extract_rendered_overview_panel(source, variables, existing)
- L619: def add(widget_id, text, x, y, width, height, kind)
- L658: def _placeholder_rows(rows_src)
- L665: def extract_placeholder_modules(source, variables, existing)
- L710: def extract_toggle_content_rows(source, variables, existing)
- L743: def extract_rendered_hunting_panel(source, variables, existing)
- L762: def add(widget_id, text, y, section, width, kind)
- L817: def extract_rendered_cavebot_panel(source, variables, existing)
- L835: def add(widget_id, text, x, y, width, section, kind)
- L889: def extract_rendered_tools_panel(source, variables, existing)
- L909: def add(widget_id, text, y, section, width, kind)
- L987: def extract_rendered_profile_panel(source, variables, existing)
- L998: def add(widget_id, y_key, section, x, width, kind)
- L1046: def extract_rendered_engine_panel(source, variables, existing)
- L1057: def add(widget_id, y_key, section, x, width, kind)
- L1088: def validate(window, widgets)
- L1140: def render_stage(width, height, widgets, active)
- L1257: def render_html(window, widgets)
- L1405: def parse_args()
- L1412: def main()

## `scripts/ops/ctoa_loader.py`

- L41: def _slugify(value)
- L45: def _target_candidates(name)
- L52: def add(value)
- L76: def _is_relative_to(path, root)
- L84: def _safe_target_candidate(candidate)
- L102: def _resolve_target_root(root)
- L110: def _target_child(root, candidate)
- L126: def _target_child_file(root, candidate)
- L142: def _resolve_target_dir(root, name)
- L167: def _list_targets(root)
- L200: def _sync_with_output(source, target)
- L222: def _sync(source, target)
- L231: def _build_parser()
- L253: def _run_cli(argv)
- L281: def _launch_gui()
- L342: def write_output(text)
- L346: def list_targets()
- L356: def sync_targets()
- L372: def open_target()
- L384: def export_manifest()
- L432: def _open_target_dir(root, name)
- L450: def _open_path(path)
- L470: def _export_manifest(root, name, out_path)
- L518: def main()

## `scripts/ops/ctoa_otprofile_builder.py`

- L31: def default_profile()
- L242: def normalize(text)
- L249: def find_percent(text, keywords)
- L259: def set_spell_min(profile, spell_words, min_nearby)
- L266: def remove_spell(profile, spell_words)
- L274: def apply_request(profile, request)
- L373: def lua_quote(value)
- L377: def to_lua(value, indent)
- L401: def render_profile(profile)
- L410: def write_profile(profile, deploy)
- L417: def parse_args()
- L425: def main()

## `scripts/ops/ctoa_product_bootstrap.py`

- L21: def _normalize_package_tier(value)
- L28: def _tier_features(package_tier)
- L38: class BootstrapArtifacts
- L45: def _load_json(path)
- L49: def _atomic_json_temp_path(path)
- L53: def _remove_temp_path(path)
- L60: def _atomic_write_json(path, payload)
- L74: def _prompt_value(label, default)
- L79: def _artifacts(state_dir)
- L88: def _ensure_db(sqlite_path)
- L119: def bootstrap()
- L195: def main()

## `scripts/ops/ctoa_tibia_source_ingest.py`

- L26: def parse_args()
- L42: def main()

## `scripts/ops/ctoa_update_gate.py`

- L16: def _load_json(path)
- L20: def _load_bootstrap_state(path)
- L39: def _invalid_bootstrap_state(reason)
- L48: def _parse_version(value)
- L52: def run_gate(state_dir)
- L116: def main()

## `scripts/ops/depack_anchor_windows.py`

- L34: def entropy(data)
- L49: def printable_ratio(data)
- L59: def find_magic(data)
- L78: def pe_score(data)
- L97: def score_blob(data)
- L147: def make_windows(data)
- L175: def try_depack(payload, wbits)
- L206: def iter_variants()
- L220: def main()

## `scripts/ops/depack_io_assembled_focused.py`

- L13: def entropy(data)
- L25: def magic(data)
- L33: def score(data)

## `scripts/ops/depack_stream_compare.py`

- L13: def entropy(data)
- L28: def scan_offsets(data, limit)
- L42: def magic(data)
- L51: def score(data)

## `scripts/ops/depack_stream_focused.py`

- L14: def entropy(data)
- L29: def printable_ratio(data)
- L36: def detect_magic(data)
- L46: def score_blob(data)
- L66: def xor_data(data, k)
- L72: def zlib_head_offsets(data, limit)

## `scripts/ops/depack_top_candidates.py`

- L41: def entropy(data)
- L56: def printable_ratio(data)
- L63: def detect_magic(data)
- L83: def score_blob(data)
- L103: def zlib_like_offsets(data, max_scan)
- L116: def entropy_regions(data, threshold)
- L145: def local_entropy_min_offsets(data, regions, radius)
- L150: def local_min(center)
- L170: def rol_byte(v, bits)
- L175: def apply_transform(data, t)
- L188: def build_transforms()
- L197: def try_decompress(payload)
- L241: def process_candidate(cpath, transforms)
- L298: def render_md(summary, md_path)
- L326: def main()

## `scripts/ops/depack_window_aware_focused.py`

- L13: def entropy(data)
- L28: def printable_ratio(data)
- L38: def magic(data)
- L54: def score_breakdown(data)
- L95: def candidate_offsets(data)
- L108: def iter_variants()
- L121: def main()

## `scripts/ops/engine_brain_doctor.py`

- L30: class CommandResult
- L37: def run_cmd(command)
- L59: def safe_lines(value, limit)
- L64: def status(ok, warning)
- L72: def check_git()
- L108: def parse_docker_ports(ports)
- L118: def _is_unspecified_host(host_ip)
- L128: def docker_status()
- L136: def check_docker()
- L178: def docker_config_broad_binds(docker)
- L207: def powershell(script, timeout)
- L211: def check_vpn()
- L235: def check_vercel()
- L267: def check_vscode()
- L305: def check_github()
- L362: def check_update_gate()
- L378: def build_report()
- L403: def render_markdown(report)
- L461: def write_report(report, out_dir)
- L473: def main()

## `scripts/ops/engine_brain_index.py`

- L222: class FileEntry
- L227: def rel(self)
- L231: def _is_excluded(path)
- L241: def iter_files()
- L265: def python_symbols(path)
- L291: def regex_symbols(path, pattern, label)
- L307: def symbols_for(path)
- L320: def render_file_tree(files, generated_at)
- L338: def render_symbol_map(files, generated_at)
- L365: def read_audit_inventory(audit_path)
- L375: def top_level_owner(path_name)
- L379: def build_ownership_payload(audit, generated_at)
- L425: def render_ownership_map(payload)
- L447: def build_doc_sync_payload(generated_at)
- L474: def render_doc_sync(payload)
- L493: def build_secret_guardrail_payload(generated_at, audit, generated_paths)
- L529: def exact_path_appears(text, path_value)
- L535: def render_secret_guardrail(payload)
- L560: def read_validation_evidence(validation_path)
- L572: def _path_check(name, path)
- L581: def _source_needles_check(name, path, needles)
- L602: def _local_codex_skill_check()
- L614: def _local_plugin_file_check(name, relative_path)
- L628: def _local_plugin_source_needles_check(name, relative_path, needles)
- L654: def _read_local_plugin_manifest()
- L665: def _installed_plugin_cache_check()
- L721: def _plugin_mcp_absolute_script_check()
- L772: def _personal_marketplace_plugin_check()
- L814: def _validation_evidence_check(validation)
- L844: def build_p6_readiness_payload(generated_at, manifest_payload, validation)
- L1360: def render_p6_readiness(payload)
- L1382: def _validation_statuses(validation)
- L1398: def read_action_audit_summary(action_audit_path)
- L1479: def read_json_object(path)
- L1489: def read_roadmap_text(path)
- L1500: def build_roadmap_generation_payload(generated_at, doc_sync_payload)
- L1573: def read_release_evidence_summary(release_root, latest_path)
- L1645: def read_p7_cockpit_smoke_summary(smoke_path)
- L1666: def read_p7_evidence_review_summary(review_path)
- L1694: def build_p7_cockpit_handoff_payload(action_readiness_payload, action_audit)
- L1782: def _source_has_needles(relative_path, needles)
- L1791: def build_p7_action_readiness_payload(generated_at, workflow_payload, action_audit, p7_evidence_review)
- L2045: def render_p7_action_readiness(payload)
- L2082: def build_p7_safe_write_tool_design_payload(generated_at, action_readiness_payload)
- L2211: def render_p7_safe_write_tool_design(payload)
- L2247: def build_p7_operator_brief_payload(generated_at, p6_payload, validation, workflow_payload, action_readiness_payload, safe_write_tool_design_payload, action_audit, roadmap_generation_payload)
- L2472: def build_p7_operator_workflow_payload(generated_at, p6_payload)
- L2592: def render_p7_operator_workflow(payload)
- L2632: def render_p7_operator_brief(payload)
- L2729: def display_path(path)
- L2736: def build_indexes(out_dir)
- L2884: def main()

## `scripts/ops/engine_brain_pack.py`

- L136: def is_secretish_path(path)
- L149: def read_text(path)
- L153: def fence_for(path)
- L170: def append_file_section(lines, rel_path)
- L207: def build_pack(pack_path, manifest_path)
- L262: def main()

## `scripts/ops/evidence_retention.py`

- L12: def _parse_iso_utc(value)
- L27: def read_retention_policy_from_env()
- L52: def apply_retention_policy(entries)

## `scripts/ops/git_exec.py`

- L20: class GitUnavailableError
- L24: def _expand_path(value)
- L28: def resolve_git()
- L63: def run_git(args)

## `scripts/ops/gs-api-validator.py`

- L57: def fetch_json(url, noisy)
- L80: def check_schema(data, required_keys, path)
- L88: def normalize_base(base)
- L96: def join_url(base, path)
- L100: def health_candidates()
- L118: def detect_module_root()
- L141: def run_checks()
- L188: def main()

## `scripts/ops/kv_attach_first_hit.py`

- L22: def run_attach_first_hit()
- L55: def main()

## `scripts/ops/kv_first_hit_from_live_session.py`

- L21: def _safe_read_dword(client, addr)
- L28: def _safe_read_bytes(client, addr, size)
- L37: def _ascii_preview(data)
- L41: def _dump_blob(addr, requested_len, data)
- L51: def _detect_headers(data)
- L66: def _extract_payload(data, artifact_dir)
- L94: def _scan_moving_windows(chunks, window_size, step)
- L128: def _extract_from_joined_scan(joined_data, moving_scan, artifact_dir)
- L152: def _entropy(data)
- L167: def _high_entropy_regions(data, window, step, threshold, min_region)
- L211: def _carve_regions(data, regions, artifact_dir, prefix)

## `scripts/ops/lab003_mobile_proxy_smoke.ps1`

- L11: function Resolve-InputValue
- L36: function Test-CtoaLoopbackHost
- L42: function Assert-LocalApiBaseUrl

## `scripts/ops/lab003_shift_guard.ps1`

- L22: function Test-CtoaLoopbackHost
- L28: function Assert-LocalApiBaseUrl
- L62: function Assert-AlertWebhookUrl
- L97: function Get-CurrentPowerShellPath
- L121: function Resolve-OptionalValue
- L146: function Write-Log
- L157: function Send-AlertWebhook

## `scripts/ops/lab003_shift_smoke_webhook.ps1`

- L21: function Test-CtoaLoopbackHost
- L27: function Assert-LocalApiBaseUrl
- L61: function Assert-AlertWebhookUrl
- L96: function Get-CurrentPowerShellPath
- L117: function Resolve-OptionalValue

## `scripts/ops/lab003_validate_bundle.ps1`

- L11: function Test-CtoaLoopbackHost
- L17: function Assert-LocalApiBaseUrl
- L51: function Get-CurrentPowerShellPath
- L60: function Write-Log

## `scripts/ops/launch_kamil_client_macro_studio.ps1`

- L12: function Assert-BotProfileName
- L24: function Resolve-ClientExecutablePath
- L42: function Get-PythonExe
- L50: function Resolve-ClientProfile
- L66: function Start-KamilClient
- L74: function Start-MacroStudio

## `scripts/ops/link_check_docs.py`

- L11: def is_ignored(link)
- L20: def normalize_target(link)
- L23: def main()

## `scripts/ops/night-report.py`

- L24: def parse_args()
- L33: def parse_ts(line)
- L51: def resolve_manifest_dir(cli_value)
- L76: def _night_report_log_max_bytes()
- L87: def _tail_log_lines(path, max_bytes)
- L117: def collect_manifest_stats(manifest_dir, window_start)
- L147: def build_report(log_file, manifest_dir, window_hours)
- L231: def main()

## `scripts/ops/nightly_stability.py`

- L26: def _run(cmd, cwd)
- L32: def _reason_code_from_manifest(manifest)
- L45: def _collect_manifest_entries(root)
- L73: def _compute_window_trend(entries, window_seconds)
- L98: def _read_float_env(name, default)
- L108: def _read_int_env(name, default)
- L119: def _compute_anomaly_signal(trend_24h, trend_7d)
- L164: def _sha256_file(path)
- L172: def _upsert_evidence_index(index_path, entry)
- L194: def _record_evidence(root, artifact_paths, sprint_id)
- L216: def main()

## `scripts/ops/orchestrator-loop-worker.ps1`

- L23: function Write-LoopLog

## `scripts/ops/orchestrator-loop.ps1`

- L29: function Assert-ChildPath
- L57: function Test-LoopCommandLine
- L77: function Get-LoopProcess
- L106: function Start-Loop
- L146: function Stop-Loop
- L163: function Show-Status
- L175: function Get-LogTail

## `scripts/ops/otclient_external_bot_intake.py`

- L94: class SourceFileReport
- L103: def _sha256_bytes(data)
- L107: def _read_limited(path)
- L112: def _is_text_candidate(path)
- L116: def _decode(data)
- L120: def _matches(patterns, haystack)
- L124: def _directory_snapshot_sha256(path)
- L137: def _zip_text_entries(path)
- L146: def _directory_text_entries(path)
- L153: def _source_entries(path)
- L163: def _source_sha256(path)
- L169: def inspect_source_file(name, data)
- L182: def build_import_gate(report)
- L230: def build_report(source)
- L300: def render_markdown(report)
- L354: def write_text_atomic(path, text)
- L367: def main()

## `scripts/ops/otclient_helper_module_audit.py`

- L294: class ModuleAuditItem
- L305: class ExtractionPlanItem
- L315: class SupplementalPlanItem
- L325: class ModuleAudit
- L352: def write_json_atomic(path, payload)
- L369: def write_text_atomic(path, text)
- L387: def _status_for_contract(contract, helper_text, otclient_dir)
- L406: def _passed_json(path, accepted)
- L416: def _static_gate_evidence(module_id, evidence_dir)
- L439: def build_audit(helper_path, otclient_dir, plan_path, evidence_dir)
- L559: def render_markdown(audit)
- L655: def parse_args()
- L666: def main()

## `scripts/ops/otclient_helper_module_contract.py`

- L515: class ModuleContractItem
- L528: class ModuleContractReport
- L547: def write_json_atomic(path, payload)
- L564: def write_text_atomic(path, text)
- L582: def parse_loader_modules(loader_text)
- L592: def parse_registry_lanes(registry_text)
- L596: def forbidden_hits(source)
- L604: def missing_functions(source, module_global, required)
- L615: def build_report(otclient_dir, loader_path, registry_path)
- L708: def render_markdown(report)
- L758: def parse_args()
- L769: def main()

## `scripts/ops/otclient_helper_next_modules_plan.py`

- L21: class CandidateModule
- L33: class SupplementalExecution
- L257: def current_budget_priority()
- L280: def write_text_atomic(path, text)
- L298: def build_payload()
- L371: def render_markdown(payload)
- L444: def main()

## `scripts/ops/otclient_helper_profile_audit.py`

- L37: class Finding
- L45: class ProfileAudit
- L54: def _lua_bool(text, key)
- L61: def _lua_string(text, key)
- L66: def audit_profile(profile_path, schema_path)
- L122: def write_json_atomic(path, payload)
- L139: def parse_args()
- L148: def main()

## `scripts/ops/otclient_helper_shell_budget_plan.py`

- L53: class FunctionSpan
- L63: class DomainBudget
- L72: class ShellBudgetPlan
- L92: def write_json_atomic(path, payload)
- L109: def write_text_atomic(path, text)
- L127: def classify_function(name)
- L135: def strip_lua_literals(line)
- L161: def lua_block_delta(line)
- L168: def find_function_end(lines, start_index)
- L177: def parse_function_spans(source)
- L200: def build_plan(helper_path)
- L253: def render_markdown(plan)
- L308: def parse_args()
- L317: def main()

## `scripts/ops/otclient_input_contract_fixtures.py`

- L22: class FixtureCheck
- L30: class InputContractReport
- L45: def write_json_atomic(path, payload)
- L62: def write_text_atomic(path, text)
- L80: def passed_if(source)
- L84: def build_report(otclient_dir)
- L215: def render_markdown(report)
- L265: def parse_args()
- L274: def main()

## `scripts/ops/phase5_nightly_checklist.py`

- L20: def parse_args()
- L44: def _parse_snapshot_timestamp(name)
- L54: def _parse_summary(path)
- L71: def _nightly_delta_minutes(ts, nightly_hour, nightly_minute)
- L76: def _build_snapshot_record(snapshot_dir, ts, nightly_hour, nightly_minute, window_minutes)
- L115: def _evaluate_nightly_record(record)
- L134: def build_report(evidence_dir, target_runs, nightly_hour, nightly_minute, window_minutes)
- L190: def render_markdown(report)
- L258: def determine_exit_code(report, require_complete)
- L266: def main()

## `scripts/ops/phase5_nightly_sync.py`

- L39: def _default_key_path()
- L51: def parse_args()
- L85: def _run(cmd, check)
- L99: def _ssh_base(key_path, timeout)
- L113: def _scp_base(key_path, timeout)
- L127: def parse_remote_timestamps(raw)
- L136: def list_remote_timestamps(host, user, key_path, timeout, remote_dir)
- L148: def _local_snapshot_dir(local_evidence_dir, timestamp)
- L152: def should_sync_snapshot(local_snapshot_dir, sync_all)
- L163: def sync_snapshot(host, user, key_path, timeout, remote_dir, local_evidence_dir, timestamp)
- L184: def run_checklist(args)
- L214: def load_checklist_payload(json_path)
- L220: def render_short_status(payload, pulled_new, skipped_existing)
- L233: def _as_int(value, default)
- L240: def load_notify_env_file(path)
- L257: def resolve_webhook_urls(discord_cli, slack_cli, notify_env_file)
- L282: def render_notify_source_status(source, env_file, discord_set, slack_set)
- L289: def build_morning_brief(payload, pulled_new, skipped_existing)
- L319: def render_morning_brief_markdown(brief)
- L347: def write_morning_brief(path, brief)
- L352: def render_morning_brief_status(path, brief)
- L360: def _post_json(url, payload, timeout_sec)
- L384: def build_attention_message(brief)
- L393: def send_attention_notifications(brief, discord_webhook_url, slack_webhook_url, post_json)
- L444: def render_attention_notify_status(notification_result)
- L455: def is_step9_ready(payload)
- L463: def render_step9_closure_markdown(brief, payload, plan_path)
- L481: def write_step9_closure_evidence(path, brief, payload, plan_path)
- L486: def mark_step9_done_in_plan(plan_path, done_utc, evidence_rel_path)
- L516: def update_step9_closure_in_readme(readme_path, done_utc)
- L540: def auto_close_step9_if_ready(payload, brief, plan_path, closure_evidence_path, evidence_readme_path)
- L578: def render_step9_close_status(result)
- L587: def main()

## `scripts/ops/project_progress_diagram.py`

- L24: def _load_yaml(path)
- L32: def _now_iso()
- L36: def _state_by_task_id(state, backlog_id)
- L52: def _percent(value, total)
- L58: def _render_markdown()
- L131: def generate(backlog_path, state_path, output_path, project_name)
- L182: def main()

## `scripts/ops/queue_enqueue_job.py`

- L13: def main()

## `scripts/ops/release_evidence_pack.py`

- L29: def _now_iso()
- L33: def _safe_filename(value)
- L38: def build_release_evidence_pack()
- L74: def write_release_evidence_pack(output_dir, pack)
- L111: def _configured_path(env_name, fallback)
- L116: def _safe_file_stat(path)
- L126: def _safe_dir_stat(path)
- L136: def _read_text_bounded(path, max_bytes)
- L152: def _read_json(path)
- L159: def _read_json_or_none(path)
- L168: def _count_jsonl_records(path)
- L193: def _find_latest_markdown(releases_dir)
- L213: def _count_markdown_files(releases_dir)
- L219: def _helper_status(helper_dev_dir)
- L383: def _p7_operator_brief_status(operator_brief_path)
- L496: def _list_release_sprints(releases_dir)
- L526: def build_evidence_pack(releases_dir, quality_path, cost_report_path, action_audit_path, helper_dev_dir, operator_brief_path)
- L631: def render_markdown(pack)
- L758: def _build_parser()
- L787: def main()

## `scripts/ops/repo_hygiene_audit.py`

- L182: def classify_distribution(path)
- L215: def _tracked_top_level_entries()
- L231: def _scan_top_level()
- L302: def main()

## `scripts/ops/repo_hygiene_migration_plan.py`

- L14: def classify(path, reason)
- L124: def load_findings(input_path)
- L129: def build_plan(findings)
- L169: def write_markdown(plan, path)
- L192: def main()

## `scripts/ops/rosetta_bundle.py`

- L33: class Preset
- L43: def _load_presets()
- L68: def _build_parser()
- L82: def _relative(path)
- L89: def _manifest_path(output_dir, preset, suffix)
- L93: def _bundle_path(output_dir, preset, output_format)
- L98: def _reserve_unique_path(path)
- L112: def _build_command(args, preset, bundle_path)
- L123: def _resolve_assembler(executable_name)
- L153: def _write_manifest(path, preset, bundle_path, command, source)
- L172: def main()

## `scripts/ops/run-x64dbg-enc3-dynamic-pass.py`

- L29: def _hexdump(data, width)
- L39: def _safe_read(client, address, size)
- L51: def _terminate_pid(pid)
- L70: def _render_markdown(binary_path, timeout_seconds, hit_events, errors, started_at)
- L135: def main()

## `scripts/ops/runtime_path_guard.py`

- L24: def _tracked_files()
- L29: def _load_policy()
- L36: def _matches_any(path, patterns)
- L40: def check()
- L84: def main()

## `scripts/ops/runtime_smoke_e2e_8001.py`

- L25: def req(path, method, token, payload)

## `scripts/ops/solteria_api_audit.py`

- L21: class ApiFunction
- L31: def parse_meta(meta_path)
- L114: def printable_strings(path, min_len)
- L135: def scan_binary(path, keywords)
- L146: def list_archive(path)
- L172: def render_markdown(report)
- L252: def main()

## `scripts/ops/solteria_helper_goal_audit.py`

- L21: class AuditItem
- L29: class GoalAudit
- L39: def _load_json(path)
- L45: def write_json_atomic(path, payload)
- L62: def write_text_atomic(path, content)
- L78: def _exists_item(name, path)
- L82: def _roadmap_items(plan_path, validation_status, gate, gate_path)
- L109: def build_audit(plan_path, dev_dir)
- L186: def _status_tone(status)
- L195: def _label(value)
- L199: def _render_status_badge(status)
- L203: def _render_item_rows(items)
- L218: def render_html(audit)
- L322: def render_terminal_dashboard(audit)
- L343: def parse_args()
- L354: def main()

## `scripts/ops/solteria_helper_release_gate.py`

- L60: class Gate
- L68: class GateReport
- L77: def _load_json(path)
- L83: def write_json_atomic(path, payload)
- L100: def _file_gate(name, path, reason)
- L108: def _sha256(path)
- L116: def _zip_gate(path, expected_sha256)
- L131: def _manifest_gate(manifest_path, manifest)
- L175: def find_latest_inworld_smoke_report(screenshot_dir)
- L186: def _resolve_report_screenshot(smoke_report, screenshot_value)
- L197: def _smoke_gate(smoke_report, manifest_path)
- L247: def _smoke_preflight_gate(preflight_path, manifest_path, manifest)
- L283: def _module_static_gates_gate(gates_path, manifest_path)
- L312: def _module_attach_smoke_gate(gates_path, manifest_path)
- L341: def _live_root_from_manifest(manifest)
- L350: def _live_package_matches_manifest(live_root, manifest)
- L376: def _live_approval_gate(dev_dir, manifest_path, manifest, approved)
- L417: def _command_for_attach_gate(dev_dir, ready_command)
- L439: def _command_for_smokeattach_gate(dev_dir)
- L443: def _command_for_module_attach_gate(dev_dir)
- L447: def _command_for_next_gate(gates, approved, dev_dir)
- L474: def build_report(dev_dir, smoke_report)
- L523: def parse_args()
- L534: def main()

## `scripts/ops/solteria_helper_sandbox_smoke_queue.py`

- L24: class SmokeQueueStep
- L34: def read_json(path)
- L40: def _gate_status(release_gate, name)
- L47: def _fresh_status(status)
- L55: def _valid_attach_tabs(script_path)
- L69: def _attach_tab(command)
- L74: def _static_module_steps(goal_status, valid_tabs)
- L122: def build_queue(dev_dir)
- L244: def render_markdown(queue)
- L292: def write_text_atomic(path, text)
- L305: def main()

## `scripts/ops/sprint027_validate.py`

- L40: def _safe_yaml_load(path)
- L45: def _sha256_file(path)
- L53: def check_file_exists(root, rel_path)
- L62: def check_yaml_syntax(root)
- L77: def check_missing_hooks(root)
- L99: def check_pipeline_gate(root)
- L128: def check_local_tasks(root)
- L150: def check_release_pack_state(root)
- L164: def _record_evidence(root, report_path)
- L196: def validate_sprint_027(root)
- L217: def main()

## `scripts/ops/sprint028_validate.py`

- L43: def _safe_yaml_load(path)
- L49: def _run(cmd, cwd)
- L56: def check_file_exists(root, rel_path)
- L66: def check_yaml_syntax(root)
- L82: def check_pipeline_gate(root)
- L110: def check_local_tasks(root)
- L132: def check_backlog_item(root)
- L149: def check_dashboard_regressions(root)
- L167: def check_nightly_evidence_interaction(root)
- L279: def _collect_diagnostics(checks)
- L302: def validate(root, run_tests)
- L330: def main()

## `scripts/ops/sprint029_validate.py`

- L17: def _safe_yaml_load(path)
- L22: def check_file_exists(root, rel_path)
- L31: def check_yaml_syntax(root)
- L46: def check_missing_hooks(root)
- L68: def check_pipeline_gate(root)
- L91: def check_local_tasks(root)
- L112: def validate(root)
- L132: def main()

## `scripts/ops/sprint030_validate.py`

- L17: def _safe_yaml_load(path)
- L22: def check_file_exists(root, rel_path)
- L31: def check_yaml_syntax(root)
- L46: def check_missing_hooks(root)
- L68: def check_pipeline_gate(root)
- L91: def check_local_tasks(root)
- L112: def validate(root)
- L132: def main()

## `scripts/ops/sprint031_validate.py`

- L17: def _safe_yaml_load(path)
- L22: def check_file_exists(root, rel_path)
- L31: def check_yaml_syntax(root)
- L46: def check_missing_hooks(root)
- L68: def check_pipeline_gate(root)
- L91: def check_local_tasks(root)
- L112: def validate(root)
- L132: def main()

## `scripts/ops/sprint032_validate.py`

- L17: def _safe_yaml_load(path)
- L22: def check_file_exists(root, rel_path)
- L31: def check_yaml_syntax(root)
- L46: def check_missing_hooks(root)
- L68: def check_pipeline_gate(root)
- L91: def check_local_tasks(root)
- L112: def validate(root)
- L132: def main()

## `scripts/ops/sprint033_validate.py`

- L17: def _safe_yaml_load(path)
- L22: def check_file_exists(root, rel_path)
- L31: def check_yaml_syntax(root)
- L46: def check_missing_hooks(root)
- L68: def check_pipeline_gate(root)
- L91: def check_local_tasks(root)
- L112: def validate(root)
- L132: def main()

## `scripts/ops/sprint034_validate.py`

- L17: def _safe_yaml_load(path)
- L22: def check_file_exists(root, rel_path)
- L31: def check_yaml_syntax(root)
- L46: def check_missing_hooks(root)
- L68: def check_pipeline_gate(root)
- L91: def check_local_tasks(root)
- L112: def validate(root)
- L132: def main()

## `scripts/ops/sprint035_validate.py`

- L17: def _safe_yaml_load(path)
- L22: def check_file_exists(root, rel_path)
- L31: def check_yaml_syntax(root)
- L46: def check_missing_hooks(root)
- L68: def check_pipeline_gate(root)
- L91: def check_local_tasks(root)
- L112: def validate(root)
- L132: def main()

## `scripts/ops/sprint036_validate.py`

- L17: def _safe_yaml_load(path)
- L22: def check_file_exists(root, rel_path)
- L31: def check_yaml_syntax(root)
- L46: def check_missing_hooks(root)
- L68: def check_pipeline_gate(root)
- L91: def check_local_tasks(root)
- L112: def validate(root)
- L132: def main()

## `scripts/ops/sprint037_validate.py`

- L17: def _safe_yaml_load(path)
- L22: def check_file_exists(root, rel_path)
- L31: def check_yaml_syntax(root)
- L46: def check_missing_hooks(root)
- L68: def check_pipeline_gate(root)
- L91: def check_local_tasks(root)
- L112: def validate(root)
- L132: def main()

## `scripts/ops/sprint038_validate.py`

- L17: def _safe_yaml_load(path)
- L22: def check_file_exists(root, rel_path)
- L31: def check_yaml_syntax(root)
- L46: def check_missing_hooks(root)
- L68: def check_pipeline_gate(root)
- L91: def check_local_tasks(root)
- L112: def validate(root)
- L132: def main()

## `scripts/ops/sprint039_validate.py`

- L34: def _config()
- L50: def validate(root)
- L54: def main()

## `scripts/ops/sprint040_validate.py`

- L34: def _config()
- L50: def validate(root)
- L54: def main()

## `scripts/ops/sprint041_validate.py`

- L47: def _run(cmd, cwd)
- L53: def _quality_check(root, run_tests)
- L77: def _config()
- L94: def validate(root, run_tests)
- L98: def main()

## `scripts/ops/sprint042_validate.py`

- L40: def _safe_yaml_load(path)
- L45: def _run(cmd, cwd)
- L51: def check_file_exists(root, rel_path)
- L60: def check_yaml_syntax(root)
- L75: def check_missing_hooks(root)
- L97: def check_pipeline_gate(root)
- L120: def check_local_tasks(root)
- L141: def check_quality_regression_tests(root)
- L158: def _collect_diagnostics(checks)
- L179: def validate(root, run_tests)
- L204: def main()

## `scripts/ops/sprint043_validate.py`

- L40: def _safe_yaml_load(path)
- L45: def _run(cmd, cwd)
- L51: def check_file_exists(root, rel_path)
- L60: def check_yaml_syntax(root)
- L75: def check_missing_hooks(root)
- L111: def check_pipeline_gate(root)
- L134: def check_local_tasks(root)
- L155: def check_quality_regression_tests(root)
- L172: def _collect_diagnostics(checks)
- L193: def validate(root, run_tests)
- L218: def main()

## `scripts/ops/sprint044_validate.py`

- L42: def _safe_yaml_load(path)
- L47: def _run(cmd, cwd)
- L53: def check_file_exists(root, rel_path)
- L62: def check_yaml_syntax(root)
- L77: def check_missing_hooks(root)
- L113: def check_pipeline_gate(root)
- L136: def check_local_tasks(root)
- L157: def check_quality_regression_tests(root)
- L174: def _collect_diagnostics(checks)
- L195: def validate(root, run_tests)
- L220: def main()

## `scripts/ops/sprint045_validate.py`

- L45: def _safe_yaml_load(path)
- L50: def _run(cmd, cwd)
- L56: def check_file_exists(root, rel_path)
- L65: def check_yaml_syntax(root)
- L80: def check_missing_hooks(root)
- L102: def check_pipeline_gate(root)
- L125: def check_local_tasks(root)
- L147: def check_quality_regression_tests(root)
- L164: def _collect_diagnostics(checks)
- L185: def validate(root, run_tests)
- L210: def main()

## `scripts/ops/sprint046_validate.py`

- L45: def _safe_yaml_load(path)
- L50: def _run(cmd, cwd)
- L56: def check_file_exists(root, rel_path)
- L65: def check_yaml_syntax(root)
- L80: def check_missing_hooks(root)
- L102: def check_pipeline_gate(root)
- L125: def check_local_tasks(root)
- L147: def check_quality_regression_tests(root)
- L164: def _collect_diagnostics(checks)
- L185: def validate(root, run_tests)
- L210: def main()

## `scripts/ops/sprint047_validate.py`

- L45: def _safe_yaml_load(path)
- L50: def _run(cmd, cwd)
- L56: def check_file_exists(root, rel_path)
- L65: def check_yaml_syntax(root)
- L80: def check_missing_hooks(root)
- L102: def check_pipeline_gate(root)
- L125: def check_local_tasks(root)
- L147: def check_quality_regression_tests(root)
- L164: def _collect_diagnostics(checks)
- L185: def validate(root, run_tests)
- L210: def main()

## `scripts/ops/sprint048_validate.py`

- L46: def _safe_yaml_load(path)
- L51: def _run(cmd, cwd)
- L57: def check_file_exists(root, rel_path)
- L66: def check_yaml_syntax(root)
- L81: def check_missing_hooks(root)
- L103: def check_pipeline_gate(root)
- L126: def check_local_tasks(root)
- L149: def check_quality_regression_tests(root)
- L166: def _collect_diagnostics(checks)
- L187: def validate(root, run_tests)
- L212: def main()

## `scripts/ops/sprint049_validate.py`

- L46: def _safe_yaml_load(path)
- L51: def _run(cmd, cwd)
- L57: def check_file_exists(root, rel_path)
- L66: def check_yaml_syntax(root)
- L81: def check_missing_hooks(root)
- L103: def check_pipeline_gate(root)
- L126: def check_local_tasks(root)
- L149: def check_quality_regression_tests(root)
- L166: def _collect_diagnostics(checks)
- L187: def validate(root, run_tests)
- L212: def main()

## `scripts/ops/sprint050_validate.py`

- L46: def _safe_yaml_load(path)
- L51: def _run(cmd, cwd)
- L57: def check_file_exists(root, rel_path)
- L66: def check_yaml_syntax(root)
- L81: def check_missing_hooks(root)
- L103: def check_pipeline_gate(root)
- L126: def check_local_tasks(root)
- L149: def check_quality_regression_tests(root)
- L166: def _collect_diagnostics(checks)
- L187: def validate(root, run_tests)
- L212: def main()

## `scripts/ops/sprint051_validate.py`

- L46: def _safe_yaml_load(path)
- L51: def _run(cmd, cwd)
- L57: def check_file_exists(root, rel_path)
- L66: def check_yaml_syntax(root)
- L81: def check_missing_hooks(root)
- L103: def check_pipeline_gate(root)
- L126: def check_local_tasks(root)
- L149: def check_quality_regression_tests(root)
- L166: def _collect_diagnostics(checks)
- L187: def validate(root, run_tests)
- L212: def main()

## `scripts/ops/sprint052_validate.py`

- L47: def _safe_yaml_load(path)
- L52: def _run(cmd, cwd)
- L58: def check_file_exists(root, rel_path)
- L67: def check_yaml_syntax(root)
- L82: def check_missing_hooks(root)
- L104: def check_pipeline_gate(root)
- L127: def check_local_tasks(root)
- L151: def check_state_evidence_alignment(root)
- L204: def check_quality_regression_tests(root)
- L221: def _collect_diagnostics(checks)
- L243: def validate(root, run_tests)
- L269: def main()

## `scripts/ops/sprint053_validate.py`

- L47: def _safe_yaml_load(path)
- L52: def _run(cmd, cwd)
- L58: def check_file_exists(root, rel_path)
- L67: def check_yaml_syntax(root)
- L82: def check_missing_hooks(root)
- L104: def check_pipeline_gate(root)
- L127: def check_local_tasks(root)
- L151: def check_state_evidence_alignment(root)
- L204: def check_quality_regression_tests(root)
- L221: def _collect_diagnostics(checks)
- L243: def validate(root, run_tests)
- L269: def main()

## `scripts/ops/sprint054_validate.py`

- L48: def _safe_yaml_load(path)
- L53: def _run(cmd, cwd)
- L59: def check_file_exists(root, rel_path)
- L68: def check_yaml_syntax(root)
- L83: def check_missing_hooks(root)
- L105: def check_pipeline_gate(root)
- L131: def check_local_tasks(root)
- L156: def check_state_evidence_alignment(root)
- L209: def check_quality_regression_tests(root)
- L226: def _collect_diagnostics(checks)
- L248: def validate(root, run_tests)
- L274: def main()

## `scripts/ops/sprint055_validate.py`

- L48: def _safe_yaml_load(path)
- L53: def _run(cmd, cwd)
- L59: def check_file_exists(root, rel_path)
- L68: def check_yaml_syntax(root)
- L83: def check_missing_hooks(root)
- L105: def check_pipeline_gate(root)
- L131: def check_local_tasks(root)
- L156: def check_state_evidence_alignment(root)
- L209: def check_quality_regression_tests(root)
- L226: def _collect_diagnostics(checks)
- L248: def validate(root, run_tests)
- L274: def main()

## `scripts/ops/sprint056_validate.py`

- L48: def _safe_yaml_load(path)
- L53: def _run(cmd, cwd)
- L59: def check_file_exists(root, rel_path)
- L68: def check_yaml_syntax(root)
- L83: def check_missing_hooks(root)
- L105: def check_pipeline_gate(root)
- L131: def check_local_tasks(root)
- L156: def check_state_evidence_alignment(root)
- L209: def check_quality_regression_tests(root)
- L226: def _collect_diagnostics(checks)
- L248: def validate(root, run_tests)
- L274: def main()

## `scripts/ops/sprint057_validate.py`

- L48: def _safe_yaml_load(path)
- L53: def _run(cmd, cwd)
- L59: def check_file_exists(root, rel_path)
- L68: def check_yaml_syntax(root)
- L83: def check_missing_hooks(root)
- L105: def check_pipeline_gate(root)
- L131: def check_local_tasks(root)
- L156: def check_state_evidence_alignment(root)
- L209: def check_quality_regression_tests(root)
- L226: def _collect_diagnostics(checks)
- L248: def validate(root, run_tests)
- L274: def main()

## `scripts/ops/sprint058_validate.py`

- L48: def _safe_yaml_load(path)
- L53: def _run(cmd, cwd)
- L59: def check_file_exists(root, rel_path)
- L68: def check_yaml_syntax(root)
- L83: def check_missing_hooks(root)
- L106: def check_pipeline_gate(root)
- L133: def check_local_tasks(root)
- L158: def check_state_evidence_alignment(root)
- L211: def check_quality_regression_tests(root)
- L228: def _collect_diagnostics(checks)
- L250: def validate(root, run_tests)
- L276: def main()

## `scripts/ops/sprint059_validate.py`

- L48: def _safe_yaml_load(path)
- L53: def _run(cmd, cwd)
- L59: def check_file_exists(root, rel_path)
- L68: def check_yaml_syntax(root)
- L83: def check_missing_hooks(root)
- L106: def check_pipeline_gate(root)
- L133: def check_local_tasks(root)
- L158: def check_state_evidence_alignment(root)
- L211: def check_quality_regression_tests(root)
- L228: def _collect_diagnostics(checks)
- L250: def validate(root, run_tests)
- L276: def main()

## `scripts/ops/sprint060_validate.py`

- L48: def _safe_yaml_load(path)
- L53: def _run(cmd, cwd)
- L59: def check_file_exists(root, rel_path)
- L68: def check_yaml_syntax(root)
- L83: def check_missing_hooks(root)
- L106: def check_pipeline_gate(root)
- L133: def check_local_tasks(root)
- L158: def check_state_evidence_alignment(root)
- L211: def check_quality_regression_tests(root)
- L228: def _collect_diagnostics(checks)
- L250: def validate(root, run_tests)
- L276: def main()

## `scripts/ops/sprint061_validate.py`

- L48: def _safe_yaml_load(path)
- L53: def _run(cmd, cwd)
- L59: def check_file_exists(root, rel_path)
- L68: def check_yaml_syntax(root)
- L83: def check_missing_hooks(root)
- L106: def check_pipeline_gate(root)
- L133: def check_local_tasks(root)
- L158: def check_state_evidence_alignment(root)
- L211: def check_quality_regression_tests(root)
- L228: def _collect_diagnostics(checks)
- L250: def validate(root, run_tests)
- L276: def main()

## `scripts/ops/sprint062_validate.py`

- L48: def _safe_yaml_load(path)
- L53: def _run(cmd, cwd)
- L59: def check_file_exists(root, rel_path)
- L68: def check_yaml_syntax(root)
- L83: def check_missing_hooks(root)
- L106: def check_pipeline_gate(root)
- L133: def check_local_tasks(root)
- L158: def check_state_evidence_alignment(root)
- L211: def check_quality_regression_tests(root)
- L228: def _collect_diagnostics(checks)
- L250: def validate(root, run_tests)
- L276: def main()

## `scripts/ops/sprint063_validate.py`

- L48: def _safe_yaml_load(path)
- L53: def _run(cmd, cwd)
- L59: def check_file_exists(root, rel_path)
- L68: def check_yaml_syntax(root)
- L83: def check_missing_hooks(root)
- L106: def check_pipeline_gate(root)
- L133: def check_local_tasks(root)
- L158: def check_state_evidence_alignment(root)
- L211: def check_quality_regression_tests(root)
- L228: def _collect_diagnostics(checks)
- L250: def validate(root, run_tests)
- L276: def main()

## `scripts/ops/sprint064_validate.py`

- L48: def _safe_yaml_load(path)
- L53: def _run(cmd, cwd)
- L59: def check_file_exists(root, rel_path)
- L68: def check_yaml_syntax(root)
- L83: def check_missing_hooks(root)
- L106: def check_pipeline_gate(root)
- L133: def check_local_tasks(root)
- L158: def check_state_evidence_alignment(root)
- L211: def check_quality_regression_tests(root)
- L228: def _collect_diagnostics(checks)
- L250: def validate(root, run_tests)
- L276: def main()

## `scripts/ops/sprint065_validate.py`

- L48: def _safe_yaml_load(path)
- L53: def _run(cmd, cwd)
- L59: def check_file_exists(root, rel_path)
- L68: def check_yaml_syntax(root)
- L83: def check_missing_hooks(root)
- L106: def check_pipeline_gate(root)
- L133: def check_local_tasks(root)
- L158: def check_state_evidence_alignment(root)
- L211: def check_quality_regression_tests(root)
- L228: def _collect_diagnostics(checks)
- L250: def validate(root, run_tests)
- L276: def main()

## `scripts/ops/sprint066_validate.py`

- L47: def _safe_yaml_load(path)
- L51: def _check_required_files(root)
- L56: def _check_syntax(root)
- L68: def _check_backlog_contract(root)
- L77: def _check_hooks(root)
- L87: def _check_pipeline_gate(root)
- L94: def _check_local_tasks(root)
- L100: def _check_state_evidence_alignment(root)
- L109: def _check_quality(run_tests)
- L126: def build_report(root, run_tests)
- L151: def main()

## `scripts/ops/sprint067_validate.py`

- L48: def _safe_yaml_load(path)
- L52: def _check_required_files(root)
- L61: def _check_syntax(root)
- L73: def _check_backlog_contract(root)
- L82: def _check_hooks(root)
- L96: def _check_pipeline_gate(root)
- L103: def _check_local_tasks(root)
- L109: def _check_plan_scope(root)
- L120: def _check_state_evidence_alignment(root)
- L129: def _check_progress_alignment(root)
- L139: def _check_quality(run_tests)
- L156: def build_report(root, run_tests)
- L183: def main()

## `scripts/ops/sprint068_validate.py`

- L48: def _safe_yaml_load(path)
- L52: def _check_required_files(root)
- L61: def _check_syntax(root)
- L73: def _check_backlog_contract(root)
- L82: def _check_hooks(root)
- L96: def _check_pipeline_gate(root)
- L103: def _check_local_tasks(root)
- L109: def _check_plan_scope(root)
- L120: def _check_state_evidence_alignment(root)
- L129: def _check_progress_alignment(root)
- L144: def _check_quality(run_tests)
- L161: def build_report(root, run_tests)
- L188: def main()

## `scripts/ops/sprint069_validate.py`

- L48: def _safe_yaml_load(path)
- L52: def _check_required_files(root)
- L61: def _check_syntax(root)
- L73: def _check_backlog_contract(root)
- L82: def _check_hooks(root)
- L96: def _check_pipeline_gate(root)
- L103: def _check_local_tasks(root)
- L109: def _check_plan_scope(root)
- L120: def _check_state_evidence_alignment(root)
- L129: def _check_progress_alignment(root)
- L144: def _check_quality(run_tests)
- L161: def build_report(root, run_tests)
- L188: def main()

## `scripts/ops/sprint_state_sync.py`

- L19: def _default_ci_artifacts_dir(root)
- L26: def _now_iso()
- L30: def _load_yaml(path)
- L40: def _save_yaml_atomic(path, payload)
- L56: def _init_state_from_backlog(backlog)
- L86: def _preview_release_counts(backlog_path)
- L96: def synchronize_state(backlog_path, state_path, reason, evidence_dir)
- L182: def main()

## `scripts/ops/sprint_validator_engine.py`

- L18: class SprintValidatorConfig
- L32: def safe_yaml_load(path)
- L37: def check_file_exists(root, rel_path)
- L46: def check_yaml_syntax(root, yaml_files)
- L61: def check_missing_hooks(root, flow_file, required_hooks)
- L83: def check_pipeline_gate(root, pipeline_file, validator_snippet, artifact_snippet)
- L111: def check_local_tasks(root, required_task_labels)
- L126: def collect_diagnostics(checks, critical_checks)
- L137: def build_report(root, config, run_tests)
- L172: def write_json_report(root, json_out, report)

## `scripts/ops/start_local_free_stack.ps1`

- L10: function Test-PortListening
- L15: function Wait-HttpOk

## `scripts/ops/sync-live-targets.py`

- L13: def _is_relative_to(path, root)
- L21: def _resolve_directory(path)
- L31: def _validate_target_name(name)
- L37: def _assert_target_child(target_root, candidate)
- L47: def _assert_relative_child(target_root, candidate)
- L52: def _copy_tree(source, target, target_root)
- L76: def sync_live_targets(source, target)
- L107: def main()

## `scripts/ops/sync-mythibia-client.ps1`

- L66: function Write-OpsLogLine
- L73: function Test-EnvEnabled
- L80: function Assert-UnsafeRuntimeBootstrapApproved
- L86: function Resolve-ClientChildPath
- L104: function Ensure-CriticalScripts
- L132: function Ensure-TrainerEnabled
- L185: function Write-Utf8NoBomFile
- L195: function Get-RuntimeProbeContent
- L234: function Get-RuntimeAutoloadContent
- L295: function Ensure-RuntimeAutoloadDiagnostics
- L361: function Ensure-RuntimeScriptMirrors
- L429: function Ensure-UnsafeRuntimeBootstrap
- L471: function init
- L526: function Remove-UnsafeRuntimeBootstrapArtifacts
- L551: function New-LuaStubContent
- L566: function Ensure-LocalLuaFiles
- L602: function Write-ManifestVsDiskReports

## `scripts/ops/tibia_source_collector.py`

- L40: class SourceDefinition
- L76: class RawSnapshot
- L85: class UpdateEvent
- L96: class FetchResult
- L103: class NewsParseError
- L107: class ParserPendingFixture
- L111: class NewsLinkParser
- L114: def __init__(self, base_url)
- L121: def handle_starttag(self, tag, attrs)
- L132: def handle_data(self, data)
- L136: def handle_endtag(self, tag)
- L146: class SourceParser
- L149: def parse(self, snapshot, body)
- L155: def _parse_news(snapshot, body)
- L184: class SourceCollector
- L187: def __init__(self)
- L196: def fetch(self, source_kind, cursor)
- L230: def from_html_file(self, source_kind, html_file, cursor)
- L250: def archive_snapshot(archive_dir, fetched)
- L341: def _fetch_result(source_kind, url, fetched_at, body, status, fetch_error)
- L363: def _raw_snapshot_dict(snapshot)
- L370: def _build_events()
- L426: def _record_event(source_kind, snapshot_id, detected_at, diff_type, record)
- L446: def _previous_records(index, source_kind)
- L459: def _read_index(archive_dir)
- L472: def _append_ledger(path, events)
- L481: def _atomic_write_json(path, value)
- L488: class _ArchiveLock
- L489: def __init__(self, archive_dir, timeout_seconds)
- L494: def __enter__(self)
- L508: def __exit__(self, exc_type, exc, traceback)
- L513: def _news_entity_id(link)
- L524: def _safe_identifier(value)
- L531: def _record_key(record)
- L535: def _canonical_json(value)
- L539: def _clean_text(value)
- L543: def _looks_blocked(body)
- L548: def _read_limited(response)
- L553: def _bounded_error(error)
- L557: def _freshness_for(status)
- L566: def _next_action_for(status, source_kind, parser_status)
- L578: def _source_definition(source_kind)
- L585: def _validate_source_url(value)
- L591: def _snapshot_id(fetched_at)
- L596: def _utc_now()
- L600: def main()

## `scripts/ops/triage_entropy_carves.py`

- L27: class DecompressResult
- L35: def shannon_entropy(data)
- L50: def printable_ratio(data)
- L57: def detect_magic(data)
- L67: def try_zlib(data)
- L99: def try_lzma(data)
- L119: def try_lz4(data)
- L141: def score_blob(size, entropy, p_ratio, magic_hits, decompress_results, data)
- L174: def triage_blob(path)
- L200: def render_markdown(results, out_md)
- L233: def main()

## `scripts/ops/triage_io_dense_dumps.py`

- L11: def entropy(data)
- L23: def printable_ratio(data)
- L30: def magics(data)
- L39: def decomp_hints(data)

## `scripts/ops/validate_package_boundaries.py`

- L60: def _load_manifest(path)
- L67: def _normalized_paths(values)
- L73: def validate_package_boundaries(core_manifest, pro_manifest, studio_manifest)
- L135: def main()

## `scripts/ops/validate_release_artifact_contract.py`

- L20: def fail(msg)
- L24: def main()

## `scripts/ops/watch-mythibia-client-sync.ps1`

- L29: function Resolve-RepoScriptPath
- L53: function Assert-LogChildPath
- L78: function Write-Log
- L85: function Rotate-LogIfNeeded

## `scripts/ops/wave_summary_utf8.py`

- L14: def _now_iso()
- L18: def _load_json(path)
- L27: def _load_yaml(path)
- L35: def _state_release_counts(state, backlog, expected_backlog_id)
- L49: def generate_summary(sprint_id, validation_json, output, repo_hygiene_json, state_yaml, backlog_yaml)
- L91: def main()

## `scripts/ops/windows-task-guard.ps1`

- L3: function Assert-CtoaTaskName
- L16: function Assert-CtoaRunKeyName
- L29: function Assert-CtoaStartTime
- L46: function Resolve-RepoChildPath
- L72: function Resolve-CtoaLogPath
- L100: function Format-CtoaCommandArgument

## `scripts/test_local_model.py`

- L23: def test_health()
- L41: def test_completion(prompt)
- L68: def main()

## `scripts/windows/install-ctoa-vscode-extensions.ps1`

- L10: function Assert-ChildPath

## `scripts/windows/open-control-center.ps1`

- L8: function Resolve-ControlCenterUrl

## `scripts/windows/solteria_helper_test_env.ps1`

- L22: function Get-RepoRoot
- L25: function Get-CtoaHelperBootGraphSource
- L40: function Test-CtoaHelperBootGraphModule
- L51: function Assert-UnderLocalAppData
- L68: function Assert-SandboxClientPath
- L85: function New-DirectoryJunction
- L96: function New-FileHardlink
- L118: function Copy-FreshFile
- L139: function Copy-IfExists
- L149: function Write-JsonAtomic
- L177: function Write-TextAtomic
- L204: function Write-TestPrefs
- L230: function Write-SmokeCommand
- L252: function Sync-CtoaRuntimeFiles
- L259: function Copy-CtoaRuntimeFile
- L341: function Ensure-CtoaBootHook
- L422: function Get-HelperVersion
- L432: function Get-LiveClientSummary
- L454: function Get-SourceClientProcessSummaries
- L485: function Start-LiveClientAfterPromotion
- L513: function Get-DevPackageFiles
- L571: function Get-LiveRootFallbackFiles
- L577: function Get-DevFileManifest
- L595: function Write-DevChangelog
- L653: function Write-ReleaseReadinessReport
- L697: function Write-DevValidationReport
- L717: function New-DevPackage
- L822: function Invoke-DevValidation
- L877: function Resolve-SmokeTab
- L904: function Initialize-Sandbox
- L952: function Invoke-SmokePreflight
- L1033: function Start-SandboxClient
- L1042: function Get-SandboxProcesses
- L1059: function Get-SandboxProcessSummaries
- L1106: function Stop-SandboxClient
- L1119: function Set-LiveCtoaEnabled
- L1223: function Set-LiveCtoaUiOnly
- L1321: function New-LiveCtoaBackup
- L1366: function Assert-LiveDeployApproved
- L1372: function Assert-ReleaseGateForLivePromotion
- L1388: function Assert-LivePromotionMatchesStage
- L1415: function Invoke-LivePromotion
- L1496: function Invoke-LiveEmergencyRepair
- L1559: function Capture-Screenshot
- L1616: function Wait-ForSmokeTab
- L1655: function Get-SmokeLogLineCount
- L1663: function Test-AtCharacterSelect
- L1672: function Invoke-SmokeStatus
- L1750: function Invoke-HealFriendNoTargetSmoke
- L1806: function Invoke-ConditionsObserverSmoke
- L1865: function Invoke-EquipmentObserverSmoke
- L1925: function Invoke-ScriptingPolicySmoke
- L1985: function Invoke-PlannerStaticSmoke
- L2035: function Invoke-RuntimePolicyStaticSmoke
- L2088: function Invoke-DispatchGuardStaticSmoke
- L2138: function Invoke-PlanQueueStaticSmoke
- L2188: function Invoke-RuntimeReadinessStaticSmoke
- L2239: function Invoke-ModuleStatusStaticSmoke
- L2290: function Invoke-ActionCatalogStaticSmoke
- L2344: function Invoke-DecisionTraceStaticSmoke
- L2396: function Invoke-SandboxHandoffStaticSmoke
- L2447: function Invoke-FeatureFlagsStaticSmoke
- L2505: function Invoke-HudStaticSmoke
- L2560: function Invoke-HotkeysStaticSmoke
- L2614: function Invoke-ModalStaticSmoke
- L2670: function Invoke-InputContractsStaticSmoke
- L2692: function Invoke-RouteStaticSmoke
- L2747: function Invoke-TargetingStaticSmoke
- L2804: function Invoke-CombatRuntimeStaticSmoke
- L2860: function Invoke-CavebotRuntimeStaticSmoke
- L2916: function Invoke-LootRuntimeStaticSmoke
- L2974: function Invoke-TimerRuntimeStaticSmoke
- L3030: function Invoke-RecoveryRuntimeStaticSmoke
- L3083: function Invoke-HealingVitalsSmoke
- L3150: function Invoke-CombatSafetySmoke
- L3181: function Get-ReportCheckStatus
- L3236: function Invoke-CavebotSafetySmoke
- L3266: function Test-CavebotStaticReport
- L3322: function Invoke-LootSafetySmoke
- L3349: function Test-LootReport
- ... 25 more symbols omitted

## `tests/conftest.py`

- L15: def project_root()
- L21: def config_path()
- L27: def sample_env()
- L37: def pytest_configure(config)
- L51: def pytest_collection_modifyitems(config, items)

## `tests/e2e/test_bot_live.py`

- L8: def _make_frame(w, h)
- L19: class TestBotE2EHeadless
- L22: def setUpClass(cls)
- L39: def test_no_errors(self)
- L42: def test_all_ticks_produced_action(self)
- L45: def test_actions_are_strings(self)
- L49: def test_state_has_hp_mp(self)
- L55: def test_not_all_idle(self)
- L59: class TestOTSConfig
- L61: def _reset(self)
- L69: def test_defaults(self)
- L75: def test_env_override(self)
- L85: def test_summary_not_configured(self)
- L90: class TestWindowModule
- L92: def test_find_returns_none_or_handle(self)
- L98: def test_capture_without_mss_returns_none(self)

## `tests/e2e/test_browser_smoke.py`

- L23: def test_browser_smoke_login_settings_ideas()
- L115: def test_browser_smoke_operator_owner_only_block()
- L208: def test_browser_smoke_operator_ideas_allowed_settings_denied()
- L306: def _free_port()
- L312: def _start_process(cmd, cwd, env)
- L323: def _wait_for_http(url, timeout_s)
- L338: def _stop_process(proc)

## `tests/integration/bot/test_bot_loop.py`

- L21: def _make_fake_pixels()
- L32: class TestParseGameState
- L33: def test_returns_gamestate_no_pixels(self)
- L40: def test_carries_over_level_from_prev(self)
- L48: def test_returns_gamestate_with_fake_pixels(self)
- L56: def test_no_crash_on_tiny_frame(self)
- L69: class TestActionRegistry
- L70: def test_select_target_in_map(self)
- L74: def test_follow_route_in_map(self)
- L78: def test_core_actions_present(self)
- L88: class TestMLFallback
- L89: def test_brain_falls_back_to_rules_on_ml_error(self)
- L106: def test_brain_returns_valid_action_healthy_state(self)
- L115: def test_brain_heals_on_low_hp(self)
- L128: class TestTickLoop
- L131: def _run_loop(self, n)
- L149: def test_loop_runs_n_ticks(self)
- L153: def test_loop_actions_are_valid_strings(self)
- L158: def test_loop_no_unhandled_exceptions(self)
- L167: class TestHumanizerWired
- L168: def test_combat_pause_called_during_attack(self)
- L187: class TestTelemetryInTick
- L188: def test_log_loot_does_not_raise(self)
- L195: def test_get_stats_returns_dict(self)
- L205: class TestDashboard
- L206: def _client(self)
- L214: def test_stats_endpoint(self)
- L221: def test_metrics_endpoint(self)
- L226: def test_health_endpoint(self)
- L231: def test_index_returns_html(self)

## `tests/integration/bot/test_stress.py`

- L23: class TestStressTickLoop
- L27: def setUpClass(cls)
- L97: def tearDownClass(cls)
- L114: def test_zero_errors(self)
- L118: def test_all_actions_recorded(self)
- L121: def test_actions_are_valid_strings(self)
- L129: def test_completes_in_time(self)
- L134: def test_avg_latency_under_10ms(self)
- L139: def test_p99_latency_under_50ms(self)
- L144: def test_throughput_above_100_ticks_per_sec(self)
- L151: def test_action_diversity(self)
- L158: def test_idle_not_only_action(self)
- L164: class TestStressGameData
- L167: def test_total_routes_count(self)
- L172: def test_fibula_routes_present(self)
- L179: def test_mintwallin_routes_present(self)
- L185: def test_level_routing_fibula_l1(self)
- L192: def test_level_routing_mintwallin(self)
- L197: def test_total_monsters_count(self)
- L201: def test_new_monsters_present(self)
- L207: def test_monsters_for_level_60(self)

## `tests/legacy/test_agents_all.py`

- L7: def main()

## `tests/legacy/test_local.py`

- L47: def test_components()
- L96: async def test_screenshot_capture(duration_sec)
- L139: async def test_command_execution()
- L171: async def run_autonomous(duration_sec, use_llm, location)
- L229: async def run_interactive()
- L257: def main()

## `tests/test_agent_framework.py`

- L16: class TestAgentDefinitions
- L19: def test_agent_count(self)
- L28: def test_agent_properties(self)
- L44: def test_task_assignments(self)
- L52: def test_tool_weights_sum(self)
- L66: def test_registry_consistency_validator(self)
- L74: class TestBraverTemplates
- L77: def test_template_components(self)
- L89: def test_template_types(self)
- L96: def test_template_rendering(self)
- L115: def test_template_missing_variables_are_explicit_unknowns(self)
- L130: class TestToolAdvisor
- L133: def test_tool_count(self)
- L140: def test_tool_properties(self)
- L163: def test_tool_scoring(self)
- L175: def test_operational_prompt_prefers_evidence_backed_scoring(self)
- L193: def test_tool_ranking(self)

## `tests/test_agent_http_security.py`

- L29: def test_require_http_url_rejects_non_http_urls(url)
- L35: def test_require_http_url_allows_http_urls(url)
- L60: def test_require_public_discovery_url_rejects_ssrf_and_secret_urls(url)
- L75: def test_require_public_discovery_url_allows_public_discovery_targets(url)
- L81: def test_discovery_agents_use_public_discovery_url_guard()
- L110: def test_require_github_api_url_rejects_unsafe_urls(url)
- L124: def test_require_github_api_url_allows_repo_api_urls(url)
- L144: def test_require_github_repository_rejects_unsafe_repo_ids(repo)
- L157: def test_require_github_repository_allows_owner_repo_ids(repo)
- L161: def test_token_bearing_github_callers_validate_repository_ids()
- L189: def test_require_loopback_http_url_rejects_unsafe_urls(url)
- L203: def test_require_loopback_http_url_allows_local_urls(url)
- L218: def test_require_model_backend_url_rejects_unsafe_defaults(url)
- L231: def test_require_model_backend_url_allows_local_backends(url)
- L235: def test_require_model_backend_url_allows_remote_only_with_https_opt_in()
- L257: def test_require_azure_service_url_rejects_unsafe_urls(url)
- L270: def test_require_azure_service_url_allows_azure_hosts(url)
- L290: def test_require_notify_webhook_url_rejects_unsafe_urls(url)
- L304: def test_require_notify_webhook_url_allows_slack_and_discord(url)
- L324: def test_require_discord_webhook_url_rejects_unsafe_urls(url)
- L336: def test_require_discord_webhook_url_allows_discord_hosts(url)
- L340: def test_discovery_ssl_context_verifies_tls_by_default(monkeypatch)
- L351: def test_discovery_ssl_context_requires_explicit_insecure_opt_in(monkeypatch)

## `tests/test_api_auth_hardening.py`

- L13: def _reload_api_module(monkeypatch, tmp_path)
- L62: def test_bootstrap_owner_only_once(monkeypatch, tmp_path)
- L84: def test_bootstrap_rejects_missing_or_invalid_code(monkeypatch, tmp_path)
- L102: def test_seed_accounts_disabled_by_default(monkeypatch, tmp_path)
- L117: def test_seed_accounts_can_be_explicitly_enabled(monkeypatch, tmp_path)
- L129: def test_public_register_cannot_create_privileged_user_without_owner(monkeypatch, tmp_path)
- L162: def test_prod_rejects_wildcard_cors(monkeypatch, tmp_path)
- L173: def test_prod_rejects_missing_or_weak_jwt_secret(monkeypatch, tmp_path)
- L193: def test_non_prod_generates_ephemeral_jwt_when_missing(monkeypatch, tmp_path)

## `tests/test_api_auth_registration_security.py`

- L15: def _load_api(monkeypatch, tmp_path)
- L57: def _write_auth_store(module, path, users)
- L62: def test_api_rejects_production_self_register_enabled_without_code(tmp_path)
- L84: def test_api_self_register_is_disabled_by_default_in_production(monkeypatch, tmp_path)
- L99: def test_api_self_register_requires_matching_code_in_production(monkeypatch, tmp_path)
- L125: def test_api_public_register_cannot_create_owner_when_auth_store_is_empty(monkeypatch, tmp_path)
- L139: def test_api_auth_store_rejects_oversized_existing_file(monkeypatch, tmp_path)
- L154: def test_api_auth_store_rejects_symlinked_existing_file(monkeypatch, tmp_path)
- L171: def test_api_owner_token_can_create_privileged_account(monkeypatch, tmp_path)
- L197: def test_api_http_audit_redacts_spoofed_header_secrets(monkeypatch, tmp_path)
- L237: def test_api_rate_limit_ignores_x_forwarded_for_without_proxy_trust(monkeypatch, tmp_path)
- L261: def test_api_rate_limit_uses_x_forwarded_for_only_with_proxy_trust(monkeypatch, tmp_path)

## `tests/test_api_chat_safety.py`

- L22: class TestSanitizeAssistantContent
- L23: def test_clean_content_is_unchanged(self)
- L27: def test_create_user_claim_is_blocked(self)
- L33: def test_set_password_claim_is_blocked(self)
- L38: def test_grant_permissions_claim_is_blocked(self)
- L43: def test_self_terminate_claim_is_blocked(self)
- L48: def test_wylaczam_sie_claim_is_blocked(self)
- L53: def test_jestem_juz_wylaczony_claim_is_blocked(self)
- L58: def test_utworzylem_uzytkownika_claim_is_blocked(self)
- L63: def test_i_have_created_claim_is_blocked(self)
- L68: def test_i_have_terminated_claim_is_blocked(self)
- L73: def test_case_insensitive_matching(self)
- L78: def test_normal_technical_response_passes(self)
- L91: class TestFriendlyModelError
- L92: def _http_status_error(self, status_code)
- L101: def test_rate_limit_429_returns_503(self)
- L108: def test_server_error_500_returns_503(self)
- L114: def test_bad_gateway_502_http_returns_502(self)
- L120: def test_timeout_returns_503(self)
- L126: def test_connect_error_returns_503(self)
- L132: def test_generic_exception_returns_502(self)
- L146: def _make_chat_req(content)
- L150: def _mock_execute_chat(result_content)
- L151: async def _inner(req)
- L172: class TestChatEndpointSafetyIntegration
- L173: def test_chat_endpoint_sanitizes_fabricated_admin_action(self)
- L188: def test_chat_endpoint_passes_normal_content(self)
- L201: def test_chat_debug_route_requires_operator_identity(self)
- L216: def test_chat_debug_route_rejects_member_role(self)
- L234: def test_chat_debug_route_returns_sanitized_route_for_operator(self)
- L257: def test_openai_chat_debug_route_returns_sanitized_route_for_operator(self)
- L280: def test_router_log_uses_sanitized_route_without_backend_urls(self, capsys)
- L281: async def _ok(_model, _url, _key, _msgs, _temp, _max)
- L319: class TestModelErrorNoLeak
- L320: def test_rate_limit_error_yields_503_no_raw_detail(self)
- L331: async def _fail(_model, _url, _key, _msgs, _temp, _max)
- L345: def test_generic_model_exception_yields_502_no_raw_detail(self)
- L348: async def _fail(_model, _url, _key, _msgs, _temp, _max)
- L362: class TestSafetyTelemetryAndStatus
- L363: def test_snapshot_helper_alert_inactive_below_threshold(self)
- L379: def test_snapshot_helper_alert_active_at_threshold(self)
- L392: def test_status_includes_safety_block(self)
- L409: def test_safety_telemetry_auth_and_owner_access(self)

## `tests/test_api_cost_optimizer_agent.py`

- L10: def test_api_cost_optimizer_registered()
- L23: def test_api_cost_optimizer_facade_risk_scores()
- L34: def test_api_cost_optimizer_braver_template_registered()

## `tests/test_api_cost_report.py`

- L11: def _load_module()
- L20: def test_api_cost_report_handles_missing_runs_dir(tmp_path)
- L32: def test_api_cost_report_reads_jsonl_usage_and_cost(tmp_path)
- L78: def test_api_cost_report_uses_explicit_pricing_json(tmp_path)
- L108: def test_api_cost_report_includes_eval_artifact_summary(tmp_path)
- L151: def test_api_cost_report_uses_configured_defaults(tmp_path, monkeypatch)
- L171: def test_api_cost_report_uses_md_path_alias(tmp_path, monkeypatch)

## `tests/test_atomic_state_writes_security.py`

- L9: def test_api_auth_store_atomic_write_uses_unique_hidden_temp_paths(tmp_path)
- L21: def test_api_auth_store_source_rejects_predictable_suffix_temp()
- L29: def test_runner_state_atomic_writes_use_unique_hidden_temp_paths(tmp_path)
- L44: def test_runner_state_source_rejects_predictable_suffix_temp()

## `tests/test_azure_activity_alerts.py`

- L7: def _load_module()
- L16: def test_parse_records_payload_supports_log_analytics_tables()
- L35: def test_normalize_record_picks_expected_fields()
- L56: def test_classify_high_impact_flags_rbac_and_keyvault_as_critical()
- L73: def test_run_pipeline_filters_below_min_severity(tmp_path)
- L112: def test_run_pipeline_routes_critical_alert_to_jsonl(tmp_path)
- L155: def test_post_json_rejects_non_http_webhook_url(monkeypatch)
- L159: def fake_urlopen()
- L170: def test_post_json_uses_validated_http_url(monkeypatch)
- L174: class Response
- L177: def __enter__(self)
- L180: def __exit__(self, exc_type, exc, tb)
- L183: def fake_urlopen(request, timeout)
- L195: def test_post_discord_json_rejects_non_discord_webhook_url(monkeypatch)
- L199: def fake_urlopen()
- L226: def test_post_discord_json_uses_discord_allowlisted_url(monkeypatch)
- L230: class Response
- L233: def __enter__(self)
- L236: def __exit__(self, exc_type, exc, tb)
- L239: def fake_urlopen(request, timeout)
- L252: def test_route_alert_discord_webhook_rejects_generic_fallback_url(tmp_path, monkeypatch)
- L255: def fake_urlopen()

## `tests/test_azure_activity_listener_security.py`

- L18: def _powershell()
- L25: def test_azure_activity_listener_rejects_public_bind_without_ingest_secret()
- L51: def test_azure_alerts_runner_defaults_listener_to_loopback_and_secret_gate()
- L63: def test_azure_alerts_runner_rejects_public_listener_before_start(tmp_path)
- L98: def test_azure_alerts_docs_do_not_recommend_public_listener_without_secret()

## `tests/test_bot_vps_bootstrap_security.py`

- L8: def _script_text()
- L12: def test_bot_vps_bootstrap_does_not_pipe_remote_installers_to_shell()
- L22: def test_bot_vps_bootstrap_requires_root_and_valid_local_user()
- L33: def test_bot_vps_bootstrap_keeps_deploy_dir_under_opt()
- L42: def test_bot_vps_bootstrap_does_not_expose_grafana_by_default()

## `tests/test_bot_vps_deploy_security.py`

- L8: def _script_text()
- L12: def test_bot_vps_deploy_validates_remote_user_host_and_dir()
- L26: def test_bot_vps_deploy_uses_ssh_end_of_options_and_quoted_remote_path()
- L35: def test_bot_vps_deploy_uses_guarded_rsync_and_scp_targets()
- L45: def test_bot_vps_deploy_remote_block_receives_deploy_dir_as_argument()

## `tests/test_control_center_p6_plugin_handoff_smoke.py`

- L12: def load_module()
- L22: def write_json(path, payload)
- L27: def write_ready_fixture(root, plugin_root)
- L144: def test_p6_plugin_handoff_smoke_reports_ready(tmp_path)
- L177: def test_p6_plugin_handoff_smoke_blocks_version_mismatch(tmp_path)
- L192: def test_p6_plugin_handoff_smoke_blocks_missing_cache(tmp_path)
- L211: def test_p6_plugin_handoff_smoke_blocks_relative_mcp_script_path(tmp_path)
- L228: def test_p6_plugin_handoff_smoke_rejects_symlinked_p6_readiness(tmp_path)

## `tests/test_control_center_p7_cockpit_smoke.py`

- L12: def load_module()
- L20: def write_json(path, payload)
- L25: def write_ready_fixture(root)
- L162: def test_p7_cockpit_smoke_reports_ready(tmp_path)
- L180: def test_p7_cockpit_smoke_blocks_missing_safe_write_audit(tmp_path)
- L200: def test_p7_cockpit_smoke_blocks_forbidden_plugin_tool(tmp_path)
- L214: def test_p7_cockpit_smoke_rejects_symlinked_operator_brief(tmp_path)

## `tests/test_control_center_p7_evidence_review.py`

- L10: def load_module()
- L18: def write_json(path, payload)
- L23: def write_ready_fixture(root)
- L134: def test_p7_evidence_review_reports_ready(tmp_path)
- L148: def test_p7_evidence_review_blocks_without_confirmed_audit(tmp_path)
- L167: def test_p7_evidence_review_accepts_design_next_operator_brief(tmp_path)

## `tests/test_control_center_p7_safe_write_dry_run_smoke.py`

- L11: def load_module()
- L21: def write_fake_plugin(plugin_root)
- L134: def test_safe_write_dry_run_smoke_reports_ready(tmp_path)
- L161: def test_safe_write_dry_run_smoke_finalizes_self_bootstrap_preflight(tmp_path)
- L184: def test_safe_write_dry_run_smoke_blocks_forbidden_tool(tmp_path)

## `tests/test_copilot_instructions.py`

- L8: class TestCopilotInstructions
- L10: def setUpClass(cls)
- L13: def test_azure_activity_log_guidance_is_present(self)
- L20: def test_brave_r_components_are_canonical(self)
- L30: def test_architecture_defaults_section_is_present(self)
- L36: def test_ci_and_core_integrity_section_references_guard(self)
- L41: def test_canonical_commands_section_references_tasks_json(self)
- L46: def test_coding_conventions_references_status_flow(self)
- L52: def test_link_do_not_embed_lists_canonical_docs(self)
- L64: def test_linked_canonical_docs_exist_on_disk(self)

## `tests/test_ctoa_env_doctor.py`

- L6: def test_doctor_reports_fail_when_git_missing(monkeypatch)
- L16: def test_doctor_reports_ok_when_checks_pass(monkeypatch)
- L17: def fake_run_git(args)

## `tests/test_ctoa_full_workspace_audit.py`

- L8: def test_full_workspace_audit_categories_keep_git_vendor_and_secrets_visible()
- L25: def test_three_development_plans_render_expected_plan_names()
- L45: def test_full_workspace_audit_markdown_reports_integrity_gate_without_stale_pass_claims()
- L95: def test_full_workspace_audit_markdown_reports_validation_evidence_gate()
- L183: def test_full_workspace_audit_does_not_follow_symlinked_files(tmp_path, monkeypatch)

## `tests/test_ctoa_helper_combat_observer.py`

- L13: def test_combat_observer_is_loader_wired_and_passive()
- L39: def test_combat_observer_normalization_and_disabled_attach_with_real_lua(tmp_path)

## `tests/test_ctoa_helper_decision_pipeline.py`

- L13: def test_decision_pipeline_is_packaged_dependency_ordered_and_passive()
- L49: def test_full_decision_pipeline_with_real_lua(tmp_path)
- L140: def test_boot_phase_and_dependency_status_with_real_lua(tmp_path)
- L176: def test_engine_panel_exposes_boot_pipeline_and_blocker_status()

## `tests/test_ctoa_helper_domain_contract.py`

- L12: def test_domain_contract_covers_all_helper_lanes_with_passive_envelopes()
- L53: def test_domain_contract_is_in_boot_graph_and_official_package()
- L63: def test_planner_normalizes_domain_edges_without_enabling_dispatch()
- L80: def test_timer_uses_the_canonical_catalog_action_name()
- L91: def test_combat_and_loot_use_canonical_catalog_actions()
- L107: def test_domain_protocol_and_planner_boundary_with_real_lua(tmp_path)

## `tests/test_ctoa_helper_magic_shooter_direction.py`

- L13: def test_exori_min_selects_best_facing_and_beats_exori_for_two_aligned_mobs(tmp_path)
- L56: def test_magic_shooter_turns_before_directional_cast()

## `tests/test_ctoa_helper_otclient_observation_adapter.py`

- L16: def test_otclient_observation_adapter_is_read_only_and_loader_wired()
- L40: def test_otclient_adapter_reads_mocked_state_and_attaches_disabled_task(tmp_path)

## `tests/test_ctoa_helper_profile_migration.py`

- L13: def test_profile_version_is_preserved_across_build_load_and_export()
- L27: def test_versioned_profile_migration_is_safe_and_future_versions_fail_closed(tmp_path)

## `tests/test_ctoa_helper_recovery_jitter.py`

- L10: def test_recovery_jitter_stays_bounded_and_affects_rotation_thresholds(tmp_path)

## `tests/test_ctoa_helper_recovery_observer.py`

- L14: def test_recovery_observer_is_loader_wired_and_passive()
- L31: def test_recovery_observer_normalizes_vitals_and_stays_disabled_with_real_lua(tmp_path)

## `tests/test_ctoa_helper_runtime_core.py`

- L13: def test_runtime_core_is_loader_wired_and_documented()
- L23: def test_runtime_core_exposes_registry_event_bus_and_budgeted_scheduler()
- L49: def test_runtime_core_is_passive_and_safe_by_default()
- L71: def test_runtime_core_is_failure_isolated_and_budget_bounded()
- L82: def test_runtime_core_behavior_with_real_lua(tmp_path)

## `tests/test_ctoa_helper_smoke_report.py`

- L6: def test_expected_views_cover_zerobot_shell()
- L27: def test_collect_report_detects_complete_coverage(tmp_path)
- L40: def test_collect_report_supports_attach_prefix(tmp_path)
- L56: def test_collect_report_reports_missing_views(tmp_path)
- L66: def test_render_markdown_includes_modal_limited_acceptance_note(tmp_path)
- L80: def test_render_markdown_inworld_note(tmp_path)
- L96: def test_render_html_includes_visual_review_cards(tmp_path)
- L110: def test_report_paths_are_browser_friendly(tmp_path)
- L125: def test_render_html_inworld_status(tmp_path)

## `tests/test_ctoa_helper_ui_preview_security.py`

- L4: def test_as_int_evaluates_limited_numeric_expressions()
- L12: def test_as_int_rejects_non_numeric_expressions_without_eval()
- L20: def test_helper_ui_preview_source_does_not_use_eval()

## `tests/test_ctoa_helper_vocation_profiles.py`

- L16: def _run_lua(tmp_path, source)
- L31: def test_vocation_detection_routes_promoted_and_base_vocations(tmp_path)
- L56: def test_shell_renders_detected_vocation_in_profile_hint()
- L61: def test_live_promotion_manifest_includes_vocation_router_and_all_profiles()
- L78: def test_ek_rotation_never_falls_back_to_single_target_in_large_pack(tmp_path)
- L98: def test_ek_stance_selects_attack_for_small_pack_and_defense_for_large_pack(tmp_path)
- L116: def test_targeting_rejects_unreachable_candidate_when_required(tmp_path)
- L130: def test_profile_persistence_exports_modules_vocation_and_real_workdir_path()
- L152: def test_profile_save_path_maps_virtual_resource_to_real_mod_file(tmp_path)
- L169: def test_every_vocation_profile_passes_safe_migration_audit(profile_name)

## `tests/test_ctoa_loader_process_safety.py`

- L9: class _Proc
- L15: def test_sync_with_output_uses_trusted_runner(monkeypatch, tmp_path)
- L20: def fake_run(command)
- L40: def test_open_path_resolves_launcher_before_launch(monkeypatch, tmp_path)
- L43: def fake_resolve(name)
- L47: def fake_run(command)
- L64: def test_resolve_target_dir_rejects_parent_traversal(tmp_path)
- L73: def test_open_target_dir_does_not_launch_parent_traversal(monkeypatch, tmp_path)
- L87: def test_export_manifest_rejects_parent_traversal(tmp_path)
- L99: def test_export_manifest_keeps_normal_export(tmp_path)
- L111: def test_resolve_target_dir_rejects_symlink_escape(tmp_path)
- L127: def test_export_manifest_rejects_symlink_manifest_escape(tmp_path)
- L148: def test_export_manifest_rejects_symlink_output_path(tmp_path)
- L170: def test_list_targets_ignores_unsafe_manifest_symlink(tmp_path)
- L200: def test_resolve_target_dir_keeps_host_slug_lookup(tmp_path)

## `tests/test_ctoa_product_bootstrap.py`

- L13: def test_bootstrap_writes_local_json_and_sqlite_state(tmp_path)
- L50: def _make_file_symlink(link_path, target_path)
- L57: def test_bootstrap_replaces_symlinked_local_json_without_touching_target(tmp_path)
- L80: def test_product_bootstrap_source_uses_atomic_state_writer()

## `tests/test_ctoa_root_action_security.py`

- L8: def _script_text()
- L12: def test_root_action_dashboard_health_uses_private_temp_file()
- L25: def test_root_action_keeps_action_allowlist_and_rejects_unknown_actions()

## `tests/test_ctoa_runtime_remaining_observers.py`

- L20: def test_remaining_observers_are_loader_wired_passive_and_disabled()
- L48: def test_all_five_observers_attach_disabled_and_read_mocked_state_with_real_lua(tmp_path)

## `tests/test_ctoa_runtime_telemetry.py`

- L14: def test_runtime_core_telemetry_is_wired_to_diagnostics_and_reporter()
- L32: def test_runtime_telemetry_reports_disabled_deferred_and_failed_states_with_real_lua(tmp_path)
- L111: def test_runtime_telemetry_remains_read_only()

## `tests/test_ctoa_update_gate.py`

- L9: def test_update_gate_requires_bootstrap_state(tmp_path)
- L15: def test_update_gate_allows_current_bootstrapped_version(tmp_path)
- L27: def test_update_gate_blocks_outdated_version(tmp_path)
- L39: def test_update_gate_rejects_invalid_bootstrap_json_without_echoing_content(tmp_path)
- L55: def test_update_gate_rejects_oversized_bootstrap_state(tmp_path)
- L68: def test_update_gate_rejects_invalid_version_or_schema(tmp_path)
- L82: def test_update_gate_rejects_symlinked_bootstrap_state_before_read(tmp_path)

## `tests/test_desktop_console_url_security.py`

- L18: def test_desktop_api_url_allows_local_http_and_remote_https()
- L36: def test_desktop_api_url_rejects_unsafe_values_without_echoing_secret(raw_url, message)
- L45: def test_desktop_settings_normalizer_drops_unsafe_urls()
- L51: def test_desktop_settings_save_uses_atomic_hidden_temp_paths(tmp_path, monkeypatch)
- L63: def test_desktop_settings_save_replaces_symlink_without_touching_target(tmp_path, monkeypatch)
- L81: def test_desktop_settings_load_rejects_non_object_json(tmp_path, monkeypatch)
- L92: def test_desktop_settings_load_rejects_oversized_json(tmp_path, monkeypatch)
- L108: def test_desktop_settings_load_rejects_symlink_without_reading_target(tmp_path, monkeypatch)
- L124: def test_desktop_settings_source_uses_atomic_hidden_temp_and_fsync()
- L134: def test_desktop_update_asset_selection_rejects_unsafe_names_and_urls()
- L156: def test_desktop_update_download_rejects_unsafe_asset_before_network(tmp_path, monkeypatch)
- L157: def fail_get()
- L177: def test_desktop_update_download_rejects_untrusted_url_before_network(tmp_path, monkeypatch)
- L178: def fail_get()
- L202: def test_desktop_update_download_accepts_signed_github_asset_redirect(tmp_path, monkeypatch)
- L203: class FakeResponse
- L207: def __enter__(self)
- L210: def __exit__(self)
- L213: def raise_for_status(self)
- L216: def iter_content(self, chunk_size)
- L239: def test_desktop_update_download_rejects_untrusted_final_redirect_without_echoing_query(tmp_path, monkeypatch)
- L240: class FakeResponse
- L244: def __enter__(self)
- L247: def __exit__(self)
- L250: def raise_for_status(self)
- L253: def iter_content(self, chunk_size)
- L278: def test_desktop_update_download_rejects_oversized_content_length_before_write(tmp_path, monkeypatch)
- L281: class FakeResponse
- L285: def __enter__(self)
- L288: def __exit__(self)
- L291: def raise_for_status(self)
- L294: def iter_content(self, chunk_size)
- L317: def test_desktop_update_download_removes_partial_temp_file_when_stream_exceeds_limit(tmp_path, monkeypatch)
- L320: class FakeResponse
- L324: def __enter__(self)
- L327: def __exit__(self)
- L330: def raise_for_status(self)
- L333: def iter_content(self, chunk_size)
- L357: def test_desktop_update_download_replaces_final_file_only_after_complete_stream(tmp_path, monkeypatch)
- L361: class FakeResponse
- L365: def __enter__(self)
- L368: def __exit__(self)
- L371: def raise_for_status(self)
- L374: def iter_content(self, chunk_size)
- L397: def test_desktop_update_check_sanitizes_release_notes_url(monkeypatch)
- L398: class FakeResponse
- L399: def raise_for_status(self)
- L402: def json(self)
- L424: def test_desktop_update_repo_must_be_owner_repo()
- L429: def test_desktop_admin_console_is_preset_only()

## `tests/test_docker_bind_defaults.py`

- L9: def test_root_compose_api_binds_to_loopback_by_default()
- L16: def test_bot_infra_compose_binds_dashboard_and_monitoring_to_loopback_by_default()
- L26: def test_env_example_documents_local_bind_controls()

## `tests/test_docs_site_security.py`

- L9: def _site_script()
- L13: def _live_dashboard()
- L17: def test_docs_site_script_avoids_dynamic_html_rendering()
- L26: def test_docs_site_api_base_is_normalized_with_url_guardrails()
- L37: def test_docs_site_does_not_persist_auth_secrets_in_local_storage()
- L47: def test_docs_site_owner_reset_clears_session_scoped_auth_state()
- L60: def test_live_dashboard_avoids_dynamic_html_and_inline_handlers()
- L70: def test_live_dashboard_api_base_is_normalized_with_url_guardrails()
- L82: def test_live_dashboard_keeps_auth_token_session_scoped()
- L91: def test_live_dashboard_uses_dom_render_helpers_for_api_payloads()

## `tests/test_engine_brain_doctor.py`

- L7: def test_parse_docker_ports_flags_broad_binds()
- L16: def test_docker_status_warns_when_daemon_is_unavailable_but_compose_works()
- L20: def test_docker_status_fails_when_compose_is_unavailable()
- L24: def test_render_markdown_summarizes_key_risks()
- L57: def test_run_cmd_resolves_executable_before_launch(monkeypatch)
- L60: class FakeProc
- L65: def fake_resolve(name)
- L69: def fake_run(command)

## `tests/test_engine_brain_index.py`

- L19: def test_release_evidence_summary_exposes_helper_sandbox_queue(tmp_path)
- L68: def test_engine_brain_index_writes_secret_safe_outputs(tmp_path)
- L389: def test_source_needles_check_blocks_missing_contract_markers(tmp_path, monkeypatch)
- L405: def test_p6_installed_plugin_cache_check_matches_local_manifest(tmp_path, monkeypatch)
- L447: def test_p6_plugin_mcp_absolute_script_check_requires_runnable_absolute_arg(tmp_path, monkeypatch)
- L487: def test_p6_plugin_status_script_reports_ready_for_current_workspace()
- L529: def test_p6_plugin_self_check_reports_ready_for_current_workspace()
- L591: def test_p7_operator_brief_reports_next_safe_step()
- L714: def test_p6_control_center_cockpit_script_reports_read_only_status()
- L795: def write_cockpit_preflight_fixture(root)
- L1021: def test_p6_plugin_cockpit_blocks_bootstrap_only_dry_run_smoke(tmp_path)
- L1056: def test_p6_plugin_mcp_server_exposes_expected_tools_and_audited_safe_write(tmp_path)
- L1618: def test_p6_plugin_safe_write_blocks_without_cockpit_preflight(tmp_path)

## `tests/test_engine_brain_pack.py`

- L9: def test_engine_brain_pack_writes_manifest_and_markdown(tmp_path)
- L40: def test_engine_brain_pack_can_include_generated_sections(tmp_path)
- L51: def test_engine_brain_pack_supports_helper_profile(tmp_path)

## `tests/test_evidence_retention_policy.py`

- L6: def _entry(path, recorded_at)
- L15: def test_apply_retention_policy_prunes_by_age_and_count()

## `tests/test_executor_deliverable_security.py`

- L8: def test_write_deliverable_writes_repo_relative_file(tmp_path, monkeypatch)
- L33: def test_write_deliverable_rejects_unsafe_paths_before_write(tmp_path, monkeypatch, path_str)
- L46: def test_write_deliverable_rejects_existing_symlink(tmp_path, monkeypatch)

## `tests/test_generated_manifest_safety.py`

- L15: def _make_dir_symlink(link_path, target_path)
- L22: def test_latest_manifest_path_prefers_safe_run_manifest_over_external_pointer(tmp_path)
- L47: def test_iter_safe_manifest_files_skips_symlinked_run_dir_escape(tmp_path)
- L72: def test_generator_validator_samples_reject_external_manifest_pointer(tmp_path)
- L91: def test_generator_validator_samples_uses_public_manifest_path(tmp_path)
- L111: def test_weekly_report_latency_kpi_rejects_external_manifest_pointer(tmp_path, monkeypatch)

## `tests/test_generator_agent_output_security.py`

- L10: def _patch_db(monkeypatch, executed)
- L13: def fake_query_one(sql, params)
- L33: def _mod(output_file)
- L43: def test_generator_output_file_stays_under_generated_server_dir(tmp_path, monkeypatch)
- L73: def test_generator_rejects_unsafe_output_file_before_write_or_db_update(tmp_path, monkeypatch, output_file)
- L93: def test_generator_rejects_symlinked_server_output_dir_before_write_or_db_update(tmp_path, monkeypatch)
- L118: def test_generator_manifest_rejects_symlinked_latest_file(tmp_path, monkeypatch)
- L145: def test_generator_manifest_rejects_symlinked_manifests_dir(tmp_path, monkeypatch)

## `tests/test_git_exec.py`

- L9: def test_resolve_git_uses_ctoa_git_bin(monkeypatch, tmp_path)
- L18: def test_resolve_git_uses_path(monkeypatch)
- L25: def test_resolve_git_uses_windows_fallback(monkeypatch, tmp_path)
- L38: def test_resolve_git_raises_when_missing(monkeypatch)
- L48: def test_run_git_uses_resolved_binary(monkeypatch)
- L51: def fake_run()

## `tests/test_git_unavailable_guards.py`

- L5: def test_runtime_path_guard_returns_clear_error_when_git_unavailable(monkeypatch, capsys)
- L15: def test_bridge_readiness_returns_clear_error_when_git_unavailable(monkeypatch, capsys)

## `tests/test_gs_api_validator_security.py`

- L8: def _load_module()
- L17: def test_fetch_json_rejects_unsafe_urls_before_urlopen(monkeypatch)
- L21: def fail_urlopen()
- L42: def test_fetch_json_allows_loopback_url(monkeypatch)
- L46: class Response
- L49: def __enter__(self)
- L52: def __exit__(self, exc_type, exc, tb)
- L55: def read(self)
- L58: def fake_urlopen(url, timeout)
- L68: def test_normalize_base_requires_local_origin()
- L90: def test_detect_module_root_rejects_remote_base_before_urlopen(monkeypatch)
- L94: def fail_urlopen()

## `tests/test_gs_reset_security.py`

- L8: def _script_text()
- L12: def test_gs_reset_validates_env_provided_api_urls_before_curl()
- L34: def test_gs_reset_validates_numeric_wait_and_retry_env_values()

## `tests/test_health_metrics_process_safety.py`

- L9: class _Result
- L15: def test_disk_cleanup_uses_resolved_bash(monkeypatch)
- L18: def fake_resolve(name, env_var)
- L22: def fake_run(command)
- L48: def test_health_publish_validates_github_url_before_requests_post(monkeypatch)
- L51: class Response
- L55: def fake_require_github_api_url(url)
- L59: def fake_post(url)
- L85: def test_health_publish_rejects_unsafe_repo_id_before_requests_post(monkeypatch)
- L86: def fail_post()
- L98: def _make_file_symlink(link_path, target_path)
- L105: def test_persist_snapshot_uses_atomic_latest_json_write(monkeypatch, tmp_path)
- L121: def test_persist_snapshot_replaces_latest_symlink_without_touching_target(monkeypatch, tmp_path)

## `tests/test_hybrid_bot.py`

- L33: class TestVisionLayer
- L35: def test_vision_init(self)
- L41: def test_gps_position_type(self)
- L51: def test_health_state_type(self)
- L60: def test_target_info_type(self)
- L79: class TestPathfinding
- L81: def test_coordinate_creation(self)
- L89: def test_pathfinder_init(self)
- L95: def test_pathfinding_basic(self)
- L109: def test_terrain_cost_calculation(self)
- L119: def test_waypoint_buffer(self)
- L143: class TestPromptLogic
- L145: def test_prompt_logic_init(self)
- L151: def test_action_enum(self)
- L160: def test_game_state_creation(self)
- L182: def test_heuristic_decision_flee(self)
- L207: def test_heuristic_decision_heal(self)
- L235: class TestStateManager
- L237: def test_state_manager_init(self)
- L245: def test_player_state_update(self)
- L261: def test_target_update(self)
- L277: def test_location_metrics(self)
- L292: def test_game_state_snapshot(self)
- L309: class TestMetrics
- L311: def test_metrics_collector_init(self)
- L319: def test_record_snapshot(self)
- L339: def test_session_summary(self)
- L373: class TestBotConfig
- L375: def test_bot_config_defaults(self)
- L384: def test_bot_config_custom(self)
- L401: class TestIntegration
- L403: def test_decision_loop_heuristic(self)
- L422: class TestTickLoopCharacterization
- L424: def test_tick_stops_early_when_no_frame(self)
- L437: def test_tick_applies_state_and_executes_decision(self)
- L476: def test_tick_emits_telemetry_every_100_ticks(self)

## `tests/test_hybrid_bot_file_safety.py`

- L10: def _record_sample(collector)
- L21: def test_metrics_export_writes_under_metrics_dir(tmp_path)
- L32: def test_metrics_load_reads_only_under_metrics_dir(tmp_path)
- L64: def test_safe_child_path_rejects_unsafe_metrics_paths(tmp_path, relative_path)
- L73: def test_metrics_export_rejects_unsafe_output_before_write(tmp_path)
- L83: def test_metrics_load_rejects_unsafe_input_before_read(tmp_path)
- L91: def test_profiler_export_rejects_unsafe_filename(tmp_path)
- L101: def test_safe_child_path_rejects_existing_symlink(tmp_path)

## `tests/test_integration_e2e.py`

- L38: class TestHybridBotE2E
- L42: def temp_cache(self)
- L48: def template_library(self, temp_cache)
- L74: def vision_layer(self, temp_cache)
- L80: def state_manager(self)
- L94: def metrics_collector(self, temp_cache)
- L100: def command_executor(self)
- L106: def prompt_logic(self)
- L113: def test_full_loop_healthy_combat(self, vision_layer, state_manager, metrics_collector, command_executor, prompt_logic)
- L190: def test_full_loop_low_health_flee(self, vision_layer, state_manager, metrics_collector, command_executor, prompt_logic)
- L248: def test_full_loop_healing_recovery(self, vision_layer, state_manager, metrics_collector, command_executor, prompt_logic)
- L307: def test_vision_detection_pipeline(self, vision_layer, template_library)
- L330: def test_metrics_collection_complete_session(self, metrics_collector)
- L366: def test_state_snapshot_consistency(self, state_manager)
- L405: def test_command_execution_sequence(self, command_executor)
- L429: def test_decision_priority_cascade(self, prompt_logic, state_manager)
- L465: def _create_mock_screenshot(size)
- L473: def _create_mock_minimap(size)
- L481: class TestIntegrationWithMocks
- L484: def test_bot_runner_initialization(self, tmp_path)
- L496: def test_template_library_stats(self, tmp_path)

## `tests/test_integration_simple.py`

- L26: class TestScreenshotProvider
- L29: def test_screenshot_provider_creation(self)
- L36: def test_screenshot_provider_capture_method_exists(self)
- L42: def test_screenshot_provider_bounds_setting(self)
- L51: class TestCommandExecutor
- L54: def test_command_executor_creation(self)
- L61: def test_command_executor_has_methods(self)
- L68: def test_direction_map_coverage(self)
- L81: class TestTemplateLibrary
- L85: def temp_cache(self)
- L90: def test_template_library_creation(self, temp_cache)
- L97: def test_template_library_load_creatures(self, temp_cache)
- L123: def test_template_library_stats(self, temp_cache)
- L146: def test_template_save_and_retrieve(self, temp_cache)
- L173: class TestIntegrationScenarios
- L177: def temp_cache(self)
- L182: def test_provider_executor_integration(self)
- L196: def test_template_library_with_provider(self, temp_cache)
- L222: def test_all_components_together(self, temp_cache)

## `tests/test_issue_sync.py`

- L4: def test_list_open_issues_paginates(monkeypatch)
- L7: def fake_github_api(method, url, token, payload)
- L25: def test_split_primary_and_duplicates_keeps_oldest_issue_number()

## `tests/test_lab003_operator_url_security.py`

- L17: def _read(path)
- L21: def _powershell()
- L28: def _run_script(path)
- L46: def test_lab003_scripts_validate_local_base_url_before_network_or_child_process()
- L76: def test_lab003_child_processes_use_current_powershell_executable()
- L89: def test_lab003_webhook_urls_are_validated_before_env_transfer_or_post()
- L109: def test_lab003_shift_guard_rejects_unsafe_base_url_before_missing_bundle_check()
- L128: def test_lab003_mobile_proxy_rejects_remote_base_url_before_password_lookup()
- L137: def test_lab003_webhook_smoke_rejects_remote_http_before_env_transfer()
- L152: def test_lab003_validate_bundle_rejects_unsafe_base_url_before_child_process()

## `tests/test_llm_provider_url_security.py`

- L10: def test_local_model_provider_rejects_remote_backend_without_opt_in(monkeypatch)
- L19: def test_local_model_provider_allows_local_backend(monkeypatch)
- L27: def test_local_model_provider_requires_https_for_remote_opt_in(monkeypatch)
- L39: def test_azure_provider_rejects_unsafe_endpoint_before_client(monkeypatch)
- L42: class FakeAzureOpenAI
- L43: def __init__(self)
- L59: def test_azure_provider_accepts_allowlisted_https_endpoint(monkeypatch)
- L62: class FakeAzureOpenAI
- L63: def __init__(self)
- L79: def test_api_call_model_rejects_remote_backend_before_http_client(monkeypatch)
- L80: class FailClient
- L81: def __init__(self)

## `tests/test_mobile_console_api_contract_snapshot.py`

- L10: def _load_app_module(monkeypatch, tmp_path)
- L36: def _extract_api_route_map(app)
- L53: def test_mobile_console_contract_snapshot_required_routes(monkeypatch)
- L78: def test_mobile_console_critical_endpoints_keep_security_regressions(monkeypatch)

## `tests/test_mobile_console_capability_gate.py`

- L9: def _load_app_module(monkeypatch, tmp_path)
- L27: def test_mobile_console_api_blocked_for_core_tier(monkeypatch)
- L37: def test_mobile_console_console_route_blocked_for_core_tier(monkeypatch)
- L46: def test_mobile_console_api_allowed_for_pro_tier(monkeypatch)

## `tests/test_mobile_console_client_sync_security.py`

- L7: def _load_app(monkeypatch, tmp_path)
- L26: def _source_dir(tmp_path)
- L33: def test_client_sync_keeps_writes_inside_configured_client_root(monkeypatch, tmp_path)
- L58: def test_client_sync_rejects_target_slug_path_traversal_before_writing(monkeypatch, tmp_path)
- L75: def test_client_sync_rejects_autoloader_path_traversal_before_writing(monkeypatch, tmp_path)
- L93: def test_client_sync_rejects_init_file_path_traversal_before_writing(monkeypatch, tmp_path)
- L111: def test_client_sync_rejects_oversized_init_file_before_writing(monkeypatch, tmp_path)
- L133: def test_client_sync_rejects_symlinked_init_file_before_writing(monkeypatch, tmp_path)
- L161: def test_client_sync_rejects_symlinked_lua_source_before_writing(monkeypatch, tmp_path)
- L184: def test_client_sync_rejects_oversized_lua_source_before_writing(monkeypatch, tmp_path)
- L202: def test_client_sync_rejects_symlinked_lua_destination_before_writing(monkeypatch, tmp_path)
- L227: def test_client_sync_uses_default_autoloader_when_env_is_blank(monkeypatch, tmp_path)

## `tests/test_mobile_console_command_audit_security.py`

- L10: def _load_app_module(monkeypatch, tmp_path)
- L32: def test_mobile_console_audit_redacts_command_secrets(monkeypatch)
- L51: def test_mobile_console_audit_persists_redacted_command(monkeypatch, tmp_path)

## `tests/test_mobile_console_command_execution_security.py`

- L12: def _load_app_module(monkeypatch, tmp_path)
- L35: def test_safe_preset_command_executes_as_structured_argv(monkeypatch)
- L45: def fake_run_argv(args, timeout, cwd, env, redact_output)
- L53: def unexpected_run()
- L86: def test_safe_mode_rejects_non_preset_without_launching(monkeypatch)
- L91: def unexpected_launch()
- L110: def test_full_access_env_does_not_enable_arbitrary_command_execution(monkeypatch)
- L118: def unexpected_launch()
- L134: def test_full_access_env_is_not_reported_as_shell_mode(monkeypatch)
- L157: def test_command_output_is_redacted_before_return(monkeypatch)
- L190: def test_logs_fallback_reads_bounded_tail_and_redacts_output(monkeypatch)
- L223: def test_logs_rejects_symlinked_log_without_reading_target(monkeypatch)

## `tests/test_mobile_console_csrf_security.py`

- L9: def _load_app_module(monkeypatch, tmp_path)
- L27: def _login(client)
- L36: def test_cookie_authenticated_mutation_requires_csrf(monkeypatch)
- L56: def test_bearer_authenticated_mutation_does_not_require_csrf(monkeypatch)

## `tests/test_mobile_console_db_exec_security.py`

- L5: def _load_app(monkeypatch, tmp_path)
- L20: def test_db_exec_psql_fallback_does_not_put_password_in_argv(monkeypatch, tmp_path)
- L32: def fake_run_argv(args, timeout, cwd, env)
- L48: def test_db_exec_docker_fallback_passes_password_by_env_name_only(monkeypatch, tmp_path)
- L56: def fake_run_argv(args, timeout, cwd, env)
- L71: def test_run_argv_resolves_executable_before_launch(monkeypatch, tmp_path)
- L75: def fake_resolve(name)
- L79: class FakeProc
- L84: def fake_run(command)

## `tests/test_mobile_console_display_path_security.py`

- L9: def _load_app_module(monkeypatch, tmp_path)
- L28: def _login_token(client, username, password)
- L37: def test_operator_file_metadata_uses_display_safe_paths(monkeypatch)
- L66: def test_auto_trainer_latest_reads_markdown_with_size_bound(monkeypatch)
- L92: def test_auto_trainer_latest_rejects_oversized_json_report(monkeypatch)
- L119: def test_auto_trainer_latest_returns_stable_invalid_json_error(monkeypatch)
- L144: def test_local_disk_probe_uses_display_safe_repo_path(monkeypatch)
- L157: def test_client_sync_response_uses_display_safe_paths(monkeypatch)
- L180: def test_client_sync_generic_errors_do_not_expose_local_paths(monkeypatch)

## `tests/test_mobile_console_generated_latest_api.py`

- L11: def _load_app_module(monkeypatch, tmp_path)
- L29: def _login_token(client, username, password)
- L40: def _make_dir_symlink(link_path, target_path)
- L47: def test_latest_generated_requires_auth(monkeypatch)
- L56: def test_latest_generated_reads_manifest(monkeypatch)
- L109: def test_latest_generated_rejects_external_latest_manifest_pointer(monkeypatch)
- L163: def test_latest_generated_rejects_oversized_latest_pointer(monkeypatch)
- L196: def test_execution_manifest_reads_skip_symlinked_run_dir_escape(monkeypatch)
- L265: def test_execution_manifest_reads_skip_oversized_manifest(monkeypatch)
- L321: def test_latest_generated_scan_uses_public_artifact_paths(monkeypatch)
- L345: def test_public_artifact_path_redacts_unknown_absolute_paths(monkeypatch)
- L355: def test_commands_dictionary_requires_operator_auth(monkeypatch)
- L364: def test_commands_dictionary_reads_valid_payload(monkeypatch)
- L396: def test_commands_dictionary_handles_missing_or_invalid_file(monkeypatch)
- L431: def test_commands_dictionary_rejects_oversized_payload(monkeypatch)
- L459: def test_commands_dictionary_rejects_symlinked_payload(monkeypatch)

## `tests/test_mobile_console_guarded_agent_actions_security.py`

- L10: def _load_app_module(monkeypatch, tmp_path)
- L28: def _audit_records(path)
- L32: def test_intel_launch_requires_confirmation_before_side_effects(monkeypatch)
- L39: def unexpected_side_effect()
- L65: def test_one_click_execution_requires_confirmation_before_side_effects(monkeypatch)
- L72: def unexpected_side_effect()
- L92: def test_confirmed_intel_launch_audits_redacted_reason(monkeypatch)
- L125: def test_confirmed_one_click_execution_audits_reason(monkeypatch)

## `tests/test_mobile_console_ideas_api.py`

- L11: def _load_app_module(monkeypatch, tmp_path)
- L28: def _login_token(client, username, password)
- L39: def test_ideas_requires_auth(monkeypatch)
- L48: def test_ideas_crud_for_operator(monkeypatch)
- L88: def _make_file_symlink(link_path, target_path)
- L95: def test_admin_settings_and_idea_parking_writes_are_atomic(monkeypatch)
- L114: def test_admin_settings_write_replaces_symlink_without_touching_target(monkeypatch)
- L134: def test_local_mobile_state_reads_are_bounded(monkeypatch)
- L151: def test_mobile_local_state_source_uses_atomic_bounded_json_helpers()

## `tests/test_mobile_console_intel_proxy_api.py`

- L10: class _FakeResponse
- L11: def __init__(self, body, status)
- L15: def read(self)
- L18: def __enter__(self)
- L21: def __exit__(self, exc_type, exc, tb)
- L25: def _load_app_module(monkeypatch, tmp_path)
- L48: def _auth_headers(client)
- L58: def test_intel_status_proxy_success(monkeypatch)
- L62: def fake_urlopen(url, timeout)
- L81: def test_intel_status_proxy_unavailable(monkeypatch)
- L85: def fake_urlopen(_url, timeout)
- L100: def test_runtime_proxy_errors_redact_secret_bearing_exception_text(monkeypatch)
- L106: def fake_urlopen(_url, timeout)
- L126: def test_intel_status_proxy_rejects_unsafe_runtime_base_url(monkeypatch)
- L136: def fake_urlopen(_url, timeout)
- L155: def test_release_evidence_proxy_rejects_remote_runtime_api_base_url(monkeypatch)
- L162: def fake_urlopen(_url, timeout)
- L198: def test_runtime_proxy_rejects_unsafe_proxy_paths_before_urlopen(monkeypatch, path, error)
- L206: def fail_urlopen(_url, timeout)
- L225: def test_intel_state_and_diff_proxy_success(monkeypatch)
- L229: def fake_urlopen(_url, timeout)

## `tests/test_mobile_console_live_dashboard_profile_api.py`

- L9: def _load_app_module(monkeypatch, tmp_path)
- L26: def _login_token(client, username, password)
- L37: def test_live_dashboard_profile_requires_auth(monkeypatch)
- L46: def test_live_dashboard_profile_get_and_put(monkeypatch)
- L53: def fake_load(username, role)
- L67: def fake_save(username, role, payload)

## `tests/test_mobile_console_self_register_hardening.py`

- L9: def _load_app_module(monkeypatch, tmp_path)
- L25: def test_self_register_disabled_by_default(monkeypatch)
- L38: def test_self_register_requires_code_when_enabled(monkeypatch)
- L53: def test_self_register_creates_member_role_only(monkeypatch)
- L61: def fake_create(username, password, role, created_by)
- L80: def test_login_cookie_is_secure_in_production(monkeypatch)

## `tests/test_mobile_console_static_xss_security.py`

- L9: def test_mobile_console_app_does_not_render_api_payloads_with_inner_html()
- L19: def test_mobile_console_app_uses_dom_nodes_for_dashboard_tables()
- L27: def test_mobile_console_legacy_ui_does_not_render_full_command_box()

## `tests/test_mobile_console_url_validation_security.py`

- L8: def _load_app(monkeypatch, tmp_path)
- L47: def test_intel_url_validation_rejects_private_or_local_targets_in_production(monkeypatch, tmp_path, url)
- L61: def test_intel_url_validation_allows_public_targets_in_production(monkeypatch, tmp_path)
- L91: def test_intel_url_validation_rejects_secret_bearing_or_unsafe_url_parts(monkeypatch, tmp_path, url, detail)
- L106: def test_intel_url_validation_allows_private_targets_with_explicit_production_opt_in(monkeypatch, tmp_path)
- L115: def test_intel_url_validation_keeps_local_targets_available_outside_production(monkeypatch, tmp_path)
- L124: def test_intel_url_validation_rejects_invalid_ports(monkeypatch, tmp_path)
- L137: def test_http_proxy_url_guard_rejects_non_http_or_hostless_urls(monkeypatch, tmp_path, url)
- L177: def test_local_runtime_api_base_url_rejects_unsafe_values(monkeypatch, tmp_path, url, detail)
- L200: def test_local_runtime_api_base_url_allows_local_runtime_hosts(monkeypatch, tmp_path, url)

## `tests/test_mobile_console_user_accounts_api.py`

- L19: def _make_hash(pw)
- L23: def _load_app_module(monkeypatch, tmp_path)
- L39: def _patch_db(monkeypatch, module)
- L46: def fake_ensure()
- L49: def fake_create(username, password, role, created_by)
- L63: def fake_get(username)
- L67: def fake_list()
- L73: def fake_update_pw(username, password)
- L78: def fake_update_role(username, role)
- L83: def fake_deactivate(username)
- L99: def _login(client, username, password)
- L107: def test_register_requires_owner(monkeypatch)
- L122: def test_register_creates_account(monkeypatch)
- L141: def test_register_conflict_with_env_account(monkeypatch)
- L157: def test_register_duplicate_rejected(monkeypatch)
- L174: def test_login_with_db_account(monkeypatch)
- L195: def test_self_register_creates_member_without_operator_access(monkeypatch)
- L223: def test_list_accounts_requires_owner(monkeypatch)
- L234: def test_list_accounts_returns_env_and_db(monkeypatch)
- L262: def test_change_password_own_account(monkeypatch)
- L296: def test_change_password_other_requires_owner(monkeypatch)
- L331: def test_change_role_requires_owner(monkeypatch)
- L355: def test_change_role_promotes_account(monkeypatch)
- L380: def test_role_change_revokes_existing_owner_session(monkeypatch)
- L419: def test_deactivate_account(monkeypatch)
- L452: def test_deactivate_self_fails(monkeypatch)

## `tests/test_mythibia_sync_security.py`

- L8: def _script_text()
- L12: def test_unsafe_runtime_bootstrap_requires_second_env_approval()
- L21: def test_unsafe_runtime_bootstrap_paths_are_clientroot_scoped()
- L37: def test_default_flow_removes_unsafe_runtime_bootstrap_artifacts()

## `tests/test_mythibia_watcher_security.py`

- L8: def _script_text()
- L12: def test_mythibia_watcher_uses_strict_mode_and_log_child_path_guard()
- L21: def test_mythibia_watcher_log_rotation_uses_literal_paths()
- L33: def test_mythibia_watcher_archives_are_checked_before_delete()
- L41: def test_mythibia_watcher_sync_script_path_is_repo_local_ps1()

## `tests/test_night_report_security.py`

- L11: def _load_module()
- L19: def test_night_report_reads_bounded_tail_sample_for_large_logs(tmp_path, monkeypatch)
- L56: def test_night_report_full_small_log_is_not_marked_truncated(tmp_path)

## `tests/test_nightly_stability_artifact.py`

- L7: def _load_nightly_stability_module()
- L16: def test_nightly_stability_writes_valid_artifact_schema(monkeypatch, tmp_path)
- L37: def fake_run(cmd, cwd)

## `tests/test_ops_process_safety.py`

- L12: def _load_module(name, relative_path)
- L22: def test_smoke_must_pass_resolves_executable_before_launch(monkeypatch)
- L26: def fake_resolve_executable(name)
- L30: def fake_run(command)
- L49: def test_run_validator_preflight_uses_resolved_python(monkeypatch, tmp_path)
- L61: def fake_run(command)
- L76: def test_nightly_stability_run_resolves_executable_before_launch(monkeypatch, tmp_path)
- L82: def fake_resolve_executable(name)
- L86: def fake_run(command)
- L107: def test_sprint_validator_run_resolves_executable_before_launch(monkeypatch, tmp_path)
- L113: def fake_resolve_executable(name)
- L117: def fake_run(command)
- L138: def test_latest_sprint_validator_quality_check_uses_trusted_runner(monkeypatch)
- L146: def fake_run(command)
- L167: def test_rosetta_python_assembler_uses_resolved_python(monkeypatch, tmp_path)
- L179: def test_kv_attach_first_hit_launches_target_through_process_safety()
- L186: def test_x64dbg_dynamic_pass_uses_trusted_launchers()
- L197: def test_executor_drift_checker_generator_uses_process_safety(monkeypatch, tmp_path)
- L215: def test_executor_doc_generators_write_timestamped_files(monkeypatch, tmp_path)
- L235: def test_activation_agent_sync_hook_uses_resolved_python(monkeypatch, tmp_path)
- L251: def fake_run(command)

## `tests/test_orchestrator_loop_security.py`

- L9: def test_orchestrator_loop_launcher_avoids_encoded_inline_command()
- L19: def test_orchestrator_loop_launcher_keeps_password_out_of_process_arguments()
- L31: def test_orchestrator_loop_launcher_verifies_pid_owner_before_stop()
- L44: def test_orchestrator_loop_worker_uses_literal_paths_and_inherited_env()

## `tests/test_otclient_external_bot_intake.py`

- L8: def test_missing_source_reports_source_required()
- L19: def test_directory_intake_indexes_capabilities_and_runtime_risks(tmp_path)
- L51: def test_secret_like_values_block_import(tmp_path)
- L67: def test_zip_intake_and_markdown_render(tmp_path)
- L88: def test_write_text_atomic_outputs_json_and_markdown(tmp_path)

## `tests/test_otclient_helper_module_audit.py`

- L12: def test_module_audit_tracks_remaining_function_modularization_pressure()
- L39: def test_module_audit_maps_runtime_and_placeholder_lanes()
- L73: def test_module_audit_defines_professional_extraction_map()
- L102: def test_module_audit_defines_supplemental_runtime_refactor_plan()
- L187: def test_module_audit_writes_atomic_json_and_plan(tmp_path)
- L262: def test_module_workplan_markdown_lists_verification_commands()
- L274: def test_module_audit_promotes_only_fresh_static_gate_evidence(tmp_path)
- L296: def test_module_audit_promotes_healing_after_fresh_vitals_and_tab_evidence(tmp_path)
- L316: def test_module_audit_promotes_combat_after_fresh_safety_and_magic_tab_evidence(tmp_path)
- L336: def test_module_audit_promotes_cavebot_after_fresh_safety_and_tab_evidence(tmp_path)
- L356: def test_module_audit_promotes_timer_after_fresh_passive_tick_and_tab_evidence(tmp_path)
- L375: def test_module_audit_promotes_loot_after_fresh_read_only_probe_and_diag_evidence(tmp_path)

## `tests/test_otclient_helper_module_contract.py`

- L13: def test_module_contract_passes_current_passive_modules()
- L29: def test_module_contract_requires_loader_registry_global_and_return()
- L726: def test_module_contract_blocks_forbidden_passive_actions(tmp_path)
- L748: def test_module_contract_writes_json_and_markdown(tmp_path)

## `tests/test_otclient_helper_next_modules_plan.py`

- L7: def test_next_modules_plan_is_safe_and_ordered()
- L103: def test_vbot_import_review_keeps_source_required_contract()
- L124: def test_next_modules_plan_markdown_calls_out_runtime_blockers()
- L184: def test_next_modules_plan_writes_atomic_json_and_markdown(tmp_path)

## `tests/test_otclient_helper_profile_audit.py`

- L13: def test_helper_config_schema_documents_safe_boot_defaults()
- L35: def test_profile_audit_passes_repo_safe_boot_profile()
- L42: def test_profile_audit_blocks_unsafe_migrated_profile(tmp_path)
- L81: def test_profile_audit_atomic_writer_uses_unique_temp_and_fsync(tmp_path)
- L95: def test_validate_dev_runs_profile_audit_before_pytest()
- L103: def test_solteria_helper_test_env_atomic_json_uses_guid_temp_cleanup()

## `tests/test_otclient_helper_shell_budget_plan.py`

- L7: def test_shell_budget_plan_measures_current_helper_pressure()
- L24: def test_shell_budget_plan_has_ranked_domain_guidance()
- L50: def test_shell_budget_plan_uses_lua_block_ends_not_next_function()
- L78: def test_shell_budget_plan_writes_json_and_markdown(tmp_path)

## `tests/test_otclient_helper_zerobot_shell.py`

- L81: def test_zerobot_shell_sections_render_without_layout_issues()
- L92: def test_helper_redesign_keeps_operator_layout_contract()
- L149: def test_helper_client_reporter_is_passive_packaged_and_safe_by_default()
- L180: def test_helper_redesign_phase3_summaries_are_wired()
- L221: def test_helper_has_module_lane_registry_for_all_runtime_surfaces()
- L303: def test_helper_ui_primitives_are_guarded_and_packaged()
- L566: def test_helper_diagnostics_domain_is_passive_and_wired()
- L700: def test_placeholder_modules_have_visible_preview_rows()
- L709: def test_heal_friend_is_profiled_module_lane_without_runtime_casting()
- L780: def test_coming_soon_sidebar_tabs_are_non_interactive()
- L794: def test_conditions_is_read_only_profiled_module_lane()
- L860: def test_hud_domain_is_passive_and_packaged()
- L922: def test_hotkeys_domain_is_passive_and_packaged()
- L970: def test_modal_domain_is_passive_and_guards_destructive_actions()
- L1016: def test_route_domain_is_passive_and_packaged()
- L1086: def test_targeting_domain_is_passive_and_packaged()
- L1151: def test_combat_runtime_adapter_is_passive_and_packaged()
- L1244: def test_cavebot_runtime_adapter_is_passive_and_packaged()
- L1352: def test_loot_runtime_adapter_is_passive_and_packaged()
- L1392: def test_timer_runtime_adapter_is_passive_and_packaged()
- L1421: def test_recovery_runtime_adapter_is_passive_and_consumed_by_shell()
- L1462: def test_profile_schema_adapter_is_passive_and_packaged()
- L1622: def test_feature_flags_adapter_is_passive_and_consumed_by_tools_summary()
- L1662: def test_operator_summary_adapter_is_passive_and_packaged()
- L1718: def test_planner_domain_is_passive_and_packaged()
- L1752: def test_runtime_policy_is_passive_gatekeeper_and_packaged()
- L1794: def test_dispatch_guard_is_passive_policy_handoff_and_packaged()
- L1826: def test_plan_queue_is_passive_bounded_decision_queue_and_packaged()
- L1860: def test_runtime_readiness_is_passive_bridge_status_and_packaged()
- L1895: def test_equipment_is_read_only_profiled_module_lane()
- L1965: def test_scripting_is_policy_shell_without_runtime_execution()
- L2025: def test_cavebot_tab_is_interactive_waypoint_loop()
- L2079: def test_cavebot_route_editor_does_not_trigger_movement()
- L2105: def test_cavebot_runtime_has_guarded_retry_budget_before_looped_movement()
- L2134: def test_smokeall_lists_every_zerobot_shell_view()
- L2149: def test_solteria_dev_lane_packages_without_touching_live_client()
- L2515: def test_solteria_sandbox_path_guard_rejects_live_client_aliases()
- L2535: def test_solteria_updated_client_boot_hook_is_controlled()
- L2562: def test_live_promotion_requires_explicit_approval_and_fresh_backup()
- L2599: def test_live_promotion_launch_after_promote_is_explicit_and_non_restart()
- L2623: def test_live_emergency_repair_is_audited_and_removes_root_fallback()
- L2643: def test_helper_logs_subtab_smoke_markers()
- L2650: def test_helper_supports_runtime_smoke_command_file()
- L2686: def test_helper_otclient_architecture_hooks_are_registered()
- L2702: def test_loader_is_helper_ui_only_and_loads_without_online_gate()
- L2737: def test_helper_safe_boot_disables_runtime_automation()
- L2758: def test_otprofile_builder_emits_safe_boot_profile_shape()
- L2782: def test_helper_runtime_arming_has_pz_and_non_monster_guards()
- L2806: def test_helper_targeting_on_executes_safe_monster_retarget()
- L2849: def test_helper_blocks_npc_icons_and_known_npc_names_before_attack()
- L2866: def test_runtime_modules_auto_arm_helper_runtime()
- L2881: def test_healing_and_magic_cards_expose_actionbar_box_controls()
- L2904: def test_actionbar_slots_are_the_runtime_source_for_potions_and_runes()
- L2923: def test_rotation_debug_reports_runtime_decision_reasons()
- L2967: def test_combat_action_selection_lives_in_passive_runtime_adapter()
- L2992: def test_offensive_actions_are_pz_aware_and_rate_limited_at_execution()
- L3023: def test_magic_v11b_has_safe_api_probe()
- L3053: def test_helper_v11b_has_central_api_registry_probe()
- L3090: def test_helper_v11b_exposes_api_snapshot_in_tools_ui()
- L3101: def test_helper_tools_diag_tab_exposes_api_and_feature_flags()
- L3124: def test_helper_bounded_diagnostics_export_is_wired()
- L3157: def test_recovery_actions_do_not_hard_stop_targeting_or_rotation()
- L3177: def test_timer_runtime_is_bounded_and_profile_persisted()
- L3204: def test_standalone_heal_and_loot_are_profile_fed_and_passive()
- L3225: def test_healing_spell_rotation_has_threshold_rules()
- L3238: def test_helper_login_singleton_module_visibility_and_healing_jitter_contracts()
- L3260: def test_healing_uses_real_local_player_vitals_before_percent_fallback()
- L3288: def test_smoke_runner_supports_attach_without_restart()
- L3316: def boot_graph_source()
- L3320: def boot_graph_has_module(source, name, file_name)

## `tests/test_otclient_input_contract_fixtures.py`

- L7: def test_input_contract_fixture_report_covers_hotkeys_and_modal_states()
- L37: def test_input_contract_fixture_markdown_and_json_outputs(tmp_path)

## `tests/test_phase5_nightly_checklist.py`

- L5: def _load_module()
- L14: def _write_snapshot(root, stamp, summary, status_porcelain)
- L26: def test_build_report_tracks_pending_and_non_nightly_runs(tmp_path)
- L74: def test_build_report_raises_alert_when_nightly_run_is_dirty(tmp_path)

## `tests/test_phase5_nightly_checklist_more.py`

- L12: def _load_module()
- L21: def test_parse_snapshot_timestamp_and_summary_handle_invalid_inputs(tmp_path)
- L32: def test_build_snapshot_record_and_evaluate_capture_all_alerts(tmp_path)
- L68: def test_determine_exit_code_and_main_write_outputs(tmp_path, monkeypatch, capsys)

## `tests/test_phase5_nightly_sync.py`

- L5: def _load_module()
- L14: def test_parse_remote_timestamps_filters_invalid_rows()
- L31: def test_should_sync_snapshot_detects_missing_required_files(tmp_path)
- L47: def test_render_short_status_includes_key_kpis()
- L66: def test_build_morning_brief_returns_attention_when_pending_runs_exist()
- L83: def test_render_morning_brief_markdown_includes_sprint_log_paste_line()
- L105: def test_send_attention_notifications_sends_only_configured_channels()
- L110: def fake_post(url, payload)
- L137: def test_send_attention_notifications_skips_when_verdict_is_pass()
- L142: def fake_post(url, payload)
- L166: def test_mark_step9_done_in_plan_updates_active_line(tmp_path)
- L188: def test_auto_close_step9_if_ready_writes_evidence_and_updates_docs(tmp_path)
- L232: def test_load_notify_env_file_parses_supported_lines(tmp_path)
- L250: def test_resolve_webhook_urls_prefers_cli_and_falls_back_to_env_file(tmp_path)

## `tests/test_phase5_nightly_sync_more.py`

- L13: def _load_module()
- L22: def test_default_key_path_prefers_env_then_userprofile(monkeypatch)
- L33: def test_run_raises_runtime_error_for_failed_checked_command(monkeypatch)
- L46: def test_post_json_handles_missing_url_and_http_error(monkeypatch)
- L52: def raise_http()
- L72: def test_post_json_rejects_unsafe_webhook_urls_before_urlopen(url, monkeypatch)
- L75: def fail_urlopen()
- L95: def test_post_json_allows_slack_and_discord_webhooks(url, monkeypatch)
- L98: class FakeResponse
- L101: def __enter__(self)
- L104: def __exit__(self, exc_type, exc, tb)
- L109: def fake_urlopen(request, timeout)
- L121: def test_update_step9_closure_in_readme_appends_and_updates_timestamp(tmp_path)
- L136: def test_main_returns_3_when_key_is_missing(monkeypatch, capsys)
- L147: def test_main_returns_4_when_remote_listing_fails(tmp_path, monkeypatch, capsys)

## `tests/test_phase5_ops_acceleration.py`

- L4: def test_phase5_incident_runbook_exists_and_has_core_sections()
- L14: def test_phase5_scheduler_scripts_exist_and_reference_strict_sync_flow()
- L35: def test_phase5_scheduler_install_remove_commands_are_documented()

## `tests/test_powershell_launcher_security.py`

- L17: def test_control_center_opener_restricts_url_protocols()
- L37: def test_ctoa_cli_control_center_restricts_url_before_probe_or_open()
- L58: def test_ctoa_cli_up_binds_mobile_console_to_loopback()
- L69: def test_mobile_console_operator_docs_do_not_recommend_public_dev_bind()
- L79: def test_ctoa_cli_uses_explicit_file_path_for_generated_helper_html()
- L88: def test_ctoa_cli_uses_official_wrapper_for_helper_operations()
- L102: def test_control_center_opener_rejects_traversal_urls_at_runtime()
- L127: def test_control_center_opener_rejects_backslash_urls_at_runtime()
- L152: def test_ctoa_cli_rejects_control_center_traversal_env_url_before_probe()
- L175: def test_kamil_launcher_restricts_client_path_and_profile_override()
- L188: def test_kamil_launcher_keeps_macro_studio_on_repo_local_python()

## `tests/test_process_safety.py`

- L9: def test_resolve_python_defaults_to_current_interpreter(monkeypatch)
- L15: def test_resolve_executable_rejects_missing_absolute_path(tmp_path)
- L22: def test_resolve_executable_accepts_existing_absolute_path(tmp_path)
- L29: def test_resolve_executable_honors_env_override(monkeypatch)
- L35: def test_run_trusted_rejects_empty_command()
- L40: def test_start_trusted_rejects_empty_command()

## `tests/test_project_progress_diagram.py`

- L10: def _load_module()
- L19: def test_state_by_task_id_normalizes_invalid_status_and_backlog_mismatch()
- L39: def test_generate_writes_markdown_with_percentages_and_defaults(tmp_path, monkeypatch)
- L88: def test_generate_raises_when_backlog_tasks_is_not_a_list(tmp_path)

## `tests/test_queue_worker_security.py`

- L6: def test_queue_worker_redacts_redis_url_credentials_and_query()
- L16: def test_queue_worker_redacts_password_only_redis_url()
- L23: def test_queue_worker_parse_invalid_payload_drops_raw_secret()
- L30: def test_queue_worker_source_does_not_log_raw_redis_url()

## `tests/test_release_evidence_pack.py`

- L12: def _load_module()
- L20: def test_build_evidence_pack_handles_missing_artifacts(tmp_path)
- L47: def test_build_evidence_pack_reads_current_artifacts(tmp_path)
- L365: def test_build_evidence_pack_uses_configured_defaults(tmp_path, monkeypatch)
- L432: def test_build_evidence_pack_rejects_symlinked_configured_json_and_audit(tmp_path)
- L474: def test_build_evidence_pack_ignores_symlinked_release_markdown(tmp_path)
- L507: def test_build_evidence_pack_rejects_symlinked_p7_operator_brief(tmp_path)
- L547: def test_helper_status_rejects_symlinked_helper_dev_dir(tmp_path)
- L569: def test_helper_status_blocks_inconsistent_releasable_gate_with_pending_blocker(tmp_path)
- L605: def test_helper_status_promoted_requires_durable_live_promotion_evidence(tmp_path)

## `tests/test_repo_hygiene_audit.py`

- L8: def test_tracked_top_level_entries_returns_top_level_names(monkeypatch)
- L20: def test_tracked_top_level_entries_returns_empty_set_on_git_failure(monkeypatch)
- L21: def fail()
- L29: def test_tracked_top_level_entries_returns_empty_set_on_git_unavailable(monkeypatch)
- L30: def fail()
- L38: def test_scan_top_level_ignores_untracked_local_outputs_and_flags_unknowns(tmp_path, monkeypatch)
- L66: def test_main_writes_json_and_honors_fail_on_findings(tmp_path, monkeypatch, capsys)

## `tests/test_repo_hygiene_distribution.py`

- L5: def test_classify_distribution_marks_raw_artifacts_private_studio()
- L11: def test_classify_distribution_marks_mobile_console_as_pro_public()
- L17: def test_classify_distribution_marks_src_as_core_public()
- L23: def test_build_plan_carries_visibility_and_package_tier()

## `tests/test_repo_hygiene_migration_plan.py`

- L8: def test_classify_routes_known_and_unknown_paths()
- L15: def test_load_findings_and_write_markdown(tmp_path)
- L31: def test_main_writes_json_and_markdown(tmp_path, monkeypatch, capsys)

## `tests/test_response_guardrails.py`

- L18: def test_prompt_library_declares_response_guardrails()
- L28: def test_agent_roster_declares_response_guardrails()
- L38: def test_hidden_reasoning_markers_are_rejected()
- L46: def test_empty_follow_up_is_rejected()
- L53: def test_meta_correction_is_rejected()
- L60: def test_direct_corrected_answer_passes()
- L70: def test_operational_structure_missing_sections_is_rejected()
- L78: def test_operational_structure_facts_inference_next_step_passes()

## `tests/test_runner_agent_db_security.py`

- L7: def _load_db_module(monkeypatch)
- L15: def test_agent_db_pool_uses_keyword_config_instead_of_password_dsn(monkeypatch)
- L26: class FakePool
- L29: class FakePgPool
- L31: def SimpleConnectionPool(minconn, maxconn)
- L56: def test_agent_db_missing_password_error_does_not_echo_secret(monkeypatch)
- L64: def test_agent_db_log_run_redacts_secret_bearing_db_errors(monkeypatch, caplog)
- L67: def fail_execute(sql, params)

## `tests/test_runner_backlog_selection.py`

- L7: def _load_runner_module(module_name)
- L16: def test_runner_uses_env_backlog_file_for_selection(monkeypatch, tmp_path)
- L31: def test_runner_raises_on_invalid_backlog_yaml_object(monkeypatch, tmp_path)
- L42: def test_runner_raises_on_missing_backlog_file(monkeypatch, tmp_path)

## `tests/test_runner_execution_summary.py`

- L6: def _load_runner_module(module_name)
- L15: def test_build_execution_summary_counts_and_eta()
- L43: def test_build_execution_summary_blocked_has_priority_over_other_states()
- L61: def test_build_report_includes_normalized_execution_summary_section()
- L78: def test_report_command_writes_execution_summary_artifact(tmp_path, monkeypatch, capsys)

## `tests/test_runner_imports.py`

- L6: def test_runner_help_works_as_script_and_module(project_root)
- L25: def test_executor_import_with_runner_on_path(project_root)

## `tests/test_runner_pipeline_scheduler.py`

- L4: def test_count_active_tasks_counts_only_selected_states()
- L16: def test_build_new_task_candidates_sorts_by_priority_then_id()
- L24: def rank(priority)

## `tests/test_security_hardening.py`

- L16: def test_api_rejects_default_jwt_secret_in_production()
- L35: def test_api_allows_non_default_jwt_secret_in_production()
- L54: def test_api_rejects_wildcard_cors_in_production()
- L73: def test_api_rejects_default_auth_account_seeding_in_production(tmp_path)
- L93: def test_api_rejects_default_auth_account_seeding_without_explicit_opt_in(tmp_path)
- L114: def test_api_allows_default_auth_account_seeding_only_with_explicit_opt_in(tmp_path)
- L144: def test_api_rejects_seed_account_opt_in_without_seed_passwords(tmp_path)
- L166: def test_public_seed_login_surfaces_do_not_embed_legacy_passwords()
- L184: def test_db_password_is_not_documented_or_passed_in_cli_dsn()
- L203: def test_runtime_smoke_keeps_credentials_on_loopback_api()
- L215: def test_api_release_evidence_sanitizes_paths_and_secrets(monkeypatch, tmp_path)
- L264: def test_api_release_evidence_rejects_oversized_file_without_leaking_content(monkeypatch, tmp_path)
- L296: def test_api_release_evidence_rejects_symlink_without_reading_target(monkeypatch, tmp_path)
- L332: def test_mobile_console_requires_registration_code_when_self_register_enabled_in_production()
- L358: def test_mobile_console_allows_production_start_with_self_register_disabled()
- L381: def test_mobile_console_login_sets_httponly_cookie_and_cookie_auth(monkeypatch)

## `tests/test_solteria_api_audit.py`

- L6: def test_parse_meta_extracts_global_functions_and_methods(tmp_path)
- L48: def test_render_markdown_includes_high_value_api(tmp_path)

## `tests/test_solteria_helper_goal_audit.py`

- L7: def _write_json(path, payload)
- L11: def test_goal_audit_atomic_json_write_leaves_complete_artifact(tmp_path)
- L24: def _write_base_artifacts(tmp_path)
- L55: def test_goal_audit_resolves_versioned_zip_from_manifest(tmp_path)
- L71: def test_goal_audit_reports_pending_smokeattachall(tmp_path)
- L110: def test_goal_audit_can_report_complete_when_release_gate_is_releasable(tmp_path)
- L135: def test_goal_audit_keeps_empty_next_command_after_completed_live_promotion(tmp_path)
- L158: def test_goal_audit_prefers_release_gate_promotion_command_when_only_approval_is_pending(tmp_path)
- L182: def test_goal_audit_renders_safe_operator_dashboard_and_terminal_summary(tmp_path)

## `tests/test_solteria_helper_release_gate.py`

- L9: def _write_json(path, payload)
- L13: def test_release_gate_atomic_json_write_leaves_complete_artifact(tmp_path)
- L26: def _write_static_artifacts(dev_dir)
- L67: def _write_complete_smoke_report(path)
- L86: def test_release_gate_blocks_without_inworld_smoke_and_approval(tmp_path)
- L99: def test_release_gate_uses_smoke_status_next_command_for_smokeattach_blocker(tmp_path)
- L116: def test_release_gate_runs_smokeattachall_when_readycheck_is_ready(tmp_path)
- L127: def test_release_gate_runs_smokeattachmodules_when_module_attach_is_missing_and_ready(tmp_path)
- L140: def test_release_gate_blocks_when_module_attach_failed(tmp_path)
- L154: def test_release_gate_blocks_when_module_attach_is_stale(tmp_path)
- L166: def test_release_gate_ignores_stale_readycheck_when_sandbox_is_not_running(tmp_path)
- L183: def test_release_gate_passes_with_complete_inworld_smoke_and_approval(tmp_path)
- L196: def test_release_gate_points_to_live_promotion_when_only_approval_is_pending(tmp_path)
- L208: def test_release_gate_accepts_durable_live_promotion_evidence(tmp_path)
- L232: def test_release_gate_blocks_stale_live_promotion_evidence(tmp_path)
- L257: def test_release_gate_blocks_when_live_promotion_hashes_do_not_match(tmp_path)
- L279: def test_release_gate_blocks_when_live_root_helper_fallback_remains(tmp_path)
- L302: def test_release_gate_blocks_when_live_root_profile_hash_drifts(tmp_path)
- L339: def test_release_gate_blocks_when_smoke_report_lacks_view_evidence(tmp_path)
- L361: def test_release_gate_blocks_when_smoke_report_screenshot_file_is_missing(tmp_path)
- L377: def test_release_gate_blocks_when_smoke_report_is_older_than_manifest(tmp_path)
- L392: def test_release_gate_discovers_latest_inworld_smoke_report(tmp_path)
- L409: def test_release_gate_ignores_modal_limited_coverage_reports(tmp_path)
- L417: def test_release_gate_blocks_when_smoke_preflight_is_missing(tmp_path)
- L429: def test_release_gate_blocks_when_smoke_preflight_failed(tmp_path)
- L440: def test_release_gate_blocks_when_smoke_preflight_is_stale_for_manifest(tmp_path)
- L455: def test_release_gate_accepts_preflight_manifest_hash_across_datetime_formats(tmp_path)
- L475: def test_release_gate_blocks_when_module_static_gates_are_missing(tmp_path)
- L488: def test_release_gate_blocks_when_module_static_gates_failed(tmp_path)
- L503: def test_release_gate_blocks_when_module_static_gates_are_stale(tmp_path)
- L517: def test_release_gate_blocks_when_zip_evidence_is_missing(tmp_path)
- L536: def test_release_gate_blocks_when_zip_hash_does_not_match_readiness(tmp_path)
- L556: def test_release_gate_blocks_when_manifest_stage_file_is_missing(tmp_path)
- L569: def test_release_gate_blocks_when_manifest_stage_hash_mismatches(tmp_path)

## `tests/test_solteria_helper_sandbox_smoke_queue.py`

- L7: def write_json(path, payload)
- L12: def seed_dev_dir(tmp_path)
- L200: def test_smoke_queue_routes_current_blockers(tmp_path)
- L270: def test_smoke_queue_requires_static_refresh_when_preflight_missing(tmp_path)
- L283: def test_smoke_queue_rejects_invalid_attach_tabs(tmp_path)
- L300: def test_render_markdown_includes_live_safety_and_queue(tmp_path)
- L327: def test_write_text_atomic_outputs_queue_files(tmp_path)

## `tests/test_sprint029_ci_evidence.py`

- L14: def _load_nightly_stability()
- L23: def test_sprint029_evidence_discoverable_at_canonical_path(monkeypatch, tmp_path)
- L27: def fake_run(cmd, cwd)
- L61: def test_sprint029_evidence_entries_have_required_fields(monkeypatch, tmp_path)
- L65: def fake_run(cmd, cwd)

## `tests/test_sprint029_dashboard_ergonomics.py`

- L17: def _load_app_module(monkeypatch, tmp_path)
- L33: def _login_token(client, username, password)
- L39: def test_dashboard_healthy_has_operational_status_message(monkeypatch)
- L45: def fake_db_exec(sql, params, timeout)
- L70: def test_dashboard_degraded_has_descriptive_status_message(monkeypatch)
- L76: def fake_db_exec(sql, params, timeout)

## `tests/test_sprint029_nightly_trend.py`

- L14: def _load_nightly_stability()
- L23: def test_sprint029_nightly_artifact_has_drift_visibility_fields(monkeypatch, tmp_path)
- L27: def fake_run(cmd, cwd)
- L71: def test_sprint029_nightly_evidence_entries_carry_sprint_id(monkeypatch, tmp_path)
- L75: def fake_run(cmd, cwd)

## `tests/test_sprint029_validate.py`

- L5: def _load_sprint029_validate_module()
- L14: def test_sprint029_validate_passes_on_repo_root()
- L25: def test_sprint029_validate_reports_expected_check_ids()

## `tests/test_sprint039_validate.py`

- L5: def _load_sprint039_validate_module()
- L14: def test_sprint039_validate_passes_on_repo_root()
- L25: def test_sprint039_validate_reports_expected_check_ids()

## `tests/test_sprint040_validate.py`

- L5: def _load_sprint040_validate_module()
- L14: def test_sprint040_validate_passes_on_repo_root()
- L25: def test_sprint040_validate_reports_expected_check_ids()

## `tests/test_sprint041_dashboard_ergonomics.py`

- L17: def _load_app_module(monkeypatch, tmp_path)
- L33: def _login_token(client, username, password)
- L39: def test_dashboard_healthy_returns_status_context(monkeypatch)
- L44: def fake_db_exec(sql, params, timeout)
- L73: def test_dashboard_degraded_status_context_points_to_impacted_sections(monkeypatch)
- L78: def fake_db_exec(sql, params, timeout)
- L106: def test_dashboard_error_status_context_highlights_critical_sections(monkeypatch)
- L111: def fake_db_exec(sql, params, timeout)

## `tests/test_sprint042_validate.py`

- L5: def _load_sprint042_validate_module()
- L14: def test_sprint042_validate_passes_on_repo_root_without_focused_regressions()
- L25: def test_sprint042_validate_reports_expected_base_check_ids()
- L48: def test_sprint042_validate_run_tests_adds_quality_regression_check(monkeypatch)
- L52: def fake_run(_cmd, cwd)

## `tests/test_sprint044_control_tick.py`

- L7: def _load_runner_module(module_name)
- L16: def _single_task_backlog(backlog_id)
- L38: def test_control_tick_reaches_waiting_approval_in_expected_cycles(monkeypatch)
- L52: def test_manual_approval_releases_task_after_waiting_approval(monkeypatch)
- L67: def test_manual_approval_rejects_task_not_waiting(monkeypatch)
- L78: def test_load_state_resets_when_backlog_id_changes(monkeypatch, tmp_path)

## `tests/test_sprint061_065_validator_contracts.py`

- L12: def validator_case(request)
- L22: def _write_workspace(root, sprint)
- L88: def _failed_ids(report)
- L96: def test_legacy_sprint_validators_pass_for_complete_workspace(tmp_path, validator_case)
- L106: def test_legacy_sprint_validators_flag_missing_local_tasks(tmp_path, validator_case)
- L117: def test_legacy_sprint_validator_quality_check_reports_pytest_failure(monkeypatch)
- L139: def test_legacy_sprint_validators_flag_released_doc_state_mismatch(tmp_path, validator_case)

## `tests/test_sprint067_validate.py`

- L11: def _load_module()
- L20: def _write_valid_workspace(root)
- L98: def _failed_ids(report)
- L106: def test_build_report_passes_for_complete_workspace(tmp_path, monkeypatch)
- L118: def test_build_report_flags_missing_local_tasks(tmp_path, monkeypatch)
- L130: def test_build_report_flags_missing_pipeline_gate(tmp_path, monkeypatch)
- L142: def test_build_report_flags_misaligned_progress_doc(tmp_path, monkeypatch)
- L154: def test_check_quality_reports_pytest_failure(monkeypatch)
- L171: def test_main_writes_json_and_returns_nonzero_for_failed_report(monkeypatch, tmp_path, capsys)

## `tests/test_sprint_state_sync.py`

- L12: def _load_module()
- L21: def test_init_state_from_backlog_applies_defaults_and_skips_invalid_items(monkeypatch)
- L46: def test_preview_release_counts_raises_for_missing_or_empty_backlog(tmp_path)
- L56: def test_synchronize_state_initializes_and_releases_all_tasks(tmp_path, monkeypatch)
- L115: def test_sprint_state_sync_atomic_writer_uses_unique_temp_and_fsync()
- L123: def test_synchronize_state_reuses_matching_state_and_adds_missing_task(tmp_path, monkeypatch)

## `tests/test_sprint_validator_contracts.py`

- L12: def validator_case(request)
- L22: def _write_validator_workspace(root, sprint, task_ids)
- L86: def _failed_ids(report)
- L94: def test_sprint_validators_pass_for_complete_workspace(tmp_path, monkeypatch, validator_case)
- L105: def test_sprint_validators_flag_missing_local_tasks(tmp_path, monkeypatch, validator_case)
- L117: def test_sprint066_quality_check_reports_pytest_failure(monkeypatch)
- L138: def test_sprint066_main_writes_json_and_reports_fail(monkeypatch, tmp_path, capsys)

## `tests/test_static_security_scan_contract.py`

- L9: def test_non_security_sha1_fingerprints_are_marked_explicitly()
- L25: def test_bandit_scope_legacy_python_tools_compile()
- L36: def test_pre_commit_bandit_scope_covers_operator_surfaces()

## `tests/test_status_sync.py`

- L4: def test_update_live_issue_sla_section_appends_and_patches(monkeypatch)
- L7: def fake_github_api(method, url, token, payload)
- L30: def test_update_live_issue_sla_section_no_change(monkeypatch)
- L39: def fake_github_api(method, url, token, payload)
- L58: def test_update_live_issue_sla_section_removes_stale_section(monkeypatch)
- L67: def fake_github_api(method, url, token, payload)

## `tests/test_suite.py`

- L15: class TestRunnerBasics
- L18: def test_imports(self)
- L26: def test_config_validation(self)
- L33: def test_env_variables(self)
- L40: def test_log_output_format(self)
- L47: class TestReporterBasics
- L50: def test_status_sync_exists(self)
- L55: def test_issue_markdown_format(self)
- L66: def test_timestamp_format(self)
- L74: class TestVPSConnectivity
- L77: def test_ssh_key_format(self)
- L84: def test_vps_host_config(self)
- L91: def test_ctoa_cli_default_host_is_active_vps(self)
- L98: def test_ctoa_vps_script_default_host_is_active_vps(self)
- L105: def test_ctoa_vps_preupdate_gate_present(self)
- L113: def test_ctoa_vps_preupdate_gate_applied_to_update_paths(self)
- L133: def test_phase5_worktree_drycheck_script_exists_and_checks_porcelain(self)
- L141: def test_ctoa_root_action_supports_phase5_guardrail_actions(self)
- L149: def test_ctoa_vps_exposes_phase5_guardrail_actions(self)
- L156: def test_vps_crontab_example_contains_nightly_worktree_drycheck(self)
- L162: class TestGitHubIntegration
- L165: def test_github_api_format(self)
- L177: def test_pat_not_in_code(self)
- L186: class TestFileStructure
- L189: def test_required_files_exist(self)
- L203: def test_gitignore_configured(self)

## `tests/test_sync_live_targets_security.py`

- L12: def load_module()
- L20: def test_sync_live_targets_replaces_only_child_directory(tmp_path)
- L40: def test_sync_live_targets_rejects_target_inside_source(tmp_path)
- L49: def test_sync_live_targets_rejects_unsafe_source_directory_name(tmp_path)
- L59: def test_sync_live_targets_rejects_existing_target_symlink(tmp_path)

## `tests/test_template_library_security.py`

- L11: def _template(name, template_type)
- L39: def test_template_server_url_rejects_unsafe_parts_before_urlopen(tmp_path, monkeypatch, caplog, url)
- L47: def fail_urlopen()
- L57: def test_template_library_rejects_unsafe_server_url_on_init(tmp_path)
- L65: def test_template_library_rejects_private_server_url_on_init(tmp_path)
- L74: def test_template_cache_rejects_traversal_names(tmp_path, name)
- L82: def test_template_load_rejects_unsafe_creature_names_without_placeholder(tmp_path)
- L91: def test_template_load_allows_existing_space_separated_creature_names(tmp_path)

## `tests/test_tibia_source_collector.py`

- L9: def _write_news_fixture(path, entries)
- L16: def test_archives_news_raw_html_and_emits_added_events(tmp_path)
- L35: def test_second_news_snapshot_emits_changed_and_removed_events(tmp_path)
- L50: def test_blocked_and_parser_broken_attempts_keep_raw_evidence(tmp_path)
- L81: def test_unimplemented_source_parser_stays_pending_without_losing_its_raw_snapshot(tmp_path)

## `tests/test_tibia_sources.py`

- L14: def test_snapshot_archive_preserves_raw_content_and_emits_added_then_changed(tmp_path)
- L52: def test_unchanged_snapshot_does_not_invent_a_diff_event(tmp_path)
- L67: def test_blocked_snapshot_is_preserved_and_inventory_reports_source_blocked(tmp_path)
- L88: def test_parser_failure_keeps_raw_snapshot_and_emits_parser_error(tmp_path)
- L89: class BrokenParser
- L90: def parse(self, _snapshot)
- L116: def test_archive_writes_control_center_source_index_contract(tmp_path)
- L134: def test_file_collector_rejects_non_official_url_and_oversized_input(tmp_path)

## `tests/test_training_supply_chain_security.py`

- L16: def load_collect_github_module()
- L24: def test_finetune_requires_pinned_huggingface_revision()
- L46: def test_colab_notebook_requires_pinned_huggingface_revision()
- L61: def test_collect_github_rejects_untrusted_api_urls_before_urlopen(monkeypatch)
- L64: def fail_urlopen()
- L89: def test_collect_github_allows_only_recursive_tree_query()
- L108: def test_collect_github_builds_only_trusted_raw_urls()
- L135: def test_collect_github_dataset_filename_blocks_path_traversal()
- L149: def test_build_dataset_uses_deterministic_non_security_rng_and_visible_errors()

## `tests/test_validate_package_boundaries.py`

- L10: def test_validate_package_boundaries_passes_for_repo_manifests()
- L20: def test_validate_package_boundaries_detects_core_mobile_console_leak(tmp_path)

## `tests/test_vps_python_parity.py`

- L45: def test_control_center_launcher_uses_repo_local_python()
- L53: def test_vps_systemd_services_use_repo_local_python()
- L63: def test_ctoa_vps_script_pins_publish_and_validation_to_venv_python()
- L70: def test_control_center_evidence_env_surface_stays_in_sync()
- L89: def test_operator_next_command_is_visible_in_cli_docs_and_dictionary()
- L104: def test_control_center_open_command_is_visible_in_cli_docs_and_dictionary()

## `tests/test_vps_root_action_wrapper_security.py`

- L8: def _script_text()
- L12: def test_deploy_root_action_dashboard_health_uses_private_temp_file()
- L26: def test_deploy_root_action_reuses_dashboard_health_helper()

## `tests/test_vscode_extension_installer_security.py`

- L8: def _script_text()
- L12: def test_vscode_extension_installer_uses_separator_aware_child_path_guard()
- L21: def test_vscode_extension_installer_uses_literal_paths_for_recursive_replace()

## `tests/test_vscode_workspace_security.py`

- L10: def _load_json(path)
- L14: def test_mobile_console_launch_uses_loopback_and_env_secrets()
- L34: def test_vscode_configs_do_not_embed_mobile_console_dev_secrets()
- L45: def test_mobile_console_tasks_use_preflight_and_loopback_bind()

## `tests/test_wave_summary_utf8.py`

- L10: def _load_module()
- L19: def test_state_release_counts_reports_alignment_and_mismatch()
- L31: def test_generate_summary_uses_defaults_when_inputs_missing(tmp_path, monkeypatch)
- L70: def test_main_writes_summary_and_returns_zero(tmp_path, monkeypatch, capsys)
- L118: def test_load_json_and_yaml_invalid_inputs_return_empty(tmp_path)
- L129: def test_main_passes_paths_to_generate_summary(monkeypatch, tmp_path, capsys)
- L133: def fake_generate_summary()

## `tests/test_web_dependency_security.py`

- L12: def _read_json(path)
- L16: def _version_tuple(version)
- L25: def test_web_package_pins_postcss_override_for_next_advisory()
- L32: def test_web_lockfile_has_no_vulnerable_postcss_tree()

## `tests/test_windows_task_autostart_security.py`

- L20: def test_windows_task_guard_constrains_names_paths_and_logs()
- L36: def test_task_installers_and_removers_use_shared_guard()
- L44: def test_watcher_autostart_fallback_is_constrained()
- L59: def test_task_installers_quote_only_guarded_repo_child_paths()
- L74: def test_hidden_runner_accepts_only_repo_ps1_targets()

## `tests/unit/bot/test_command_executor.py`

- L4: def _make_executor(monkeypatch)
- L7: class FakeKeyboard
- L8: def __init__(self)
- L11: def press(self, key)
- L14: def release(self, key)
- L17: def type(self, text)
- L20: class FakeMouse
- L21: def __init__(self)
- L24: def press(self, btn)
- L27: def release(self, btn)
- L53: def test_command_executor_supports_named_key_combo_and_wait(monkeypatch)
- L77: def test_command_executor_supports_say_and_pause_alias(monkeypatch)
- L90: def test_batch_command_executor_supports_bare_wait_and_pause(monkeypatch)
- L94: async def fake_sleep(value)
- L101: async def fake_execute_async(command)

## `tests/unit/bot/test_decision.py`

- L8: def make_state()
- L15: def test_critical_hp_flees()
- L20: def test_low_hp_uses_potion()
- L25: def test_low_mp_uses_potion()
- L30: def test_loot_dead_target()
- L35: def test_attack_live_target()
- L40: def test_find_monster_when_no_target()
- L45: def test_brain_uses_rules_as_fallback(monkeypatch)
- L58: def test_bag_full_goes_depot()
- L63: def test_brain_ml_respects_auto_follow_rule(monkeypatch)
- L72: def _fake_predict_action(_state)

## `tests/unit/bot/test_game_data.py`

- L13: def test_monsters_load()
- L20: def test_routes_load()
- L27: def test_items_load()
- L33: def test_monsters_for_level_8()
- L39: def test_monsters_for_level_20()
- L45: def test_monsters_for_level_40()
- L51: def test_route_for_level_10()
- L57: def test_route_respects_risk()
- L63: def test_should_loot_gold()
- L67: def test_should_not_loot_skip_item()
- L71: def test_should_loot_valuable()

## `tests/unit/bot/test_humanizer.py`

- L12: def test_human_delay_within_bounds()
- L19: def test_combat_pause_executes()
- L26: def test_reaction_delay_executes()
- L33: def test_think_pause_rarely_fires()
- L43: def test_think_pause_usually_skips()
- L51: def test_bezier_path_length()
- L56: def test_bezier_starts_near_start()
- L61: def test_bezier_ends_near_end()
- L66: def test_misclick_jitter_within_range()
- L73: def test_move_mouse_human_no_error()

## `tests/unit/bot/test_hunt_strategy.py`

- L8: def make_state()
- L15: def test_best_target_no_nearby()
- L20: def test_best_target_picks_highest_exp()
- L26: def test_best_target_fallback_unknown_monster()
- L32: def test_active_route_returns_route_for_level()
- L38: def test_active_route_none_for_impossible_level()
- L46: def test_next_waypoint_returns_coords()
- L51: def test_next_waypoint_advances_with_cursor(monkeypatch)
- L71: def test_rules_select_target_when_nearby()
- L77: def test_rules_follow_route_when_no_monsters()
- L83: def test_rules_flee_takes_priority_over_route()

## `tests/unit/bot/test_input_backend.py`

- L6: def test_press_and_click_noop_when_unavailable(monkeypatch)
- L10: def _press(_key)
- L13: def _click(_x, _y)
- L26: def test_press_and_click_forward_when_available(monkeypatch)
- L31: def _press(key)
- L34: def _click(x, y)
- L47: def test_backend_introspection(monkeypatch)
- L55: def test_press_blocked_when_focus_required_and_inactive(monkeypatch)
- L62: def _press(_key)
- L71: def test_press_forwards_when_focus_required_and_active(monkeypatch)
- L78: def _press(_key)

## `tests/unit/bot/test_ml_model.py`

- L12: def make_state()
- L19: def test_predict_returns_valid_action()
- L25: def test_state_key_format()
- L33: def test_update_q_changes_value()
- L49: def test_compute_reward_kill()
- L56: def test_compute_reward_hp_loss()
- L63: def test_compute_reward_potion_waste()
- L70: def test_compute_reward_loot_dead_target()
- L76: def test_compute_reward_loot_without_target_is_penalized()
- L82: def test_brain_uses_ml(monkeypatch)
- L86: def fake_predict(state)

## `tests/unit/bot/test_movement_follow.py`

- L6: def test_auto_follow_throttles(monkeypatch)
- L35: def test_auto_follow_suppresses_when_moving(monkeypatch)
- L62: def test_auto_follow_refreshes_even_while_moving(monkeypatch)

## `tests/unit/bot/test_perception.py`

- L6: def test_game_state_defaults()
- L13: def test_hp_pct()
- L18: def test_mp_pct()
- L23: def test_is_low_hp_true()
- L28: def test_is_low_hp_false()
- L33: def test_is_low_mp()
- L38: def test_parse_game_state_stub()
- L46: def test_parse_game_state_template_target_fallback(monkeypatch)
- L49: class _Frame
- L52: def __getitem__(self, _item)
- L66: def test_parse_game_state_hp_target_has_priority(monkeypatch)
- L69: class _Frame
- L72: def __getitem__(self, _item)
- L86: def test_scale_region_matches_frame_size()
- L89: class _Frame
- L95: def test_bar_percentage_green_hp_fallback(monkeypatch)
- L106: def test_parse_game_state_zero_hp_spike_guard(monkeypatch)
- L109: class _Frame
- L112: def __getitem__(self, _item)
- L127: def test_parse_game_state_keeps_real_low_hp(monkeypatch)
- L130: class _Frame
- L133: def __getitem__(self, _item)

## `tests/unit/bot/test_runtime_profile_security.py`

- L11: def runtime_profile_loader(monkeypatch)
- L14: def _load(config_path)
- L24: def test_invalid_runtime_profile_json_is_diagnostic_not_silent(tmp_path, caplog, runtime_profile_loader)
- L40: def test_runtime_profile_save_uses_atomic_temp_and_cleanup(tmp_path, runtime_profile_loader)

## `tests/unit/bot/test_safety.py`

- L7: def test_human_delay_within_range()
- L14: def test_bezier_path_length()
- L19: def test_bezier_path_starts_near_start()
- L24: def test_bezier_path_ends_near_end()

## `tests/unit/bot/test_spell_rotation.py`

- L6: def test_spell_rotation_respects_level_and_cooldown(monkeypatch, tmp_path)
- L46: def test_spell_rotation_no_backend_noop(monkeypatch)
- L53: def test_detect_profession_from_profile_window_title(monkeypatch)
- L76: def test_detect_profession_from_promoted_keyword(monkeypatch)
- L92: def test_detect_profession_from_client_profile_override(monkeypatch)
- L114: def test_spell_rotation_uses_kamil_client_monk_profile(monkeypatch, tmp_path)

## `tests/unit/bot/test_sprint6.py`

- L10: class TestDoubleQLearning
- L11: def _state(self, hp, mp, target, level)
- L19: def test_predict_returns_valid_action(self)
- L25: def test_two_tables_exist(self)
- L31: def test_update_q_does_not_raise(self)
- L39: def test_epsilon_decays(self)
- L49: def test_double_update_alternates_tables(self)
- L62: def test_save_qtable_does_not_raise(self)
- L72: def test_compute_reward_kill(self)
- L79: def test_compute_reward_hp_loss_penalty(self)
- L90: class TestScheduler
- L91: def _make(self)
- L95: def test_should_run_during_active_window(self)
- L100: def test_should_not_run_outside_window(self)
- L111: def test_session_elapsed_increases(self)
- L118: def test_status_returns_dict(self)
- L124: def test_break_triggered_when_session_expires(self)
- L131: def test_get_scheduler_singleton(self)
- L141: class TestMemoryReader
- L142: def test_attach_returns_false_when_no_process(self)
- L148: def test_read_all_returns_dict_when_not_attached(self)
- L156: def test_read_position_returns_none_not_attached(self)
- L161: def test_get_reader_singleton(self)
- L168: def test_detach_does_not_raise(self)
- L179: class TestDashboardStats
- L180: def test_stats_keys(self)

## `tests/unit/bot/test_telemetry.py`

- L19: def temp_db(tmp_path)
- L28: def test_create_session_returns_id()
- L33: def test_log_loot_increments_gold()
- L47: def test_log_exp_increments_xp()
- L61: def test_log_event_writes_action()
- L73: def test_get_stats_returns_dict()
- L85: def test_get_stats_no_session()
- L91: def test_log_incident_updates_session_stats()

## `tests/unit/test_client_profile_router.py`

- L1: def test_resolve_client_profile_from_kamil_client_path()
- L7: def test_resolve_client_profile_from_otclient_path()

## `tests/unit/test_lua_pack_contracts.py`

- L9: def _read(rel_path)
- L13: def test_event_logger_contract()
- L21: def test_pathing_helper_contract()
- L29: def test_auto_heal_contract()
- L37: def test_supply_manager_contract()
- L45: def test_target_priority_contract()
- L53: def test_loot_filter_contract()

## `training/kaggle-notebook/ctoa_finetune.py`

- L13: def run(cmd)
- L25: def require_pinned_model_revision()
- L35: def trust_remote_code_enabled()
- L157: class FiniteGuardCallback
- L160: def on_log(self, args, state, control, logs, model)
- L166: def on_step_end(self, args, state, control, model)

## `training/scripts/build_dataset.py`

- L144: def ext_to_lang(ext)
- L154: def chunk_code(content, max_chars)
- L169: def make_code_example(file_path, content, rng)
- L194: def main()

## `training/scripts/collect_github.py`

- L35: def _validate_repo_component(value, label)
- L44: def _validate_branch(value)
- L51: def _safe_url_path_parts(path)
- L63: def _validate_github_api_url(url)
- L83: def _validate_github_raw_url(url)
- L97: def _safe_dataset_filename(repo_path)
- L108: def _build_raw_url(owner, repo, branch, repo_path)
- L120: def gh_get(url, token)
- L135: def collect_tree(owner, repo, token, out_dir)
- L197: def main()

## `web/src/app/api/auth/route.test.ts`

- L10: symbol authRequest

## `web/src/app/api/auth/route.ts`

- L16: symbol validateAuthRequestOrigin
- L20: symbol backendFetch
- L33: symbol GET
- L53: symbol POST

## `web/src/app/api/auth/seed-login/route.test.ts`

- L16: symbol seedRequest

## `web/src/app/api/auth/seed-login/route.ts`

- L16: symbol isLocalSeedLoginAllowed
- L24: symbol localSeedPassword
- L29: symbol validateSeedLoginRequestOrigin
- L33: symbol POST

## `web/src/app/api/chat/route.test.ts`

- L4: symbol chatRequest

## `web/src/app/api/chat/route.ts`

- L22: symbol ChatRole
- L24: symbol ChatMessage
- L30: symbol normalizeMessages
- L47: symbol toSafeError
- L71: symbol sanitizeAssistantContent
- L89: symbol prependSafetySystemMessage
- L93: symbol buildBackendChatPayload
- L117: symbol validateChatRequestOrigin
- L121: symbol POST

## `web/src/app/api/clients/[id]/capabilities/route.ts`

- L7: symbol GET

## `web/src/app/api/clients/route.ts`

- L7: symbol GET

## `web/src/app/api/config/validate-dry-run/route.ts`

- L7: symbol POST

## `web/src/app/api/control-center/access.ts`

- L8: symbol requireControlCenterReadAccess

## `web/src/app/api/control-center/actions/route.test.ts`

- L30: symbol actionRequest

## `web/src/app/api/control-center/actions/route.ts`

- L17: symbol validateControlCenterActionRequestOrigin
- L21: symbol loadViewer
- L26: symbol sanitizeControlCenterActionError
- L30: symbol GET
- L44: symbol POST

## `web/src/app/api/control-center/evidence/api-cost-report/route.ts`

- L9: symbol GET

## `web/src/app/api/control-center/evidence/report/route.ts`

- L9: symbol GET

## `web/src/app/api/control-center/evidence/route.test.ts`

- L36: symbol denyAccess
- L46: symbol allowAccess
- L53: symbol mockMarkdownFile

## `web/src/app/api/control-center/evidence/route.ts`

- L7: symbol GET

## `web/src/app/api/control-center/legacy/route.ts`

- L10: symbol LegacyFetchResult
- L18: symbol sanitizeLegacyBackendError
- L22: symbol backendGet
- L43: symbol GET

## `web/src/app/api/control-center/operational-routes-auth.test.ts`

- L22: symbol denyAccess

## `web/src/app/api/control-center/ops/route.ts`

- L7: symbol GET

## `web/src/app/api/control-center/route.ts`

- L9: symbol sanitizeControlCenterProbeError
- L13: symbol localOperationalState
- L38: symbol GET

## `web/src/app/api/diffs/[surface]/route.ts`

- L7: symbol GET

## `web/src/app/api/events/route.ts`

- L7: symbol GET

## `web/src/app/api/sources/route.ts`

- L7: symbol GET

## `web/src/app/api/status/route.ts`

- L6: symbol GET

## `web/src/app/api/updates/latest/route.ts`

- L7: symbol GET

## `web/src/app/page.tsx`

- L11: symbol makeId
- L15: symbol newSession

## `web/src/components/ChatWindow.tsx`

- L8: symbol ChatQualityAssessment
- L12: symbol Message
- L16: symbol Props
- L31: symbol send

## `web/src/components/CommunityPanel.tsx`

- L5: symbol CommunityMember
- L12: symbol CommunityEvent
- L21: symbol CommunityPanelProps
- L63: symbol createInvite
- L88: symbol changeRole

## `web/src/components/ControlCenterActionPanel.tsx`

- L9: symbol ActionLoadState
- L41: symbol loadActions
- L92: symbol actionGate
- L96: symbol runAction

## `web/src/components/ControlCenterChatPanel.tsx`

- L19: symbol ControlCenterViewer
- L25: symbol SeedAccount
- L46: symbol loadMessages
- L66: symbol saveMessages
- L250: symbol handleMessagesChange
- L256: symbol resetChat
- L260: symbol copyTranscript
- L277: symbol downloadTranscript
- L281: symbol exportMarkdown
- L285: symbol exportTranscript

## `web/src/components/ControlCenterDetailPanels.tsx`

- L7: symbol PanelMode
- L9: symbol DetailState
- L20: symbol loadDetails
- L70: symbol OperatorNextPanel
- L95: symbol RepoHygienePanel
- L118: symbol ReleaseEvidencePanel
- L183: symbol EngineBrainPanel
- L280: symbol ApiCostPanel
- L315: symbol AuditPanel
- L382: symbol RecommendationsPanel
- L397: symbol Metric
- L406: symbol CountPills
- L426: symbol PanelHeader
- L438: symbol formatTimestamp
- L444: symbol placeholderActions

## `web/src/components/ControlCenterEvidencePanel.tsx`

- L7: symbol EvidenceState
- L44: symbol loadEvidence
- L942: symbol MetricCard
- L952: symbol placeholderSprints
- L959: symbol placeholderReleaseEvidenceFiles
- L965: symbol placeholderActionAuditRecords
- L982: symbol placeholderRecommendations
- L990: symbol placeholderArtifactChecks
- L1000: symbol formatCheckName
- L1004: symbol renderCountPills
- L1024: symbol formatTimestamp
- L1030: symbol formatBytes
- L1037: symbol renderCostDrivers
- L1081: symbol EvidenceLink

## `web/src/components/ControlCenterLegacyPanels.tsx`

- L7: symbol LegacyResult
- L13: symbol LegacySnapshot
- L25: symbol LegacyState
- L36: symbol loadLegacy
- L92: symbol DashboardSummary
- L110: symbol AgentStatus
- L124: symbol ReleaseEvidence
- L139: symbol CommandDictionary
- L155: symbol RunnerLog
- L168: symbol PanelCard
- L185: symbol MetricLine
- L194: symbol CommandRow
- L211: symbol asRecord
- L215: symbol listValue

## `web/src/components/ControlCenterLiveProbe.tsx`

- L7: symbol ProbeState
- L18: symbol loadProbe

## `web/src/components/ControlCenterOpsGrid.tsx`

- L7: symbol OpsState
- L32: symbol loadOps
- L99: symbol placeholderTiles

## `web/src/components/ControlCenterShell.tsx`

- L15: symbol ControlCenterTab
- L31: symbol ToneOrb
- L127: symbol OverviewPanel
- L192: symbol TabSwitchBar
- L213: symbol CodexPanel
- L236: symbol LocalStatusPanel
- L245: symbol ActionsPanel
- L253: symbol EvidencePanel
- L267: symbol DocsPanel
- L294: symbol FoundationCleanupPanel
- L338: symbol LegacyInventoryPanel
- L384: symbol CommandRiskPanel
- L427: symbol PlatformMap
- L455: symbol CodexDock
- L479: symbol TimelinePanel

## `web/src/components/LoginPanel.tsx`

- L6: symbol AccountRole
- L8: symbol AuthUser
- L15: symbol LoginPanelProps
- L36: symbol submit

## `web/src/components/SessionManager.tsx`

- L7: symbol Session
- L14: symbol Props

## `web/src/components/StatusBar.tsx`

- L7: symbol Status
- L12: symbol StatusBarProps

## `web/src/lib/__tests__/chatQuality.test.ts`

- L21: symbol Saper
- L34: symbol Sample

## `web/src/lib/__tests__/controlCenterEvidence.test.ts`

- L51: symbol isolateEvidenceEnv

## `web/src/lib/__tests__/requestOriginGuard.test.ts`

- L4: symbol guardedRequest

## `web/src/lib/__tests__/sessionStorage.test.ts`

- L4: symbol MemoryStorage
- L14: symbol QuotaStorage

## `web/src/lib/api.ts`

- L4: symbol streamChat
- L14: symbol getStatus

## `web/src/lib/authCookies.ts`

- L4: symbol ctoaTokenCookieOptions

## `web/src/lib/authProxySanitizer.ts`

- L16: symbol sanitizeAuthProxyPayload
- L33: symbol authProxyCookieToken

## `web/src/lib/chatQuality.ts`

- L1: symbol ChatQualityLevel
- L3: symbol ChatQualityAssessment
- L9: symbol ChatPublicationDecision
- L16: symbol ChatReviewTemplate
- L22: symbol looksLikeCode
- L31: symbol countCodeLines
- L38: symbol evaluateControlCenterChatTemplate
- L65: symbol assessControlCenterChatQuality
- L121: symbol decideControlCenterChatPublication

## `web/src/lib/chatTranscript.ts`

- L4: symbol ChatTranscriptMetadata
- L12: symbol redactChatText
- L16: symbol redactControlCenterChatMessage
- L30: symbol redactControlCenterChatMessages
- L34: symbol formatMessage
- L52: symbol escapeMarkdown
- L56: symbol buildFence
- L62: symbol buildControlCenterChatTranscript
- L76: symbol buildControlCenterChatMarkdown
- L114: symbol buildControlCenterChatLog
- L126: symbol buildControlCenterChatTranscriptFileName
- L132: symbol buildControlCenterChatMarkdownFileName

## `web/src/lib/config.ts`

- L3: symbol isLocalHttpHost
- L8: symbol configuredUrl
- L45: symbol getServerApiUrl
- L49: symbol getPublicApiUrl

## `web/src/lib/controlCenterActions.ts`

- L14: symbol ControlCenterActor
- L20: symbol ControlCenterAction
- L34: symbol ControlCenterActionResult
- L43: symbol CommandSpec
- L50: symbol ActionDefinition
- L54: symbol AuditRecord
- L70: symbol ControlCenterAuthorizationError
- L80: symbol redactControlCenterAuditText
- L84: symbol sanitizeControlCenterActionOutput
- L92: symbol getWorkspaceRoot
- L109: symbol isExistingFile
- L117: symbol isExistingDirectory
- L125: symbol resolveControlCenterWorkspaceRoot
- L129: symbol resolveControlCenterWorkspaceFile
- L155: symbol resolveControlCenterPython
- L181: symbol pythonCommand
- L193: symbol actionCatalog
- L276: symbol listControlCenterActions
- L283: symbol getControlCenterAction
- L288: symbol runControlCenterAction
- L380: symbol appendAuditRecord

## `web/src/lib/controlCenterAuth.ts`

- L4: symbol ControlCenterViewer
- L10: symbol ControlCenterAuthStatus
- L12: symbol resolveControlCenterViewer

## `web/src/lib/controlCenterDisplayPath.ts`

- L3: symbol repoRoot
- L10: symbol isWindowsAbsolutePath
- L14: symbol toControlCenterDisplayPath
- L43: symbol toControlCenterDisplayConfig

## `web/src/lib/controlCenterEvidence.ts`

- L8: symbol ControlCenterEvidence
- L391: symbol ApiCostReportArtifact
- L401: symbol ReleaseEvidenceFile
- L412: symbol collectControlCenterEvidence
- L526: symbol collectOperatorBriefCard
- L615: symbol buildOperatorNextRecommendation
- L790: symbol isGuardedLiveCommand
- L794: symbol readJsonIfExists
- L807: symbol readBoundedTextFileIfExists
- L835: symbol collectReleaseEvidenceDrilldown
- L896: symbol readMarkdownTitle
- L912: symbol collectReleaseComparison
- L970: symbol collectActionAuditDrilldown
- L1072: symbol readBoundedControlCenterActionAuditLines
- L1121: symbol countBy
- L1130: symbol auditSummary
- L1138: symbol sanitizeText
- L1142: symbol collectArtifactHealth
- L1333: symbol collectOtclientHelperStatus
- L1425: symbol collectP6PluginHandoff
- L1490: symbol collectEngineBrainStatus
- L1650: symbol collectP7CockpitSmokeStatus
- L1693: symbol collectP7SafeWriteDryRunSmokeStatus
- L1758: symbol collectLatestAuditRecordForAction
- L1858: symbol isRecord
- L1862: symbol sanitizeCountMap
- L1874: symbol findGate
- L1880: symbol sha256IfExists
- L1893: symbol fileAgeMinutes
- L1905: symbol statIfExists
- L1914: symbol resolveEvidencePath
- L1925: symbol findLatestReleaseEvidence
- L1961: symbol countMarkdownFiles
- L1979: symbol listReleaseSprints

## `web/src/lib/controlCenterEvidenceAccess.ts`

- L4: symbol ControlCenterEvidenceAccess
- L20: symbol authorizeControlCenterEvidenceAccess
- L45: symbol denied

## `web/src/lib/controlCenterEvidenceConfig.ts`

- L3: symbol ControlCenterEvidenceConfig
- L34: symbol trimTrailingSeparators
- L38: symbol getRepoRoot
- L46: symbol resolveConfiguredPath
- L51: symbol configuredPath
- L55: symbol configuredPathFrom
- L64: symbol getControlCenterEvidenceConfig

## `web/src/lib/controlCenterMarkdownReport.ts`

- L8: symbol sanitizeControlCenterMarkdownReport
- L23: symbol trimPathSuffix

## `web/src/lib/controlCenterMarkdownReportFile.ts`

- L5: symbol ControlCenterMarkdownReportTooLargeError
- L12: symbol ControlCenterMarkdownReportUnsafePathError
- L19: symbol readBoundedControlCenterMarkdownReport

## `web/src/lib/controlCenterOps.ts`

- L5: symbol ControlCenterEvidence
- L11: symbol OpsStatus
- L13: symbol OpsTile
- L23: symbol LocalAuditAction
- L39: symbol ControlCenterOps
- L80: symbol collectControlCenterOps
- L198: symbol summarizeRepoHygiene
- L205: symbol summarizeApiCostReport
- L209: symbol summarizeAuditTrail
- L217: symbol summarizeEngineBrain
- L224: symbol readRecentAuditActions
- L252: symbol sanitizeOpsText

## `web/src/lib/controlCenterPolicy.ts`

- L1: symbol ControlCenterRiskClass
- L2: symbol ControlCenterRole
- L10: symbol controlCenterRoleMeets
- L14: symbol minimumRoleForRiskClass
- L20: symbol canRunControlCenterAction

## `web/src/lib/controlCenterRedaction.ts`

- L1: symbol redactControlCenterAuditText
- L22: symbol sanitizeControlCenterDisplayText

## `web/src/lib/controlCenterSnapshot.ts`

- L1: symbol ControlCenterSnapshot

## `web/src/lib/fetchWithTimeout.ts`

- L1: symbol fetchWithTimeout

## `web/src/lib/rateLimit.ts`

- L4: symbol RateWindow
- L9: symbol getClientIp
- L24: symbol trustProxyHeaders
- L29: symbol normalizeIp
- L34: symbol createIpRateLimiter

## `web/src/lib/requestOriginGuard.ts`

- L1: symbol SameOriginRequestValidation
- L6: symbol validateSameOriginRequest

## `web/src/lib/sessionStorage.ts`

- L3: symbol StoredMessage
- L11: symbol StoredSession
- L24: symbol sessionsKey
- L28: symbol activeKey
- L32: symbol normalizeMessage
- L64: symbol normalizeSession
- L88: symbol clampSessions
- L96: symbol loadUserSessions
- L107: symbol saveUserSessions
- L130: symbol loadActiveSessionId
- L138: symbol saveActiveSessionId

## `web/src/lib/tibiaOperationalState.ts`

- L13: symbol TibiaOperationalState
- L15: symbol RawSnapshot
- L23: symbol UpdateEvent
- L33: symbol SourceInventoryItem
- L48: symbol ClientCapabilities
- L66: symbol TelemetryEvent
- L73: symbol ConfigDryRunResult
- L89: symbol ClientReport
- L104: symbol TibiaSourcePayload
- L111: symbol TibiaSourceArchiveIndex
- L117: symbol defaultTibiaSources
- L207: symbol getTibiaSources
- L220: symbol defaultLatestUpdates
- L253: symbol getLatestUpdates
- L269: symbol getDiffLedger
- L282: symbol getClients
- L344: symbol getClientCapabilities
- L349: symbol getTelemetryEvents
- L372: symbol repoRoot
- L381: symbol clientReportPath
- L391: symbol readClientReport
- L411: symbol sourceArchiveIndexPath
- L421: symbol readSourceArchiveIndex
- L440: symbol isSourceArchiveIndex
- L454: symbol isSourceInventoryItem
- L468: symbol isRawSnapshot
- L475: symbol isUpdateEvent
- L489: symbol isSourceOperationalState
- L493: symbol isSourceFreshness
- L497: symbol isTimestamp
- L501: symbol isClientReport
- L527: symbol isBoundedString
- L531: symbol isNodeError
- L535: symbol validateConfigDryRun
- L563: symbol isRecord
