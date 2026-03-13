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
