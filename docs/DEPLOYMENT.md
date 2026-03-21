# Bot Deployment Guide

Complete guide for packaging and deploying the CTOA Hybrid Bot locally, on VPS, or to cloud environments.

## Table of Contents
1. [Local Deployment](#local-deployment)
2. [VPS Deployment](#vps-deployment)  
3. [Docker Container Deployment](#docker-deployment)
4. [Performance Requirements](#requirements)

---

## Local Deployment

### Prerequisites
- Python 3.11+
- Tibia Client running and visible
- Virtual environment configured

### Installation

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\Activate.ps1  # PowerShell

# Install dependencies
pip install -r requirements.txt

# Verify dependencies
pip list | grep -E "(mss|pynput|opencv|numpy|Pillow)"
```

### Running Locally

**Option 1: Component Testing**
```bash
python test_local.py --mode test
```

**Option 2: Screenshot Capture Benchmark**
```bash
python test_local.py --mode capture --duration 30
```

**Option 3: Autonomous Hunting**
```bash
python test_local.py --mode auto --location "Wasp Cave" --duration 600
```

**Option 4: Manual Control (like Easybot)**
```bash
python test_local.py --mode manual
```

**Option 5: CLI Entry Point**
```bash
python -m runner.hybrid_bot.cli run --level 50 --location "Wasp Cave" --use-llm
```

### Expected Output

```
2026-03-21 15:32:10 [hybrid_bot.cli] INFO 🤖 Hybrid Bot Runner started
2026-03-21 15:32:10 [hybrid_bot.runner] INFO 🏹 Starting hunt at: Wasp Cave
2026-03-21 15:32:11 [hybrid_bot.runner] INFO Tick 10: attack (priority 50)
...
2026-03-21 15:40:00 [hybrid_bot.runner] INFO Stopping Hybrid Bot
2026-03-21 15:40:00 [hybrid_bot.runner] INFO 🐝 Wasp Cave session:
  - Duration: 8m 0s
  - Creatures killed: 47
  - XP gained: 12,450
  - Gold looted: 8,900g
```

---

## VPS Deployment

### Prerequisites
- Linux VPS or cloud VM (Ubuntu 20.04+ recommended)
- SSH access with key authentication
- Python 3.11+
- Display server (X11) or virtual frame buffer for screenshots

### Installation Steps

1. **Connect to VPS**
```bash
ssh -i /path/to/key.pem user@vps-ip
```

2. **Clone/Deploy Repository**
```bash
cd /opt/ctoa
git clone https://github.com/famatyyk/CTOAi.git
cd CTOAi
```

3. **Setup Environment**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# For Xvfb support (headless mode)
pip install pyvirtualdisplay
sudo apt-get install xvfb x11-utils
```

4. **Configure VPS Settings**
```bash
# Create environment file
cat > .env.vps << EOF
TIBIA_WINDOW_TITLE="Tibia Client"
BOT_MODE=autonomous
BOT_LOCATION="Wasp Cave"
LOG_LEVEL=INFO
METRICS_DIR=/var/log/ctoa-bot/
EOF

# Restrict permissions
chmod 600 .env.vps
```

5. **Systemd Service Setup** (optional)
```bash
sudo cp scripts/systemd/ctoa-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ctoa-bot
sudo systemctl start ctoa-bot
```

6. **Run Bot Headlessly**
```bash
# Using virtual display
xvfb-run -a -s "-screen 0 1920x1080x24" python test_local.py --mode auto --duration 3600

# Or via systemd
sudo journalctl -u ctoa-bot -f
```

### Monitoring

**Real-time Logs**
```bash
tail -f /var/log/ctoa-bot/metrics-latest.json
```

**Health Check**
```bash
systemctl status ctoa-bot
ps aux | grep python
```

**Metrics Export**
```bash
python -m runner.hybrid_bot.cli benchmark --metrics-file metrics-latest.jsonl
```

---

## Docker Container Deployment

### Building Container

```dockerfile
# Dockerfile
FROM python:3.11-slim-bullseye

WORKDIR /app
RUN apt-get update && apt-get install -y \
    xvfb x11-utils libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DISPLAY=:99
ENTRYPOINT ["xvfb-run", "-a", "-s", "-screen 0 1920x1080x24", "python", "test_local.py"]
```

**Build and Run**
```bash
# Build image
docker build -t ctoa-hybrid-bot:latest .

# Run container
docker run -it \
    -v $(pwd)/metrics:/app/metrics \
    -e BOT_MODE=autonomous \
    ctoa-hybrid-bot:latest \
    --mode auto --duration 3600
```

---

## Cloud Deployment

### AWS EC2

```bash
# Launch EC2 instance (Ubuntu 20.04 t3.medium)
aws ec2 run-instances \
    --image-id ami-0c55b159cbfafe1f0 \
    --instance-type t3.medium \
    --key-name my-key \
    --security-groups sg-allow-ssh

# SSH and deploy (as per VPS section above)
```

### Azure VM

```bash
# Create VM
az vm create \
    --resource-group myResourceGroup \
    --name ctoa-bot-vm \
    --image UbuntuLTS \
    --size Standard_B2s

# SSH and deploy
```

---

## Requirements

### Hardware
- **CPU**: 2+ cores (1 core minimum for 10 Hz bot loop)
- **RAM**: 512 MB minimum, 2 GB recommended
- **Storage**: 500 MB for app + dependencies
- **Network**: Stable connection (bot will retry on timeout)

### Software
- Python 3.11+
- mss (or PIL for screenshots)
- pynput (keyboard/mouse automation)
- opencv-python (vision processing)
- numpy (numerics)
- asyncio (async loop - stdlib)

### Performance Targets
- Screenshot capture: 20-50 ms
- Vision layer: 30-100 ms
- Decision making: 10-50 ms (heuristics) or 500-2000 ms (LLM)
- Command execution: 1-5 ms
- **Total tick**: ~100-200 ms @ 10 Hz

### Bandwidth (if using LLM)
- If using OpenAI API: ~10 KB/request, ~6 requests/minute @ 10 Hz with decisions
- ~3-5 MB/hour for API calls

---

## Troubleshooting

### Screenshots not captured (returns None)
```bash
# Check window title
xdotool search --name "Tibia"

# Update window title in config
python test_local.py --mode test
```

### Keyboard input not working
```bash
# Verify pynput is installed
python -c "from pynput.keyboard import Controller; print('OK')"

# Check for input permissions
# On Linux: grant `input` group permissions
sudo usermod -a -G input $USER
```

### High CPU usage
```bash
# Profile bot performance
python test_local.py --mode capture --duration 30
# Check "PERFORMANCE PROFILE REPORT" - identify bottleneck
```

### VPS screenshot is black
```bash
# Use virtual display
xvfb-run -a -s "-screen 0 1024x768x24" python test_local.py --mode capture

# Or configure real display
export DISPLAY=:0
```

---

## Backup & Recovery

### Metrics Backup
```bash
# Backup all metrics
tar -czf metrics-backup-$(date +%Y%m%d).tar.gz ./metrics/

# Upload to S3 (if desired)
aws s3 cp metrics-backup-*.tar.gz s3://my-bucket/backups/
```

### Configuration Backup
```bash
# Backup configs
tar -czf config-backup-$(date +%Y%m%d).tar.gz \
    runner/hybrid_bot/*.yaml \
    .env.vps
```

---

## Upgrades

### Update Code
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

### Restart Service
```bash
sudo systemctl restart ctoa-bot

# Verify
sudo systemctl status ctoa-bot
```

---

## Support

For issues or questions:
- Check [README.md](README.md)
- Review logs in `./metrics/`
- Run diagnostic: `python test_local.py --mode test`
