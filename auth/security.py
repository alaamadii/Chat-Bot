import os
from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select

from db.database import SessionLocal
from db.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "480"))


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def seed_default_users() -> None:
    defaults = [
        (os.getenv("ADMIN_USERNAME", "admin"), os.getenv("ADMIN_PASSWORD", "admin123"), "admin"),
        (os.getenv("AGENT_USERNAME", "agent"), os.getenv("AGENT_PASSWORD", "agent123"), "agent"),
    ]
    with SessionLocal() as db:
        for username, password, role in defaults:
            if not db.scalar(select(User).where(User.username == username)):
                db.add(User(username=username, password_hash=hash_password(password), role=role))
        db.commit()


def authenticate(username: str, password: str) -> dict | None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username, User.is_active.is_(True)))
        if not user or not verify_password(password, user.password_hash):
            return None
        return {"username": user.username, "role": user.role}


def create_user(username: str, password: str, role: str = "agent") -> dict:
    if role not in {"agent", "admin"}:
        raise ValueError("role must be agent or admin")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == username)):
            raise ValueError("username already exists")
        user = User(username=username, password_hash=hash_password(password), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"id": user.id, "username": user.username, "role": user.role, "is_active": user.is_active}


def list_users() -> list[dict]:
    with SessionLocal() as db:
        rows = list(db.scalars(select(User).order_by(User.username.asc())).all())
        return [{"id": u.id, "username": u.username, "role": u.role, "is_active": u.is_active} for u in rows]


def create_access_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user["username"],
        "role": user["role"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
    username = payload.get("sub")
    role = payload.get("role")
    if not username or not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    return {"username": username, "role": role}


def require_roles(*roles: str) -> Callable:
    def dependency(user: dict = Depends(current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return dependency
