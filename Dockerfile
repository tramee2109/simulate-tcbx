# ==============================================================================
# Dockerfile for TCEX Spot BTC/VND Multi-Account Strategy Engine (simulate-tcbx)
# ==============================================================================
FROM python:3.11-slim

# Avoid writing .pyc files & enable unbuffered standard I/O for real-time logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Ho_Chi_Minh

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY local/requirements.txt /app/local/requirements.txt
RUN pip install --no-cache-dir -r /app/local/requirements.txt

# Create runtime directories for logs, SQLite database, and reports
RUN mkdir -p /app/local/logs /app/local/data /app/local/reports

# Copy Simulation SDK root files and local engine package
COPY *.py /app/
COPY local/ /app/local/

# Declare mountable volumes for persistence
VOLUME ["/app/local/logs", "/app/local/data", "/app/local/reports"]

# Healthcheck: verifies Python process is running and can export balance snapshot
HEALTHCHECK --interval=60s --timeout=15s --start-period=30s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/app/local/reports/balance_snapshot_latest.json') else 1)"

# Default command: launch the multi-account engine
CMD ["python", "-u", "local/main.py"]
