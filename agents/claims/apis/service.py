"""
Claims service layer — bridges FastAPI routes and the agentic layer.

Manages session lifecycle, file storage, and delegates processing/chat to
agent.py.  The in-memory _sessions dict maps session_id → case_id so that
routes can look up a case_id from a session_id without scanning disk on every
request.  On restart the dict is rebuilt lazily from status.json files.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from utils.logger import get_logger  # noqa: E402
from .schemas import ChatRequest  # noqa: E402

logger = get_logger(__name__)

STORAGE_PATH = os.getenv("STORAGE_PATH", "./storage")
DOMAIN = "claims"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _read_json(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


class ClaimsService:
    def __init__(self) -> None:
        # session_id → case_id  (in-memory; rebuilt from disk on miss)
        self._sessions: dict[str, str] = {}

    # ── internal helpers ─────────────────────────────────────────────────────

    def _case_dir(self, case_id: str) -> Path:
        return Path(STORAGE_PATH) / DOMAIN / case_id

    def _create_case_dirs(self, case_id: str) -> None:
        base = self._case_dir(case_id)
        for sub in ("input", "analysis", "decisions", "chat_history"):
            (base / sub).mkdir(parents=True, exist_ok=True)

    def _resolve_case_id(self, session_id: str) -> str | None:
        """Return case_id for session_id, scanning disk if not cached."""
        if session_id in self._sessions:
            case_id = self._sessions[session_id]
            logger.debug("[SERVICE] resolve_case_id  session_id=%s  cache_hit  case_id=%s", session_id, case_id)
            return case_id
        # Fallback: scan storage for a status.json that matches
        logger.debug("[SERVICE] resolve_case_id  session_id=%s  cache_miss  scanning_disk", session_id)
        root = Path(STORAGE_PATH) / DOMAIN
        if root.exists():
            for status_file in root.glob("*/status.json"):
                data = _read_json(status_file)
                if data and data.get("session_id") == session_id:
                    case_id = status_file.parent.name
                    self._sessions[session_id] = case_id
                    logger.debug("[SERVICE] resolve_case_id  session_id=%s  found_on_disk  case_id=%s", session_id, case_id)
                    return case_id
        logger.warning("[SERVICE] resolve_case_id  session_id=%s  not_found", session_id)
        return None

    def _has_active_session(self, case_id: str) -> bool:
        """Return True if case_id already has a non-terminal session."""
        status_path = self._case_dir(case_id) / "status.json"
        data = _read_json(status_path)
        if data is None:
            return False
        terminal = {"CLOSED", "REJECTED", "EXPIRED", "ERROR"}
        return data.get("status", "") not in terminal

    # ── session creation (POST /process) ─────────────────────────────────────

    def create_session(self, case_id: str, payload: dict, user_id: str) -> dict:
        logger.info("[SERVICE] create_session  case_id=%s user_id=%s", case_id, user_id)
        if self._has_active_session(case_id):
            logger.warning("[SERVICE] create_session  rejected  case_id=%s  reason=active_session_exists", case_id)
            raise ValueError(f"case_id '{case_id}' already has an active session.")

        session_id = str(uuid.uuid4())
        self._sessions[session_id] = case_id
        self._create_case_dirs(case_id)

        now = _now_iso()
        status = {
            "session_id": session_id,
            "case_id": case_id,
            "status": "INITIATED",
            "created_at": now,
            "updated_at": now,
            "user_id": user_id,
        }
        _write_json(self._case_dir(case_id) / "status.json", status)
        logger.info("[SERVICE] create_session  session_created  session_id=%s case_id=%s status=INITIATED",
                    session_id, case_id)

        # Import here to avoid circular import at module load time
        from .agent_bridge import spawn_workflow  # noqa: PLC0415
        spawn_workflow(session_id, case_id, payload)

        return {"session_id": session_id, "case_id": case_id, "status": "INITIATED"}

    # ── file upload helpers ───────────────────────────────────────────────────

    def prepare_upload_case(self, case_id: str | None) -> tuple[str, str]:
        """
        Return (case_id, session_id), creating a new session if needed.
        If case_id is None a new UUID is generated.
        """
        if case_id is None:
            case_id = str(uuid.uuid4())

        # Reuse existing session if present, else create a lightweight one
        status_path = self._case_dir(case_id) / "status.json"
        existing = _read_json(status_path)
        if existing and existing.get("session_id"):
            session_id = existing["session_id"]
            self._sessions[session_id] = case_id
            return case_id, session_id

        session_id = str(uuid.uuid4())
        self._sessions[session_id] = case_id
        self._create_case_dirs(case_id)
        now = _now_iso()
        _write_json(status_path, {
            "session_id": session_id,
            "case_id": case_id,
            "status": "INITIATED",
            "created_at": now,
            "updated_at": now,
        })
        return case_id, session_id

    # ── status (GET /status/{session_id}) ─────────────────────────────────────

    def get_status(self, session_id: str) -> dict | None:
        case_id = self._resolve_case_id(session_id)
        if case_id is None:
            return None
        return _read_json(self._case_dir(case_id) / "status.json")

    # ── chat stream (POST /chat/{session_id}) ─────────────────────────────────

    async def chat_stream(
        self, session_id: str, req: ChatRequest
    ) -> AsyncGenerator[str, None]:
        from agents.claims.agentic.agent import run_chat  # noqa: PLC0415

        case_id = self._resolve_case_id(session_id)
        if case_id is None:
            logger.error("[SERVICE] chat_stream  session_id=%s  case_id_not_found", session_id)
            yield 'data: {"type":"error","message":"Session not found"}\n\n'
            yield 'data: {"type":"done"}\n\n'
            return

        logger.info("[SERVICE] chat_stream  session_id=%s case_id=%s role=%s file_ref=%s msg_len=%d",
                    session_id, case_id, req.role, req.file_ref, len(req.message or ""))

        # Optionally prepend file_ref context to the message
        message = req.message
        if req.file_ref:
            logger.info("[SERVICE] chat_stream  prepending_file_ref=%s to message", req.file_ref)
            message = (
                f"[The user has just uploaded a document. file_ref: {req.file_ref}]\n\n"
                + message
            )

        async for chunk in run_chat(session_id, case_id, req.role, message):
            yield chunk

        logger.info("[SERVICE] chat_stream  complete  session_id=%s", session_id)

    # ── approval / rejection (POST /approve, /reject) ────────────────────────

    def record_decision(
        self, session_id: str, decision: str, notes_or_reason: str
    ) -> tuple[bool, str]:
        """
        Returns (success, error_message).
        Caller raises HTTPException on failure.
        """
        from agents.claims.agentic.agent import approval_hook  # noqa: PLC0415

        logger.info("[SERVICE] record_decision  session_id=%s decision=%s", session_id, decision)

        case_id = self._resolve_case_id(session_id)
        if case_id is None:
            logger.warning("[SERVICE] record_decision  session_id=%s  not_found", session_id)
            return False, "not_found"

        status_data = _read_json(self._case_dir(case_id) / "status.json")
        if status_data is None:
            logger.warning("[SERVICE] record_decision  session_id=%s case_id=%s  status_file_missing", session_id, case_id)
            return False, "not_found"
        current_status = status_data.get("status")
        if current_status != "PENDING_HUMAN_APPROVAL":
            logger.warning("[SERVICE] record_decision  session_id=%s  not_pending  current_status=%s",
                           session_id, current_status)
            return False, "not_pending"

        # Write the approval record
        record = {
            "session_id": session_id,
            "decision": decision,
            "notes": notes_or_reason,
            "decided_at": _now_iso(),
        }
        _write_json(
            self._case_dir(case_id) / "decisions" / "approval_record.json",
            record,
        )

        # Update status immediately so the frontend sees the transition
        new_status = "APPROVED" if decision == "approved" else "REJECTED"
        status_data["status"] = new_status
        status_data["updated_at"] = _now_iso()
        _write_json(self._case_dir(case_id) / "status.json", status_data)
        logger.info("[SERVICE] record_decision  written  session_id=%s case_id=%s new_status=%s",
                    session_id, case_id, new_status)

        # Signal the waiting workflow coroutine
        approval_hook.resume(session_id, decision)
        return True, ""

    # ── rules ─────────────────────────────────────────────────────────────────

    def get_rules(self) -> list[str]:
        from agents.claims.agentic.memory_manager import memory_manager  # noqa: PLC0415
        return memory_manager.get_rules()

    def set_rules(self, rules: list[str]) -> None:
        from agents.claims.agentic.memory_manager import memory_manager  # noqa: PLC0415
        memory_manager.set_rules(rules)

    # ── session listing (GET /sessions) ──────────────────────────────────────

    def list_sessions(
        self,
        status_filter: str | None = None,
        role_filter: str | None = None,
        user_id_filter: str | None = None,
    ) -> list[dict]:
        root = Path(STORAGE_PATH) / DOMAIN
        results = []

        if not root.exists():
            return results

        for status_file in root.glob("*/status.json"):
            data = _read_json(status_file)
            if data is None:
                continue
            if status_filter and data.get("status") != status_filter:
                continue
            if user_id_filter and data.get("user_id") != user_id_filter:
                continue
            # role_filter is informational (no role stored on session currently)
            results.append({
                "session_id": data.get("session_id", ""),
                "case_id": data.get("case_id", status_file.parent.name),
                "status": data.get("status", ""),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
            })

        results.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
        return results
