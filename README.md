# brew-metrics

A lightweight web app for a bachelor party weekend (~20 people) at a lake house. Tracks brew consumption per person and team, runs a live scoreboard across weekend events, and handles team creation via a pre-weekend survey. Two teams compete: **Riks** vs **Wades**.

Built with FastAPI, HTMX, Jinja2, and PostgreSQL. Deployed on AWS App Runner with Terraform-managed infrastructure.

## Local Development

Prerequisites: Docker, Poetry

```bash
# From the brew-metrics/ directory:
cd brew-metrics
poetry install

# Start Postgres + app via Docker Compose
docker compose up -d

# Or: start Postgres only, run app with hot reload (faster iteration)
docker compose up -d db
DATABASE_URL=postgresql://brewadmin:localdev@localhost:5432/brewmetrics \
  poetry run uvicorn app.main:app --reload
```

App runs at http://localhost:8080 (Docker Compose) or http://localhost:8000 (uvicorn direct).

Admin login: `admin` / `admin`

## Running Tests

Requires Postgres running locally (via Docker Compose).

```bash
cd brew-metrics
docker compose up -d db
poetry run pytest
```

## Project Structure

```
brew-metrics/          Production app (FastAPI + HTMX + Postgres)
brew-metrics-test/     Minimal hello-world app for AWS deployment validation
terraform/             AWS infrastructure (VPC, ECR, RDS, App Runner, IAM, Secrets)
docs/                  Design documents
```
