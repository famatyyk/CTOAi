# CTOA Training Plan — v1.2.0

**Aktualizacja:** 2026-03-25  
**Wersja:** 1.2.0 (rozbudowana dla release pack CTOA-147)

## Cele
Wdrożyć zespół agentów do stabilnej pracy 24/7 z naciskiem na TIBIA/OpenTibia/MMO/Lua.  
Każdy agent zna: BRAVE(R), CI Gate, Lua standards i procedury VPS ops.

---

## Moduł 1 — BRAVE(R) Prompt Design (2h)

**Framework:** Business · Reasoning · Action · Value · Evidence · Reflection

### Teoria (45 min)
- Anatomia promptu BRAVE(R): 6 sekcji, każda ma konkretną funkcję
- Anti-ambiguity: zawsze podaj `success_criteria`, `output_format`, `fallback`
- Output contracts: agent MUSI zwrócić `objective`, `assumptions`, `evidence`, `acceptance_criteria`
- Guardrails: zakaz `<think>`, `TODO/FIXME`, pustych follow-upów, meta-komentarzy

### Szablony (dostępne w `prompts/braver-library.yaml`)
| Szablon | Zastosowanie |
|---|---|
| `queen-ctoa` | Decyzje GO/NO-GO, plan 24h |
| `prompt-forge` | Generowanie i optymalizacja promptów |
| `tool-advisor` | Dobór narzędzia AI z uzasadnieniem |
| `lua-scripter` | Moduły Lua z testami |

### Ćwiczenie praktyczne
> **Zadanie:** Napisz prompt dla `scout_agent` który przeskanuje nowy serwer OT i zwróci moduły Lua z polem `evidence` (snippet + hash). Format wyjścia: JSON. Fallback: jeśli serwer offline → zwróć `{"status": "SKIP", "reason": "server_unreachable"}`.
>
> **Kryterium PASS:** prompt zawiera wszystkie 6 sekcji BRAVE(R), output contract jest kompletny, brak `TODO`.

---

## Moduł 2 — QA Gate and Safety (2h)

**Polityka:** `policies/ci-gate-policy.yaml`

### Kryteria PASS
Wszystkie poniższe muszą być spełnione:
- [ ] `unit_tests_passed` — testy jednostkowe zielone
- [ ] `integration_tests_passed` — testy integracyjne zielone
- [ ] `no_critical_security_findings` — brak OWASP Top 10 naruszeń
- [ ] `objective_met` — cel zadania osiągnięty wg acceptance criteria
- [ ] `minimal_docs_present` — docstring lub README zaktualizowany

### Blokery release (automatyczny FAIL)
- `critical_test_failure` — jakikolwiek test FAIL
- `missing_evidence_of_execution` — brak logu/outputu z uruchomienia
- `policy_violation` — naruszenie guardrails (np. hardcoded secret)
- `missing_owner_approval` — brak approval w GitHub Environment `production`

### Raportowanie defektów
Format: `[SEVERITY] MODULE: opis (expected: X, got: Y)`  
Priorytety: `CRITICAL` > `HIGH` > `MEDIUM` (CRITICAL blokuje merge)

### Retest flow
1. Agent naprawia → commit z prefixem `fix:`
2. CI re-trigger automatyczny po push
3. Jeśli po 3 retestach nadal FAIL → eskalacja do `queen-ctoa`

### Ćwiczenie praktyczne
> **Zadanie:** Weź wynik z `test_agents_all.py` (plik: `test_agents_all.py`). Zidentyfikuj które testy są FAIL, napisz raport w formacie powyżej, i zaproponuj fix dla pierwszego CRITICAL.
>
> **Kryterium PASS:** raport zgodny z formatem, co najmniej 1 fix zaproponowany z uzasadnieniem.

---

## Moduł 3 — GitHub CI Approval Flow (1h)

**Konfiguracja:** GitHub Environment `production`, plik: `.github/workflows/`

### Mechanizm
1. Push → GitHub Actions trigger
2. Testy automatyczne (unit + integration)
3. Jeśli PASS → czeka na approval w Environment `production`
4. Owner zatwierdza → publikacja do `main`
5. Jeśli owner odrzuca → branch wraca do `in-progress`

### Release gating
- Merge do `main` tylko przez PR z approval
- Tag `v*` tylko po przejściu CI + approval
- Rollback: `git revert <commit>` + re-tag z suffixem `-hotfix`

### Ćwiczenie praktyczne
> **Zadanie:** Opisz krok po kroku co się stanie jeśli `generator_agent` wypchnie moduł z `missing_evidence_of_execution`. Wskaż który krok CI to przechwytuje i jak wygląda approval flow w tym przypadku.
>
> **Kryterium PASS:** poprawny opis 5-krokowego flow, identyfikacja punktu blokady.

---

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

### Ćwiczenie praktyczne
> **Zadanie:** Weź dowolny plik z `readable_pack/modules/` i zrefaktoryzuj go spełniając: modularność, docstring API, 1 test (happy path + nil input).
>
> **Kryterium PASS:** moduł ma docstring, test przechodzi, brak global side-effects.

---

## Moduł 5 — VPS 24/7 Operations (1.5h)

**Środowisko:** root@46.225.110.52, `/opt/ctoa/`, systemd

### Monitoring — kluczowe komendy
```bash
# Stan wszystkich serwisów CTOA
# Uwaga: glob ctoa-* rozwija się w bash/zsh; w innych powłokach dostosuj składnię.
# Większość poleceń systemctl/journalctl wymaga sudo lub konta z uprawnieniami roota.
systemctl list-units ctoa-* --no-pager

# Logi ostatnich 50 linii
journalctl -u ctoa-runner.service -n 50 --no-pager

# Stan bazy danych
psql -U ctoa -d ctoa -c "SELECT count(*) FROM modules WHERE status='READY';"
```

### Alerting
- Trigger: serwis w stanie `failed` → `HealService` przez `ctoa-vps.ps1`
- Trigger: task-state.yaml corrupt → backup + `runner.py tick` regeneruje stan
- Trigger: DB `must be owner of table` → sprawdź ownership: `\dt` w psql

### Standardowe SOP (procedure)
| Symptom | Diagnoza | Fix |
|---|---|---|
| `ctoa-runner` failed | `ReportErrorDetails` | sprawdź YAML/env, napraw, `reset-failed` |
| agent error w logach | `ShowPipelineProgress` | `KickoffNow` jeśli READY < 6 |
| serwis nie startuje | `journalctl -xe` | sprawdź env vars, porty, uprawnienia |
| DB permission error | `psql \dt` | przenieś ownership: `ALTER TABLE x OWNER TO ctoa` |

### Incident response — eskalacja
1. `ShowSystemHealth` → identyfikuj failed units
2. `HealService <name>` → próba auto-recovery
3. Jeśli fail po 3x → SSH manual debug
4. Jeśli krytyczny (DB down, disk full) → raport do owner natychmiast

### Ćwiczenie praktyczne
> **Zadanie:** Wykonaj `ShowSystemHealth` przez `ctoa-vps.ps1`. Na podstawie outputu: (a) zidentyfikuj wszystkie non-healthy units, (b) klasyfikuj jako CTOA/non-CTOA, (c) zaproponuj akcje naprawcze dla każdego CTOA failed.
>
> **Kryterium PASS:** poprawna klasyfikacja, przynajmniej 1 konkretna komenda naprawcza.

---

## Zaliczenie

### Wymagania ogólne
- 1 zadanie praktyczne na moduł (opisane powyżej)
- Każde zadanie musi uzyskać wynik **PASS** wg. kryterium modułu
- Całość musi przejść CI gate (`ci-gate-policy.yaml`)

### Kryteria PASS/FAIL — macierz

| Moduł | Waga | Minimalne PASS |
|---|---|---|
| BRAVE(R) Prompt Design | 25% | Kompletny output contract, 6 sekcji |
| QA Gate and Safety | 25% | Poprawny raport defektów, 1 fix |
| GitHub CI Approval Flow | 15% | Poprawny opis 5-krokowego flow |
| MMO/Lua Engineering | 20% | Działający test, docstring |
| VPS 24/7 Operations | 15% | Klasyfikacja units + akcje naprawcze |

### Wynik finalny
- **PASS:** wszystkie moduły PASS + CI zielone
- **FAIL:** jakikolwiek moduł FAIL → retest tylko tego modułu (max 2x)
- **BLOKADA:** po 3 próbach FAIL → eskalacja do `queen-ctoa` z raportem
