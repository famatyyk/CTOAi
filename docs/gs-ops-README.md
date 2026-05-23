# CTOA Global Save (GS) Reset System

## Concept

Wzorowany na mechanizmie Tibia Real Global Save:  
codziennie o **06:00 UTC** serwer wykonuje kontrolowane zatrzymanie wszystkich usĹ‚ug,  
chwilÄ™ "oddechu" (czyszczenie RAM/IO), a nastÄ™pnie sekwencyjne uruchomienie  
wg Ĺ›ciĹ›le okreĹ›lonej kolejnoĹ›ci zaleĹĽnoĹ›ci.

> DziaĹ‚a **wyĹ‚Ä…cznie na VPS** (`46.225.110.52`). Lokalnie nic nie jest automatycznie uruchamiane.

---

## Fazy cyklu GS

| Faza | Nazwa | Czas | Opis |
|------|-------|------|------|
| 1 | **SHUTDOWN** | ~30 s | Stop wszystkich `ctoa-*` serwisĂłw w odwrĂłconej kolejnoĹ›ci zaleĹĽnoĹ›ci |
| 2 | **REST** | 60 s | Pauza â€” czyszczenie pamiÄ™ci i IO (env var `GS_TIMEOUT_WAIT`) |
| 3 | **COHERENCE** | ~5 s | Weryfikacja integralnoĹ›ci plikĂłw, hash moduĹ‚Ăłw Lua, kluczy `.env` |
| 4 | **STARTUP** | ~60 s | Start serwisĂłw wg kolejnoĹ›ci: DB â†’ Health â†’ Console â†’ News â†’ Runner â†’ Reports â†’ Labs â†’ Trainer â†’ Agents |
| 5 | **INJECT** | ~5 s | Skopiowanie wszystkich moduĹ‚Ăłw Lua do folderu klienta MythibIA |
| 6 | **VALIDATE** | ~30 s | Agent dowodzÄ…cy sprawdza czy serwer API odpowiada 100% OK |

---

## Pliki systemowe na VPS

```
/opt/ctoa/scripts/ops/
â”śâ”€â”€ gs-reset.sh              # GĹ‚Ăłwna sekwencja â€” wszystkie 6 faz
â”śâ”€â”€ gs-startup-sequence.sh   # Faza 4: ordered startup
â”śâ”€â”€ gs-coherence-check.sh    # Faza 3: file & hash checks
â”śâ”€â”€ gs-module-inject.sh      # Faza 5: Lua module injector
â””â”€â”€ gs-api-validator.py      # Faza 6: commanding agent API check

/opt/ctoa/deploy/vps/systemd/
â”śâ”€â”€ ctoa-gs-reset.service    # oneshot service
â””â”€â”€ ctoa-gs-reset.timer      # fires @ 06:00 UTC daily

/opt/ctoa/logs/
â”śâ”€â”€ gs-reset.log             # gĹ‚Ăłwny log caĹ‚ego cyklu
â””â”€â”€ gs-inject.log            # log injectowania moduĹ‚Ăłw
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

## ObsĹ‚uga / monitoring

| Komenda | Co robi |
|---------|---------|
| `.\ctoa-vps.ps1 -Action GsStatus` | Status timera + tail logĂłw |
| `.\ctoa-vps.ps1 -Action TailGsReset` | Live stream gs-reset.log |
| `.\ctoa-vps.ps1 -Action TriggerGsResetNow` | Wymuszony rÄ™czny reset (prosi o potwierdzenie `YES`) |
| `.\ctoa-vps.ps1 -Action GsCoherence` | Tylko coherence check (bez restartu) |
| `.\ctoa-vps.ps1 -Action GsModuleInject` | Tylko inject moduĹ‚Ăłw Lua |
| `.\ctoa-vps.ps1 -Action GsApiValidate` | Tylko walidacja API serwera |

---

## GitHub Actions monitor

Workflow [`.github/workflows/vps-gs-cycle.yml`](.github/workflows/vps-gs-cycle.yml)  
odpala siÄ™ o **05:50 UTC** (10 min przed GS), aby:
- potwierdziÄ‡ dostÄ™pnoĹ›Ä‡ VPS
- wykonaÄ‡ `git reset --hard` (VPS pobiera nowe moduĹ‚y)
- czekaÄ‡ na zakoĹ„czenie cyklu i opublikowaÄ‡ raport do GitHub Actions Summary

**Wymagane GitHub Secrets:**

| Secret | Opis |
|--------|------|
| `CTOA_VPS_HOST` | IP VPS (`46.225.110.52`) |
| `CTOA_VPS_USER` | User SSH (`root`) |
| `CTOA_VPS_SSH_KEY` | TreĹ›Ä‡ klucza prywatnego Ed25519 |

---

## Dodawanie nowego moduĹ‚u Lua

1. UtwĂłrz folder: `scripts/lua/<nazwa-modulu>/`
2. Wstaw `init.lua` jako punkt wejĹ›cia + dowolne pliki pomocnicze `.lua`
3. Wypchnij (`git push`) na `main`
4. Przy nastÄ™pnym GS (06:00 UTC):
   - `git reset --hard` pobierze nowy moduĹ‚
   - Phase 5 (INJECT) skopiuje go do `/opt/mythibia/modules/<nazwa-modulu>/`
   - Phase 6 (VALIDATE) sprawdzi czy API serwera jest OK po zaĹ‚adowaniu nowego moduĹ‚u

Aby wgraÄ‡ nowy moduĹ‚ natychmiast bez czekania na GS:
```powershell
.\scripts\ops\ctoa-vps.ps1 -Action GsModuleInject
```

---

## KolejnoĹ›Ä‡ startowa (szczegĂłĹ‚y)

```
Layer 0: ctoa-db.service                       â† baza danych (wszystko zaleĹĽy)
Layer 1: ctoa-health-live.service              â† monitoring ciÄ…gĹ‚y
Layer 2: ctoa-mobile-console.service           â† konsola + rotacja tokenĂłw
Layer 3: ctoa-intel-news-api.service        â† news API MythibIA
         ctoa-intel-news-watcher.timer
Layer 4: ctoa-runner.timer                     â† gĹ‚Ăłwny runner (tick co 15 min)
Layer 5: ctoa-report.timer                     â† raporty co godzinÄ™
         ctoa-retention-cleanup.timer
Layer 6: ctoa-lab-runner.timer                 â† lab eksperymentĂłw
Layer 7: ctoa-auto-trainer.timer               â† auto-trener AI
Layer 8: ctoa-agents-orchestrator.timer        â† orchestrator (co 10 min, LAST)
```

---

## Zmienne Ĺ›rodowiskowe (opcjonalna konfiguracja w `.env`)

| Zmienna | DomyĹ›lna | Opis |
|---------|----------|------|
| `GS_TIMEOUT_WAIT` | `60` | Sekund pauzy w fazie REST |
| `API_CHECK_URL` | `http://127.0.0.1:7777/api/health` | Endpoint health serwera MythibIA |
| `API_CHECK_RETRIES` | `5` | Ile razy prĂłbowaÄ‡ API przed FAIL |
| `MYTHIBIA_MOD_DIR` | `/opt/mythibia/modules` | Folder docelowy moduĹ‚Ăłw klienta |

