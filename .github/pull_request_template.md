## Summary

Describe what changed and why.

## Checklist

- [ ] Changes are scoped to this PR
- [ ] Tests were added or updated where needed
- [ ] `pytest -q` passes locally
- [ ] `alembic upgrade head` succeeds on a clean database
- [ ] Database changes include an Alembic migration
- [ ] New environment variables are documented in `.env.example`
- [ ] No secrets or production credentials are committed
- [ ] Security/authorization impact was reviewed
- [ ] README/production docs were updated when behavior changed

## Deployment notes

Mention migrations, configuration changes, external integration changes, or rollout risks. Write `None` if there are none.
