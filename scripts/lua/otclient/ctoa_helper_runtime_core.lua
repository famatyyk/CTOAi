-- ctoa_helper_runtime_core.lua [CTOA OTClient Native]
-- Passive runtime orchestration core: registry, event bus, and budgeted scheduler.

local RuntimeCore = rawget(_G, "CTOA_HELPER_RUNTIME_CORE") or {}

local DEFAULT_TICK_BUDGET_MS = 4
local DEFAULT_MAX_TASKS_PER_TICK = 8
local DEFAULT_FAILURE_BACKOFF_MS = 1000

local modules = RuntimeCore.modules or {}
local moduleOrder = RuntimeCore.module_order or {}
local subscribers = RuntimeCore.subscribers or {}
local tasks = RuntimeCore.tasks or {}
local taskOrder = RuntimeCore.task_order or {}
local schedulerCursor = tonumber(RuntimeCore.scheduler_cursor) or 1
local metrics = RuntimeCore.metrics or {
    ticks = 0,
    tasks_run = 0,
    tasks_deferred = 0,
    task_failures = 0,
    events_published = 0,
    handler_failures = 0,
    last_tick_elapsed_ms = 0,
}

local function numberValue(value, fallback, minimum)
    local parsed = tonumber(value)
    if not parsed then
        parsed = fallback
    end
    if minimum and parsed < minimum then
        parsed = minimum
    end
    return parsed
end

local function copyTable(value)
    if type(value) ~= "table" then
        return value
    end
    local result = {}
    for key, item in pairs(value) do
        result[key] = copyTable(item)
    end
    return result
end

local function safeNow(nowFn)
    if type(nowFn) == "function" then
        local ok, value = pcall(nowFn)
        if ok and tonumber(value) then
            return tonumber(value)
        end
    end
    if g_clock and type(g_clock.millis) == "function" then
        local ok, value = pcall(g_clock.millis)
        if ok and tonumber(value) then
            return tonumber(value)
        end
    end
    return math.floor(os.clock() * 1000)
end

local function sortedCopy(list)
    local result = {}
    for index, value in ipairs(list or {}) do
        result[index] = value
    end
    table.sort(result, function(left, right)
        return tostring(left) < tostring(right)
    end)
    return result
end

function RuntimeCore.registerModule(spec)
    local item = spec or {}
    local id = tostring(item.id or "")
    if id == "" then
        return false, "module_id_required"
    end
    if modules[id] then
        return false, "module_already_registered"
    end
    modules[id] = {
        id = id,
        mode = tostring(item.mode or "observer"),
        enabled = item.enabled == true,
        runtime_actions = false,
        dependencies = sortedCopy(item.dependencies),
        healthcheck = item.healthcheck,
        metadata = copyTable(item.metadata or {}),
    }
    moduleOrder[#moduleOrder + 1] = id
    return true, modules[id]
end

function RuntimeCore.moduleSnapshot()
    local result = {}
    for _, id in ipairs(moduleOrder) do
        result[#result + 1] = copyTable(modules[id])
        result[#result].healthcheck = nil
    end
    return result
end

function RuntimeCore.moduleHealth(id)
    local item = modules[tostring(id or "")]
    if not item then
        return {status = "missing", module_id = tostring(id or "unknown")}
    end
    if type(item.healthcheck) ~= "function" then
        return {status = "unknown", module_id = item.id}
    end
    local ok, result = pcall(item.healthcheck)
    if not ok then
        return {status = "failed", module_id = item.id, reason = tostring(result)}
    end
    if type(result) == "table" then
        result.module_id = result.module_id or item.id
        return result
    end
    return {status = result == true and "ready" or "not_ready", module_id = item.id}
end

function RuntimeCore.subscribe(eventName, handler, owner)
    local name = tostring(eventName or "")
    if name == "" or type(handler) ~= "function" then
        return false, "event_and_handler_required"
    end
    subscribers[name] = subscribers[name] or {}
    subscribers[name][#subscribers[name] + 1] = {
        handler = handler,
        owner = tostring(owner or "anonymous"),
    }
    return true
end

function RuntimeCore.publish(eventName, payload)
    local name = tostring(eventName or "")
    local delivered = 0
    local failures = {}
    metrics.events_published = metrics.events_published + 1
    for _, subscriber in ipairs(subscribers[name] or {}) do
        local ok, err = pcall(subscriber.handler, payload, name)
        if ok then
            delivered = delivered + 1
        else
            metrics.handler_failures = metrics.handler_failures + 1
            failures[#failures + 1] = {
                owner = subscriber.owner,
                reason = tostring(err),
            }
        end
    end
    return {event = name, delivered = delivered, failures = failures}
end

function RuntimeCore.registerTask(spec)
    local item = spec or {}
    local id = tostring(item.id or "")
    if id == "" or type(item.run) ~= "function" then
        return false, "task_id_and_run_required"
    end
    if tasks[id] then
        return false, "task_already_registered"
    end
    tasks[id] = {
        id = id,
        owner = tostring(item.owner or "runtime_core"),
        interval_ms = numberValue(item.interval_ms, 1000, 50),
        enabled = item.enabled == true,
        observer_only = item.observer_only ~= false,
        runtime_actions = false,
        next_run_ms = numberValue(item.next_run_ms, 0, 0),
        failure_backoff_ms = numberValue(item.failure_backoff_ms, DEFAULT_FAILURE_BACKOFF_MS, 100),
        run = item.run,
        runs = 0,
        failures = 0,
        last_elapsed_ms = 0,
    }
    taskOrder[#taskOrder + 1] = id
    return true, tasks[id]
end

function RuntimeCore.setTaskEnabled(id, enabled)
    local task = tasks[tostring(id or "")]
    if not task then
        return false, "task_not_found"
    end
    task.enabled = enabled == true
    return true
end

function RuntimeCore.taskSnapshot()
    local result = {}
    for _, id in ipairs(taskOrder) do
        local task = copyTable(tasks[id])
        task.run = nil
        result[#result + 1] = task
    end
    return result
end

function RuntimeCore.runDue(nowMs, options)
    local opts = options or {}
    local nowFn = opts.now_fn
    local tickStarted = safeNow(nowFn)
    local now = numberValue(nowMs, tickStarted, 0)
    local budgetMs = numberValue(opts.budget_ms, DEFAULT_TICK_BUDGET_MS, 1)
    local maxTasks = numberValue(opts.max_tasks, DEFAULT_MAX_TASKS_PER_TICK, 1)
    local result = {ran = {}, deferred = {}, failures = {}, budget_ms = budgetMs}

    metrics.ticks = metrics.ticks + 1
    local taskCount = #taskOrder
    local firstDeferredIndex = nil
    for offset = 0, taskCount - 1 do
        local index = ((schedulerCursor + offset - 1) % taskCount) + 1
        local id = taskOrder[index]
        local task = tasks[id]
        if task.enabled and now >= task.next_run_ms then
            local elapsed = safeNow(nowFn) - tickStarted
            if #result.ran >= maxTasks or elapsed >= budgetMs then
                result.deferred[#result.deferred + 1] = id
                metrics.tasks_deferred = metrics.tasks_deferred + 1
                firstDeferredIndex = firstDeferredIndex or index
            else
                local started = safeNow(nowFn)
                local ok, err = pcall(task.run, {now_ms = now, task_id = id, observer_only = task.observer_only})
                local finished = safeNow(nowFn)
                task.last_elapsed_ms = math.max(0, finished - started)
                task.runs = task.runs + 1
                metrics.tasks_run = metrics.tasks_run + 1
                result.ran[#result.ran + 1] = id
                if ok then
                    task.next_run_ms = now + task.interval_ms
                else
                    task.failures = task.failures + 1
                    metrics.task_failures = metrics.task_failures + 1
                    task.next_run_ms = now + task.failure_backoff_ms
                    result.failures[#result.failures + 1] = {task_id = id, reason = tostring(err)}
                end
            end
        end
    end
    if taskCount > 0 then
        schedulerCursor = firstDeferredIndex or ((schedulerCursor % taskCount) + 1)
        RuntimeCore.scheduler_cursor = schedulerCursor
    end
    metrics.last_tick_elapsed_ms = math.max(0, safeNow(nowFn) - tickStarted)
    result.elapsed_ms = metrics.last_tick_elapsed_ms
    return result
end

function RuntimeCore.metricsSnapshot()
    return copyTable(metrics)
end

function RuntimeCore.statusSnapshot()
    local taskStates = {}
    local enabledTasks = 0
    local failedTasks = 0
    for _, id in ipairs(taskOrder) do
        local task = tasks[id]
        if task.enabled then
            enabledTasks = enabledTasks + 1
        end
        if task.failures > 0 then
            failedTasks = failedTasks + 1
        end
        taskStates[#taskStates + 1] = {
            id = task.id,
            owner = task.owner,
            enabled = task.enabled,
            observer_only = task.observer_only,
            runtime_actions = false,
            interval_ms = task.interval_ms,
            next_run_ms = task.next_run_ms,
            runs = task.runs,
            failures = task.failures,
            last_elapsed_ms = task.last_elapsed_ms,
        }
    end
    return {
        schema_version = "ctoa.runtime-core.v1",
        mode = "passive",
        runtime_actions = false,
        registered_modules = #moduleOrder,
        registered_tasks = #taskOrder,
        enabled_tasks = enabledTasks,
        disabled_tasks = #taskOrder - enabledTasks,
        failed_tasks = failedTasks,
        ticks = metrics.ticks,
        tasks_run = metrics.tasks_run,
        tasks_deferred = metrics.tasks_deferred,
        task_failures = metrics.task_failures,
        handler_failures = metrics.handler_failures,
        last_tick_elapsed_ms = metrics.last_tick_elapsed_ms,
        scheduler_cursor = schedulerCursor,
        tasks = taskStates,
    }
end

function RuntimeCore.contract()
    return {
        mode = "passive",
        runtime_actions = false,
        executes_plans = false,
        casts = false,
        talks = false,
        uses_items = false,
        walks = false,
        attacks = false,
        owns_module_registry = true,
        owns_event_bus = true,
        owns_budgeted_scheduler = true,
        scheduler_fairness = "round_robin",
        owns_status_snapshot = true,
        default_tick_budget_ms = DEFAULT_TICK_BUDGET_MS,
        default_max_tasks_per_tick = DEFAULT_MAX_TASKS_PER_TICK,
        default_tasks_enabled = false,
    }
end

RuntimeCore.modules = modules
RuntimeCore.module_order = moduleOrder
RuntimeCore.subscribers = subscribers
RuntimeCore.tasks = tasks
RuntimeCore.task_order = taskOrder
RuntimeCore.scheduler_cursor = schedulerCursor
RuntimeCore.metrics = metrics

_G.CTOA_HELPER_RUNTIME_CORE = RuntimeCore
return RuntimeCore
