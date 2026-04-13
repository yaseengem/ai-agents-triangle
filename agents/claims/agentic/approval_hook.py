"""
Human-in-the-loop approval hook for the Claims Processing agent.

When the workflow reaches a decision point it calls request_approval(), which:
  1. Writes interrupt.json to the case directory
  2. Updates status.json → PENDING_HUMAN_APPROVAL
  3. Awaits an asyncio.Event

When a supervisor POSTs to /approve or /reject, the API service calls resume(),
which sets the event and stores the decision.  The awaiting coroutine then
continues with the decision value.

IMPORTANT: This uses module-level dicts of asyncio.Event objects which are
only valid within the same OS process.  Always run uvicorn with a single
worker (no --workers flag).
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from utils.logger import get_logger

logger = get_logger(__name__)

# ── module-level registries ──────────────────────────────────────────────────
_approval_events: dict[str, asyncio.Event] = {}
_decisions: dict[str, str] = {}

_TIMEOUT = int(os.getenv("APPROVAL_TIMEOUT_SECONDS", str(24 * 3600)))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _update_status(status_path: Path, status: str) -> None:
    try:
        with open(status_path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data["status"] = status
    data["updated_at"] = _now_iso()
    _write_json(status_path, data)


class ApprovalHook:
    def __init__(self, storage_path: str, domain: str = "claims") -> None:
        self.storage_path = storage_path
        self.domain = domain

    def _case_dir(self, case_id: str) -> Path:
        return Path(self.storage_path) / self.domain / case_id

    # ── called from within the Strands workflow coroutine ───────────────────

    async def request_approval(
        self, session_id: str, case_id: str, summary: str
    ) -> str:
        """
        Pause the workflow and wait for a human decision.
        Returns 'approved', 'rejected', or 'expired'.
        """
        logger.info("[APPROVAL] request_approval  session_id=%s case_id=%s timeout_seconds=%d",
                    session_id, case_id, _TIMEOUT)
        event = asyncio.Event()
        _approval_events[session_id] = event

        case_dir = self._case_dir(case_id)
        _write_json(
            case_dir / "interrupt.json",
            {
                "session_id": session_id,
                "case_id": case_id,
                "summary": summary,
                "requested_at": _now_iso(),
            },
        )
        _update_status(case_dir / "status.json", "PENDING_HUMAN_APPROVAL")
        logger.info("[APPROVAL] status=PENDING_HUMAN_APPROVAL  session_id=%s  awaiting_decision", session_id)

        try:
            await asyncio.wait_for(event.wait(), timeout=_TIMEOUT)
            decision = _decisions.pop(session_id, "rejected")
            logger.info("[APPROVAL] decision_received  session_id=%s decision=%s", session_id, decision)
        except asyncio.TimeoutError:
            logger.warning("[APPROVAL] timeout  session_id=%s  no_decision_within_%ds",
                           session_id, _TIMEOUT)
            _update_status(case_dir / "status.json", "EXPIRED")
            decision = "expired"
        finally:
            _approval_events.pop(session_id, None)

        return decision

    # ── called from the FastAPI route handler ────────────────────────────────

    def resume(self, session_id: str, decision: str) -> bool:
        """
        Signal the waiting workflow with a decision.
        Returns False if there is no workflow waiting for this session.
        """
        logger.info("[APPROVAL] resume  session_id=%s decision=%s", session_id, decision)
        event = _approval_events.get(session_id)
        if event is None:
            logger.warning("[APPROVAL] resume  no_waiting_workflow  session_id=%s", session_id)
            return False
        _decisions[session_id] = decision
        event.set()
        logger.info("[APPROVAL] resume  event_set  session_id=%s", session_id)
        return True

    def is_pending(self, session_id: str) -> bool:
        """Return True if a workflow is currently waiting for this session."""
        return session_id in _approval_events
