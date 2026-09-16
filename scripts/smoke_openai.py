"""Live OpenAI smoke test, using an isolated local app and disposable database.

Run: python scripts/smoke_openai.py [--prompt-key]
Consumes real API tokens. Never loads .env or writes credentials to disk.
This verifies local integration, not the deployed service.
"""

import argparse
import getpass
import json
import logging
import math
import os
from pathlib import Path
import secrets
import sys
import tempfile


class SmokeFailure(RuntimeError):
    """A validation failure containing only a fixed, nonsecret message."""


def require(condition, message):
    if not condition:
        raise SmokeFailure(message)


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt-key', action='store_true')
    args = parser.parse_args()
    if args.prompt_key:
        os.environ['OPENAI_API_KEY'] = getpass.getpass('OpenAI API key: ')
    require(bool(os.getenv('OPENAI_API_KEY')), 'OPENAI_API_KEY is required')
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    original_cwd = Path.cwd()
    with tempfile.TemporaryDirectory(prefix='chatbot-openai-smoke-') as directory:
        os.environ.update({
            'PYTHON_DOTENV_DISABLED': '1',
            'DATABASE_URL': 'sqlite:///' + (Path(directory) / 'smoke.sqlite3').as_posix(),
            'ENVIRONMENT': 'development',
            'LLM_PROVIDER': 'openai',
            'EMBEDDING_PROVIDER': 'openai',
            'JWT_SECRET_KEY': secrets.token_urlsafe(48),
            'WEB_SESSION_SECRET': secrets.token_urlsafe(48),
            'WEB_SESSION_REQUIRED': 'true',
            'WEB_SESSION_COOKIE_SECURE': 'true',
            'REDIS_URL': '',
            'REDIS_REQUIRED': 'false',
            'ADMIN_USERNAME': 'smoke-admin',
            'ADMIN_PASSWORD': secrets.token_urlsafe(24),
            'AGENT_USERNAME': '',
            'AGENT_PASSWORD': '',
            'CRM_WEBHOOK_URL': '',
            'ORDER_STATUS_WEBHOOK_URL': '',
        })
        # Keep logs and static knowledge isolated as well as the database.
        os.chdir(directory)
        engine = None
        try:
            from alembic import command
            from alembic.config import Config
            config = Config(str(root / 'alembic.ini'))
            config.set_main_option('script_location', str(root / 'migrations'))
            command.upgrade(config, 'head')

            from fastapi.testclient import TestClient
            from sqlalchemy import select
            from db.database import SessionLocal, engine
            from db.models import AIInteractionMetric
            from intake.main import app
            from knowledge.document_store import document_store
            from knowledge.retriever import retriever

            logging.disable(logging.CRITICAL)
            code = 'NXT-' + secrets.token_hex(6).upper()
            question = 'What is the activation code for the Orion smoke service?'
            with TestClient(app, base_url='https://testserver') as client:
                for endpoint in ('/health', '/ready'):
                    require(client.get(endpoint).status_code == 200, endpoint + ' failed')
                login = client.post('/auth/login', json={
                    'username': os.environ['ADMIN_USERNAME'],
                    'password': os.environ['ADMIN_PASSWORD'],
                })
                require(login.status_code == 200, 'Admin login failed')
                headers = {'Authorization': 'Bearer ' + login.json()['access_token']}
                response = client.post('/admin/knowledge/documents', headers=headers, json={
                    'title': 'Orion smoke service',
                    'content': 'The activation code for the Orion smoke service is ' + code + '.',
                    'source': 'smoke-test',
                })
                require(response.status_code == 201, 'Document ingestion failed')
                document = response.json()
                require(document['embedded_chunks'] == 1, 'Document embedding missing')
                chunks = document_store.retrieval_chunks()
                require(len(chunks) == 1, 'Expected one isolated document chunk')
                vector = chunks[0]['embedding']
                require(chunks[0]['embedding_provider'] == 'openai', 'Embedding fallback detected')
                require(bool(vector) and all(math.isfinite(v) for v in vector)
                        and any(v != 0 for v in vector), 'Invalid embedding vector')
                hits = retriever.retrieve_with_sources(question)
                require(bool(hits) and hits[0]['document_id'] == document['id'], 'RAG source mismatch')
                require(hits[0]['query_embedding_provider'] == 'openai'
                        and hits[0]['semantic_score'] > 0, 'Semantic retrieval failed')
                session = client.post('/web/session')
                require(session.status_code == 200, 'Web session failed')
                response = client.post('/webhook/web', json={
                    'user_id': session.json()['user_id'],
                    'channel': 'web_chat', 'text': question,
                })
                require(response.status_code == 200, 'Chat request failed')
                chat = response.json()
                require(code in chat['reply'], 'Reply did not contain the retrieved activation code')
                require(chat['delivery_success'] and chat['action_taken'] == 'reply_only',
                        'Response was not delivered normally')
                with SessionLocal() as db:
                    metric = db.scalar(select(AIInteractionMetric).where(
                        AIInteractionMetric.conversation_id == chat['session_id']))
                    require(metric is not None and metric.provider == 'openai', 'OpenAI metric missing')
                    require(metric.input_tokens > 0 and metric.output_tokens > 0,
                            'Provider token usage missing')
                    response = client.get('/admin/quality', headers=headers)
                    require(response.status_code == 200, 'Quality endpoint failed')
                    summary = response.json()
                    require(summary['ai_interactions'] == 1, 'Unexpected interaction count')
                    require(summary['input_tokens'] == metric.input_tokens
                            and summary['output_tokens'] == metric.output_tokens
                            and summary['total_tokens'] == metric.input_tokens + metric.output_tokens,
                            'Persisted token totals mismatch')
                    print(json.dumps({
                        'status': 'passed', 'scope': 'isolated-local-app-live-openai',
                        'model': metric.model, 'embedding_model': chunks[0]['embedding_model'],
                        'embedding_dimensions': len(vector),
                        'semantic_score': hits[0]['semantic_score'],
                        'input_tokens': metric.input_tokens, 'output_tokens': metric.output_tokens,
                        'total_tokens': summary['total_tokens'],
                        'latency_ms': metric.latency_ms, 'reply': chat['reply'],
                    }, indent=2))
        finally:
            if engine is not None:
                engine.dispose()
            os.chdir(original_cwd)


if __name__ == '__main__':
    try:
        run()
    except Exception as exc:
        # API exception strings can include credentials or request bodies.
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__,
                          'http_status': getattr(exc, 'status_code', None),
                          'check': str(exc) if isinstance(exc, SmokeFailure) else None}))
        sys.exit(1)
