# syntax=docker/dockerfile:1
# Production-ready multi-stage image for CTOA toolkit.

FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .

# Build dependency wheels in a separate stage to keep runtime image smaller.
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt "numpy>=1.26" "opencv-python-headless>=4.9"

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CTOA_MOBILE_FULL_ACCESS=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends tk lua5.4 \
    && if ! command -v lua >/dev/null 2>&1; then ln -s /usr/bin/lua5.4 /usr/local/bin/lua; fi \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 ctoa

WORKDIR /opt/ctoa

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY --chown=ctoa:ctoa . .
RUN chown ctoa:ctoa /opt/ctoa \
    && mkdir -p runtime/state metrics \
    && chown -R ctoa:ctoa runtime metrics

USER ctoa

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import os,urllib.request; t=os.getenv('CTOA_MOBILE_TOKEN',''); req=urllib.request.Request('http://127.0.0.1:8787/api/health', headers={'X-CTOA-Token': t}); urllib.request.urlopen(req, timeout=5)"

CMD ["python", "-m", "uvicorn", "mobile_console.app:app", "--host", "0.0.0.0", "--port", "8787"]

# The P14 contract tests create isolated Git worktrees to prove that only
# reviewed, tracked helper sources can be signed. Keep this dependency out of
# the runtime image: the runner itself fails closed when tracking is unavailable.
FROM runtime AS test

USER root
ARG CTOA_P14_SOURCE_PROVENANCE_B64
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Docker contexts intentionally exclude .git.  CI injects a bounded, generated
# sidecar only into this non-production stage; the runner rejects it unless it
# binds every fixed package source byte-for-byte.
RUN test -n "${CTOA_P14_SOURCE_PROVENANCE_B64}" \
    && printf '%s' "${CTOA_P14_SOURCE_PROVENANCE_B64}" \
        | base64 --decode > /opt/ctoa/.ctoa-p14-source-provenance.json \
    && chown root:root /opt/ctoa /opt/ctoa/.ctoa-p14-source-provenance.json \
    && chmod 0555 /opt/ctoa \
    && chmod 0444 /opt/ctoa/.ctoa-p14-source-provenance.json

USER ctoa

# Leave the production image as the default Docker target. Build/test CI opts
# into the test target explicitly so Git is never a production dependency.
FROM runtime AS production
