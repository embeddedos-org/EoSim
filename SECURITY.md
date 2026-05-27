# Security Policy

## Supported Versions

| Version | Supported | Description |
|---------|-----------|-------------|
| **3.0.x** | ✅ Current | Production Release (v3.0.1) |
| **2.0.x** | ❌ No | Deprecated |
| **1.0.x** | ❌ No | Deprecated |

---

## Reporting a Vulnerability

**Email:** [security@embeddedos.org](mailto:security@embeddedos.org)  
**Response time:** Within 48 hours.

### What to include
- Description of the vulnerability
- Steps to reproduce (PoC)
- Affected versions
- Impact assessment (if known)

### Process
1. **Report via email** (do **NOT** open a public issue).
2. We acknowledge receipt within **48 hours**.
3. We investigate, patch, and provide a fix timeline.
4. **CVE** is assigned for confirmed issues.
5. Security advisory published after fix is released.

---

## Scope

| Component | Status | Notes |
|-----------|--------|-------|
| `eosim/` | **In Scope** | Core engine, CLI, GUI, registry, and analysis modules. |
| `eosim/api/` | **In Scope** | REST API endpoints, middleware, CORS, and security filters. |
| Platform configs | **In Scope** | Configuration parsing and schema validation. |
| Third-party tools | *Out of Scope* | QEMU, Renode, OpenOCD (report to upstream). |
| Examples / Demos | *Out of Scope* | Non-production example/demo configurations. |

---

## Security Hardening

- **HTTPS Enforced:** All production API connections use `https://api.eosim.io` with TLS 1.3.
- **Non-Root Execution:** Docker images and Helm/Kubernetes deployments run as non-root user `eosim` (UID 1000).
- **Cleartext Blocked:** Native Android and iOS app configurations explicitly block cleartext HTTP traffic.
- **CORS Restricted:** CORS is strictly configured to only allow production domains (`*.eosim.io`, `embeddedos-org.github.io`) and localhost (only in development mode).
