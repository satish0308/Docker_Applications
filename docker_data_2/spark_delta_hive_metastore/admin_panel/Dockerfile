# =============================================================
# STAGE 1: FRONTEND BUILDER (React 18 + Vite + TailwindCSS)
# =============================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# =============================================================
# STAGE 2: BACKEND RUNNER (FastAPI + WebSockets + Docker CLI)
# =============================================================
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install official standalone Docker CLI & Compose plugin
RUN curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-27.5.1.tgz | tar -xz -C /usr/local/bin --strip-components=1 docker/docker \
    && curl -fsSL https://github.com/docker/compose/releases/download/v2.32.4/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose \
    && mkdir -p /usr/local/lib/docker/cli-plugins \
    && cp /usr/local/bin/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and supporting modules
COPY . .
COPY diagnose_cluster.sh /app/diagnose_cluster.sh
RUN chmod +x /app/diagnose_cluster.sh

# Copy compiled React 18 frontend static assets to non-shadowed directory
COPY --from=frontend-builder /app/frontend/dist /frontend_dist

EXPOSE 8501

# Run FastAPI Uvicorn Master Server with WebSockets on Port 8501
ENTRYPOINT ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8501"]
