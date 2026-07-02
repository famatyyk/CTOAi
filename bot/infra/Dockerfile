FROM python:3.12-slim

LABEL maintainer="STRATEGOS Agent 9 - DEVOPS MASTER"
LABEL description="Tibia Bot - Sprint 1 skeleton"

WORKDIR /app

# System deps for mss (X11 / display) and OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev python3-tk libevdev-dev \
    libgl1 libglib2.0-0 xvfb x11-utils libxcb-render0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-bot.txt .
RUN awk '!/^torch([<>=~! ]|$)/ { print }' requirements-bot.txt > /tmp/requirements-bot-no-torch.txt \
    && pip install --no-cache-dir -r /tmp/requirements-bot-no-torch.txt \
    && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch>=2.2.0"

COPY bot/ ./bot/
RUN mkdir -p data

ENV BOT_DB_PATH=/app/data/bot.db
ENV DISPLAY=:99

CMD ["sh", "-c", "rm -f /tmp/.X99-lock /tmp/.X11-unix/X99; Xvfb :99 -screen 0 1280x720x24 >/tmp/xvfb.log 2>&1 & sleep 1; exec python -m bot.main"]
