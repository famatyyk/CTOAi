#!/usr/bin/env python3
"""Test all agents - Track A-D execution"""

from runner.agents import TrackAAgent, TrackBAgent, TrackCAgent, TrackDAgent
import json

def main():
    # Track A: Documentation
    print("\n" + "="*60)
    print("TRACK A: DOCUMENTATION COMPLETION")
    print("="*60 + "\n")
    
    task_a1 = {
        "id": "CTOA-031",
        "title": "Create disk emergency runbook",
        "domain": ["documentation", "ops"],
        "deliverables": ["docs/runbook-disk-emergency.md"]
    }
    result_a1 = TrackAAgent.execute(task_a1.get("id"), task_a1.get("deliverables"))
    print("CTOA-031 Result:")
    print(json.dumps(result_a1, indent=2))

    task_a2 = {
        "id": "CTOA-032",
        "title": "Create validation checklist",
        "domain": ["documentation", "reliability"],
        "deliverables": ["docs/VALIDATION_CHECKLIST.md"]
    }
    result_a2 = TrackAAgent.execute(task_a2.get("id"), task_a2.get("deliverables"))
    print("\nCTOA-032 Result:")
    print(json.dumps(result_a2, indent=2))

    # Track B: KPI Automation
    print("\n" + "="*60)
    print("TRACK B: KPI AUTOMATION")
    print("="*60 + "\n")
    
    task_b = {
        "id": "CTOA-035",
        "title": "Standardize weekly KPI report",
        "domain": ["kpi", "automation", "metrics"],
        "deliverables": ["runner/weekly_report.py"]
    }
    result_b = TrackBAgent.execute(task_b.get("id"), task_b.get("deliverables"))
    print("CTOA-035 Result:")
    print(json.dumps(result_b, indent=2))

    # Track C: Reliability
    print("\n" + "="*60)
    print("TRACK C: RELIABILITY GUARDRAILS")
    print("="*60 + "\n")
    
    task_c = {
        "id": "CTOA-039",
        "title": "Implement service drift detection",
        "domain": ["reliability", "guardrails", "automation"],
        "deliverables": ["runner/drift_checker.py"]
    }
    result_c = TrackCAgent.execute(task_c.get("id"), task_c.get("deliverables"))
    print("CTOA-039 Result:")
    print(json.dumps(result_c, indent=2))

    # Track D: Governance
    print("\n" + "="*60)
    print("TRACK D: GOVERNANCE")
    print("="*60 + "\n")
    
    task_d = {
        "id": "CTOA-041",
        "title": "Sprint closure gate formalization",
        "domain": ["governance"],
        "deliverables": ["docs/SPRINT_GOVERNANCE.md"]
    }
    result_d = TrackDAgent.execute(task_d.get("id"), task_d.get("deliverables"))
    print("CTOA-041 Result:")
    print(json.dumps(result_d, indent=2))

    print("\n" + "="*60)
    print("ALL AGENTS EXECUTED SUCCESSFULLY")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
