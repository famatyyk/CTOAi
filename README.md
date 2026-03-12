# CTOA AI Toolkit Pack

Minimalny pakiet organizacji CTOA (10 agentow) pod prace 24/7 na VPS.

## Zawartosc
- agents/ctoa-agents.yaml
- prompts/braver-library.yaml
- prompts/mmo-lua-pack.yaml
- scoring/tool-advisor-rules.yaml
- scoring/tibia-tool-matrix.yaml
- policies/ci-gate-policy.yaml
- workflows/backlog-sprint-001.yaml
- workflows/runbook-24x7.yaml
- runner/runner.py
- runner/issue_sync.py
- deploy/vps/SETUP.md
- .github/workflows/ctoa-pipeline.yml
- .github/workflows/ctoa-issue-sync.yml
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

## Week 1 Automation
1. Backlog issue sync co godzine: `.github/workflows/ctoa-issue-sync.yml`
2. Zadania sprintu sa mapowane do issue `[CTOA-XXX]` przez `runner/issue_sync.py`.
3. Start realizacji sprintu obejmuje moduły Lua w `scripts/lua/` i testy opisowe w `tests/lua/`.
4. Dzienny komentarz insight pod issue #1: `.github/workflows/ctoa-daily-insights.yml`.
5. Insight zawiera trend 24h, alert taskow zastoju >24h i 3 propozycje do approval.
6. Auto-close po sukcesie gate: `.github/workflows/ctoa-close-on-gate.yml`.
7. Tygodniowy raport zarzadczy: `.github/workflows/ctoa-weekly-report.yml`.
8. Godzinowy status sync etykiet `status/*`: `.github/workflows/ctoa-status-sync.yml`.
9. Osobny komentarz SLA dla `WAITING_APPROVAL >12h` przez `runner/status_sync.py`.
10. Symulacja alertu SLA moze byc oznaczona przez `CTOA_SLA_ALERT_MODE=test`, wtedy komentarz dostaje widoczny znacznik `TEST`.

## Licencja
MIT
