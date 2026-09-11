# Production deployment

## Required configuration

Set `DATABASE_URL` to PostgreSQL, a long random `JWT_SECRET_KEY`, bootstrap admin credentials for the first deployment, `GEMINI_API_KEY`, and the WhatsApp credentials when that channel is enabled. Never use values from `.env.example` in production.

## Database

Run `alembic upgrade head` before starting a new application release. Back up PostgreSQL before schema migrations and use a managed database with encrypted connections and automated backups.

## Application

Build the Docker image from the repository. The container runs as an unprivileged user and exposes `/health` for liveness and `/ready` for database readiness. Put TLS termination and rate limiting at the reverse proxy or platform edge.

## Integrations

Configure `CRM_WEBHOOK_URL`, `CRM_WEBHOOK_TOKEN`, and `ORDER_STATUS_WEBHOOK_URL` only for trusted HTTPS endpoints. Configure the Meta webhook secret so incoming WhatsApp requests are signature verified.

## Release gate

A release is eligible for deployment only when GitHub Actions passes dependency installation, `alembic upgrade head`, and the full pytest suite. After deployment verify `/health`, `/ready`, login, web chat, human handoff, feedback, and the configured external channels.

## Remaining infrastructure choices

Production hosting, managed PostgreSQL provider, domain/TLS, secret manager, backups, alert destination, and real third-party CRM/order endpoints are environment-specific and must be supplied by the deployer. They are intentionally not hard-coded in this repository.
