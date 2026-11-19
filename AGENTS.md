# Review AI Dashboard — contributor guide

## Current application

This repository contains one public player feedback form and an AI-assisted admin dashboard. A Celery worker analyzes submitted reviews and generates draft replies. The optional seed loads 100 CS2-themed reviews into an empty database. The app does not implement case opening, an inventory, or Steam withdrawals.

- Backend: Python 3.11+, FastAPI, SQLAlchemy, Alembic (`backend/`).
- Frontend: Vue 3, TypeScript, Pinia, Vite (`frontend/`).
- Runtime: PostgreSQL 16, Redis 7, one web container and one Celery worker.
- AI providers: Groq, Gemini, or the offline stub. Do not add the OpenAI SDK.
- User documentation and local launch: `README.md` and `compose.yaml`.

## Checks before a push

From `backend/`: install `requirements-dev.txt`, `ruff==0.17.2`, and `mypy==2.4.0`, then run `pytest`, `ruff check .`, `ruff format --check .`, and `mypy app main.py scripts`. Pytest uses temporary SQLite files and enforces at least 90% coverage.

From `frontend/`: run `npm ci`, `npx eslint . --max-warnings 0`, `npm run format:check`, `npm run type-check`, `npm test`, and `npm run build`.

From the repository root: run `docker compose up --build -d`, then check the public form, admin login, submitted review, worker analysis, statistics, CSV export, status update, and draft regeneration. The local account is `admin-artem-leo` / `password-artem-leo`.

## Development rules

- Backend: follow Ruff and mypy checks; use English docstrings and type annotations, Pydantic v2, and SQLAlchemy 2 style.
- Frontend: use Vue Composition API with `<script setup lang="ts">`, explicit types, responsive CSS, and Prettier.
- Keep application code modular. Never commit secrets, `.env`, `node_modules`, build output, local databases, or editor settings.
- Keep seeded reviews at 100 and keep their analysis fields consistent with their language and content. Seeding must remain idempotent for nonempty databases.

## Deployment

The root `Dockerfile` builds the frontend and backend into one image. Nginx serves the SPA on the runtime `PORT` (default 8080) and proxies API requests to uvicorn. The container must listen on `0.0.0.0:$PORT`. `deploy/start.sh` runs migrations and the optional demo seed before starting the servers.

Run one separate worker from the same image with:

```sh
celery -A app.core.celery_app.celery_app worker --loglevel=info --concurrency=2 --queues=reviews --beat --schedule=/tmp/celerybeat-schedule
```

Provide PostgreSQL and Redis connection URLs, a strong `JWT_SECRET_KEY`, administrator credentials, and AI keys through deployment environment variables. See `.env.example` for setting names. Keep the web app and worker on the same Redis and database instances. `SEED_DEMO_DATA=true` fills only an empty database.

If the new repository is connected to an automatic deployment service, verify its trigger and configuration before pushing to `main`.
