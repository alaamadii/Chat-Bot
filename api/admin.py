from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.security import create_user, list_users, require_roles
from knowledge.document_store import document_store
from knowledge.retriever import retriever
from services.audit import list_audit_events, record_audit

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=200)
    role: str = Field(default="agent")


class IngestKnowledgeDocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=200000)
    source: str = Field(default="manual", max_length=500)
    content_type: str = Field(default="text/plain", max_length=50)


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=4, ge=1, le=20)


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


@router.get("/knowledge/documents")
async def list_knowledge_documents(user: dict = Depends(require_roles("admin"))):
    return document_store.list_documents()


@router.post("/knowledge/documents", status_code=201)
async def ingest_knowledge_document(payload: IngestKnowledgeDocumentRequest, user: dict = Depends(require_roles("admin"))):
    try:
        created = document_store.ingest(
            title=payload.title,
            content=payload.content,
            source=payload.source,
            content_type=payload.content_type,
            created_by=user["username"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record_audit(user["username"], "knowledge.document_ingested", "knowledge_document", created["id"], {"title": created["title"], "source": created["source"], "chunk_count": created["chunk_count"]})
    return created


@router.post("/knowledge/documents/{document_id}/reindex")
async def reindex_knowledge_document(document_id: str, user: dict = Depends(require_roles("admin"))):
    try:
        result = document_store.reindex_document(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit(user["username"], "knowledge.document_reindexed", "knowledge_document", document_id, result)
    return result


@router.delete("/knowledge/documents/{document_id}", status_code=204)
async def delete_knowledge_document(document_id: str, user: dict = Depends(require_roles("admin"))):
    if not document_store.delete_document(document_id):
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    record_audit(user["username"], "knowledge.document_deleted", "knowledge_document", document_id)
    return None


@router.post("/knowledge/search")
async def search_knowledge(payload: KnowledgeSearchRequest, user: dict = Depends(require_roles("admin"))):
    return retriever.retrieve_with_sources(payload.query, top_k=payload.top_k)
