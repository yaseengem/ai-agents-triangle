"""Pydantic v2 request/response schemas for the Claims API."""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ProcessRequest(BaseModel):
    case_id: str
    payload: dict = Field(default_factory=dict)
    user_id: str = "anonymous"


class ChatRequest(BaseModel):
    message: str
    role: Literal["user", "support", "admin"] = "user"
    user_id: str = "anonymous"
    file_ref: Optional[str] = None  # set when the user just uploaded a file


class ApprovalRequest(BaseModel):
    notes: Optional[str] = None


class RejectionRequest(BaseModel):
    reason: str


class WorkflowStatus(BaseModel):
    session_id: str
    case_id: str
    status: str
    created_at: str
    updated_at: str
    data: Optional[dict] = None


class RuleSet(BaseModel):
    rules: list[str]


class SessionSummary(BaseModel):
    session_id: str
    case_id: str
    status: str
    created_at: str
    updated_at: str


class FileUploadResponse(BaseModel):
    file_ref: str     # "{case_id}/{filename}"
    case_id: str
    session_id: str


class ProcessResponse(BaseModel):
    session_id: str
    case_id: str
    status: str
