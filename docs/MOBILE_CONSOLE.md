# CTOA Mobile Console (Samsung Note 10+)

Mobilna aplikacja webowa do podgladu VPS i wykonywania komend.

## Co potrafi
- Live status uslug (runner/report/health)
- Podglad logow (runner, health)
- Preset commands
- Audytowane preset commands; dowolny shell nie jest wystawiany przez API

Szybki podglad tego, co agenci wygenerowali na VPS:
- [VPS Agent Outputs Runbook](runbook-vps-agent-outputs.md)

## Bezpieczenstwo
Uwierzytelnianie:
- Zalecane: `POST /api/auth/login`, sesja `ctoa_session` w cookie i
  `X-CSRF-Token` dla mutacji wykonywanych przez cookie.
- Alternatywa dla klientow automatycznych: `Authorization: Bearer <token>` albo
  legacy `X-CTOA-Token`.

Zmienne w `/opt/ctoa/.env`:
- `CTOA_MOBILE_TOKEN=<silny_token>`
- `CTOA_ENV=prod` (wlacza twarde zasady produkcyjne)
- `CTOA_CORS_ORIGINS=https://twoja-domena.pl,https://admin.twoja-domena.pl`
- `CTOA_ALLOW_PRIVATE_INTEL_TARGETS=false` (domyslnie blokuje lokalne/prywatne cele Intel w produkcji)

Uwaga:
- Legacy `CTOA_MOBILE_FULL_ACCESS=true` nie wlacza juz dowolnego shella przez
  `/api/command`; endpoint przyjmuje tylko backend-owned presety z
  `/api/presets`.
- Uzywaj tylko przez VPN / trusted network / reverse proxy z TLS.
- Presety z `/api/presets` dzialaja w safe mode jako jawne `argv/cwd/env`
  specyfikacje po stronie backendu, a nie jako dowolny tekst shella.
- `/api/command` zapisuje audyt do `logs/mobile-console-audit.log`; komenda
  jest maskowana przed zapisem, ale operator nadal nie powinien wpisywac
  sekretow w komendy ani w argumenty CLI. Wpis audytu zawiera `actor`,
  `actor_role`, `auth_mode` i `auth_transport`, ale nie zapisuje tokenow sesji
  ani CSRF.
- Endpointy z wygenerowanymi artefaktami zwracaja publiczne sciezki artefaktow
  zamiast absolutnych lokalnych sciezek `GENERATED_DIR`, katalogow tymczasowych
  albo nieznanych sciezek runtime.
- Metadane plikow i raportow w JSON-ach operatorskich sa display-safe:
  admin settings, idea parking, auto-trainer, disk probe i client-sync zwracaja
  nazwy artefaktow albo sciezki repo-relative zamiast absolutnych lokalnych
  katalogow hosta.
- Self-registration tworzy tylko konto `member`. Endpointy operatorskie
  wymagaja roli `operator` albo `owner`; awans roli robi wlasciciel przez
  endpointy zarzadzania kontami.
- W trybie `CTOA_ENV=prod` backend nie wystartuje, jezeli `CTOA_CORS_ORIGINS` jest puste lub zawiera `*`.
- W trybie `CTOA_ENV=prod` endpointy Intel odrzucaja localhost, prywatne IP,
  link-local/metadata IP, nazwy `.local` i jednowyrazowe hosty, chyba ze
  swiadomie ustawisz `CTOA_ALLOW_PRIVATE_INTEL_TARGETS=true`.

## Automatyczna rotacja tokenu (co 7 dni)

VPS posiada timer systemd do rotacji tokenu:
- `ctoa-mobile-token-rotation.timer`
- skrypt: `deploy/vps/rotate-mobile-token.sh`

Co robi rotacja:
- generuje nowy `CTOA_MOBILE_TOKEN`
- aktualizuje `/opt/ctoa/.env`
- zapisuje nowy token do prywatnego pliku: `/opt/ctoa/secrets/mobile-token.txt`
- dopisuje wpis historii (maska + sha256) do: `/opt/ctoa/secrets/mobile-token-history.log`
- restartuje `ctoa-mobile-console.service`
- dopisuje wpis do: `/opt/ctoa/logs/mobile-token-rotation.log`

Uprawnienia prywatnego pliku tokenu:
- owner: `root:root`
- mode: `600`

Uprawnienia pliku historii tokenu:
- owner: `root:root`
- mode: `600`

## Start lokalny
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m uvicorn mobile_console.app:app --host 127.0.0.1 --port 8787
```

Otworz:
- `http://localhost:8787`

## Deploy na VPS
1. Pull najnowszego kodu
2. `pip install -r requirements.txt`
3. Skopiuj service:
   - `deploy/vps/systemd/ctoa-mobile-console.service` -> `/etc/systemd/system/`
4. `systemctl daemon-reload`
5. `systemctl enable --now ctoa-mobile-console.service`

## Endpointy API
- `GET /api/health`
- `GET /api/auth/auto-check`
- `GET /api/status`
- `GET /api/logs?target=runner|health|report&lines=120`
- `GET /api/presets`
- `POST /api/command`
- `POST /api/agents/intel/launch`
- `GET /api/agents/intel/report`
- `GET /api/agents/auto-trainer/latest`
- `POST /api/agents/intel/run` (primary)

Guarded write actions:
- `POST /api/agents/intel/launch` and `POST /api/agents/intel/run`
  require owner auth plus JSON confirmation fields:
  `{"confirm": true, "reason": "<audit reason>"}`.
- Requests missing confirmation or audit reason are rejected before DB writes,
  orchestrator triggers, or client sync.

## Auto trainer (co 6h)

Wersjonowany raport treningowy jest generowany przez systemd:
- `ctoa-auto-trainer.service`
- `ctoa-auto-trainer.timer`

Artefakty raportu na VPS:
- `/opt/ctoa/runtime/training-reports/latest.md`
- `/opt/ctoa/runtime/training-reports/latest.json`
- `/opt/ctoa/runtime/training-reports/auto-trainer-YYYYMMDD-HHMMSS.md`

Log:
- `/opt/ctoa/logs/auto-trainer.log`

## Auto-sync do klienta (po One-click Intel Run)

One-click endpoint moze automatycznie kopiowac wygenerowane skrypty do katalogu klienta
i tworzyc plik autoloadera.

Wymagane zmienne w `/opt/ctoa/.env`:
- `CTOA_CLIENT_SYNC_ENABLED=true`
- `CTOA_CLIENT_SCRIPTS_DIR=/sciezka/do/katalogu/skryptow/klienta`

Opcjonalne:
- `CTOA_CLIENT_TARGET_SLUG=intel_target`
- `CTOA_CLIENT_AUTOLOADER_NAME=ctoa_intel_autoload.lua`
- `CTOA_CLIENT_INIT_FILE=/sciezka/do/katalogu/skryptow/klienta/init.lua`

Guardrail:
- `CTOA_CLIENT_TARGET_SLUG`, `CTOA_CLIENT_AUTOLOADER_NAME` i
  `CTOA_CLIENT_INIT_FILE` sa rozwiazywane wzgledem
  `CTOA_CLIENT_SCRIPTS_DIR` i nie moga wyjsc poza ten katalog.

Po ustawieniu zmiennych endpoint `POST /api/agents/intel/run` zwraca sekcje `client_sync` z informacja o skopiowanych plikach i statusie autoloadera .
Ten endpoint pozostaje guarded write: caller musi wyslac `confirm=true` i
niepusty `reason`, a audyt zapisuje powod z redakcja sekretow.
