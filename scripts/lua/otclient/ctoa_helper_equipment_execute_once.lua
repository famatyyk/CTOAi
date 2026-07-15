-- ctoa_helper_equipment_execute_once.lua [CTOA OTClient Native]
-- P12 Equipment: one approved sandbox ring move request, then mandatory KILL/disarm.

local Bridge = rawget(_G, "CTOA_HELPER_EQUIPMENT_EXECUTE_ONCE") or {}
local state = Bridge.state or {armed=false, killed=false, consumed=false, attempt_count=0}
local controller = Bridge.controller or {}

local function text(value) if value == nil then return "" end return tostring(value) end
local function number(value) return tonumber(value) end
local function sha(value) return text(value):match("^[0-9a-f]+$") and #text(value) == 64 end
local function add(values, value) values[#values + 1] = value end
local function call(name, ...) local fn=controller[name]; if type(fn)~="function" then return nil end; local ok,value=pcall(fn,...); return ok and value or nil end
local function sandboxWorkDir() return text(call("work_dir")):lower():gsub("\\","/"):find("/solteriacodextest/client",1,true) ~= nil end

local function terminate(reason)
    state.armed=false; state.killed=true; state.consumed=true; state.kill_reason=text(reason)
end

function Bridge.configure(callbacks) controller=callbacks or {}; Bridge.controller=controller; return Bridge.contract() end
function Bridge.reset()
    state.armed=false; state.killed=false; state.consumed=false; state.attempt_count=0
    state.session_id=nil; state.plan_sha256=nil; state.p10_receipt_sha256=nil; state.kill_reason=nil
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
    if text(data.action)~="move_ring_candidate_to_equipment_slot" then add(blockers,"action_mismatch") end
    if number(data.before_item_id)~=3096 or number(data.candidate_item_id)~=3097 then add(blockers,"ring_id_mismatch") end
    if not sha(data.plan_sha256) or not sha(data.p10_receipt_sha256) then add(blockers,"hash_binding_required") end
    if text(data.session_id)=="" then add(blockers,"session_id_required") end
    if #blockers>0 then return false,table.concat(blockers,",") end
    state.armed=true; state.killed=false; state.consumed=false; state.session_id=text(data.session_id)
    state.plan_sha256=text(data.plan_sha256); state.p10_receipt_sha256=text(data.p10_receipt_sha256)
    return true,{status="armed",attempt_count=state.attempt_count}
end

function Bridge.preview(observation, context)
    local item=observation or {}; local ctx=context or {}; local blockers={}
    if not state.armed or state.killed or state.consumed then add(blockers,"bridge_not_armed") end
    if text(ctx.session_id)~=text(state.session_id) then add(blockers,"session_mismatch") end
    if text(ctx.plan_sha256)~=text(state.plan_sha256) then add(blockers,"plan_hash_mismatch") end
    if text(ctx.p10_receipt_sha256)~=text(state.p10_receipt_sha256) then add(blockers,"p10_receipt_hash_mismatch") end
    if item.online~="online" or item.alive~="alive" then add(blockers,"player_not_ready") end
    if item.protection_zone~="outside" then add(blockers,"protection_zone") end
    if item.inventory_api_available~=true or item.containers_complete~=true then add(blockers,"inventory_incomplete") end
    local ring=type(item.ring)=="table" and item.ring or {}
    if ring.present~=true or number(ring.item_id)~=3096 or number(ring.count)~=1 then add(blockers,"equipped_ring_mismatch") end
    local matches={}
    for _,candidate in ipairs(type(item.candidates)=="table" and item.candidates or {}) do
        if number(candidate.item_id)==3097 then matches[#matches+1]=candidate end
    end
    if #matches~=1 then add(blockers,"candidate_ring_not_unique") else
        local candidate=matches[1]
        if number(candidate.container_id)~=number(ctx.source_container_id) or number(candidate.slot_index)~=number(ctx.source_slot_index) or number(candidate.count)~=1 then
            add(blockers,"candidate_location_drift")
        end
    end
    local observed=number(item.observed_at_unix_ms); local now=number(ctx.now_unix_ms)
    if not observed or not now or now<observed or now-observed>1000 then add(blockers,"observation_not_fresh") end
    return {schema_version="ctoa.p12-equipment-execute-once-trace.v1",status=#blockers==0 and "ready" or "blocked",
        result="not_called",blockers=blockers,action="move_ring_candidate_to_equipment_slot",attempt_count=state.attempt_count,
        retry_budget=0,dispatch_allowed=false,runtime_actions=false,execute_once_allowed=#blockers==0,live_promotion=false}
end

function Bridge.executeOnce(observation, context, executor)
    local trace=Bridge.preview(observation,context); local called=false
    if trace.status=="ready" and type(executor)=="function" and not state.consumed then
        state.attempt_count=state.attempt_count+1; trace.attempt_count=state.attempt_count; called=true
        local ok,result=pcall(executor,{container_id=number(context.source_container_id),slot_index=number(context.source_slot_index),item_id=3097,count=1})
        trace.status=ok and result==true and "dispatched" or "failed"; trace.result=ok and result==true and "requested" or "executor_failed"
        trace.dispatch_allowed=true; trace.runtime_actions=true
    end
    terminate("execute_once_attempt_complete")
    trace.executor_called=called; trace.plan_sha256=text((context or {}).plan_sha256); trace.p10_receipt_sha256=text((context or {}).p10_receipt_sha256)
    trace.execute_once_allowed=false; trace.live_promotion=false; trace.retry_scheduled=false; trace.final_state="killed_and_disarmed"; trace.terminal_snapshot=Bridge.snapshot()
    return trace
end

function Bridge.snapshot() return {armed=state.armed,killed=state.killed,consumed=state.consumed,attempt_count=state.attempt_count,kill_reason=state.kill_reason} end

function Bridge.controlExecuteOnce(command)
    local data=command or {}; if not sandboxWorkDir() then call("status","P12 Equipment blocked: sandbox required"); return false end
    local planSha=text(data.plan_sha256); local receiptSha=text(data.p10_receipt_sha256); local sessionId=text(data.session_id)
    local armed,reason=Bridge.arm({sandbox=true,operator_confirmed=data.confirm==true,session_approved=data.session_approved==true,
        execution_approved=data.execution_approved==true,runtime_disarmed=true,live_promotion=false,retry_budget=number(data.retry_budget),
        action="move_ring_candidate_to_equipment_slot",before_item_id=number(data.before_item_id),candidate_item_id=number(data.candidate_item_id),
        plan_sha256=planSha,p10_receipt_sha256=receiptSha,session_id=sessionId})
    if not armed then Bridge.kill("arm_failed"); call("status","P12 Equipment blocked: "..text(reason)); return false end
    local now=number(call("now_ms")) or 0; local observation=call("observe",now) or {}
    local trace=Bridge.executeOnce(observation,{session_id=sessionId,plan_sha256=planSha,p10_receipt_sha256=receiptSha,
        source_container_id=number(data.source_container_id),source_slot_index=number(data.source_slot_index),now_unix_ms=now},function(payload) return call("move",payload)==true end)
    local blockers=type(trace.blockers)=="table" and table.concat(trace.blockers,",") or ""
    call("status","P12 Equipment execute-once: status="..text(trace.status).." result="..text(trace.result).." attempt="..text(trace.attempt_count)..
        " final="..text(trace.final_state).." retry="..text(trace.retry_scheduled).." armed="..text(trace.terminal_snapshot.armed)..
        " killed="..text(trace.terminal_snapshot.killed).." consumed="..text(trace.terminal_snapshot.consumed).." plan="..planSha.." p10="..receiptSha..
        (blockers~="" and (" blockers="..blockers) or ""))
    return trace.status=="dispatched"
end

function Bridge.contract() return {module="ctoa_helper_equipment_execute_once",phase="p12_equipment",mode="sandbox_execute_once",
    default_armed=false,exact_action="move_ring_candidate_to_equipment_slot",before_item_id=3096,candidate_item_id=3097,
    retry_budget=0,mandatory_kill_and_disarm_after_attempt=true,requires_post_action_receipt=true,schedules_retry=false,live_promotion=false} end

Bridge.state=state; Bridge.controller=controller; _G.CTOA_HELPER_EQUIPMENT_EXECUTE_ONCE=Bridge; return Bridge
