# Changelog

All notable changes to this project are documented in this file.

The project follows Semantic Versioning for published releases.

## [6.0.0] - 2026-09-11

### Added
- Browser-based customer Web Chat at `/`.
- Agent dashboard at `/dashboard` with queue, transcript, claim, reply, resolve, and return-to-bot flows.
- Persistent conversations and messages using SQLAlchemy with PostgreSQL support and SQLite fallback.
- Conversation lifecycle states: `BOT_ACTIVE`, `WAITING_FOR_AGENT`, `HUMAN_ACTIVE`, `RESOLVED`, and `CLOSED`.
- JWT authentication and role-based access control for agents and admins.
- Persistent users with bcrypt password hashing and controlled bootstrap credentials.
- Meta WhatsApp webhook verification, signature validation, inbound parsing, and outbound delivery.
- Human-agent assignment and ownership enforcement.
- Managed knowledge entries stored in the database.
- BM25 retrieval across static and managed knowledge.
- Structured AI intent propagation and deterministic action routing.
- Configurable Gemini model and temperature.
- AI interaction metrics including provider, model, latency, confidence, and escalation state.
- Customer feedback / CSAT endpoint and admin quality summary.
- Audit events for privileged and support operations.
- CRM lead and order-status integration hooks.
- Alembic migrations and migration validation in CI.
- Docker and Docker Compose support with non-root runtime and healthcheck.
- Liveness (`/health`) and database readiness (`/ready`) endpoints.
- GitHub Actions CI for dependency installation, migrations, and pytest.
- Production deployment documentation.
- Security policy, contribution guide, Dependabot configuration, PR template, and CODEOWNERS.

### Changed
- Replaced the original in-memory-only conversation flow with database-backed persistence.
- Replaced free-text reasoning-based action routing with structured intent-based routing.
- Replaced basic term-frequency retrieval with BM25 ranking.
- Updated the project README to reflect the completed v6 platform.
- Aligned application and health endpoint version metadata to `6.0.0`.

### Security
- Added WhatsApp webhook HMAC signature verification when `WHATSAPP_APP_SECRET` is configured.
- Added password hashing for persistent users.
- Added JWT-protected agent/admin routes.
- Added non-root Docker runtime.
- Added audit logging for sensitive support/admin actions.

### Release notes
See `docs/releases/v6.0.0.md`.
