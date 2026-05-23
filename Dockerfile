# syntax=docker/dockerfile:1
# Production-ready multi-stage image for CTOA toolkit.

FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .

# Build dependency wheels in a separate stage to keep runtime image smaller.
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CTOA_MOBILE_TOKEN=change-me \
    CTOA_MOBILE_FULL_ACCESS=false

RUN useradd --create-home --uid 1000 ctoa

WORKDIR /opt/ctoa

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY --chown=ctoa:ctoa . .

USER ctoa

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import os,urllib.request; t=os.getenv('CTOA_MOBILE_TOKEN',''); req=urllib.request.Request('http://127.0.0.1:8787/api/health', headers={'X-CTOA-Token': t}); urllib.request.urlopen(req, timeout=5)"

CMD ["python", "-m", "uvicorn", "mobile_console.app:app", "--host", "0.0.0.0", "--port", "8787"]
