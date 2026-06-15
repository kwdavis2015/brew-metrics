# brew-metrics — High-Level Design

## 1. Project Summary

brew-metrics is a short-lived event web app for a bachelor party weekend (June 25–27, 2026) at a lake house with approximately 20 attendees. It tracks brews consumption per person and team, runs a live team scoreboard across ~20 weekend events, and assigns participants to teams via a pre-weekend survey. The two competing teams are **Riks** and **Wades** — they are fixed (seeded in the schema); there is no team-creation flow. Admins manage team membership, not the teams themselves.

This document covers architecture, technology decisions, infrastructure, and security. The original requirements were captured in `riks-vs-wades-dashboard-spec.md`, which is kept for historical reference only (gitignored).

---

## 2. Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Backend | Python / FastAPI | Async support, simple REST + SSE, familiar language |
| Frontend | HTMX + Jinja2 templates | No build step, SSE-friendly, sufficient for mobile-first polling UI |
| Database | PostgreSQL 16 (RDS) | Relational audit trail, joins across brew log and event results, SQL aggregations for Brew Cup formula |
| DB layer | Raw SQL + psycopg2 | No ORM — queries are plain SQL in `app/queries.py`, schema in `app/schema.sql`, connection pool via psycopg2 |
| Container base image | `public.ecr.aws/docker/library/python:3.12-slim` | AWS-hosted, no Docker Hub rate limits |
| Container registry | AWS ECR (private) | Native ECS integration |
| Infrastructure-as-code | Terraform | Fits SRE background, reproducible, state managed in S3 |

**Frontend note:** HTMX is chosen over React because this app is mostly server-rendered data with incremental updates. The TV dashboard uses HTMX polling or Server-Sent Events for auto-refresh. If a richer SPA experience is needed, the backend API is clean enough to swap in React without changes to the backend.

---

## 3. AWS Infrastructure

### Hosting

**Amazon ECS Express Mode** is the compute platform. ECS Express Mode provisions a complete application stack (ECS Fargate service, Application Load Balancer, autoscaling, networking) from a single API call. No EC2, no EKS cluster management required.

- Source: ECR private image
- Deploy by calling `aws ecs update-express-gateway-service` (or `terraform apply`) after pushing a new image
- TLS/HTTPS provided automatically; service URL format: `https://<name>.ecs.<region>.on.aws`
- Custom domain optional via Route 53 CNAME → ALB DNS name (see §6)

> **Migration note:** AWS App Runner closed to new customers in 2026. ECS Express Mode is AWS's official replacement, preserving the same operational simplicity.

### Infrastructure Components

```
┌────────────────────────────────────────────────────────────────┐
│ AWS Account                                                    │
│                                                                │
│  ECR (private)                                                 │
│      │                                                         │
│      │              VPC (10.0.0.0/16)                          │
│      │         ┌──────────────────────────────────────┐        │
│      │         │  Public subnets (10.0.10-11.0/24)    │        │
│      │         │  ┌─────────────────────────────┐     │        │
│      └────────►│  │  ALB (managed by ECS)        │     │        │
│                │  │  ECS Fargate tasks           │     │        │
│  (HTTPS URL)   │  └──────────────┬──────────────┘     │        │
│                │                 │ port 5432           │        │
│                │  Private subnets│(10.0.1-2.0/24)     │        │
│                │  ┌──────────────▼──────────────┐     │        │
│                │  │  RDS PostgreSQL 16           │     │        │
│                │  └─────────────────────────────┘     │        │
│                │                                       │        │
│                │  Secrets Manager (VPC-reachable)      │        │
│                └──────────────────────────────────────┘        │
└────────────────────────────────────────────────────────────────┘
```

### Terraform Resources

| Resource | Purpose |
|---|---|
| `aws_vpc` + subnets (public + private) | Public subnets for ECS/ALB; private subnets for RDS |
| `aws_internet_gateway` + route table | Internet access for Fargate tasks and ALB |
| `aws_ecr_repository` | Private container registry |
| `aws_db_instance` | RDS Postgres 16, `db.t3.micro` |
| `aws_secretsmanager_secret` | DB credentials, admin credentials |
| `aws_cloudwatch_log_group` | Container logs at `/ecs/brew-metrics` |
| `aws_ecs_express_gateway_service` | Provisions Fargate service + ALB + autoscaling |
| `aws_iam_role` (x3) | Task execution, infrastructure, task roles |
| `aws_security_group` (x2) | ECS tasks SG → RDS SG on port 5432 |

State backend: S3 bucket + DynamoDB lock table (provisioned separately or manually first).

---

## 4. Application Architecture

### Request Flow

```
Phone browser / TV browser
        │
        │ HTTPS
        ▼
  App Runner (FastAPI container)
        │
        ├── /survey             → pre-event skill/arrival survey (public)
        ├── /                   → participant brews input page
        ├── /dashboard          → public phone dashboard
        ├── /tv                 → TV 16:9 auto-refresh dashboard
        ├── /admin              → admin portal (JWT cookie required)
        │     ├── /admin/survey → review responses + build teams
        │     ├── /admin/brews  → brew log + reversals
        │     └── /admin/events → event scoring
        │
        ▼
  RDS PostgreSQL (private VPC)
```

### Key Architectural Rules

- The container is **stateless** — all state lives in RDS. Any restart or scale event is safe.
- Brew log is **append-only**. No row is ever deleted or updated. Corrections are new rows with `status: reversed` and `reversal_of_entry_id` set.
- Brew Cup points are **computed at query time** from the live brew log using a proportional formula: leading team gets the full `points_available` (200), trailing team gets `round((their_total / leader_total) * 200)`. Never stored statically.
- Keg totals are enforced at the API layer: the server rejects keg brew entries that would push a team past 330. Keg totals are computed live from `brew_log WHERE status = 'active' AND source = 'keg'` rather than maintained as a counter.

---

## 5. Authentication & Authorization

### Admin Portal

- Simple username/password login at `/admin/login`
- Credentials stored in AWS Secrets Manager (not env vars, not code)
- On successful login, server issues a signed JWT stored in an HTTP-only cookie (short expiry, e.g. 8 hours)
- All `/admin/*` routes are protected by JWT middleware
- Single admin account to start; the secret can hold a small list if multiple admins are needed

### Regular Users

- **No authentication required**
- On first visit, the app prompts the user to create a display name / userid (e.g., "MikeD")
- The chosen userid is stored in `localStorage` in the browser
- If the user clears storage or switches devices, they re-select their name from the active participant list — **honor system**
- The server does not validate identity; it trusts the submitted `person_id`
- Admins can correct misattributed entries via the correction workflow

### Survey Access

- `/survey` is public with no authentication — the link is shared with all invitees ~1 week before the event
- Submissions are deduplicated by name at the application layer (a second submission from the same name overwrites the first)
- Survey responses create a `people` record in `pre_registered` status with no team assignment — their name is in the system before the weekend starts

### Team Assignment Flow

**Pre-event (survey-driven):**
1. Admin shares `/survey` link with all ~20 invitees ~1 week out
2. Invitees complete the form — skills, brews rank, arrival/departure times
3. Admin opens `/admin/survey` to review all responses
4. Admin uses the team builder view (skill balance + arrival time view) to assign each person to Riks or Wades
5. Admin finalizes teams — `people` records are updated with `team_name` and status `active`

**Day-of (walk-up):**
1. Participant opens the app URL and selects their name from the pre-registered list
2. If someone shows up who didn't complete the survey, admin creates their record manually from `/admin/survey`
3. Their name is stored in browser `localStorage` — honor system from that point forward

---

## 6. URL and Access Strategy

- ECS Express Mode provides a default HTTPS URL (`https://<name>.ecs.<region>.on.aws`)
- The URL is not publicly advertised or indexed — shared only via QR code or group chat link
- **No IP allowlisting or auth wall on the URL itself** — obscurity via unguessable subdomain is sufficient for a 3-day event
- Optional: map a custom subdomain (e.g., `brews.yourdomain.com`) via Route 53 CNAME → ALB DNS name — adds a cleaner QR code URL
- HTTPS is terminated at the ALB; HTTP redirects to HTTPS automatically

---

## 7. Data Model

Full schema defined in `brew-metrics/app/schema.sql` (applied automatically on app startup). Summary:

| Table | Purpose |
|---|---|
| `teams` | Fixed seed of `Riks` + `Wades`; FK target for people/brew_log/keg state. Not added to at runtime |
| `people` | Participant identity, team assignment, userid |
| `team_survey_responses` | Pre-weekend skill/arrival survey results |
| `brew_log` | Append-only brew entries; reversals are rows not deletes |
| `team_keg_state` | Per-team keg capacity (330), logged total, finish timestamp |
| `event_master` | Event catalog with status and `points_available` |
| `event_results` | Per-event Riks/Wades points, entered by admin |
| `admin_adjustments` | Audit ledger for manual corrections and overrides |

---

## 8. Application Views

| View | Path | Auth | Primary Device | Phase |
|---|---|---|---|---|
| Pre-event survey | `/survey` | None | Phone | Pre-event |
| Participant brew input | `/` | None | Phone | Weekend |
| Public phone dashboard | `/dashboard` | None | Phone | Weekend |
| Public event scoring | `/events` | None | Phone | Weekend |
| TV dashboard | `/tv` | None | TV browser (16:9) | Weekend |
| Admin login | `/admin/login` | None (form) | Any | Both |
| Admin — survey review + team builder + roster | `/admin/survey` | JWT cookie | Laptop preferred | Pre-event |
| Admin — brew log + corrections | `/admin/brews` | JWT cookie | Phone or laptop | Weekend |
| Admin — event scoring | `/admin/events` | JWT cookie | Phone or laptop | Weekend |

`/events` is the public, honor-system scoring page: anyone selects their name (stored in `localStorage`) and enters points; the submitter is recorded as `entered_by`. `/admin/events` shows the same scoring with an `entered_by` audit column so cheating can be spotted. There is no `/admin/teams` route — team membership and the team roster live on `/admin/survey`.

TV dashboard auto-refreshes every 15–30 seconds via HTMX polling or SSE. No manual reload needed on the TV.

### `/admin/survey` — Team Builder Detail

This is the primary pre-event admin tool. It needs:

- **Responses table** — all survey submissions with arrival time, ranked skills, brew skill rank
- **Skill balance panel** — for each skill category, shows how the current draft split distributes talent across Riks/Wades
- **Arrival timeline** — visual or tabular view of who arrives Thursday vs. Friday so teams aren't lopsided at the start
- **Team assignment controls** — dropdown per person to assign Riks / Wades / Unassigned (auto-submits on change)
- **Finalize button** — locks team assignments and marks all assigned people as `active`; unassigned respondents remain `pre_registered`
- **Add person manually** — for walk-ups or people who skipped the survey
- **Team roster** — read-only view grouping all participants by team (Riks / Wades / Unassigned) with per-team counts, for an at-a-glance view of the whole team

---

## 9. Survey Lifecycle

```
~1 week before event
        │
        ├── Admin shares /survey link (group chat or email)
        │
        ▼
Invitees complete /survey on their phones
  → team_survey_responses row created
  → people row created (status: pre_registered, team: null)
        │
        ▼
Admin reviews /admin/survey
  → checks skill balance across proposed split
  → checks arrival timeline for early/late skew
  → assigns each person to Riks or Wades
  → clicks Finalize
        │
        ▼
people rows updated (status: active, team_name: Riks|Wades)
        │
        ▼
Event weekend begins
  → participants open app URL, select their pre-registered name
  → localStorage saves their identity
  → brew logging and event scoring go live
```

### Survey Form Fields

Matches spec §5. Collected fields:
- `full_name` (required)
- `nickname` (optional)
- `expected_arrival_day` — Thursday / Friday / Saturday (required)
- `expected_arrival_time` — approximate time (optional)
- `expected_departure_day/time` (optional)
- `top_3_skills_ranked` — ordered selection from the skill list
- `brew_drinking_skill_rank` — 1 (light), 2 (average), 3 (heavy)
- `notes` (optional free text)

Skill list (from spec): brew drinking, flong/drinking games, billiards, cornhole, Brewsby, darts, shuffleboard, golf sim, arcade games, giant Jenga/Connect 4, trivia, keg race/relay.

### Data flow: survey → people table

Survey submission creates both records atomically:

```sql
-- On survey submit
INSERT INTO team_survey_responses (...) VALUES (...);
INSERT INTO people (full_name, nickname, arrival_time, status, team_name)
  VALUES (..., 'pre_registered', NULL)
  ON CONFLICT (full_name) DO UPDATE SET ...;  -- handles re-submissions
```

---

## 10. Repository Structure

The repo uses two application subdirectories to keep validation work separate from the production app:

```
brew-metrics-test/   Minimal hello-world FastAPI app. Used only to validate the Docker
                     build pipeline and AWS deployment (ECR push, App Runner, VPC/RDS).
                     Has its own pyproject.toml, Dockerfile, and tests. Not deployed to
                     production. Decommissioned once end-to-end AWS deployment is confirmed.

brew-metrics/        Production application. All feature development happens here.
                     Has its own pyproject.toml, Dockerfile, and tests.

terraform/           Single Terraform root managing all AWS infrastructure for both
                     apps (VPC, ECR repos, RDS, App Runner services, IAM, Secrets Manager).

docs/                Design documents. high-level-design.md is the authoritative source.
```

Each subdirectory builds to its own Docker image and pushes to its own ECR repository, avoiding any need for version tagging or URI versioning to distinguish test from production traffic.

---

## 11. Local Development

Local development uses Docker Compose (`brew-metrics/docker-compose.yml`) to run Postgres 16 alongside the app:

```bash
docker compose up -d db                    # Postgres only (for fast reload with poetry)
docker compose up -d                       # full stack (app + db)
docker compose down -v                     # tear down + wipe DB
```

DB credentials for local dev: `brewadmin` / `localdev` / `brewmetrics` on `localhost:5432`.

Schema is applied automatically on app startup via the FastAPI lifespan handler — no manual migration step needed. HTMX is vendored locally (`app/static/htmx.min.js`) so the app works without internet access.

### Testing

Tests (`pytest`) run against a real local Postgres — start it with `docker compose up -d db` (the app container is not required). Test isolation is tuned for speed:

- **Schema and the app connection pool are session-scoped** — `schema.sql` is applied once and the pool is initialized once per run.
- **Per-test reset** is a fast `TRUNCATE ... RESTART IDENTITY` + reseed of the two fixed teams over a single shared autocommit connection, rather than a per-test schema rebuild.
- The `client` fixture is built **without** the `TestClient` context manager so the app lifespan does not re-fire (and rebuild the pool/schema) on every test.

This keeps the full suite at ~1–2s. Any raw `psycopg2` connection opened inside a test must be closed in `try/finally` — a connection leaked on a failed assertion holds a lock that blocks the next test's `TRUNCATE` and hangs the suite.

---

## 12. Deployment Pipeline (Initial / Manual)

For the first deploy and testing phase, the flow is manual:

```
1. docker build -t brew-metrics .
2. docker tag brew-metrics <account>.dkr.ecr.<region>.amazonaws.com/brew-metrics:latest
3. aws ecr get-login-password | docker login --username AWS --password-stdin <ecr-url>
4. docker push <ecr-url>/brew-metrics:latest
5. terraform apply   # or: aws ecs update-express-gateway-service --service-arn <arn> --primary-container image=<new-image>
```

Terraform manages all infrastructure. After `terraform apply`, the ECR repo URL and ECS Express Mode service URL are output variables.

A GitHub Actions pipeline can be added later using the `aws-actions/amazon-ecs-deploy-express-service` action to automate steps 1–5 on push to `main`.

A GitHub Actions pipeline can be added later to automate steps 1–4 on push to `main`.

---

## 13. Scope Boundaries

**In scope:**
- Brew logging, keg tracking, Brew Cup auto-scoring
- Event scoreboard with admin point entry
- Pre-weekend team survey and team assignment
- TV dashboard, phone dashboard, participant input, admin portal
- Terraform-managed AWS infrastructure

**Out of scope:**
- Native mobile app
- User account creation / email verification / password reset
- Real-time WebSocket push (polling is sufficient for this use case)
- Multi-event / multi-weekend reuse (this is a one-time weekend app)
- CI/CD pipeline (manual deploy is acceptable for the timeline)
