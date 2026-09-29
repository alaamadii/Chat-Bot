import uuid

import pytest

from ai_brain.confidence_scorer import scorer
from ai_brain.intent_classifier import classifier
from ai_brain.models import AIResponse


@pytest.mark.parametrize('message', ['hi', 'HI!', 'hello', 'hey there', 'مرحبا', 'أهلاً', 'السلام عليكم'])
def test_greeting_does_not_trigger_handoff(message):
    output = scorer.score(AIResponse(text='Hello!'), classifier.classify(message))
    assert not output.escalate_to_human


@pytest.mark.parametrize('message', ['hi, I have a problem', 'hello, my website is broken'])
def test_greeting_does_not_hide_support_request(message):
    output = scorer.score(AIResponse(text='Let us help.'), classifier.classify(message))
    assert output.intent.category == 'support'
    assert output.escalate_to_human


def test_return_to_bot_then_greeting_stays_with_bot(monkeypatch):
    from fastapi.testclient import TestClient
    from auth.security import create_access_token
    from intake.main import app

    monkeypatch.setenv('EMBEDDING_PROVIDER', 'local')
    monkeypatch.setenv('WEB_SESSION_COOKIE_SECURE', 'false')
    monkeypatch.setattr('ai_brain.pipeline.generator.generate',
                        lambda *args: AIResponse(text='Hello! How can I help?'))
    with TestClient(app) as client:
        user_id = client.post('/web/session').json()['user_id']
        payload = {'channel': 'web_chat', 'user_id': user_id, 'text': 'I have a problem'}
        first = client.post('/webhook/web', json=payload)
        assert first.status_code == 200
        assert first.json()['conversation_status'] == 'WAITING_FOR_AGENT'
        token = create_access_token({'username': 'test-' + uuid.uuid4().hex, 'role': 'admin'})
        returned = client.patch(
            '/agent/conversations/' + first.json()['session_id'] + '/status',
            headers={'Authorization': 'Bearer ' + token}, json={'status': 'BOT_ACTIVE'},
        )
        assert returned.status_code == 200
        payload['text'] = 'hi'
        reply = client.post('/webhook/web', json=payload)
        assert reply.status_code == 200
        assert reply.json()['conversation_status'] == 'BOT_ACTIVE'
        assert reply.json()['action_taken'] == 'reply_only'
        assert reply.json()['reply'] == 'Hello! How can I help?'
