# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`brew-metrics` is a lightweight web app built for a bachelor party weekend (~20 people). It tracks brew consumption, runs a live scoreboard across team events, and handles team creation via a pre-weekend survey. The two competing teams are **Riks** and **Wades**.

`docs/high-level-design.md` is the authoritative source for architecture, technology decisions, and screen requirements. Read it before making significant design decisions.

> **Note:** `docs/riks-vs-wades-dashboard-spec.md` is kept for historical reference only and is gitignored. Do not update it and do not treat it as an active requirement source. The HLD supersedes it.

## Stack

- **Backend:** Python / FastAPI
- **Frontend:** HTMX + Jinja2 templates (no build step, no React)
- **Database:** PostgreSQL 16 on RDS
- **Container base:** `public.ecr.aws/docker/library/python:3.12-slim`
- **Registry:** AWS ECR (private)
- **Hosting:** AWS App Runner (stateless container; all state in RDS)
- **Secrets:** AWS Secrets Manager — DB credentials and admin credentials are never in env vars or code
- **IaC:** Terraform (`terraform/`)

## Common Commands

```bash
# Install dependencies (run from brew-metrics-test/ or brew-metrics/)
poetry install

# Run dev server
poetry run uvicorn app.main:app --reload

# Run all tests
poetry run pytest

# Run a single test file
poetry run pytest tests/test_main.py

# Build Docker image (run from the relevant subdirectory)
docker build -t brew-metrics-test .   # from brew-metrics-test/
docker build -t brew-metrics .        # from brew-metrics/

# Provision / update infrastructure
cd terraform && terraform init && terraform plan && terraform apply
```

## Project Structure

```
brew-metrics-test/   Hello-world app for validating Docker build and AWS deployment only
  app/               FastAPI application code
  tests/             Tests mirroring app/ structure
  Dockerfile
  pyproject.toml

brew-metrics/        Production application (active development)
  app/
  tests/
  Dockerfile
  pyproject.toml

terraform/           All AWS infrastructure (VPC, ECR, RDS, App Runner, IAM, Secrets)
docs/                Design documents
```

## Key Domain Concepts

- **Brew Cup** — highest-point event category. Points are computed at query time from live brew totals using a proportional formula; never stored statically until an admin locks them.
- **Keg cap** — each team's keg is capped at 330 brews. The API layer enforces this; it rejects entries that would exceed the cap unless the request carries an admin override flag.
- **Append-only brew log** — no row is ever deleted or updated. Reversals are new rows with `status: reversed` and `reversal_of_entry_id` set.
- **People status lifecycle** — `pre_registered` (survey submitted, no team yet) → `active` (team assigned by admin) → used for brew logging and dashboards.
- **Honor system identity** — regular users have no auth. They pick their name from the participant list; it is stored in browser `localStorage`. The server trusts the submitted `person_id`.

## Authentication

- **Admin portal** (`/admin/*`): username/password → signed JWT in HTTP-only cookie (8h expiry). Credentials live in Secrets Manager, read by the app at startup via the instance IAM role.
- **Regular users**: no authentication. Honor system.
- **`/survey`**: public, no auth. Name collisions (re-submissions) are handled with `ON CONFLICT (full_name) DO UPDATE`.

## Application Routes

| Path | Auth | Phase |
|---|---|---|
| `/survey` | None | Pre-event |
| `/` | None | Weekend |
| `/dashboard` | None | Weekend |
| `/tv` | None | Weekend |
| `/admin/login` | None | Both |
| `/admin/survey` | JWT cookie | Pre-event |
| `/admin/brews` | JWT cookie | Weekend |
| `/admin/events` | JWT cookie | Weekend |

## Data Model

Core tables (see spec §10 for full field lists):
- `people` — identity, team assignment, status (`pre_registered` | `active`)
- `team_survey_responses` — pre-weekend skill/arrival survey
- `brew_log` — append-only; reversals are new rows
- `team_keg_state` — per-team keg capacity, logged total, finish timestamp
- `event_master` — event catalog with status and `points_available`
- `event_results` — per-event Riks/Wades points, entered by admin
- `admin_adjustments` — audit ledger for manual corrections

## Testing

Every feature change must include tests. The test suite uses `pytest` with `httpx` for FastAPI route testing.

**Structure:** `tests/` mirrors `app/`. A file at `app/routers/survey.py` gets tests at `tests/routers/test_survey.py`.

**What to test per change:**
- Happy path for each new route or function
- Input validation / rejection cases
- Business rule enforcement (keg cap, append-only log, Brew Cup formula, status transitions)
- Auth boundary — protected routes must return 401/403 without a valid JWT; unprotected routes must not require one

**Fixtures:** Use a test database (real Postgres via a `DATABASE_URL` pointed at a local or CI instance) rather than mocking the DB layer. Mock only external AWS calls (Secrets Manager, boto3).

**Keep tests simple** — one assertion per test where possible, descriptive names, no shared mutable state between tests.

## Reference Documents

| Document | Status | Purpose |
|---|---|---|
| `docs/high-level-design.md` | Active — authoritative | Architecture, routes, data model, tech decisions |
| `docs/riks-vs-wades-dashboard-spec.md` | Gitignored — historical only | Original requirements; do not edit or reference for new work |
