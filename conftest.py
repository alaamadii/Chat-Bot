"""Keep normal pytest runs independent of local secrets and application data."""

import os
import tempfile
from pathlib import Path

import pytest


_test_data = tempfile.TemporaryDirectory(prefix="chatbot-tests-", ignore_cleanup_errors=True)
os.environ.update({
    "PYTHON_DOTENV_DISABLED": "1",
    "DATABASE_URL": "sqlite:///" + (Path(_test_data.name) / "tests.sqlite3").as_posix(),
    "LLM_PROVIDER": "offline",
    "EMBEDDING_PROVIDER": "local",
    "OPENAI_API_KEY": "",
    "ENVIRONMENT": "development",
    "JWT_SECRET_KEY": "test-secret",
    "WEB_SESSION_SECRET": "test-web-session-secret",
    "WEB_SESSION_REQUIRED": "false",
    "WEB_SESSION_COOKIE_SECURE": "false",
    "ADMIN_USERNAME": "admin",
    "ADMIN_PASSWORD": "admin123",
    "AGENT_USERNAME": "agent",
    "AGENT_PASSWORD": "agent123",
    "REDIS_URL": "",
    "REDIS_REQUIRED": "false",
    "CRM_WEBHOOK_URL": "",
    "ORDER_STATUS_WEBHOOK_URL": "",
    "WHATSAPP_ACCESS_TOKEN": "",
    "WHATSAPP_PHONE_NUMBER_ID": "",
    "WHATSAPP_APP_SECRET": "",
    "WHATSAPP_VERIFY_TOKEN": "test-verify-token",
})


@pytest.fixture(scope="session", autouse=True)
def isolate_interaction_log():
    from analytics.logger import logger

    original = logger.log_file
    logger.log_file = str(Path(_test_data.name) / "chat_logs.jsonl")
    yield
    logger.log_file = original
