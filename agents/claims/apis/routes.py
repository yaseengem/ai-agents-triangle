"""FastAPI route handlers for the Claims Processing API."""

from __future__ import annotations

import os
import uuid
from typing import Optional

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from .schemas import (
    ApprovalRequest,
    ChatRequest,
    FileUploadResponse,
    ProcessRequest,
    ProcessResponse,
    RejectionRequest,
    RuleSet,
    SessionSummary,
    WorkflowStatus,
)
from .service import ClaimsService

from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()
service = ClaimsService()

STORAGE_PATH = os.getenv("STORAGE_PATH", "./storage")
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
_ALLOWED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".docx"}


# ── health ────────────────────────────────────────────────────────────────────

@router.get("/ping")
def ping():
    """Health-check endpoint. Returns ``{"status": "ok"}`` when the service is up."""
    return {"status": "ok", "agent": "claims"}


# ── process ───────────────────────────────────────────────────────────────────

@router.post("/process", response_model=ProcessResponse)
async def process(req: ProcessRequest):
    """Start an autonomous claims-processing workflow for *case_id*.

    Creates a new session, persists an INITIATED status file, and spawns a
    background asyncio task that runs the full agent workflow.  Returns the
    new ``session_id`` immediately so the client can poll ``GET /status``.

    Raises 400 if the case already has an active (non-terminal) session.
    """
    logger.info("[ROUTE] POST /process  case_id=%s user_id=%s payload_keys=%s",
                req.case_id, req.user_id, list(req.payload.keys()) if req.payload else [])
    try:
        result = service.create_session(req.case_id, req.payload, req.user_id)
    except ValueError as exc:
        logger.warning("[ROUTE] POST /process rejected  case_id=%s reason=%s", req.case_id, exc)
        raise HTTPException(status_code=400, detail=str(exc))
    logger.info("[ROUTE] POST /process success  session_id=%s case_id=%s status=%s",
                result.get("session_id"), result.get("case_id"), result.get("status"))
    return result


# ── upload ────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=FileUploadResponse)
async def upload(
    file: UploadFile = File(...),
    user_id: str = Form("anonymous"),
    case_id: Optional[str] = Form(None),
):
    """Accept a claim document upload and save it to the case's input directory.

    Accepted formats: pdf, png, jpg, jpeg, docx (max 20 MB).  If *case_id* is
    omitted a new UUID is generated.  The returned ``file_ref`` value should be
    passed to ``POST /chat`` so the agent can parse the document via the
    ``document_parser`` tool.

    Raises 415 for unsupported file types and 413 if the file exceeds 20 MB.
    """
    logger.info("[ROUTE] POST /upload  filename=%s user_id=%s case_id=%s",
                file.filename, user_id, case_id)
    # Validate extension
    suffix = ""
    if file.filename:
        suffix = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if suffix not in _ALLOWED_SUFFIXES:
        logger.warning("[ROUTE] POST /upload rejected  filename=%s unsupported_suffix=%s", file.filename, suffix)
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Accepted: pdf, png, jpg, jpeg, docx.",
        )

    # Read and size-check
    contents = await file.read()
    if len(contents) > _MAX_UPLOAD_BYTES:
        logger.warning("[ROUTE] POST /upload rejected  filename=%s size_bytes=%d exceeds_limit=True",
                       file.filename, len(contents))
        raise HTTPException(status_code=413, detail="File exceeds 20 MB limit.")

    resolved_case_id, session_id = service.prepare_upload_case(case_id)

    # Save to storage
    input_dir = Path(STORAGE_PATH) / "claims" / resolved_case_id / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    safe_name = file.filename or f"upload_{uuid.uuid4().hex}{suffix}"
    dest = input_dir / safe_name
    with open(dest, "wb") as f_out:
        f_out.write(contents)

    file_ref = f"{resolved_case_id}/{safe_name}"
    logger.info("[ROUTE] POST /upload success  file_ref=%s case_id=%s session_id=%s size_bytes=%d",
                file_ref, resolved_case_id, session_id, len(contents))
    return FileUploadResponse(file_ref=file_ref, case_id=resolved_case_id, session_id=session_id)


# ── chat (SSE) ────────────────────────────────────────────────────────────────

@router.post("/chat/{session_id}")
async def chat(session_id: str, req: ChatRequest):
    """Open a streaming SSE chat session with the agent for an existing session.

    Streams server-sent events of the form ``data: <json>\\n\\n``.  Event types:
    ``text-delta`` (incremental token), ``tool-status`` (tool invocation notice),
    ``done`` (stream finished), ``error`` (agent error).

    Raises 404 if *session_id* is not found.
    """
    logger.info("[ROUTE] POST /chat/%s  role=%s user_id=%s file_ref=%s msg_len=%d",
                session_id, req.role, req.user_id, req.file_ref, len(req.message or ""))
    status = service.get_status(session_id)
    if status is None:
        logger.warning("[ROUTE] POST /chat/%s  session_not_found", session_id)
        raise HTTPException(status_code=404, detail="Session not found.")

    logger.info("[ROUTE] POST /chat/%s  session_status=%s  opening_sse_stream",
                session_id, status.get("status"))
    return StreamingResponse(
        service.chat_stream(session_id, req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── status ────────────────────────────────────────────────────────────────────

@router.get("/status/{session_id}", response_model=WorkflowStatus)
def get_status(session_id: str):
    """Return the current workflow status for *session_id*.

    Raises 404 if the session is not found.
    """
    data = service.get_status(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return data


# ── approve / reject ──────────────────────────────────────────────────────────

@router.post("/approve/{session_id}")
def approve(session_id: str, req: ApprovalRequest = ApprovalRequest()):
    """Approve the claim recommendation for a session that is PENDING_HUMAN_APPROVAL.

    Signals the waiting workflow coroutine, which will then close the case.
    Raises 404 if the session is not found, 400 if it is not pending approval.
    """
    logger.info("[ROUTE] POST /approve/%s  notes=%s", session_id, req.notes)
    ok, err = service.record_decision(session_id, "approved", req.notes or "")
    if not ok:
        logger.warning("[ROUTE] POST /approve/%s  failed  reason=%s", session_id, err)
        if err == "not_found":
            raise HTTPException(status_code=404, detail="Session not found.")
        raise HTTPException(status_code=400, detail="Session is not pending approval.")
    logger.info("[ROUTE] POST /approve/%s  success", session_id)
    return {"status": "ok", "decision": "approved"}


@router.post("/reject/{session_id}")
def reject(session_id: str, req: RejectionRequest):
    """Reject the claim recommendation for a session that is PENDING_HUMAN_APPROVAL.

    Signals the waiting workflow coroutine, which will mark the case REJECTED.
    Raises 404 if the session is not found, 400 if it is not pending approval.
    """
    logger.info("[ROUTE] POST /reject/%s  reason=%s", session_id, req.reason)
    ok, err = service.record_decision(session_id, "rejected", req.reason)
    if not ok:
        logger.warning("[ROUTE] POST /reject/%s  failed  reason=%s", session_id, err)
        if err == "not_found":
            raise HTTPException(status_code=404, detail="Session not found.")
        raise HTTPException(status_code=400, detail="Session is not pending approval.")
    logger.info("[ROUTE] POST /reject/%s  success", session_id)
    return {"status": "ok", "decision": "rejected"}


# ── rules ─────────────────────────────────────────────────────────────────────

@router.get("/rules", response_model=RuleSet)
def get_rules():
    """Return the agent's current operating rules."""
    return RuleSet(rules=service.get_rules())


@router.post("/rules")
def post_rules(ruleset: RuleSet):
    """Replace the agent's operating rules with the provided list."""
    service.set_rules(ruleset.rules)
    return {"status": "ok"}


# ── sessions ──────────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=list[SessionSummary])
def list_sessions(
    status: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
):
    """List all known sessions, optionally filtered by *status* or *user_id*.

    Results are sorted by ``updated_at`` descending (most recent first).
    """
    return service.list_sessions(
        status_filter=status,
        role_filter=role,
        user_id_filter=user_id,
    )
