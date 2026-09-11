from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.security import create_user, list_users, require_roles
from services.audit import list_audit_events, record_audit

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=200)
    role: str = Field(default="agent")


@router.get("/users")
async def users(user: dict = Depends(require_roles("admin"))):
    return list_users()


@router.post("/users", status_code=201)
async def add_user(payload: CreateUserRequest, user: dict = Depends(require_roles("admin"))):
    try:
        created = create_user(payload.username, payload.password, payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_audit(user["username"], "user.created", "user", created["id"], {"username": created["username"], "role": created["role"]})
    return created


@router.get("/audit")
async def audit(limit: int = 100, user: dict = Depends(require_roles("admin"))):
    return list_audit_events(limit=min(max(limit, 1), 500))
