# CTOA Training Plan — v1.3.0

**Aktualizacja:** 2026-05-25  
**Wersja:** 1.3.0 (synchronizacja z obecnym Sprint-056 governance)

## Cele

Wdrożyć zespół agentów do stabilnej pracy 24/7 z naciskiem na TIBIA/OpenTibia/MMO/Lua.  
Każdy agent zna: BRAVE(R), Wave-1/Wave-2, PR-only release flow, validator chain, state sync oraz procedury VPS ops.

---

## Moduł 1 — BRAVE(R) Prompt Design (2h)

**Framework:** Business · Reasoning · Action · Value · Evidence · Reflection

### Teoria (45 min)

- Anatomia promptu BRAVE(R): 6 sekcji, każda ma konkretną funkcję
- Anti-ambiguity: zawsze podaj `success_criteria`, `output_format`, `fallback`
- Output contracts: agent MUSI zwrócić `objective`, `assumptions`, `evidence`, `acceptance_criteria`
- Guardrails: zakaz `<think>`, `TODO/FIXME`, pustych follow-upów, meta-komentarzy
- Zasada audytu: każdy wynik musi dać się obronić evidence packiem lub linkiem do artefaktu

### Szablony

Dostępne w `prompts/braver-library.yaml`:

| Szablon | Zastosowanie |
| --- | --- |
| `queen-ctoa` | Decyzje GO/NO-GO, plan 24h |
| `prompt-forge` | Generowanie i optymalizacja promptów |
| `tool-advisor` | Dobór narzędzia AI z uzasadnieniem |
| `lua-scripter` | Moduły Lua z testami |

### Ćwiczenie praktyczne — BRAVE(R)

> **Zadanie:** Napisz prompt dla `scout_agent` który przeskanuje nowy serwer OT i zwróci moduły Lua z polem `evidence` (snippet + hash). Format wyjścia: JSON. Fallback: jeśli serwer offline → zwróć `{"status": "SKIP", "reason": "server_unreachable"}`.
>
> **Kryterium PASS:** prompt zawiera wszystkie 6 sekcji BRAVE(R), output contract jest kompletny, brak `TODO`, evidence jest weryfikowalne.

## Moduł 2 — QA Gate and Safety (2h)

**Polityka:** `docs/SPRINT_GOVERNANCE.md` + `docs/VALIDATION_CHECKLIST.md`

### Kryteria PASS

Wszystkie poniższe muszą być spełnione:

- [ ] `unit_tests_passed` — testy jednostkowe zielone
- [ ] `integration_tests_passed` — testy integracyjne zielone
- [ ] `no_critical_security_findings` — brak OWASP Top 10 naruszeń
- [ ] `objective_met` — cel zadania osiągnięty wg acceptance criteria
- [ ] `minimal_docs_present` — docstring lub README zaktualizowany
- [ ] `evidence_pack_complete` — output, validator, state sync, repo hygiene i core guard są spójne

### Blokery release (automatyczny FAIL)

- `critical_test_failure` — jakikolwiek test FAIL
- `missing_evidence_of_execution` — brak logu/outputu z uruchomienia
- `policy_violation` — naruszenie guardrails (np. hardcoded secret)
- `missing_owner_approval` — brak approval w PR flow lub brak wymaganej ścieżki zatwierdzenia

### Raportowanie defektów

Format: `[SEVERITY] MODULE: opis (expected: X, got: Y)`  
Priorytety: `CRITICAL` > `HIGH` > `MEDIUM` (CRITICAL blokuje merge)

### Retest flow

1. Agent naprawia → commit z prefixem `fix:`
2. CI re-trigger automatyczny po push
3. Jeśli po 3 retestach nadal FAIL → eskalacja do `queen-ctoa`

### Ćwiczenie praktyczne — QA

> **Zadanie:** Weź wynik z `test_agents_all.py` (plik: `test_agents_all.py`). Zidentyfikuj które testy są FAIL, napisz raport w formacie powyżej, i zaproponuj fix dla pierwszego CRITICAL.
>
> **Kryterium PASS:** raport zgodny z formatem, co najmniej 1 fix zaproponowany z uzasadnieniem.

## Moduł 3 — GitHub CI Approval Flow (1h)

**Konfiguracja:** PR-only flow, plik: `.github/workflows/` + `.github/workflows/ctoa-pipeline.yml`

### Mechanizm

1. Push → GitHub Actions trigger
2. Testy automatyczne (unit + integration)
3. Jeśli PASS → czeka na `PR Quality Report` i review
4. Owner zatwierdza PR → merge do `main`
5. Jeśli owner odrzuca → branch wraca do `in-progress`

### Release gating

- Merge do `main` tylko przez PR z approval
- Tag `v*` tylko po przejściu CI + approval
- Rollback: `git revert <commit>` + re-tag z suffixem `-hotfix`
- Direct push do `main` tylko dla udokumentowanego incydentu i zgodnie z governance

### Ćwiczenie praktyczne — CI

> **Zadanie:** Opisz krok po kroku co się stanie jeśli `generator_agent` wypchnie moduł z `missing_evidence_of_execution`. Wskaż który krok CI to przechwytuje i jak wygląda approval flow w tym przypadku.
>
> **Kryterium PASS:** poprawny opis 5-krokowego flow, identyfikacja punktu blokady.

## Moduł 4 — MMO/Lua Engineering Standards (2h)

**Domena:** OpenTibia, Tibia-like serwery, Lua 5.1/5.4

### Modularność

- Jeden plik = jedna odpowiedzialność (np. `modules/spells/`, `modules/quests/`)
- Brak globalnych side-effects poza `dofile()` / `require()` entrpointami
- Wszystkie public API udokumentowane komentarzem `--- @param`, `--- @return`

### Testowalność

- Każdy moduł ma odpowiadający test w `tests/lua/`
- Test sprawdza: happy path, edge case (nil input, empty table), error handling
- Mock dla funkcji serwerowych (np. `getPlayerById`, `getTileThingByPos`)
- Każdy moduł ma evidence-ready output albo test fixture, które można podpiąć do release packa

### Observability

- Każda akcja loguje: `[MODULE][LEVEL] message (context)`
- Poziomy: `DEBUG` (dev only), `INFO`, `WARN`, `ERROR`
- Błędy krytyczne: `doSendMail` lub `print` do stderr + return `false`

### Przykład sprawnego modułu

```lua
--- Zwraca level gracza lub 0 jeśli nie znaleziono
--- @param player_id number
--- @return number
local function getPlayerLevel(player_id)
    local player = getPlayerById(player_id)
    if not player then
        print("[CTOA][WARN] getPlayerLevel: player_id=" .. tostring(player_id) .. " not found")
        return 0
    end
    return getPlayerLevel(player)
end
```

### Ćwiczenie praktyczne — Lua

> **Zadanie:** Weź dowolny plik z `readable_pack/modules/` i zrefaktoryzuj go spełniając: modularność, docstring API, 1 test (happy path + nil input).
>
> **Kryterium PASS:** moduł ma docstring, test przechodzi, brak global side-effects.

## Moduł 5 — VPS 24/7 Operations (1.5h)

**Środowisko:** VPS ops, `/opt/ctoa/`, systemd, PR-only governance

### Monitoring — kluczowe komendy

```bash
# Stan wszystkich serwisów CTOA
# Uwaga: glob ctoa-* rozwija się w bash/zsh; w innych powłokach dostosuj składnię.
# Większość poleceń systemctl/journalctl wymaga sudo lub konta z uprawnieniami roota.
systemctl list-units ctoa-* --no-pager

# Logi ostatnich 50 linii
journalctl -u ctoa-runner.service -n 50 --no-pager

# Szybki status backlogu i release evidence
python scripts/ops/sprint_state_sync.py --backlog workflows/backlog-sprint-056.yaml --state runtime/task-state.yaml --dry-run
python scripts/ops/run_validator_with_preflight.py scripts/ops/sprint056_validate.py --run-tests --json-out runtime/ci-artifacts/sprint-056-validation.json
python scripts/ops/wave_summary_utf8.py --sprint-id 056 --validation-json runtime/ci-artifacts/sprint-056-validation.json --output runtime/ci-artifacts/sprint-056-wave1-summary.txt --repo-hygiene-json runtime/repo-hygiene/latest.json --state-yaml runtime/task-state.yaml --backlog-yaml workflows/backlog-sprint-056.yaml
```

### Alerting

- Trigger: serwis w stanie `failed` → `HealService` przez `ctoa-vps.ps1`
- Trigger: task-state.yaml corrupt → backup + `sprint_state_sync.py` regeneruje stan
- Trigger: DB `must be owner of table` → sprawdź ownership: `\dt` w psql

### Standardowe SOP (procedure)

| Symptom | Diagnoza | Fix |
| --- | --- | --- |
| `ctoa-runner` failed | `ReportErrorDetails` | sprawdź YAML/env, napraw, `reset-failed` |
| validator FAIL | `sprint056_validate.py` | napraw backlog/flow/evidence, rerun validator |
| agent error w logach | `ShowPipelineProgress` | `KickoffNow` jeśli READY < 6 |
| serwis nie startuje | `journalctl -xe` | sprawdź env vars, porty, uprawnienia |
| DB permission error | `psql \dt` | przenieś ownership: `ALTER TABLE x OWNER TO ctoa` |

### Incident response — eskalacja

1. `ShowSystemHealth` → identyfikuj failed units
2. `HealService <name>` → próba auto-recovery
3. Jeśli fail po 3x → SSH manual debug
4. Jeśli krytyczny (DB down, disk full) → raport do owner natychmiast
5. Jeśli regression dotyczy release evidence, zatrzymaj release lane i odtwórz wave chain od validatora

### Ćwiczenie praktyczne — VPS

> **Zadanie:** Wykonaj `ShowSystemHealth` przez `ctoa-vps.ps1`. Na podstawie outputu: (a) zidentyfikuj wszystkie non-healthy units, (b) klasyfikuj jako CTOA/non-CTOA, (c) zaproponuj akcje naprawcze dla każdego CTOA failed.
>
> **Kryterium PASS:** poprawna klasyfikacja, przynajmniej 1 konkretna komenda naprawcza.

## Zaliczenie

### Wymagania ogólne

- 1 zadanie praktyczne na moduł (opisane powyżej)
- Każde zadanie musi uzyskać wynik **PASS** wg. kryterium modułu
- Całość musi przejść aktualny chain: validator + state sync + repo hygiene + core guard + wave summary

### Kryteria PASS/FAIL — macierz

| Moduł | Waga | Minimalne PASS |
| --- | --- | --- |
| BRAVE(R) Prompt Design | 25% | Kompletny output contract, 6 sekcji |
| QA Gate and Safety | 25% | Poprawny raport defektów, 1 fix |
| GitHub CI Approval Flow | 15% | Poprawny opis 5-krokowego flow |
| MMO/Lua Engineering | 20% | Działający test, docstring |
| VPS 24/7 Operations | 15% | Klasyfikacja units + akcje naprawcze |

### Wynik finalny

- **PASS:** wszystkie moduły PASS + evidence chain zielony
- **FAIL:** jakikolwiek moduł FAIL → retest tylko tego modułu (max 2x)
- **BLOKADA:** po 3 próbach FAIL → eskalacja do `queen-ctoa` z raportem
