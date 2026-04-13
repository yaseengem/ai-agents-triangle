"""Pydantic v2 request/response schemas for the Claims API."""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ProcessRequest(BaseModel):
    """Body for ``POST /process`` — starts a new claims-processing workflow."""

    case_id: str
    payload: dict = Field(default_factory=dict)
    user_id: str = "anonymous"


class ChatRequest(BaseModel):
    """Body for ``POST /chat/{session_id}`` — sends a message to the agent."""

    message: str
    role: Literal["user", "support", "admin"] = "user"
    user_id: str = "anonymous"
    file_ref: Optional[str] = None  # set when the user just uploaded a file


class ApprovalRequest(BaseModel):
    """Optional body for ``POST /approve/{session_id}``."""

    notes: Optional[str] = None


class RejectionRequest(BaseModel):
    """Body for ``POST /reject/{session_id}`` — must include a rejection reason."""

    reason: str


class WorkflowStatus(BaseModel):
    """Full status record returned by ``GET /status/{session_id}``."""

    session_id: str
    case_id: str
    status: str
    created_at: str
    updated_at: str
    data: Optional[dict] = None


class RuleSet(BaseModel):
    """A list of processing rules used by ``GET /rules`` and ``POST /rules``."""

    rules: list[str]


class SessionSummary(BaseModel):
    """Lightweight session record returned by ``GET /sessions``."""

    session_id: str
    case_id: str
    status: str
    created_at: str
    updated_at: str


class FileUploadResponse(BaseModel):
    """Response from ``POST /upload`` — includes the ``file_ref`` for chat use."""

    file_ref: str     # "{case_id}/{filename}"
    case_id: str
    session_id: str


class ProcessResponse(BaseModel):
    """Response from ``POST /process`` — confirms session creation."""

    session_id: str
    case_id: str
    status: str
