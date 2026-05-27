"""CTOAI Foundry agent scaffold (two-stage routing: mini triage -> main reasoning)."""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

try:
    from openai import AzureOpenAI
except Exception:  # pragma: no cover - scaffold fallback when dependency is missing
    AzureOpenAI = None  # type: ignore[assignment]

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional in minimal environments
    load_dotenv = None  # type: ignore[assignment]


if load_dotenv:
    # Keep local scaffold self-contained: read settings from adjacent .env when present.
    load_dotenv(Path(__file__).with_name(".env"), override=False)


class IncidentInput(BaseModel):
    """Operator payload for incident analysis."""

    title: str = Field(..., min_length=3)
    details: str = Field(..., min_length=5)
    context: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Fact-first response contract aligned with CTOAI guardrails."""

    facts: list[str]
    inference: list[str]
    next_step: str
    triage: dict[str, Any]
    used_model: str


class CTOAIFoundryRouter:
    """Routes low-risk incidents to mini analysis, escalates complex cases to main model."""

    def __init__(self) -> None:
        self.endpoint = os.getenv("FOUNDRY_ENDPOINT", "")
        self.api_key = os.getenv("FOUNDRY_API_KEY", "")
        self.api_version = os.getenv("FOUNDRY_API_VERSION", "2024-10-21")
        self.main_model = os.getenv("MODEL_MAIN_DEPLOYMENT", "gpt-4.1")
        self.mini_model = os.getenv("MODEL_MINI_DEPLOYMENT", "gpt-4.1-mini")
        self.evidence_file = Path(
            os.getenv(
                "EVIDENCE_FILE",
                "runtime/evidence/aitk-agent/ctoai_foundry_agent.jsonl",
            )
        )

        self.client = None
        if AzureOpenAI and self.endpoint and self.api_key:
            self.client = AzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version,
            )

    def _append_evidence(self, kind: str, payload: dict[str, Any]) -> None:
        self.evidence_file.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "recorded_at": datetime.now(UTC).isoformat(),
            "kind": kind,
            "payload": payload,
        }
        with self.evidence_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True) + "\n")

    def _chat(self, model: str, prompt: str) -> str:
        if not self.client:
            return "{\"severity\":\"medium\",\"category\":\"ops\",\"needs_main\":true,\"reason\":\"client_not_configured\"}"

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are CTOAI incident analyst. Respond in strict JSON when requested. "
                        "Keep outputs factual and operational."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content or ""

    def triage(self, incident: IncidentInput) -> dict[str, Any]:
        triage_prompt = (
            "Classify this incident. Return strict JSON with fields: "
            "severity (low|medium|high), category, needs_main (bool), reason.\n"
            f"TITLE: {incident.title}\nDETAILS: {incident.details}\n"
            f"CONTEXT: {json.dumps(incident.context, ensure_ascii=True)}"
        )
        raw = self._chat(self.mini_model, triage_prompt)

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {
                "severity": "medium",
                "category": "ops",
                "needs_main": True,
                "reason": "triage_parse_failed",
                "raw": raw,
            }

        self._append_evidence("triage", {"input": incident.model_dump(), "triage": parsed})
        return parsed

    def finalize(self, incident: IncidentInput, triage: dict[str, Any]) -> AgentResponse:
        if not triage.get("needs_main", True):
            response = AgentResponse(
                facts=[
                    f"Incident categorized as {triage.get('category', 'ops')}",
                    f"Severity classified as {triage.get('severity', 'low')}",
                ],
                inference=["Mini triage determined no deep reasoning is required."],
                next_step="Execute standard runbook for low-risk incident and monitor for regressions.",
                triage=triage,
                used_model=self.mini_model,
            )
            self._append_evidence("final", response.model_dump())
            return response

        main_prompt = (
            "Prepare operator response using explicit structure: facts, inference, next_step. "
            "Return strict JSON with keys facts (array), inference (array), next_step (string).\n"
            f"TITLE: {incident.title}\nDETAILS: {incident.details}\n"
            f"TRIAGE: {json.dumps(triage, ensure_ascii=True)}\n"
            f"CONTEXT: {json.dumps(incident.context, ensure_ascii=True)}"
        )
        raw = self._chat(self.main_model, main_prompt)

        try:
            parsed = json.loads(raw)
            response = AgentResponse(
                facts=parsed.get("facts", []),
                inference=parsed.get("inference", []),
                next_step=parsed.get("next_step", "Escalate to operator for manual review."),
                triage=triage,
                used_model=self.main_model,
            )
        except json.JSONDecodeError:
            response = AgentResponse(
                facts=["Main model response was not valid JSON."],
                inference=["Fallback path used to preserve operator-safe output contract."],
                next_step="Escalate to operator and rerun analysis with stricter prompt.",
                triage=triage,
                used_model=self.main_model,
            )

        self._append_evidence("final", response.model_dump())
        return response

    def invoke(self, incident: IncidentInput) -> AgentResponse:
        triage = self.triage(incident)
        return self.finalize(incident, triage)


router = CTOAIFoundryRouter()
app = FastAPI(title="CTOAI Foundry Agent", version="0.1.0")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "main_model": router.main_model, "mini_model": router.mini_model}


@app.post("/invoke", response_model=AgentResponse)
def invoke(payload: IncidentInput) -> AgentResponse:
    return router.invoke(payload)


def run_cli() -> None:
    print("CTOAI Foundry Agent (CLI mode). Type 'exit' to quit.")
    while True:
        title = input("Title: ").strip()
        if title.lower() in {"exit", "quit"}:
            return
        details = input("Details: ").strip()
        if details.lower() in {"exit", "quit"}:
            return
        response = router.invoke(IncidentInput(title=title, details=details, context={}))
        print(json.dumps(response.model_dump(), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="CTOAI Foundry agent scaffold")
    parser.add_argument("--server", action="store_true", help="Run FastAPI server mode")
    parser.add_argument("--cli", action="store_true", help="Run interactive CLI mode")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8088)
    args = parser.parse_args()

    if args.server:
        import uvicorn

        uvicorn.run("app:app", host=args.host, port=args.port, reload=False)
        return

    run_cli()


if __name__ == "__main__":
    main()
