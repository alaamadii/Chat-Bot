import hashlib
import re

from sqlalchemy import select

from db.database import SessionLocal
from knowledge.document_models import KnowledgeChunk, KnowledgeDocument
from knowledge.embeddings import get_embedding_provider


def chunk_text(text: str, max_words: int = 180, overlap_words: int = 30) -> list[str]:
    words = re.findall(r"\S+", text.strip())
    if not words:
        return []
    if max_words <= 0:
        raise ValueError("max_words must be positive")
    overlap_words = max(0, min(overlap_words, max_words - 1))
    step = max_words - overlap_words
    return [" ".join(words[start:start + max_words]) for start in range(0, len(words), step)]


class KnowledgeDocumentStore:
    def ingest(self, *, title: str, content: str, source: str, content_type: str, created_by: str) -> dict:
        clean_content = content.strip()
        if not clean_content:
            raise ValueError("Document content cannot be empty")

        checksum = hashlib.sha256(clean_content.encode("utf-8")).hexdigest()
        chunks = chunk_text(clean_content)
        provider = get_embedding_provider()

        with SessionLocal() as db:
            existing = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.checksum == checksum))
            if existing:
                return self._serialize_document(existing, db, duplicate=True)

            document = KnowledgeDocument(
                title=title.strip(),
                source=source.strip() or "manual",
                content_type=content_type.strip() or "text/plain",
                checksum=checksum,
                created_by=created_by,
            )
            db.add(document)
            db.flush()
            for index, chunk in enumerate(chunks):
                vector = provider.embed(chunk, task="document")
                db.add(KnowledgeChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk,
                    token_count=len(chunk.split()),
                    embedding_json=vector,
                    embedding_provider=provider.name,
                    embedding_model=provider.model,
                ))
            db.commit()
            db.refresh(document)
            return self._serialize_document(document, db, duplicate=False)

    def list_documents(self) -> list[dict]:
        with SessionLocal() as db:
            rows = list(db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.updated_at.desc())).all())
            return [self._serialize_document(row, db) for row in rows]

    def delete_document(self, document_id: str) -> bool:
        with SessionLocal() as db:
            row = db.get(KnowledgeDocument, document_id)
            if not row:
                return False
            db.delete(row)
            db.commit()
            return True

    def reindex_document(self, document_id: str) -> dict:
        provider = get_embedding_provider()
        with SessionLocal() as db:
            document = db.get(KnowledgeDocument, document_id)
            if not document:
                raise ValueError("Knowledge document not found")
            chunks = list(db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id)).all())
            for chunk in chunks:
                chunk.embedding_json = provider.embed(chunk.content, task="document")
                chunk.embedding_provider = provider.name
                chunk.embedding_model = provider.model
            db.commit()
            return {"document_id": document_id, "chunks_reindexed": len(chunks), "provider": provider.name, "model": provider.model}

    def retrieval_chunks(self) -> list[dict]:
        with SessionLocal() as db:
            stmt = (
                select(KnowledgeChunk, KnowledgeDocument)
                .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                .order_by(KnowledgeDocument.updated_at.desc(), KnowledgeChunk.chunk_index.asc())
            )
            return [{
                "text": chunk.content,
                "source": document.source,
                "title": document.title,
                "document_id": document.id,
                "chunk_id": chunk.id,
                "chunk_index": chunk.chunk_index,
                "embedding": chunk.embedding_json,
                "embedding_provider": chunk.embedding_provider,
                "embedding_model": chunk.embedding_model,
            } for chunk, document in db.execute(stmt).all()]

    @staticmethod
    def _serialize_document(document: KnowledgeDocument, db, duplicate: bool = False) -> dict:
        chunks = list(db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id).order_by(KnowledgeChunk.chunk_index.asc())).all())
        return {
            "id": document.id,
            "title": document.title,
            "source": document.source,
            "content_type": document.content_type,
            "checksum": document.checksum,
            "created_by": document.created_by,
            "chunk_count": len(chunks),
            "embedded_chunks": sum(1 for chunk in chunks if chunk.embedding_json),
            "duplicate": duplicate,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat(),
        }


document_store = KnowledgeDocumentStore()
