# ============================================================================
# EoSim — Makefile
# ============================================================================
# Usage: make <target>
# Run `make help` to see all available targets.
# ============================================================================

.PHONY: help install install-dev install-all test test-unit test-integration \
        coverage lint format check clean build docker docker-push \
        api docs serve-docs version

PYTHON    := python3
PIP       := pip3
PACKAGE   := eosim
VERSION   := 3.0.1
IMAGE     := ghcr.io/embeddedos-org/eosim
PORT      := 8080

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  EoSim v$(VERSION) — Build Targets"
	@echo "  ─────────────────────────────────────────────────────────────"
	@echo "  install         Install production dependencies"
	@echo "  install-dev     Install development dependencies"
	@echo "  install-all     Install all dependencies"
	@echo "  test            Run all unit tests"
	@echo "  test-unit       Run unit tests only"
	@echo "  test-integration Run integration tests"
	@echo "  coverage        Run tests with coverage report"
	@echo "  lint            Run ruff linter"
	@echo "  format          Auto-format with ruff"
	@echo "  check           Run lint + tests"
	@echo "  clean           Remove build artifacts"
	@echo "  build           Build Python package"
	@echo "  docker          Build Docker image"
	@echo "  docker-push     Push Docker image to registry"
	@echo "  api             Start local API server"
	@echo "  docs            Build documentation"
	@echo "  serve-docs      Serve docs locally"
	@echo "  version         Show version info"
	@echo ""

# ── Install ───────────────────────────────────────────────────────────────────
install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[dev]"

install-all:
	$(PIP) install -e ".[all]"

# ── Testing ───────────────────────────────────────────────────────────────────
test: test-unit

test-unit:
	$(PYTHON) -m pytest tests/unit/ -v --tb=short

test-integration:
	$(PYTHON) -m pytest tests/integration/ -v --tb=short

coverage:
	$(PYTHON) -m pytest tests/unit/ \
		--cov=$(PACKAGE) \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-report=xml:coverage.xml \
		--tb=short
	@echo ""
	@echo "  HTML report: htmlcov/index.html"

# ── Code Quality ──────────────────────────────────────────────────────────────
lint:
	ruff check $(PACKAGE)/

format:
	ruff format $(PACKAGE)/
	ruff check --fix $(PACKAGE)/

check: lint test

# ── Build ─────────────────────────────────────────────────────────────────────
clean:
	rm -rf dist/ build/ *.egg-info htmlcov/ .coverage coverage.xml .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build: clean
	$(PIP) install build
	$(PYTHON) -m build
	@echo "  Built: dist/"

# ── Docker ────────────────────────────────────────────────────────────────────
docker:
	docker build -t $(IMAGE):$(VERSION) -t $(IMAGE):latest .

docker-push:
	docker push $(IMAGE):$(VERSION)
	docker push $(IMAGE):latest

# ── API Server ────────────────────────────────────────────────────────────────
api:
	@echo "  Starting EoSim API server on http://localhost:$(PORT)"
	@echo "  Swagger UI: http://localhost:$(PORT)/docs"
	@echo "  Production API: https://api.eosim.io"
	$(PYTHON) -m eosim.api.server

# ── Documentation ─────────────────────────────────────────────────────────────
docs:
	doxygen docs/Doxyfile

serve-docs:
	$(PYTHON) -m http.server 8000 --directory docs/site/

# ── Version ───────────────────────────────────────────────────────────────────
version:
	@$(PYTHON) -c "import eosim; print('EoSim', eosim.__version__)"
	@echo "  API: https://api.eosim.io"
	@echo "  Docs: https://docs.eosim.io"
