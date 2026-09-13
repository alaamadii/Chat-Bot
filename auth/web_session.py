import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt

ALGORITHM = "HS256"
WEB_SESSION_MINUTES = int(os.getenv("WEB_SESSION_MINUTES", "1440"))


def _secret() -> str:
    return os.getenv("WEB_SESSION_SECRET") or os.getenv("JWT_SECRET_KEY", "change-me-in-production")


def create_web_session(user_id: str, conversation_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "conversation_id": conversation_id,
        "type": "web_session",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=WEB_SESSION_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def verify_web_session(token: str, *, user_id: str | None = None, conversation_id: str | None = None) -> dict:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired web session") from exc

    if payload.get("type") != "web_session" or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid web session")
    if user_id is not None and payload.get("sub") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Web session user mismatch")
    if conversation_id is not None and payload.get("conversation_id") != conversation_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Web session conversation mismatch")
    return payload


def validate_production_secrets() -> None:
    if os.getenv("ENVIRONMENT", "development").lower() != "production":
        return

    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    web_secret = os.getenv("WEB_SESSION_SECRET", "")
    if not jwt_secret or jwt_secret == "change-me-in-production" or len(jwt_secret) < 32:
        raise RuntimeError("Production requires JWT_SECRET_KEY with at least 32 characters")
    if not web_secret or len(web_secret) < 32:
        raise RuntimeError("Production requires WEB_SESSION_SECRET with at least 32 characters")
