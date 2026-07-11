import json
from dataclasses import asdict

from scripts.ops import otclient_helper_shell_budget_plan as plan


def test_shell_budget_plan_measures_current_helper_pressure():
    budget = plan.build_plan()

    assert budget.name == "otclient-helper-shell-budget-plan"
    assert budget.status == "needs_extraction"
    assert budget.helper_line_count <= budget.helper_line_budget
    # Recovery Runtime Bridge v1 intentionally adds the bounded sandbox
    # executor and operator controls while remaining below the 4500-line
    # product budget. Keep this ratchet at the accepted post-bridge size.
    assert budget.helper_line_count <= 4484
    assert budget.helper_function_count > budget.helper_function_budget
    assert budget.helper_function_count <= 163
    assert budget.over_line_budget_by == 0
    assert budget.over_function_budget_by == budget.helper_function_count - budget.helper_function_budget
    assert budget.under_hard_ceiling is True
    assert budget.top_domains
    assert budget.next_extraction_domains
    assert "ShellBudgetPlan is repo-only static analysis" in budget.live_safety


def test_shell_budget_plan_has_ranked_domain_guidance():
    budget = plan.build_plan()
    top_domains = [item.domain for item in budget.top_domains]
    candidate_domains = set(budget.next_extraction_domains)

    assert "shell_misc" in top_domains
    assert candidate_domains <= set(top_domains)
    assert "shell_misc" not in candidate_domains
    assert any(
        domain in candidate_domains
        for domain in {
            "ui_builder",
            "profile_persistence",
            "runtime_combat",
            "runtime_cavebot",
            "diagnostics_smoke",
            "input_contracts",
        }
    )
    for domain in budget.top_domains:
        assert domain.function_count > 0
        assert domain.line_count > 0
        assert domain.largest_functions
        assert domain.next_action


def test_shell_budget_plan_uses_lua_block_ends_not_next_function():
    source = """
local function first(value)
    if value then
        return function()
            return "not an end"
        end
    end
    return nil
end

if externalModules then
    externalModules.getModuleLanes()
end

local function second()
    return "done"
end
"""

    spans = plan.parse_function_spans(source)

    assert [(span.name, span.start_line, span.end_line) for span in spans] == [
        ("first", 2, 9),
        ("second", 15, 17),
    ]


def test_shell_budget_plan_writes_json_and_markdown(tmp_path):
    budget = plan.build_plan()
    json_out = tmp_path / "helper_shell_budget_plan.json"
    markdown_out = tmp_path / "solteria_helper_shell_budget_plan.md"

    plan.write_json_atomic(json_out, asdict(budget))
    plan.write_text_atomic(markdown_out, plan.render_markdown(budget))

    payload = json.loads(json_out.read_text(encoding="utf-8"))
    markdown = markdown_out.read_text(encoding="utf-8")

    assert payload["status"] == "needs_extraction"
    assert payload["under_hard_ceiling"] is True
    assert payload["top_domains"]
    assert "# Solteria Helper Shell Budget Plan" in markdown
    assert "## Top Domains" in markdown
    assert "## Largest Functions" in markdown
    assert "HelperShellBudgetPlanStaticSmoke" in markdown
