FROM python:3.11-slim

WORKDIR /app

# Install ffmpeg and curl (for health check) for video thumbnail generation
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code only — inject env vars at runtime, not build time
COPY app/ app/

# Create non-root user and required directories
RUN useradd -m appuser \
    && mkdir -p /app/logs /app/thumbnails /app/previews /app/data \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:5000/about || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "app:create_app()"]
