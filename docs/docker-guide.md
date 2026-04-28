# Docker Build & Deployment Guide

This guide covers building, running, and deploying EoSim using Docker in production environments.

---

## Quick Start

```bash
# Build and start the API server
docker compose up api -d

# Check it's running
curl http://localhost:8080/api/v1/platforms

# View logs
docker compose logs -f api

# Stop
docker compose down
```

---

## Docker Images

The Dockerfile provides **6 build stages** for different use cases:

| Stage | Target | Size | Use Case |
|-------|--------|------|----------|
| `builder` | — | — | Internal build stage |
| `test` | `--target test` | ~250 MB | CI test runner |
| `production` | `--target production` | ~180 MB | Slim CLI runner (no QEMU) |
| `production-qemu` | `--target production-qemu` | ~800 MB | CLI + full QEMU emulation |
| `api-server` | `--target api-server` | ~200 MB | REST API server (FastAPI) |
| `development` | `--target development` | ~1.2 GB | Full dev environment |

### Building Specific Targets

```bash
# Production slim (CLI only, no QEMU)
docker build --target production -t eosim:latest .

# API server
docker build --target api-server -t eosim-api:latest .

# Full simulation with QEMU
docker build --target production-qemu -t eosim-qemu:latest .

# Development environment
docker build --target development -t eosim-dev:latest .

# Test runner (for CI)
docker build --target test -t eosim-test:latest .
```

---

## Running Containers

### CLI Commands

```bash
# List platforms
docker run --rm eosim:latest eosim list

# Platform info
docker run --rm eosim:latest eosim info stm32h7

# Run simulation
docker run --rm eosim:latest eosim run stm32f4

# Validate all platforms
docker run --rm eosim:latest eosim validate --all

# Platform statistics
docker run --rm eosim:latest eosim stats

# Search
docker run --rm eosim:latest eosim search bluetooth
```

### API Server

```bash
# Start API server
docker run -d \
  --name eosim-api \
  -p 8080:8080 \
  --restart unless-stopped \
  --memory 2g \
  --cpus 2 \
  eosim-api:latest

# Endpoints:
#   GET  http://localhost:8080/api/v1/platforms
#   GET  http://localhost:8080/api/v1/domains
#   GET  http://localhost:8080/api/v1/simulators
#   GET  http://localhost:8080/api/v1/templates
#   GET  http://localhost:8080/api/v1/simulations
#   POST http://localhost:8080/api/v1/simulations/{name}/tick
#   WS   ws://localhost:8080/ws/simulations/{name}
#
# Interactive docs:
#   http://localhost:8080/docs      (Swagger UI)
#   http://localhost:8080/redoc     (ReDoc)
```

### With Custom Platforms

```bash
# Mount your own platform definitions
docker run -d \
  -p 8080:8080 \
  -v /path/to/my/platforms:/opt/eosim/platforms:ro \
  eosim-api:latest
```

### With Plugins

```bash
# Mount plugin directory
docker run -d \
  -p 8080:8080 \
  -v /path/to/plugins:/opt/eosim/plugins:ro \
  eosim-api:latest
```

---

## Docker Compose

### Services

| Service | Purpose | Port | Profile |
|---------|---------|------|---------|
| `api` | REST API server | 8080 | default |
| `cli` | CLI runner | — | `cli` |
| `cli-qemu` | CLI + QEMU | — | `cli` |
| `test` | Test runner | — | `test` |
| `dev` | Development | 8080, 8888 | `dev` |

### Commands

```bash
# Start API server (default service)
docker compose up api -d

# Run CLI commands
docker compose run --rm cli list
docker compose run --rm cli info stm32h7
docker compose run --rm cli stats

# Run with QEMU (full firmware simulation)
docker compose run --rm cli-qemu run arm64-linux

# Run tests
docker compose --profile test run --rm test

# Start development environment
docker compose --profile dev run --rm dev

# View API logs
docker compose logs -f api

# Stop everything
docker compose down

# Rebuild after code changes
docker compose build --no-cache api
docker compose up api -d
```

---

## Production Deployment

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EOSIM_HOST` | `0.0.0.0` | API server bind address |
| `EOSIM_PORT` | `8080` | API server port |
| `EOSIM_LOG_LEVEL` | `INFO` | Logging level |
| `EOSIM_WORKERS` | `2` | Number of uvicorn workers |
| `EOSIM_DEV` | — | Enable development mode |

### Resource Limits

Recommended resource limits for production:

| Workload | CPU | Memory | Storage |
|----------|-----|--------|---------|
| API server | 1-2 cores | 512 MB - 2 GB | 500 MB |
| CLI validation | 0.5-1 core | 256 MB | 500 MB |
| QEMU simulation | 2-4 cores | 2-8 GB | 2 GB |
| Development | 2+ cores | 4+ GB | 5 GB |

### Health Checks

The production images include built-in health checks:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' eosim-api

# API server health
curl -f http://localhost:8080/api/v1/platforms

# CLI health
docker run --rm eosim:latest python -c \
  "from eosim.engine.native.simulators import SimulatorFactory; print('OK')"
```

### Logging

```bash
# Follow logs
docker compose logs -f api

# JSON structured logging (for log aggregation)
docker run -d \
  -p 8080:8080 \
  -e EOSIM_LOG_LEVEL=INFO \
  eosim-api:latest

# Export logs to file
docker compose logs api > eosim-api.log 2>&1
```

---

## Security

### Non-root Container

The production images run as a dedicated `eosim` user (non-root):

```bash
# Verify
docker run --rm eosim:latest whoami
# → eosim
```

### Read-only Filesystem

```bash
docker run -d \
  --read-only \
  --tmpfs /tmp \
  -p 8080:8080 \
  -v eosim-data:/opt/eosim/out \
  eosim-api:latest
```

### Network Isolation

```bash
# Create isolated network
docker network create eosim-net

docker run -d \
  --name eosim-api \
  --network eosim-net \
  -p 8080:8080 \
  eosim-api:latest
```

### Image Scanning

```bash
# Scan for vulnerabilities
docker scout cve eosim:latest

# Or with Trivy
trivy image eosim:latest
```

---

## Kubernetes Deployment

### Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eosim-api
  labels:
    app: eosim
spec:
  replicas: 2
  selector:
    matchLabels:
      app: eosim
  template:
    metadata:
      labels:
        app: eosim
    spec:
      containers:
        - name: eosim
          image: ghcr.io/embeddedos-org/eosim:v2.0.0
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 500m
              memory: 256Mi
            limits:
              cpu: 2000m
              memory: 2Gi
          livenessProbe:
            httpGet:
              path: /api/v1/platforms
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /api/v1/platforms
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          env:
            - name: EOSIM_LOG_LEVEL
              value: "INFO"
---
apiVersion: v1
kind: Service
metadata:
  name: eosim-api
spec:
  selector:
    app: eosim
  ports:
    - port: 80
      targetPort: 8080
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: eosim-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
    - host: eosim.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: eosim-api
                port:
                  number: 80
```

### Helm Values (example)

```yaml
replicaCount: 2
image:
  repository: ghcr.io/embeddedos-org/eosim
  tag: v2.0.0
service:
  port: 8080
resources:
  requests:
    cpu: 500m
    memory: 256Mi
  limits:
    cpu: 2000m
    memory: 2Gi
```

---

## CI/CD Integration

### GitHub Actions

```yaml
- name: Build & push Docker image
  run: |
    docker build --target api-server -t ghcr.io/embeddedos-org/eosim:${{ github.ref_name }} .
    echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin
    docker push ghcr.io/embeddedos-org/eosim:${{ github.ref_name }}
```

### GitLab CI

```yaml
docker:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build --target api-server -t registry.example.com/eosim:$CI_COMMIT_TAG .
    - docker push registry.example.com/eosim:$CI_COMMIT_TAG
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs eosim-api

# Run interactively
docker run -it --rm eosim:latest bash

# Test Python import
docker run --rm eosim:latest python -c "import eosim; print('OK')"
```

### Port already in use

```bash
# Find what's using port 8080
lsof -i :8080

# Use a different port
docker run -p 9090:8080 eosim-api:latest
```

### Permission denied

```bash
# The container runs as non-root — mount volumes with correct ownership
docker run -v ./data:/opt/eosim/out eosim:latest
# If needed, fix ownership:
sudo chown -R 999:999 ./data  # UID/GID of eosim user in container
```
