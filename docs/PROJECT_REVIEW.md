# Project review — 2026-09-29

Reviewed main commit `c595d48` and the local greeting/dashboard fixes. The project
has a working local support workflow, but it is not yet a fully verified production
deployment. Passing offline tests does not establish live AI or channel health.

## Fixes in this PR

- Load the repository `.env` before database and authentication settings are
  captured. Previously the response generator loaded it too late, allowing the
  default database/JWT signing key to be used despite configured values.
  Process environment still takes precedence, and dotenv can be disabled.
- Escape customer/assignment/channel/status data in dashboard HTML, including
  message roles. Resolve the status element explicitly instead of `window.status`.
- Preserve and test the existing local greeting fix: standalone greetings stay
  with the bot, while greetings containing support requests still escalate.
- Isolate pytest from local credentials, external providers, application databases,
  and interaction logs; use a fresh temporary database for each run.
- Exclude local secrets, databases, caches and virtual environments from Docker's
  build context and generated runtime files from Git. Exclude virtual environments
  from the application Bandit scan. Add the dashboard regression test to CI.

## Validation

- Python: 62 tests passed; CI-selected module coverage 81.66% (gate: 25%).
- Node: one dashboard regression test passed using a simulated DOM. This checks
  escaped output and status updates; it is not a real-browser visual test.
- Ruff syntax/undefined-name checks passed.
- Bandit application scan at high severity passed. This is not a dependency audit
  or penetration test. The initial scan also traversed a nested local virtual
  environment; those third-party findings are outside the corrected source scan.
- All seven Alembic migrations applied to a fresh SQLite database.
- Docker production image built successfully with Python 3.12.
- A running local HTTP server returned 200 for `/`, `/dashboard`, `/docs`,
  `/health`, and `/ready`. Verified login, signed web session, greeting, support
  handoff, claiming, agent reply, transcript retrieval, and return to bot.
- Local Python tests ran on Windows/Python 3.13. Deprecation warnings remain in
  datetime handling and test-client dependencies.
- Live OpenAI, Meta/WhatsApp, CRM, PostgreSQL, Redis, production TLS, concurrent
  load, real-browser interactions and continuous SSE delivery were not verified.

## Work needed before a production release

| Priority | Finding / evidence | Completion criterion |
| --- | --- | --- |
| High | `intake/main.py:agent_reply` and the human-support branch of `services/chat_service.py` send directly through `delivery_engine`, bypassing the durable outbox. | Route all outbound WhatsApp messages through a transactionally persisted outbox; test worker crashes, retries, and delivery state reconciliation. |
| High | `api/ops.py:readiness` accepts `REDIS_REQUIRED=true` with no `REDIS_URL`; `core/rate_limit.py` then falls back locally. | Reject missing required Redis configuration and verify readiness/rate limits against real Redis, including outages. |
| High | `auth/security.py:current_user` trusts role and username in an unexpired token without checking persisted active state. | Define and test account disablement, role changes, logout/revocation and session lifetime policy. |
| High | Real runtime credentials/infrastructure are not configured in this local checkout. | Configure AI access, PostgreSQL, Redis as needed, strong secrets, HTTPS, backups/restore, monitoring, and the outbox worker; execute deployed end-to-end tests. |
| Medium | `ai_brain/context_builder.py` assembles history, but `response_generator.py` only sends the latest message and snippets. | Pass bounded conversation history to generation; test follow-up questions against a controlled provider and a live model. |
| Medium | Intent classification is keyword-based, general requests escalate at confidence 0.5, and generation explicitly requires English. | Define supported Arabic/English behavior, evaluate realistic customer messages and false handoffs, and test grounded answers plus provider failures. |
| Medium | `actions/integrator.py` returns a generated lead ID even on missing/failed CRM delivery; the router reports `crm_lead_created`. Order lookup has no routing path. | Persist/retry leads and report actual integration state; wire order intent to authenticated lookup or remove the advertised capability. |
| Medium | `/ready` checks infrastructure, not AI availability; an offline/error reply can still produce a successful chat HTTP response. | Add operational provider monitoring and acceptance checks for grounded responses and token metrics, with explicit customer fallback behavior. |
| Medium | Dashboard and browser workflows have limited automated browser coverage. | Add real-browser tests for login, refresh/session expiry, claim conflicts, mobile layout, errors, and SSE reconnection. Expand concurrency tests on PostgreSQL. |

## Local preview

The review preview binds only to `127.0.0.1:8000`, uses a separate ignored SQLite
database, signed browser sessions, and an offline provider. It supports trying the
UI and human handoff; the offline response is an explicit AI-unavailable message.
Preview credentials are temporary local configuration and are not committed.

To enable real answers later, configure `OPENAI_API_KEY` through the runtime
environment, choose the intended model, restart with `LLM_PROVIDER=openai`, and
run the live smoke procedure in `docs/PRODUCTION.md`. Configure the remaining
channels separately. This review does not certify a production release.
