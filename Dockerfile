# ── Vol Diagnostics Dashboard ───────────────────────────────────────────────
# Multi-stage build: slim Python image, no dev deps in prod.
# Target: linux/arm64 (Oracle Cloud Free Tier ARM Ampere A1)
#         linux/amd64 (local Docker Desktop)

FROM python:3.11-slim AS base

WORKDIR /app

# System deps for numpy/scipy/pandas (pre-compiled wheels available for arm64)
# curl needed for healthchecks. No chromium/kaleido here — this image only ever
# runs the interactive dashboard, which never renders PNGs (that's run_daily's
# email-attachment path, which now runs on GitHub Actions, not this box).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (no pywin32 on Linux — filtered out by platform marker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY engine/ engine/
COPY app.py .
COPY assets/ assets/
COPY research/ research/
# Theme only — NEVER `COPY .streamlit/`, which would bake .streamlit/secrets.toml
# into the image (it is gitignored but present in the local build context).
COPY .streamlit/config.toml .streamlit/config.toml

# Entrypoint: pulls fresh data from OCI, then starts dashboard
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Ensure out/ exists for volume mount target
RUN mkdir -p /app/out

# Provenance stamp — which commit this image was built from. Declared last so a
# new SHA only busts this trivial layer, never the pip install above.
# scripts/verify-deploy.sh reads it back to prove the live site is current.
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA

# Default: run Streamlit dashboard
EXPOSE 8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

ENTRYPOINT ["/app/docker-entrypoint.sh"]
