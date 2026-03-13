# CTOA Mobile Console (Samsung Note 10+)

Mobilna aplikacja webowa do podgladu VPS i wykonywania komend.

## Co potrafi
- Live status uslug (runner/report/health)
- Podglad logow (runner, health)
- Preset commands
- Full command execution (po wlaczeniu full access)

## Bezpieczenstwo
Wymagany naglowek tokenu: `X-CTOA-Token`.

Zmienne w `/opt/ctoa/.env`:
- `CTOA_MOBILE_TOKEN=<silny_token>`
- `CTOA_MOBILE_FULL_ACCESS=false` (zalecane)

Uwaga:
- `CTOA_MOBILE_FULL_ACCESS=true` daje praktycznie shell-level kontrolę.
- Uzywaj tylko przez VPN / trusted network / reverse proxy z TLS.

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
python3 -m uvicorn mobile_console.app:app --host 0.0.0.0 --port 8787
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
- `GET /api/status`
- `GET /api/logs?target=runner|health|report&lines=120`
- `GET /api/presets`
- `POST /api/command`
