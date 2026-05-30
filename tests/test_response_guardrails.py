"""Regression tests for agent response guardrails."""

from pathlib import Path
import sys

import yaml


PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "runner"))

from response_guardrails import (
    is_response_compliant,
    validate_response,
    is_operational_structure_compliant,
    validate_operational_structure,
)


def test_prompt_library_declares_response_guardrails():
    prompt_library = yaml.safe_load(
        (PROJECT_ROOT / "prompts" / "braver-library.yaml").read_text(encoding="utf-8")
    )

    guardrails = prompt_library.get("response_guardrails", {})
    assert "<think>" in guardrails.get("forbidden_markers", [])
    assert "anything else you're curious about?" in guardrails.get("discouraged_endings", [])


def test_agent_roster_declares_response_guardrails():
    roster = yaml.safe_load(
        (PROJECT_ROOT / "agents" / "ctoa-agents.yaml").read_text(encoding="utf-8")
    )

    guardrails = roster.get("response_guardrails", [])
    assert any("<think>" in rule for rule in guardrails)
    assert any("generic follow-up question" in rule for rule in guardrails)


def test_hidden_reasoning_markers_are_rejected():
    response = "<think>internal</think>\nFinal answer."
    violations = validate_response(response)

    assert any("forbidden marker present" in item for item in violations)
    assert not is_response_compliant(response)


def test_empty_follow_up_is_rejected():
    response = "Here is the direct answer.\n\nAnything else you're curious about?"
    violations = validate_response(response)

    assert any("generic follow-up ending" in item for item in violations)


def test_meta_correction_is_rejected():
    response = "Actually, sorry for asking that, I shouldn't have done it."
    violations = validate_response(response)

    assert any("forbidden meta commentary" in item for item in violations)


def test_direct_corrected_answer_passes():
    response = (
        "Moge przeanalizowac dlugi dokument, jesli go dostarczysz. "
        "Szczegoly implementacyjne okna kontekstu sa wlasnosciowe, wiec opieram sie na publicznie "
        "dostepnych informacjach."
    )

    assert validate_response(response) == []
    assert is_response_compliant(response)

def test_operational_structure_missing_sections_is_rejected():
    response = "Facts: one item only."
    violations = validate_operational_structure(response)

    assert any("missing operational structure markers" in item for item in violations)
    assert not is_operational_structure_compliant(response)


def test_operational_structure_facts_inference_next_step_passes():
    response = (
        "Facts: CI gate for Sprint-061 is PASS.\n"
        "Inference: release risk is low after state alignment.\n"
        "Next Step: run Wave-2 sign-off and publish artifacts."
    )

    assert validate_operational_structure(response) == []
    assert is_operational_structure_compliant(response)