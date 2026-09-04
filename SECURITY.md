# Security Policy

This document defines how we handle security for **SIH26182 – VASP Wallet Attribution**. It applies to all code, dependencies, and deployment artefacts in this repository. If you are a contributor, reviewer, or downstream deployer, read this before handling secrets, dependencies, or vulnerability reports.

## Supported versions

| Branch / Tag | Status | Receives security fixes |
|--------------|--------|-------------------------|
| `main` (latest `0.1.x`) | **Supported** | Yes — all high and critical fixes are backported to the latest minor on `main` |
| `develop` | Supported (pre-release) | Yes — fixes land here first, then are promoted to `main` via release PR |
| Older minors / archived tags | **Not supported** | No — upgrade to latest `main` |

We version the API (`/api/v1`) independently from the internal engine. Breaking changes to public interfaces require `BREAKING CHANGE:` in the commit and an entry in `docs/contracts.md`.

## Reporting a vulnerability — private disclosure only

**Do NOT file a public GitHub issue for a suspected vulnerability.** Private disclosure protects investigators, cases, and LEA data that this system is built to handle.

### How to report

1. **Email the maintainers privately.** Use the addresses in [`.github/CODEOWNERS`](.github/CODEOWNERS) or `security@` contacts listed there. If no email is listed, open a **private security advisory** via GitHub: `Security → Advisories → New draft advisory`.
2. **Encrypt if possible.** If you have our PGP key, encrypt the report. If not, plain email is acceptable — do not delay the report.
3. **Include:**
   - Clear description of the issue and the affected component / file / commit.
   - Reproduction steps (PoC, curl, script, or test case).
   - Impact assessment (confidentiality / integrity / availability, who is affected).
   - Scope (which branches, chains, or deployment modes are exposed).
   - Any known mitigations or workarounds.

### What happens next

| Step | Timeline | Owner |
|------|----------|-------|
| Acknowledgement | **Within 2 business days** | Maintainers |
| Triage & severity (CVSS) | Within 5 business days | Security team |
| Fix for **critical / high** (RCE, auth bypass, data leak, SSRF) | **Within 7 days** of triage | Maintainers |
| Fix for **medium / low** | Next scheduled minor | Maintainers |
| Coordinated disclosure & advisory | After fix is available; we credit the reporter unless anonymity is requested | Maintainers + reporter |

We follow **coordinated disclosure**: we will not disclose the issue publicly until a fix is available on `main` and, where relevant, a GitHub Security Advisory is published. We expect reporters to do the same. We provide **safe harbor** for good-faith research that follows this policy and does not exfiltrate case data, degrade services, or violate law.

## Scope

### In scope

- `api/` FastAPI service, `packages/common`, `data/synthetic`, Docker images, GitHub Actions workflows, and `scripts/` that touch secrets or migrations.
- Authentication and authorization (JWT, RBAC, `passlib`/`bcrypt`, `python-jose`), session handling, and SAHYOG gateway integration.
- Blockchain provider adapters (they handle external input that becomes case evidence).
- PostgreSQL and Redis usage (injection, connection handling, migration safety).

### Out of scope (but still appreciated)

- Social engineering, physical access, or denial-of-service that requires physical proximity.
- Findings that require a heavily contrived local configuration far from our documented `docker compose` / `.env.example` setup, without demonstrating realistic impact.

### Current maturity note

The repository is at **Stage 1 + Stage 2** (synthetic offline demo + 8-stage attribution engine, see `docs/phases-mapping.md`). Authentication is intentionally minimal, providers are offline-first, and the demo stack binds to `127.0.0.1` by default. Do not expose this stage to a public network or real case data. The controls below are being hardened incrementally per `docs/work-packages.md`.

## Threat model (summary)

| Asset | Threat | Mitigation (today → planned) |
|-------|--------|------------------------------|
| LEA case data (wallets, attributions, reports) | Unauthorized read / tamper | RBAC in `app/core/security.py` + row-level case ownership (Phase 8 DDL, Phase 12) → audit pipeline (Phase 25, WP-29) |
| Secrets (`.env`, `SECRET_KEY`, `DATABASE_URL`, provider API keys) | Leak via repo, logs, or image layers | `.env` is git-ignored, `python-dotenv` loads at runtime only, CI injects via GitHub Secrets, no secrets in Docker layers (`api/Dockerfile` multi-stage), structured logs redact secrets (see `app/core/logging.py`) |
| Supply chain | Compromised dependency | Pinned dependencies in `api/pyproject.toml`, `uv.lock`, Dependabot (planned), `pip-audit` in CI (planned), no `curl | bash` in workflows |
| External input (addresses, chain payloads, SAHYOG messages) | Injection, SSRF, deserialization | Pydantic validation on every ingress (`api/app/schemas/`), `BlockchainProvider` ABC sanitizes `CanonicalTransaction`, SAHYOG adapter is the only egress point (`app/sahyog/gateway.py`) |
| Evidence integrity | Tampered attribution trails | `HAC-003` evidence-tier model (`docs/development.md`), `attribution_evidence` table with provider provenance (`api/app/db/models/`), future signed reports (WP-26) |

For a deeper architecture view see `docs/architecture.md` and `docs/contracts.md` (frozen public interfaces).

## Secure coding requirements for contributors

All contributors must follow these:

- **No secrets in source.** Never commit `.env`, tokens, or private keys. Use `.env.example` as the template; the real `.env` stays local and is injected in CI via GitHub Secrets.
- **Validate at the boundary.** Every HTTP handler, provider response, and SAHYOG payload must be validated with Pydantic before use. Do not trust raw `raw:` fields from `CanonicalTransaction`.
- **Absolute imports** inside `api` (`from app.xxx import ...`), no relative imports that obscure provenance.
- **Least privilege.** New endpoints must declare their required role; new DB queries must respect `case_id` scoping.
- **No `eval` / `exec` / `pickle` on external data.** If you need dynamic behaviour, use explicit registries (`ProviderRegistry`, `SahyogGateway`).
- **Log safely.** Use `structlog` via `app/core/logging.py`; never log `SECRET_KEY`, `DATABASE_URL`, or full payloads that contain case data. Redaction helpers are in `app/core/logging.py`.
- **Dependencies.** Add new dependencies to `api/pyproject.toml` with a lower bound (`>=`) and an upper bound when the API is unstable; run `uv pip compile` / update `uv.lock`.

## Dependency and secrets management

- **Python dependencies:** `api/pyproject.toml` + `uv.lock` are the source of truth. CI installs with `pip install -e ".[dev]"` in a fresh runner; images build with `uv pip install` in `api/Dockerfile`.
- **Base images:** `postgres:16-alpine`, `redis:7-alpine`, `python:3.12-slim` — pinned by digest in production (planned, WP-33).
- **Scanning:** `ruff` is enforced in CI (`lint` job). Secret scanning (GitHub secret scanning + `gitleaks` pre-commit hook) is enabled. `pip-audit` and container scanning are on the roadmap (WP-32/33).
- **Rotation:** If a secret is suspected leaked, rotate it immediately in `.env` and in GitHub Secrets, and notify maintainers via the private channel above.

## Vulnerability handling checklist (for maintainers)

1. Create a **private fork / security branch** (never push the fix to a public branch before advisory).
2. Reproduce, add a regression test, and fix on that branch.
3. Bump the version in `api/pyproject.toml` and root `pyproject.toml` if the fix changes behaviour.
4. Request review from at least one other maintainer; require CI green (`lint` + `import smoke` + `pytest`).
5. Publish a **GitHub Security Advisory**, link the CVE if assigned, and credit the reporter.
6. Merge to `develop` → release PR to `main` → tag → announce in `#dev` with migration steps.

## Contact

- **Security contact:** maintainers listed in [`.github/CODEOWNERS`](.github/CODEOWNERS).
- **General questions:** open a non-security issue via `.github/ISSUE_TEMPLATE/` (bug / feature / chore).
- **LEA deployment questions:** route through the SAHYOG integration channel documented in `docs/architecture.md` Layer 8.

---

*Last reviewed: September 2026. This policy is versioned with the repository — changes require a PR and review, just like code.*