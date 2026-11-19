# Contributing

Thank you for helping improve Review AI Dashboard. Keep each change focused,
tested, and easy to review.

## Development workflow

1. Update `main` and create a descriptive branch:

   ```sh
   git switch main
   git pull --ff-only
   git switch -c <type>/<short-description>
   ```

2. Make one logical change. Do not commit secrets, `.env` files,
   `node_modules`, build artifacts, or local database files.
   Shared `.editorconfig` and `.gitattributes` rules keep formatting and line
   endings consistent across operating systems and editors.
3. Run the relevant checks below.
4. Commit with a concise message such as `fix: handle an expired session` or
   `docs: clarify the Docker setup`.
5. Open a pull request, complete its checklist, and wait for CI to pass before
   merging.

## Backend checks

Use Python 3.11 or newer. From `backend/`:

```sh
pip install -r requirements-dev.txt ruff==0.17.2 mypy==2.4.0
pytest
ruff check .
ruff format --check .
mypy app main.py scripts
```

Backend tests use temporary SQLite databases and enforce at least 90% test
coverage.

## Frontend checks

Use Node.js 20. From `frontend/`:

```sh
npm ci
npx eslint . --max-warnings 0
npm run format:check
npm run type-check
npm test
npm run build
```

## Application smoke test

From the repository root:

```sh
docker compose up --build --detach --wait
curl --fail http://localhost:8080/health
docker compose down
```

Before merging runtime or deployment changes, also verify the feedback form,
admin sign-in, dashboard, and background review processing. The local demo
credentials are documented in [README.md](README.md).

## Pull requests

- Keep the title and description specific to the implemented change.
- Link an issue with `Closes #<number>` only when the PR fully resolves it.
- Update tests and documentation when behavior or configuration changes.
- Call out migrations, new environment variables, and deployment impact.
- Do not merge with failing or incomplete checks.

For architecture, setup, and environment details, see [README.md](README.md).
