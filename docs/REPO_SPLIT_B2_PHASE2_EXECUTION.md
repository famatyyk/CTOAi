# B2 Phase-2 Extraction Execution

Tracker: #135
Date: 2026-05-31
Branch: feat/b2-phase2-extract-evals-runs
Status: IN_PROGRESS

## Scope

Move evaluation run artifacts from Core to Studio:
- evals/runs/run-001/**
- evals/runs/run-002/**
- evals/runs/run-003/**
- evals/runs/run-004/**

## Destination Confirmation

- ctoa-studio repo: https://github.com/famatyyk/ctoa-studio
- import commit: 2be7109
- destination path: evals/runs/**

## Core Policy Alignment

Kept in Core:
- evals/prompt-variants/**
- evals/azure-activity-agent-eval-dataset.template.jsonl
- evals/README-azure-agent-eval-dataset.md

## Notes

This phase removes generated run artifacts from Core and preserves reusable evaluation assets in Core.
