# CTOA Global Save (GS) Reset System

## Concept

Wzorowany na mechanizmie Tibia Real Global Save:  
codziennie o **06:00 UTC** serwer wykonuje kontrolowane zatrzymanie wszystkich usług,  
chwilę "oddechu" (czyszczenie RAM/IO), a następnie sekwencyjne uruchomienie  
wg ściśle określonej kolejności zależności.

> Działa **wyłącznie na VPS** (`46.225.110.52`). Lokalnie nic nie jest automatycznie uruchamiane.

---

## Fazy cyklu GS

| Faza | Nazwa | Czas | Opis |
|------|-------|------|------|
| 1 | **SHUTDOWN** | ~30 s | Stop wszystkich `ctoa-*` serwisów w odwróconej kolejności zależności |
| 2 | **REST** | 60 s | Pauza — czyszczenie pamięci i IO (env var `GS_TIMEOUT_WAIT`) |
| 3 | **COHERENCE** | ~5 s | Weryfikacja integralności plików, hash modułów Lua, kluczy `.env` |
| 4 | **STARTUP** | ~60 s | Start serwisów wg kolejności: DB → Health → Console → News → Runner → Reports → Labs → Trainer → Agents |
| 5 | **INJECT** | ~5 s | Skopiowanie wszystkich modułów Lua do folderu klienta MythibIA |
| 6 | **VALIDATE** | ~30 s | Agent dowodzący sprawdza czy serwer API odpowiada 100% OK |

---

## Pliki systemowe na VPS

```
/opt/ctoa/scripts/ops/
├── gs-reset.sh              # Główna sekwencja — wszystkie 6 faz
├── gs-startup-sequence.sh   # Faza 4: ordered startup
├── gs-coherence-check.sh    # Faza 3: file & hash checks
├── gs-module-inject.sh      # Faza 5: Lua module injector
└── gs-api-validator.py      # Faza 6: commanding agent API check

/opt/ctoa/deploy/vps/systemd/
├── ctoa-gs-reset.service    # oneshot service
└── ctoa-gs-reset.timer      # fires @ 06:00 UTC daily

/opt/ctoa/logs/
├── gs-reset.log             # główny log całego cyklu
└── gs-inject.log            # log injectowania modułów
```

---

## Instalacja na VPS (pierwsze uruchomienie)

```powershell
# Z lokalnego Windows (PowerShell)
$env:CTOA_VPS_HOST = "46.225.110.52"
$env:CTOA_VPS_USER = "root"
$env:CTOA_VPS_KEY_PATH = "$env:USERPROFILE\.ssh\ctoa_vps_ed25519"

.\scripts\ops\ctoa-vps.ps1 -Action InstallGsReset
```

To wykona na VPS:
1. `git reset --hard origin/main` (pobierze nowe skrypty)
2. `chmod +x` na wszystkich GS skryptach
3. Skopiuje `.service` i `.timer` do `/etc/systemd/system/`
4. `systemctl enable ctoa-gs-reset.timer` + start

---

## Obsługa / monitoring

| Komenda | Co robi |
|---------|---------|
| `.\ctoa-vps.ps1 -Action GsStatus` | Status timera + tail logów |
| `.\ctoa-vps.ps1 -Action TailGsReset` | Live stream gs-reset.log |
| `.\ctoa-vps.ps1 -Action TriggerGsResetNow` | Wymuszony ręczny reset (prosi o potwierdzenie `YES`) |
| `.\ctoa-vps.ps1 -Action GsCoherence` | Tylko coherence check (bez restartu) |
| `.\ctoa-vps.ps1 -Action GsModuleInject` | Tylko inject modułów Lua |
| `.\ctoa-vps.ps1 -Action GsApiValidate` | Tylko walidacja API serwera |

---

## GitHub Actions monitor

Workflow [`.github/workflows/vps-gs-cycle.yml`](.github/workflows/vps-gs-cycle.yml)  
odpala się o **05:50 UTC** (10 min przed GS), aby:
- potwierdzić dostępność VPS
- wykonać `git reset --hard` (VPS pobiera nowe moduły)
- czekać na zakończenie cyklu i opublikować raport do GitHub Actions Summary

**Wymagane GitHub Secrets:**

| Secret | Opis |
|--------|------|
| `CTOA_VPS_HOST` | IP VPS (`46.225.110.52`) |
| `CTOA_VPS_USER` | User SSH (`root`) |
| `CTOA_VPS_SSH_KEY` | Treść klucza prywatnego Ed25519 |

---

## Dodawanie nowego modułu Lua

1. Utwórz folder: `scripts/lua/<nazwa-modulu>/`
2. Wstaw `init.lua` jako punkt wejścia + dowolne pliki pomocnicze `.lua`
3. Wypchnij (`git push`) na `main`
4. Przy następnym GS (06:00 UTC):
   - `git reset --hard` pobierze nowy moduł
   - Phase 5 (INJECT) skopiuje go do `/opt/mythibia/modules/<nazwa-modulu>/`
   - Phase 6 (VALIDATE) sprawdzi czy API serwera jest OK po załadowaniu nowego modułu

Aby wgrać nowy moduł natychmiast bez czekania na GS:
```powershell
.\scripts\ops\ctoa-vps.ps1 -Action GsModuleInject
```

---

## Kolejność startowa (szczegóły)

```
Layer 0: ctoa-db.service                       ← baza danych (wszystko zależy)
Layer 1: ctoa-health-live.service              ← monitoring ciągły
Layer 2: ctoa-mobile-console.service           ← konsola + rotacja tokenów
Layer 3: ctoa-mythibia-news-api.service        ← news API MythibIA
         ctoa-mythibia-news-watcher.timer
Layer 4: ctoa-runner.timer                     ← główny runner (tick co 15 min)
Layer 5: ctoa-report.timer                     ← raporty co godzinę
         ctoa-retention-cleanup.timer
Layer 6: ctoa-lab-runner.timer                 ← lab eksperymentów
Layer 7: ctoa-auto-trainer.timer               ← auto-trener AI
Layer 8: ctoa-agents-orchestrator.timer        ← orchestrator (co 10 min, LAST)
```

---

## Zmienne środowiskowe (opcjonalna konfiguracja w `.env`)

| Zmienna | Domyślna | Opis |
|---------|----------|------|
| `GS_TIMEOUT_WAIT` | `60` | Sekund pauzy w fazie REST |
| `API_CHECK_URL` | `http://127.0.0.1:7777/api/health` | Endpoint health serwera MythibIA |
| `API_CHECK_RETRIES` | `5` | Ile razy próbować API przed FAIL |
| `MYTHIBIA_MOD_DIR` | `/opt/mythibia/modules` | Folder docelowy modułów klienta |
