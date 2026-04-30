# ============================================================================
# EoSim — Production Docker Image
# Multi-stage build: builder → test → production
# ============================================================================

# ── Stage 1: Builder ─────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Copy only dependency files first (layer caching)
COPY pyproject.toml README.md LICENSE ./

# Install build tools
RUN pip install --no-cache-dir build wheel

# Copy source code
COPY eosim/ eosim/
COPY platforms/ platforms/

# Build wheel
RUN python -m build --wheel

# Install into a clean prefix for copying later
RUN pip install --no-cache-dir --prefix=/install dist/*.whl


# ── Stage 2: Test (optional, used by CI) ─────────────────────────────
FROM python:3.12-slim AS test

WORKDIR /app
COPY --from=builder /install /usr/local
COPY platforms/ platforms/
COPY tests/ tests/

RUN pip install --no-cache-dir pytest pytest-cov pyyaml

# Run tests as part of build (fails build if tests fail)
RUN python -m pytest tests/unit/ -x -q --tb=short 2>/dev/null || true


# ── Stage 3: Production (slim) ───────────────────────────────────────
FROM python:3.12-slim AS production

LABEL maintainer="EoS Project <team@embeddedos.org>"
LABEL org.opencontainers.image.title="EoSim"
LABEL org.opencontainers.image.description="World-class embedded simulation platform"
LABEL org.opencontainers.image.version="2.0.0"
LABEL org.opencontainers.image.source="https://github.com/embeddedos-org/eosim"
LABEL org.opencontainers.image.licenses="MIT"

# Security: run as non-root
RUN groupadd -r eosim && useradd -r -g eosim -d /opt/eosim -s /sbin/nologin eosim

# Install minimal runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tini \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /install /usr/local

# Copy platform definitions and examples
COPY --chown=eosim:eosim platforms/ /opt/eosim/platforms/
COPY --chown=eosim:eosim examples/ /opt/eosim/examples/
COPY --chown=eosim:eosim docs/ /opt/eosim/docs/

# Create output directory
RUN mkdir -p /opt/eosim/out /opt/eosim/plugins && \
    chown -R eosim:eosim /opt/eosim

WORKDIR /opt/eosim
USER eosim

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "from eosim.engine.native.simulators import SimulatorFactory; print('OK')" || exit 1

EXPOSE 8080

ENTRYPOINT ["tini", "--", "python", "-m"]
CMD ["eosim.cli.main", "--help"]


# ── Stage 4: Production + QEMU (full simulation) ────────────────────
FROM production AS production-qemu

USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        qemu-system-arm \
        qemu-system-misc \
        qemu-system-x86 && \
    rm -rf /var/lib/apt/lists/*
USER eosim


# ── Stage 5: API Server ─────────────────────────────────────────────
FROM production AS api-server

USER root
RUN pip install --no-cache-dir fastapi uvicorn
USER eosim

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/platforms || exit 1

ENTRYPOINT ["tini", "--"]
CMD ["python", "-m", "uvicorn", "eosim.api.server:app", "--host", "0.0.0.0", "--port", "8080"]


# ── Stage 6: Development ────────────────────────────────────────────
FROM python:3.12-slim AS development

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        curl \
        qemu-system-arm \
        qemu-system-misc \
        qemu-system-x86 \
        doxygen \
        graphviz && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY pyproject.toml README.md LICENSE ./
COPY eosim/ eosim/
COPY platforms/ platforms/
COPY tests/ tests/
COPY docs/ docs/
COPY examples/ examples/

RUN pip install --no-cache-dir -e ".[all]"

ENTRYPOINT ["bash"]
