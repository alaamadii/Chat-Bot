# NextTech AI Support Bot

Production-oriented customer support platform built with FastAPI, Gemini, PostgreSQL/SQLite, WhatsApp webhooks, a browser chat UI, human-agent handoff, analytics, customer feedback, audit logs, and managed knowledge retrieval.

## What the project includes

- Web chat UI at `/`
- Agent dashboard at `/dashboard`
- FastAPI API and OpenAPI docs at `/docs`
- Gemini-powered response generation
- Structured intent classification and deterministic action routing
- BM25 knowledge retrieval across static and managed knowledge
- Persistent conversations and messages
- Human handoff workflow with assignment, ownership, replies, resolve/reopen states
- WhatsApp webhook verification, signature validation, inbound parsing, and outbound delivery
- JWT role-based access control for agents and admins
- Persistent users with bcrypt password hashing
- Knowledge management endpoints
- AI quality metrics, latency/confidence tracking, escalation metrics, and CSAT feedback
- Audit trail for privileged/support operations
- CRM and order-status webhook integration points
- Alembic database migrations
- Docker and Docker Compose support
- GitHub Actions CI with migration validation and pytest
- Liveness and readiness endpoints

## Architecture

```text
User / WhatsApp / Web Chat
          |
          v
       Intake
          |
          v
   Conversation Store
          |
          +---------------------> Human Agent Queue
          |                            |
          |                            v
          |                     Agent Dashboard
          |                            |
          |                            v
          |                         Delivery
          |
          v
    Intent Classifier
          |
          v
   Knowledge Retrieval
        (BM25)
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
  Delivery
     |
     v
Analytics / AI Metrics / Feedback / Audit
```

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
ADMIN_USERNAME=admin
ADMIN_PASSWORD=replace-me
AGENT_USERNAME=agent
AGENT_PASSWORD=replace-me
```

Optional integrations are documented in `.env.example`.

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
- Database readiness: `http://127.0.0.1:8000/ready`

## Docker

For local PostgreSQL + API:

```bash
docker compose up -d db
docker compose run --rm api alembic upgrade head
docker compose up --build api
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

For local testing you can expose port `8000` with a tunneling service and configure the public `/webhook/whatsapp` URL in Meta's developer console.

## Knowledge and retrieval

The bot combines:

- `knowledge_base.json`
- managed database knowledge entries

Retrieval uses BM25 ranking before the selected snippets are passed into Gemini. Admins can add or remove managed knowledge without editing the JSON file manually.

## Quality and analytics

The project persists:

- intent
- confidence
- model/provider
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

GitHub Actions validates:

1. dependency installation
2. `alembic upgrade head` on a clean database
3. the full pytest suite

## Production deployment

See [`docs/PRODUCTION.md`](docs/PRODUCTION.md) for release, database, secrets, reverse-proxy, integration, and infrastructure guidance.

Deployment-specific infrastructure still has to be supplied by the deployer: hosting, PostgreSQL, TLS/domain, secrets, backup/alert destinations, and real third-party integration credentials.

## Demo

[Video demo](https://drive.google.com/file/d/1KfCMBhyGucs8oKSCfGJ2OcyrH42dYaYL/view?usp=sharing)

## Author

Alaa Madi
