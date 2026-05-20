FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY eosim/ eosim/
COPY platforms/ platforms/

RUN pip install --no-cache-dir build && \
    python -m build --wheel && \
    pip install --no-cache-dir dist/*.whl

FROM python:3.11-slim

# Security: install packages then clean up in one layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        qemu-system-arm \
        qemu-system-aarch64 \
        qemu-system-riscv64 \
        qemu-system-x86 \
        qemu-system-mips && \
    rm -rf /var/lib/apt/lists/*

# Security: create non-root user
RUN groupadd --gid 1000 eosim && \
    useradd --uid 1000 --gid eosim --shell /bin/sh --create-home eosim

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/eosim /usr/local/bin/eosim
COPY --chown=eosim:eosim platforms/ /opt/eosim/platforms/
COPY --chown=eosim:eosim examples/ /opt/eosim/examples/

WORKDIR /opt/eosim

# Security: run as non-root
USER eosim

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["eosim", "doctor"] || exit 1

ENTRYPOINT ["eosim"]
CMD ["--help"]
