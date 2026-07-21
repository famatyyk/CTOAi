-- ctoa_helper_heal_friend_execute_once.lua [CTOA OTClient Native]
-- P12 Heal Friend: one exact approved sandbox sio, then mandatory KILL/disarm.

local Bridge = rawget(_G, "CTOA_HELPER_HEAL_FRIEND_EXECUTE_ONCE") or {}
local state = Bridge.state or {armed=false, killed=false, consumed=false, attempt_count=0}
local controller = Bridge.controller or {}

local function text(value) if value == nil then return "" end return tostring(value) end
local function number(value) return tonumber(value) end
local function sha(value) return text(value):match("^[0-9a-f]+$") and #text(value) == 64 end
local function add(values, value) values[#values + 1] = value end
local function call(name, ...) local fn=controller[name]; if type(fn)~="function" then return nil end; local ok,value=pcall(fn,...); return ok and value or nil end
local function sandboxWorkDir() return text(call("work_dir")):lower():gsub("\\","/"):find("/solteriacodextest/client",1,true) ~= nil end
local function exactTargetName(value)
    local name=text(value):match("^%s*(.-)%s*$")
    return name~="" and #name<=40 and not name:find('[\r\n"]')
end

local function terminate(reason)
    state.armed=false; state.killed=true; state.consumed=true; state.kill_reason=text(reason)
end

function Bridge.configure(callbacks) controller=callbacks or {}; Bridge.controller=controller; return Bridge.contract() end
function Bridge.reset()
    state.armed=false; state.killed=false; state.consumed=false; state.attempt_count=0
    state.session_id=nil; state.plan_sha256=nil; state.p11_receipt_sha256=nil
    state.p12_equipment_receipt_sha256=nil; state.target_id=nil; state.target_name=nil
    state.whitelist_revision=nil; state.kill_reason=nil
    return {status="disarmed",runtime_actions=false}
end
function Bridge.kill(reason) terminate(reason or "operator_kill"); return {status="killed_and_disarmed",runtime_actions=false} end

function Bridge.arm(input)
    local data=input or {}; local blockers={}
    if state.armed then add(blockers,"already_armed") end
    if state.consumed then add(blockers,"bridge_consumed") end
    if data.sandbox~=true or not sandboxWorkDir() then add(blockers,"sandbox_required") end
    if data.operator_confirmed~=true or data.session_approved~=true or data.execution_approved~=true then add(blockers,"separate_approvals_required") end
    if data.runtime_disarmed~=true then add(blockers,"runtime_must_be_disarmed") end
    if data.live_promotion~=false or number(data.retry_budget)~=0 then add(blockers,"unsafe_runtime_policy") end
    if text(data.action)~="cast_exura_sio_exact_target" or text(data.spell)~="exura sio" then add(blockers,"action_mismatch") end
    if text(data.vocation)~="ed" then add(blockers,"vocation_must_be_ed") end
    if not number(data.target_id) or number(data.target_id)<=0 then add(blockers,"target_id_required") end
    if not exactTargetName(data.target_name) then add(blockers,"exact_target_name_required") end
    if number(data.hp_threshold)~=70 or number(data.max_range)~=7 then add(blockers,"target_policy_mismatch") end
    if not sha(data.plan_sha256) or not sha(data.p11_receipt_sha256) or not sha(data.p12_equipment_receipt_sha256) or not sha(data.whitelist_revision) then add(blockers,"hash_binding_required") end
    if text(data.session_id)=="" then add(blockers,"session_id_required") end
    if #blockers>0 then return false,table.concat(blockers,",") end
    state.armed=true; state.killed=false; state.consumed=false; state.session_id=text(data.session_id)
    state.plan_sha256=text(data.plan_sha256); state.p11_receipt_sha256=text(data.p11_receipt_sha256)
    state.p12_equipment_receipt_sha256=text(data.p12_equipment_receipt_sha256)
    state.target_id=number(data.target_id); state.target_name=text(data.target_name):match("^%s*(.-)%s*$"):lower()
    state.whitelist_revision=text(data.whitelist_revision)
    return true,{status="armed",attempt_count=state.attempt_count}
end

function Bridge.preview(observation, context)
    local item=observation or {}; local ctx=context or {}; local blockers={}
    if not state.armed or state.killed or state.consumed then add(blockers,"bridge_not_armed") end
    if text(ctx.session_id)~=text(state.session_id) then add(blockers,"session_mismatch") end
    if text(ctx.plan_sha256)~=text(state.plan_sha256) then add(blockers,"plan_hash_mismatch") end
    if text(ctx.p11_receipt_sha256)~=text(state.p11_receipt_sha256) then add(blockers,"p11_receipt_hash_mismatch") end
    if text(ctx.p12_equipment_receipt_sha256)~=text(state.p12_equipment_receipt_sha256) then add(blockers,"p12_equipment_receipt_hash_mismatch") end
    if text(ctx.vocation)~="ed" then add(blockers,"vocation_must_be_ed") end
    if item.schema_version~="ctoa.p12-heal-friend-execute-once-observation.v1" then add(blockers,"observation_schema_mismatch") end
    if item.online~="online" or item.alive~="alive" then add(blockers,"player_not_ready") end
    if item.protection_zone~="outside" then add(blockers,"protection_zone") end
    if item.cooldown~="ready" then add(blockers,"cooldown_not_ready") end
    if item.scan_complete~=true then add(blockers,"scan_incomplete") end
    for _,flag in ipairs({"dispatch_allowed","runtime_actions","executes_plan","execute_once_allowed","promotion_allowed","casts","talks"}) do
        if item[flag]~=false then add(blockers,"observation_"..flag.."_unsafe") end
    end
    local target=type(item.exact_target)=="table" and item.exact_target or {}
    if target.status~="observed" or number(target.match_count)~=1 then add(blockers,"exact_target_not_observed") end
    if number(target.target_id)~=number(state.target_id) or text(target.target_name):lower()~=text(state.target_name) then add(blockers,"exact_target_binding_mismatch") end
    if target.target_is_player~=true or target.target_is_self~=false or number(item.self_id)==number(state.target_id) then add(blockers,"target_identity_unsafe") end
    if target.target_party_member~=true then add(blockers,"target_not_party_member") end
    if target.target_same_floor~=true then add(blockers,"target_different_floor") end
    if target.target_visible~=true then add(blockers,"target_not_visible") end
    if not number(target.distance) or number(target.distance)<0 or number(target.distance)>7 then add(blockers,"target_out_of_range") end
    if not number(target.hp_percent) or number(target.hp_percent)<1 or number(target.hp_percent)>70 then add(blockers,"target_hp_not_ready") end
    local observed=number(item.observed_at_unix_ms); local now=number(ctx.now_unix_ms)
    if not observed or not now or now<observed or now-observed>1000 then add(blockers,"observation_not_fresh") end
    return {schema_version="ctoa.p12-heal-friend-execute-once-trace.v1",status=#blockers==0 and "ready" or "blocked",
        result="not_called",blockers=blockers,action="cast_exura_sio_exact_target",spell="exura sio",vocation="ed",
        target_id=state.target_id,attempt_count=state.attempt_count,retry_budget=0,dispatch_allowed=false,
        runtime_actions=false,execute_once_allowed=#blockers==0,live_promotion=false}
end

function Bridge.executeOnce(observation, context, executor)
    local trace=Bridge.preview(observation,context); local called=false
    if trace.status=="ready" and type(executor)=="function" and not state.consumed then
        state.attempt_count=state.attempt_count+1; trace.attempt_count=state.attempt_count; called=true
        local phrase='exura sio "'..state.target_name
        local ok,result=pcall(executor,phrase)
        trace.status=ok and result==true and "executed" or "failed"; trace.result=ok and result==true and "success" or "executor_failed"
        trace.dispatch_allowed=true; trace.runtime_actions=true
    end
    terminate("execute_once_attempt_complete")
    trace.executor_called=called; trace.plan_sha256=text((context or {}).plan_sha256)
    trace.p11_receipt_sha256=text((context or {}).p11_receipt_sha256)
    trace.p12_equipment_receipt_sha256=text((context or {}).p12_equipment_receipt_sha256)
    trace.execute_once_allowed=false; trace.live_promotion=false; trace.retry_scheduled=false
    trace.final_state="killed_and_disarmed"; trace.terminal_snapshot=Bridge.snapshot()
    return trace
end

function Bridge.snapshot() return {armed=state.armed,killed=state.killed,consumed=state.consumed,attempt_count=state.attempt_count,kill_reason=state.kill_reason} end

function Bridge.controlExecuteOnce(command)
    local data=command or {}; if not sandboxWorkDir() then call("status","P12 Heal Friend blocked: sandbox required"); return false end
    local planSha=text(data.plan_sha256); local p11Sha=text(data.p11_receipt_sha256)
    local equipmentSha=text(data.p12_equipment_receipt_sha256); local sessionId=text(data.session_id)
    local vocation=text(call("vocation")):lower()
    local armed,reason=Bridge.arm({sandbox=true,operator_confirmed=data.confirm==true,session_approved=data.session_approved==true,
        execution_approved=data.execution_approved==true,runtime_disarmed=true,live_promotion=false,retry_budget=number(data.retry_budget),
        action="cast_exura_sio_exact_target",spell="exura sio",vocation=vocation,target_id=number(data.target_id),target_name=data.target_name,
        hp_threshold=number(data.hp_threshold),max_range=number(data.max_range),whitelist_revision=data.whitelist_revision,
        plan_sha256=planSha,p11_receipt_sha256=p11Sha,p12_equipment_receipt_sha256=equipmentSha,session_id=sessionId})
    if not armed then Bridge.kill("arm_failed"); call("status","P12 Heal Friend blocked: "..text(reason)); return false end
    local now=number(call("now_ms")) or 0
    local binding={target_id=state.target_id,target_name=state.target_name,hp_threshold=70,max_range=7}
    local observation=call("observe",now,binding) or {}
    local trace=Bridge.executeOnce(observation,{session_id=sessionId,plan_sha256=planSha,p11_receipt_sha256=p11Sha,
        p12_equipment_receipt_sha256=equipmentSha,vocation=vocation,now_unix_ms=now},function(phrase) return call("cast",phrase)==true end)
    local blockers=type(trace.blockers)=="table" and table.concat(trace.blockers,",") or ""
    call("status","P12 Heal Friend execute-once: status="..text(trace.status).." result="..text(trace.result).." attempt="..text(trace.attempt_count)..
        " final="..text(trace.final_state).." retry="..text(trace.retry_scheduled).." armed="..text(trace.terminal_snapshot.armed)..
        " killed="..text(trace.terminal_snapshot.killed).." consumed="..text(trace.terminal_snapshot.consumed).." target="..text(state.target_id)..
        " plan="..planSha.." p11="..p11Sha.." p12e="..equipmentSha..(blockers~="" and (" blockers="..blockers) or ""))
    return trace.status=="executed"
end

function Bridge.contract() return {module="ctoa_helper_heal_friend_execute_once",phase="p12_heal_friend",mode="sandbox_execute_once",
    default_armed=false,exact_action="cast_exura_sio_exact_target",exact_vocation="ed",exact_spell="exura sio",
    exact_target_id_and_name=true,hp_threshold=70,max_range=7,retry_budget=0,mandatory_kill_and_disarm_after_attempt=true,
    requires_post_action_receipt=true,schedules_retry=false,live_promotion=false} end

Bridge.state=state; Bridge.controller=controller; _G.CTOA_HELPER_HEAL_FRIEND_EXECUTE_ONCE=Bridge; return Bridge
