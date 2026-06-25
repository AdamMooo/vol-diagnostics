# ── Gamma OMM — Vol Diagnostics Dashboard ──────────────────────────────────
# Multi-stage build: slim Python image, no dev deps in prod.
# Target: linux/arm64 (Oracle Cloud Free Tier ARM Ampere A1)
#         linux/amd64 (local Docker Desktop)

FROM python:3.11-slim AS base

WORKDIR /app

# System deps for numpy/scipy/pandas (pre-compiled wheels available for arm64)
# curl needed for healthchecks and supercronic download
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Install supercronic (cron replacement for containers — no daemon, stdout logs)
ARG TARGETARCH
RUN SUPERCRONIC_URL="https://github.com/aptible/supercronic/releases/download/v0.2.33/supercronic-linux-${TARGETARCH}" \
    && curl -fsSL "${SUPERCRONIC_URL}" -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic

# Install Python deps (no pywin32 on Linux — filtered out by platform marker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY engine/ engine/
COPY app.py .
COPY assets/ assets/
COPY research/ research/
COPY crontab /app/crontab

# Ensure out/ exists for volume mount target
RUN mkdir -p /app/out

# Default: run Streamlit dashboard
EXPOSE 8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

CMD ["streamlit", "run", "app.py"]
