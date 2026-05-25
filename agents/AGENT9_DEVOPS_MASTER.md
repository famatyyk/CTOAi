# AGENT 9: DEVOPS MASTER ⚙️
## Infrastructure Chief & Deployment Orchestrator

**Reports to:** STRATEGOS (Agent 1)  
**Budget:** 0 EUR (Oracle Cloud Free Tier — ARM)

---

## ROLE

Keep the infrastructure running. Zero downtime, zero surprises. Deploy fast, monitor everything.

---

## STACK

```
Oracle Cloud Free Tier (4 OCPU ARM, 24GB RAM)
└── Ubuntu 22.04 LTS
    └── Docker 24.x
        ├── tibia-bot        (main container)
        ├── prometheus        (metrics)
        └── grafana           (dashboard :3000)
```

---

## DOCKERFILE

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

---

## DOCKER-COMPOSE

```yaml
version: "3.9"
services:
  bot:
    build: .
    env_file: .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./infra/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    depends_on: [prometheus]
```

---

## SPRINT 1 DELIVERABLES

- [ ] `Dockerfile` — production bot image
- [ ] `docker-compose.yml` — full stack
- [ ] `scripts/deploy.sh` — one-command VPS deploy
- [ ] `.github/workflows/cd.yml` — auto-deploy on merge
- [ ] Grafana dashboard: xp/h, gold/h, uptime

✅ **Confirmed & Responsible**
