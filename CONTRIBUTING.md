# Contributing to SIH26182

Welcome! This document explains how the team collaborates on the
**SIH26182 – VASP Wallet Attribution** codebase. The goal is to make it
easy for multiple developers to work in parallel without stepping on
each other.

---

## 1. Branching model

| Branch          | Purpose                                                  |
|-----------------|----------------------------------------------------------|
| `main`          | Stable, production-ready. **PR only.**                  |
| `develop`       | Integration branch for the next release. **PR only.**    |
| `feature/<x>`   | New functionality. Branched from `develop`.             |
| `fix/<issue>`   | Bug fixes. Branched from `develop`.                      |
| `chore/<x>`     | Tooling, docs, refactors with no behaviour change.       |
| `release/<v>`   | Release prep (version bumps, changelog). From `develop`.|
| `hotfix/<x>`    | Emergency fix to `main`.                                  |

> **Naming convention:**
> - `feature/<short-kebab-name>` — e.g. `feature/eth-provider-live`
> - `fix/<issue-number>-<short-desc>` — e.g. `fix/142-attribution-stuck`
> - `chore/<short-desc>` — e.g. `chore/update-ruff`

> **Branch protection (recommended GitHub settings):**
> - `main` and `develop`: require pull request reviews, dismiss stale
>   approvals on push, require status checks from the `ci` workflow,
>   require linear history.
> - Direct pushes to `main`/`develop` are forbidden.

---

## 2. Workflow

1. Make sure your `develop` is up to date:
   ```bash
   git fetch origin
   git checkout develop
   git pull --ff-only origin develop
   ```
2. Create your branch:
   ```bash
   git checkout -b feature/<short-name>
   ```
3. Work in small, focused commits (Conventional Commits below).
4. Push and open a Pull Request **into `develop`**:
   ```bash
   git push -u origin feature/<short-name>
   gh pr create --base develop --head feature/<short-name>
   ```
5. Wait for CI to pass, request review from at least one teammate, address
   feedback, then merge (squash by default).
6. `develop` is periodically merged into `main` via a release PR.

---

## 3. Conventional Commits

We follow the [Conventional Commits](https://www.conventionalcommits.org/)
spec. Every commit message looks like:

```
<type>(<scope>)<!>: <short summary>

<body explaining motivation and trade-offs>

<footer with issue / BREAKING CHANGE markers>
```

| Type       | Use for                                                  |
|------------|----------------------------------------------------------|
| `feat`     | New user-facing feature                                  |
| `fix`      | Bug fix                                                  |
| `docs`     | Docs only                                                |
| `style`    | Formatting / lint-only changes                           |
| `refactor` | Code change with no behaviour change                     |
| `test`     | Adding or fixing tests                                   |
| `chore`    | Tooling, build, CI                                       |
| `perf`     | Performance improvement                                  |

Examples (already used in this repo):
- `feat: initial monorepo scaffold for SIH26182 VASP attribution system`
- `chore: add team collaboration base (CI, pre-commit, docs)`

---

## 4. Pull Request checklist

Every PR must:

- [ ] Have a descriptive title following the commit convention
- [ ] Reference a GitHub issue (`Closes #123`) when one exists
- [ ] Be **squash-merged** (keeps history tidy)
- [ ] Pass `ci` (lint + import smoke + tests)
- [ ] Update docs if behaviour changed (`docs/*.md`)
- [ ] Stay within the assigned **work package** (see
      `docs/work-packages.md`)
- [ ] Touch the **Work Package matrix** in `docs/work-packages.md` only
      after coordination with the owning teammate

> Use `.github/PULL_REQUEST_TEMPLATE.md` – it fills in the checklist
> automatically.

---

## 5. Local development setup

```bash
git clone <repo-url>
cd vasp-wallet-attribution
./scripts/bootstrap.sh
```

That script:

1. Copies `.env.example` → `.env` (if missing).
2. Pulls base Docker images.
3. Starts the stack via `docker compose up -d --build`.
4. Waits for `/api/v1/health` to respond.

Optional one-time setup:

```bash
pip install pre-commit
pre-commit install
```

Now `ruff` and the other hooks will fire on every commit.

---

## 6. Daily commands

| Task                        | Command                |
|-----------------------------|------------------------|
| Bring stack up              | `make up`              |
| Tail api logs               | `make logs`            |
| Open api shell              | `make shell`           |
| Apply DB migrations         | `make migrate`         |
| Run tests                   | `make test`            |
| Run linter locally          | `make lint`            |
| Auto-format                 | `make format`          |
| Generate migration          | `make revision m="..."`|
| Run quick sanity checks     | `make check`           |

---

## 7. Code style

- **Python 3.12** (target). Ruff + `ruff format` is the source of truth.
- **Absolute imports** inside `api` (`from app.xxx import ...`).
- **Docstrings** must reference the relevant SIH26182 phase.
- **No secrets** in source. Use `.env`, never commit it.
- **Tests** live in `api/tests/`. Mirror the module structure.
- **Public interfaces** (see `docs/contracts.md`) must not change without
  a `BREAKING CHANGE:` footer in the commit AND a heads-up in `#dev`.

---

## 8. Work packages & ownership

See `docs/work-packages.md` for the current split. Pick an unassigned row,
claim it, and link your branch in the matrix.

---

## 9. Reporting issues

Use the appropriate issue template in `.github/ISSUE_TEMPLATE/`:

- `bug.md` – something is broken.
- `feature.md` – new functionality proposal.
- `chore.md` – tooling, deps, refactor.

---

## 10. Getting help

- `#dev` Slack channel (or whatever your team uses).
- Open a `question.md` issue.
- Ping a CODEOWNER (`/.github/CODEOWNERS`).