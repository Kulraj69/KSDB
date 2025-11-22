# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt
RUN pip install --user gunicorn uvicorn[standard]

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime libs for Postgres
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY . .

# Production Config
ENV WORKERS=4
ENV TIMEOUT=120

EXPOSE 8000

# Run with Gunicorn for production concurrency
CMD gunicorn main:app --workers $WORKERS --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout $TIMEOUT
