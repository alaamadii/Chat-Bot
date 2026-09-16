# NextTech AI Support Bot

Production-oriented customer support platform built with FastAPI, Gemini, PostgreSQL/SQLite, Redis, WhatsApp webhooks, browser chat, human-agent handoff, analytics, durable outbound delivery, and hybrid knowledge retrieval.

## What the project includes

- Web chat UI at `/`
- Agent dashboard at `/dashboard`
- FastAPI API and OpenAPI docs at `/docs`
- Gemini-powered response generation with provider abstraction and token-usage metrics
- Structured intent classification and deterministic action routing
- Hybrid BM25 + semantic embedding retrieval across managed knowledge documents/chunks
- Persistent conversations, messages, assignments, users, audit events, webhook state, and AI metrics
- Human handoff workflow with assignment, ownership, replies, resolve/reopen states
- WhatsApp webhook verification, HMAC signature validation, inbound idempotency, and outbound delivery
- Durable transactional outbox with retries, leases, and dead-letter visibility
- JWT role-based access control for agents and admins
- Signed browser sessions in HttpOnly SameSite=Strict cookies
- Persistent users with bcrypt password hashing
- Knowledge document ingestion and reindexing endpoints
- AI quality metrics, latency/confidence tracking, escalation metrics, token usage, and CSAT feedback
- Redis-backed distributed rate limiting and realtime SSE fan-out with database reconciliation/fallback
- Audit trail for privileged/support operations
- CRM and order-status webhook integration points
- Alembic database migrations
- Docker and Docker Compose support
- GitHub Actions CI with lint, security scan, migration validation, coverage gate, and production image build
- Liveness and readiness endpoints

## Architecture

```text
User / WhatsApp / Web Chat
          |
          v
       Intake
          |
          v
   Conversation Store -----------------> Redis realtime fan-out
          |                                      |
          +---------------------> Human Agent Queue
          |                            |
          |                            v
          |                     Agent Dashboard
          |                            |
          |                            v
          |                      Durable Outbox
          |                            |
          v                            v
    Intent Classifier              Delivery
          |
          v
   Hybrid Knowledge Retrieval
      BM25 + embeddings
          |
          v
        Gemini
          |
          v
  Confidence / Escalation
          |
          v
     Action Router
      /        \
     v          v
  Reply     Integration
     |
     v
 Durable Outbox / Delivery
     |
     v
Analytics / AI Metrics / Feedback / Audit
```

PostgreSQL is the durable source of truth. Redis is used for distributed rate limiting and realtime pub/sub when configured; realtime events are emitted only after the database transaction commits.

## Quick start

### 1. Clone and create an environment

```bash
git clone https://github.com/alaamadii/Chat-Bot.git
cd Chat-Bot
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and configure the values you need.

Minimum useful local configuration:

```env
GEMINI_API_KEY=your_key
DATABASE_URL=sqlite:///./chatbot.db
JWT_SECRET_KEY=replace-with-a-long-random-secret
WEB_SESSION_SECRET=replace-with-a-separate-long-random-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=replace-me
AGENT_USERNAME=agent
AGENT_PASSWORD=replace-me
```

For multi-replica production deployments, configure `REDIS_URL` and set `REDIS_REQUIRED=true`.

### 4. Apply database migrations

```bash
alembic upgrade head
```

### 5. Start the API

```bash
uvicorn intake.main:app --reload
```

Then open:

- Web chat: `http://127.0.0.1:8000/`
- Agent dashboard: `http://127.0.0.1:8000/dashboard`
- API docs: `http://127.0.0.1:8000/docs`
- Liveness: `http://127.0.0.1:8000/health`
- Readiness: `http://127.0.0.1:8000/ready`

## Docker

For local PostgreSQL + Redis + API + outbox worker:

```bash
docker compose up -d db redis
docker compose run --rm api alembic upgrade head
docker compose up --build api outbox-worker
```

The production image runs as a non-root user and includes a container healthcheck.

## Authentication and roles

Bootstrap admin/agent accounts are created only when their environment credentials are explicitly configured. Passwords are stored as bcrypt hashes.

Available roles:

- `admin`: user management, audit logs, AI quality metrics, knowledge management, and agent capabilities
- `agent`: conversation queue, claim/assignment, transcript access, replies, and status changes

Login endpoint:

```text
POST /auth/login
```

## Human handoff flow

```text
BOT_ACTIVE
    |
    | escalation
    v
WAITING_FOR_AGENT
    |
    | agent claims conversation
    v
HUMAN_ACTIVE
    |
    | agent resolves
    v
RESOLVED
```

While a conversation is waiting for or actively handled by a human agent, new user messages bypass the AI pipeline and remain in the human support flow.

## WhatsApp

Configure:

```env
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_APP_SECRET=
WHATSAPP_API_VERSION=v23.0
```

Webhook endpoint:

```text
GET/POST /webhook/whatsapp
```

Incoming message IDs are persisted for idempotency. Outbound messages use the durable outbox/retry path where applicable. For local testing you can expose port `8000` with a tunneling service and configure the public webhook URL in Meta's developer console.

## Knowledge and retrieval

The knowledge layer supports managed documents and chunks with embedding metadata. Retrieval combines BM25 lexical relevance and cosine semantic similarity using configurable hybrid weighting. Gemini embeddings are used when configured; the project also provides a deterministic local embedding fallback for development/tests.

Admins can ingest knowledge documents and reindex existing documents without editing application code.

## Realtime and distributed runtime

The browser conversation event endpoint is:

```text
GET /web/conversations/{conversation_id}/events
```

With Redis configured, committed message events are published through Redis pub/sub and delivered over SSE. The endpoint reconciles with the database so missed pub/sub messages can be recovered. Without Redis, or when Redis is optional and unavailable, it falls back to database polling for local/single-replica operation.

For multi-replica production deployments, configure `REDIS_URL`, set `REDIS_REQUIRED=true`, and use a managed Redis service. The same Redis backend supports distributed public rate limiting.

## Quality and analytics

The project persists:

- intent and confidence
- provider/model
- input/output token usage when reported by the provider
- response latency
- escalation state
- customer feedback / rating
- conversation metrics
- audit events

Useful endpoints include:

```text
GET  /agent/analytics
POST /feedback
GET  /admin/quality
GET  /admin/audit
```

## External integrations

Optional business integration variables:

```env
CRM_WEBHOOK_URL=
CRM_WEBHOOK_TOKEN=
ORDER_STATUS_WEBHOOK_URL=
```

These must point to trusted production services; they are intentionally not hard-coded into the repository.

## Tests and CI

Run locally:

```bash
pytest -q
```

GitHub Actions validates dependency installation, Ruff linting, Bandit high-severity findings, Alembic migrations on a clean database, the pytest coverage gate, and the production Docker image build.

## Production deployment

See [`docs/PRODUCTION.md`](docs/PRODUCTION.md) for release, database, Redis, secrets, reverse-proxy, worker, integration, and infrastructure guidance.

Deployment-specific infrastructure still has to be supplied by the deployer: hosting, PostgreSQL, Redis for distributed production, TLS/domain, secrets, backups/alerts, and real third-party integration credentials.

## Release

Current application release: **v6.3.0**.

- [Changelog](CHANGELOG.md)
- [v6.3.0 release notes](docs/releases/v6.3.0.md)

## Demo

[Video demo](https://drive.google.com/file/d/1KfCMBhyGucs8oKSCfGJ2OcyrH42dYaYL/view?usp=sharing)

## Author

Alaa Madi
