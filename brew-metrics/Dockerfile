FROM --platform=linux/amd64 public.ecr.aws/docker/library/python:3.12-slim AS builder
RUN pip install poetry
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.in-project true \
 && poetry install --only main --no-root

FROM --platform=linux/amd64 public.ecr.aws/docker/library/python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY app/ app/
COPY db/ db/
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
