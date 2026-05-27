FROM python:3.12-slim

LABEL maintainer="STRATEGOS Agent 9 - DEVOPS MASTER"
LABEL description="Tibia Bot - Sprint 1 skeleton"

WORKDIR /app

# System deps for mss (X11 / display) and OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libevdev-dev \
    libgl1 libglib2.0-0 xvfb x11-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-bot.txt .
RUN pip install --no-cache-dir -r requirements-bot.txt

COPY bot/ ./bot/
COPY data/ ./data/

ENV BOT_DB_PATH=/app/data/bot.db
ENV DISPLAY=:99

CMD ["sh", "-c", "Xvfb :99 -screen 0 1280x720x24 & python -m bot.main"]
