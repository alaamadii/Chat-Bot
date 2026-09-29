"""Capture reproducible, offline evidence for the QA portfolio report."""
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'qa-evidence'
BASE = 'c595d48fbd286864f1d429b256256d0ec67ce802'


def run(name, args, *, cwd=ROOT, env=None):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=180)
    output = result.stdout + result.stderr
    output = output.replace(str(ROOT), '<PROJECT>').replace(str(Path(sys.executable)), '<PYTHON>')
    evidence = (
        f'Command: {args[0] if args[0] != sys.executable else "python"} ' +
        ' '.join(args[1:]) + f'\nExit code: {result.returncode}\n\n' + output
    )
    evidence = evidence.replace(tempfile.gettempdir(), '<TEMP>')
    (OUT / (name + '.txt')).write_text(evidence, encoding='utf-8')
    print(name, 'exit=', result.returncode)
    return result


def main():
    OUT.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update(PYTHON_DOTENV_DISABLED='1', LLM_PROVIDER='offline', EMBEDDING_PROVIDER='local',
               OPENAI_API_KEY='', REDIS_URL='', REDIS_REQUIRED='false', ENVIRONMENT='development')
    metadata = {'captured_utc': datetime.now(timezone.utc).isoformat(),
                'tested_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'baseline_commit': BASE, 'python': platform.python_version(),
                'platform': platform.system(), 'node': subprocess.check_output(['node', '--version'], text=True).strip()}
    (OUT / 'environment.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    checks = [
        ('pytest', [sys.executable, '-m', 'pytest', '-q', '--disable-warnings', '--cov=api', '--cov=auth', '--cov=core', '--cov=db', '--cov=intake', '--cov=services', '--cov=knowledge', '--cov-report=term', '--cov-fail-under=25']),
        ('dashboard', ['node', '--test', 'tests/dashboard.test.cjs']),
        ('dashboard-comparison', ['node', 'scripts/compare_dashboard.cjs']),
        ('ruff', [sys.executable, '-m', 'ruff', 'check', '.', '--select', 'E9,F63,F7,F82']),
        ('bandit', [sys.executable, '-m', 'bandit', '-q', '-r', 'api', 'auth', 'core', 'db', 'intake', 'services', 'knowledge', 'actions', 'ai_brain', 'delivery', '-x', 'tests,.venv,venv', '-lll']),
    ]
    for name, args in checks:
        assert run(name, args, env=env).returncode == 0, name
    with tempfile.TemporaryDirectory(prefix='qa-baseline-') as tmp:
        base_dir = Path(tmp)
        archive = subprocess.check_output(['git', 'archive', '--format=zip', BASE], cwd=ROOT)
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            bundle.extractall(base_dir)
        config = base_dir / 'qa.env'
        config.write_text('DATABASE_URL=sqlite:///:memory:\nJWT_SECRET_KEY=qa-synthetic-secret\nJWT_ACCESS_TOKEN_MINUTES=17\n', encoding='utf-8')
        code = '''
import sys, json, dotenv
original = dotenv.load_dotenv
dotenv.load_dotenv = lambda *a, **kw: original(sys.argv[1], override=False)
from intake.main import app
from db.database import DATABASE_URL
from auth.security import SECRET_KEY, ACCESS_TOKEN_MINUTES
from ai_brain.intent_classifier import classifier
from ai_brain.confidence_scorer import scorer
from ai_brain.models import AIResponse
result = scorer.score(AIResponse(text='Hello!'), classifier.classify('hi'))
print(json.dumps({'configured_database_used': DATABASE_URL == 'sqlite:///:memory:',
 'configured_jwt_key_used': SECRET_KEY == 'qa-synthetic-secret',
 'configured_token_lifetime_used': ACCESS_TOKEN_MINUTES == 17,
 'greeting_intent': result.intent.category, 'greeting_escalates': result.escalate_to_human}))
'''
        comparison_env = env.copy()
        for key in ['PYTHON_DOTENV_DISABLED', 'DATABASE_URL', 'JWT_SECRET_KEY', 'JWT_ACCESS_TOKEN_MINUTES']:
            comparison_env.pop(key, None)
        for label, directory in [('before', base_dir), ('after', ROOT)]:
            result = run(label, [sys.executable, '-c', code, str(config)], cwd=directory, env=comparison_env)
            assert result.returncode == 0
        migration_env = env | {'DATABASE_URL': 'sqlite:///' + (base_dir / 'migration.sqlite3').as_posix()}
        assert run('migrations', [sys.executable, '-m', 'alembic', 'upgrade', 'head'], env=migration_env).returncode == 0
    print('Evidence capture complete.')


if __name__ == '__main__':
    main()
