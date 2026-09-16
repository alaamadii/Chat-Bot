# Production deployment

## Required configuration

Set `DATABASE_URL` to PostgreSQL, a long random `JWT_SECRET_KEY`, a separate long random `WEB_SESSION_SECRET`, bootstrap admin credentials for the first deployment, `OPENAI_API_KEY`, and the WhatsApp credentials when that channel is enabled. Never use values from `.env.example` in production and never commit the real OpenAI API key to the repository.

Set `LLM_PROVIDER=openai`. `EMBEDDING_PROVIDER=auto` uses OpenAI embeddings when `OPENAI_API_KEY` is present. `OPENAI_MODEL` and `OPENAI_EMBEDDING_MODEL` can be overridden by the deployment environment without code changes.

Set `ENVIRONMENT=production` so weak secrets are rejected and secure browser-cookie behavior is enabled. Keep `WEB_SESSION_COOKIE_SECURE=true` behind HTTPS/TLS. Browser session credentials are carried in an HttpOnly, SameSite=Strict cookie and must not be moved into URLs or browser storage.

## Database

Run `alembic upgrade head` before starting a new application release. Back up PostgreSQL before schema migrations and use a managed database with encrypted connections and automated backups.

## Application

Build the Docker image from the repository. The container runs as an unprivileged user and exposes `/health` for liveness and `/ready` for database readiness. Put TLS termination at the reverse proxy or platform edge.

For multi-replica deployments configure `REDIS_URL` and set `REDIS_REQUIRED=true`. Redis provides shared public rate limiting and realtime pub/sub; the SSE path reconciles against PostgreSQL so committed events remain recoverable.

The public web chat ships with a restrictive Content Security Policy. Keep its JavaScript and CSS as same-origin external assets; do not reintroduce inline scripts or `unsafe-inline` without a security review.

## Outbound delivery

Run the outbox worker alongside the API (`python -m services.outbox_worker`) or use the provided Docker Compose service. Configure `OUTBOX_MAX_ATTEMPTS`, `OUTBOX_RETRY_BASE_SECONDS`, `OUTBOX_PROCESSING_LEASE_SECONDS`, `OUTBOX_POLL_SECONDS`, and `OUTBOX_BATCH_SIZE` for the deployment. Monitor dead-lettered outbound rows because they represent delivery attempts that exhausted retry policy.

## Integrations

Configure `CRM_WEBHOOK_URL`, `CRM_WEBHOOK_TOKEN`, and `ORDER_STATUS_WEBHOOK_URL` only for trusted HTTPS endpoints. Configure the Meta webhook secret so incoming WhatsApp requests are signature verified. `WEBHOOK_PROCESSING_LEASE_SECONDS` controls recovery of webhook events left in `processing` after a crashed worker/request.

## Release gate

A release is eligible for deployment only when GitHub Actions passes dependency installation, lint checks, the high-severity security scan, `alembic upgrade head`, the pytest coverage gate, and the production Docker image build. After deployment verify `/health`, `/ready`, OpenAI response generation, knowledge retrieval, login, cookie-authenticated web chat, SSE agent delivery, human handoff, feedback, the outbox worker, and configured external channels.

## Remaining infrastructure choices

Production hosting, managed PostgreSQL/Redis providers, domain/TLS, secret manager, backups, alert destination, and real third-party CRM/order endpoints are environment-specific and must be supplied by the deployer. They are intentionally not hard-coded in this repository.
