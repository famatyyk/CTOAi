# CTOA AI Toolkit Pack

Minimalny pakiet organizacji CTOA (10 agentow) pod prace 24/7 na VPS.

## Zawartosc
- agents/ctoa-agents.yaml
- prompts/braver-library.yaml
- scoring/tool-advisor-rules.yaml
- policies/ci-gate-policy.yaml
- workflows/backlog-sprint-001.yaml
- workflows/runbook-24x7.yaml
- runner/runner.py
- deploy/vps/SETUP.md
- .github/workflows/ctoa-pipeline.yml
- training/curriculum.md

## Szybki start
1. Skonfiguruj sekrety i environment `production` w GitHub.
2. Ustaw `required reviewers` na Ciebie dla environment `production`.
3. Uruchom workflow manualnie przez `workflow_dispatch`.

## Publikacja
Publikacja publiczna odbywa sie dopiero po:
1. PASS wszystkich gate'ow.
2. Twojej recznej akceptacji environment `production`.

## Tryb 24/7 na VPS
1. Runner tick co 15 min: `python3 runner/runner.py tick`
2. Raport live co godzine do GitHub Issue: `python3 runner/runner.py report --publish`
3. Konfiguracja Ubuntu/systemd: `deploy/vps/SETUP.md`

## Licencja
MIT
