# Contributing

## Development workflow

1. Create a feature or fix branch from `main`.
2. Keep changes focused and avoid unrelated refactors in the same pull request.
3. Add or update tests for behavior changes.
4. If the database schema changes, add an Alembic migration.
5. Run the release checks locally before opening a pull request.
6. Open a pull request to `main` and wait for CI to pass before merging.

## Local checks

```bash
pip install -r requirements.txt
alembic upgrade head
pytest -q
```

For Docker-based validation:

```bash
docker compose up -d db
docker compose run --rm api alembic upgrade head
docker compose run --rm api pytest -q
```

## Pull request expectations

A pull request should explain:

- what changed
- why the change is needed
- API/database/environment-variable changes
- tests added or updated
- deployment or migration considerations

## Architecture rules

- Keep transport/channel logic out of the AI core when possible.
- Use structured intent/action data rather than parsing generated free text.
- Preserve the human-handoff state machine and agent ownership checks.
- Keep secrets and production credentials out of source control.
- Use Alembic for production schema changes.
- Add configuration through environment variables and document it in `.env.example`.

## Security

For security issues, follow `SECURITY.md` rather than opening a public vulnerability report.