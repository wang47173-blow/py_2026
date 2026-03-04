from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class IndexDocsRequest(BaseModel):
    data_source: str = Field(..., description="Local folder path containing .md/.txt files")
    tenant_id: UUID
    visibility_policy: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    idempotency_key: str | None = None


class IndexDocsResponse(BaseModel):
    job_id: UUID


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: str
    processed_docs: int
    processed_chunks: int
    error_message: str | None = None


class RagQueryRequest(BaseModel):
    question: str
    tenant_id: UUID
    user_id: UUID
    top_k: int = 5
    filters: dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    chunk_id: UUID
    source: str
    snippet: str


class RagQueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    used_chunks: int
    latency_ms: int


class ListCorporaResponse(BaseModel):
    docs: list[dict[str, Any]]
    stats: dict[str, int]
