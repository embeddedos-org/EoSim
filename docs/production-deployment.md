# Production Deployment Guide

This guide covers deploying EoSim in production environments.

## Deployment Options

| Option | Best For | Scaling |
|--------|----------|---------|
| Python package | CI/CD pipelines, local dev | Single node |
| Docker container | Microservices, cloud | Horizontal |
| Docker Compose | Multi-service (API + workers) | Multi-container |
| Kubernetes | Enterprise, high availability | Cluster |

## Python Package Deployment

```bash
pip install eosim
eosim doctor    # Verify installation
eosim stats     # Check platform count
```

## Docker Deployment

### Build Image

```dockerfile
# Already included — just build:
docker build -t eosim:latest .
```

### Run API Server

```bash
docker run -d \
  --name eosim-api \
  -p 8080:8080 \
  eosim:latest \
  python -m eosim.api.server
```

### Docker Compose

```bash
docker-compose up -d
# API: http://localhost:8080
# Docs: http://localhost:8080/docs
```

## CI/CD Integration

### GitHub Actions

```yaml
name: EoSim Validation
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: python -m pytest tests/ -v --cov=eosim
      - run: eosim validate --all
      - run: eosim stats
```

### GitLab CI

```yaml
test:
  image: python:3.11
  script:
    - pip install -e ".[dev]"
    - pytest tests/ -v
    - eosim validate --all
```

## Monitoring

### Health Check

```bash
eosim doctor
```

### Metrics (via REST API)

```bash
curl http://localhost:8080/api/v1/platforms | jq '.platforms | length'
curl http://localhost:8080/api/v1/simulators | jq '.simulators | length'
```

## Security Considerations

1. **No secrets in platform YAML** — YAML files are configuration only
2. **REST API authentication** — add middleware for production
3. **Container isolation** — run as non-root user
4. **Input validation** — all platform data is schema-validated
5. **Dependency scanning** — minimal dependencies (click, pyyaml)

## Performance Tuning

- **Tick rate**: adjust simulation tick rate based on domain needs
- **Peripheral count**: limit active peripherals for faster simulation
- **History size**: DigitalTwin limits history to 10,000 entries by default
- **Parallel simulations**: use multiprocessing for multiple platforms
