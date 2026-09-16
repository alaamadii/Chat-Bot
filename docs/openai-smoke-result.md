# OpenAI migration verification

Live integration smoke test passed on 2026-09-16 against application revision
`4c8b7a1`, using `scripts/smoke_openai.py` and an isolated temporary SQLite database.
The API key was entered through a hidden prompt and was not saved to a file.

| Check | Result |
| --- | --- |
| Alembic migrations | Applied through `0007_outbound_outbox` |
| Local health and readiness | HTTP 200 |
| Admin login and knowledge ingestion | Passed |
| Document and query embeddings | Real OpenAI requests, `text-embedding-3-small` |
| Stored embedding dimensions | 1536 |
| Retrieved source semantic score | 0.918139 |
| Cookie-authenticated browser message | Passed through `/webhook/web` |
| Grounded answer | Contained the randomly generated fact from the ingested document |
| Response model | `gpt-5.6-luna` |
| Persisted input/output tokens | 125 / 26 |
| Quality endpoint total tokens | 151, matching persisted interaction metrics |
| Generation latency | 3600 ms |

This result verifies the local application with live OpenAI calls, not a deployed
service. It does not verify the existing production knowledge index, PostgreSQL,
Redis, or external delivery channels. Embedding request token usage is not included
in the application's generation-token metrics.

Deployment secret configuration and deployed smoke verification remain pending:
the hosting platform, target project, and service URL have not been identified.
The application version remains `6.3.0`; no release was published and the migration
has not been marked complete.
