# Multi-stage production build for CTOA Toolkit
# Non-root user, health checks, minimal footprint

# Stage 1: Builder
FROM python:3.12-slim as builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

# Create non-root user
RUN useradd -m -u 1000 ctoa

WORKDIR /opt/ctoa

# Copy Python packages from builder
COPY --from=builder /root/.local /home/ctoa/.local
ENV PATH=/home/ctoa/.local/bin:$PATH

# Copy application
COPY --chown=ctoa:ctoa . .

# Set non-root user
USER ctoa

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8787/api/health', timeout=5)" || exit 1

# Expose port for mobile console
EXPOSE 8787

# Default entrypoint
CMD ["python", "-m", "uvicorn", "mobile_console.app:app", "--host", "0.0.0.0", "--port", "8787"]
