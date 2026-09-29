import os
from pathlib import Path
import subprocess
import sys


def test_dotenv_loaded_before_database_and_auth_settings(tmp_path):
    """Use a fresh interpreter so cached imports cannot hide ordering bugs."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=sqlite:///:memory:\n"
        "JWT_SECRET_KEY=configuration-test-secret\n"
        "JWT_ACCESS_TOKEN_MINUTES=17\n"
        "WEB_SESSION_MINUTES=23\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    for key in ("DATABASE_URL", "JWT_SECRET_KEY", "JWT_ACCESS_TOKEN_MINUTES", "WEB_SESSION_MINUTES", "PYTHON_DOTENV_DISABLED"):
        env.pop(key, None)
    code = '''
import sys
import dotenv
original_load = dotenv.load_dotenv
dotenv.load_dotenv = lambda *args, **kwargs: original_load(sys.argv[1], override=False)
from intake.main import app
from db.database import DATABASE_URL
from auth.security import SECRET_KEY, ACCESS_TOKEN_MINUTES
from auth.web_session import WEB_SESSION_MINUTES
assert DATABASE_URL == "sqlite:///:memory:"
assert SECRET_KEY == "configuration-test-secret"
assert ACCESS_TOKEN_MINUTES == 17
assert WEB_SESSION_MINUTES == 23
'''
    subprocess.run([sys.executable, "-c", code, str(env_file)], env=env, check=True,
                   cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
