"""
Claims Processing Strands agent — core agentic logic.

Provides:
  create_agent(role)              → a configured Strands Agent instance
  run_processing_workflow(...)    → async workflow triggered by POST /process
  run_chat(...)                   → async SSE generator for POST /chat
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from strands import Agent  # noqa: E402
from strands.models import BedrockModel  # noqa: E402
from botocore.config import Config  # noqa: E402

from utils.logger import get_logger  # noqa: E402
from .prompts import SYSTEM_PROMPT, ROLE_INSTRUCTIONS, RULES_TEMPLATE  # noqa: E402
from .memory_manager import memory_manager  # noqa: E402
from .approval_hook import ApprovalHook  # noqa: E402
from .tools import (  # noqa: E402
    document_parser,
    read_case_status,
    read_case_analysis,
    read_decision_log,
    search_cases,
    write_analysis_result,
    write_decision_log,
)

logger = get_logger(__name__)

# ── configuration ─────────────────────────────────────────────────────────────
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
STORAGE_PATH = os.getenv("STORAGE_PATH", "./storage")

# Module-level singleton — one approval hook per process
approval_hook = ApprovalHook(STORAGE_PATH, domain="claims")

_ALL_TOOLS = [
    document_parser,
    read_case_status,
    read_case_analysis,
    read_decision_log,
    search_cases,
    write_analysis_result,
    write_decision_log,
]


# ── agent factory ─────────────────────────────────────────────────────────────

def build_system_prompt(role: str) -> str:
    """Build the full system prompt for the given role, injecting current rules."""
    rules = memory_manager.get_rules()
    logger.info("[AGENT] build_system_prompt  role=%s rules_count=%d", role, len(rules))
    rules_text = "\n".join(f"- {r}" for r in rules)
    role_instruction = ROLE_INSTRUCTIONS.get(role, ROLE_INSTRUCTIONS["user"])
    return (
        SYSTEM_PROMPT.strip()
        + "\n\n"
        + role_instruction.strip()
        + "\n\n"
        + RULES_TEMPLATE.format(rules=rules_text).strip()
    )


def create_agent(role: str = "user") -> Agent:
    """
    Create a new Strands Agent for the given role.
    A new agent is created per request so the system prompt always reflects
    the current rules.
    """
    logger.info("[AGENT] create_agent  role=%s model_id=%s region=%s", role, MODEL_ID, AWS_REGION)
    retry_config = Config(retries={"max_attempts": 5, "mode": "adaptive"})
    model = BedrockModel(
        model_id=MODEL_ID,
        region_name=AWS_REGION,
        boto_client_config=retry_config,
    )
    agent = Agent(
        model=model,
        system_prompt=build_system_prompt(role),
        tools=_ALL_TOOLS,
    )
    logger.info("[AGENT] create_agent  ready  role=%s tools=%s", role, [t.__name__ for t in _ALL_TOOLS])
    return agent


# ── status helpers ────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _update_status(case_id: str, status: str, extra: dict | None = None) -> None:
    status_path = Path(STORAGE_PATH) / "claims" / case_id / "status.json"
    try:
        with open(status_path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data["status"] = status
    data["updated_at"] = _now_iso()
    if extra:
        data.update(extra)
    _write_json(status_path, data)


# ── processing workflow ───────────────────────────────────────────────────────

async def run_processing_workflow(
    session_id: str, case_id: str, payload: dict
) -> None:
    """
    Full autonomous claims processing workflow.
    Called as an asyncio.Task from the service layer — runs in the background.
    """
    logger.info("[WORKFLOW] start  session_id=%s case_id=%s", session_id, case_id)
    try:
        _update_status(case_id, "PROCESSING")
        logger.info("[WORKFLOW] status→PROCESSING  session_id=%s case_id=%s", session_id, case_id)

        agent = create_agent(role="user")
        task_message = (
            f"Process this insurance claim autonomously.\n"
            f"case_id: {case_id}\n"
            f"session_id: {session_id}\n"
            f"Claim data: {json.dumps(payload, indent=2)}\n\n"
            f"Steps:\n"
            f"1. If there is an uploaded document, use document_parser to read it.\n"
            f"2. Analyse the claim against the current rules.\n"
            f"3. Use write_analysis_result to save your analysis.\n"
            f"4. Use write_decision_log to record your recommendation.\n"
            f"5. Respond with a one-sentence summary for the approval request."
        )

        # Run agent synchronously in a thread to avoid blocking the event loop
        logger.info("[WORKFLOW] invoking_agent  session_id=%s case_id=%s", session_id, case_id)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, agent, task_message)
        summary = str(result).strip()[:500]
        logger.info("[WORKFLOW] agent_done  session_id=%s case_id=%s summary_len=%d",
                    session_id, case_id, len(summary))

        # Pause for human approval
        logger.info("[WORKFLOW] requesting_approval  session_id=%s case_id=%s", session_id, case_id)
        decision = await approval_hook.request_approval(session_id, case_id, summary)
        logger.info("[WORKFLOW] approval_decision=%s  session_id=%s case_id=%s", decision, session_id, case_id)

        if decision == "approved":
            _update_status(case_id, "CLOSING")
            logger.info("[WORKFLOW] status→CLOSING  session_id=%s case_id=%s", session_id, case_id)
            _write_json(
                Path(STORAGE_PATH) / "claims" / case_id / "closure_summary.json",
                {"decision": "approved", "summary": summary, "closed_at": _now_iso()},
            )
            _update_status(case_id, "CLOSED")
            logger.info("[WORKFLOW] status→CLOSED  session_id=%s case_id=%s", session_id, case_id)
        elif decision == "rejected":
            _update_status(case_id, "REJECTED", {"rejection_reason": "Rejected by supervisor"})
            logger.info("[WORKFLOW] status→REJECTED  session_id=%s case_id=%s", session_id, case_id)
        # "expired" status already set by approval_hook

    except Exception:
        logger.exception("[WORKFLOW] failed  session_id=%s case_id=%s", session_id, case_id)
        try:
            _update_status(case_id, "ERROR")
            logger.info("[WORKFLOW] status→ERROR  session_id=%s case_id=%s", session_id, case_id)
        except Exception:
            pass


# ── SSE chat stream ───────────────────────────────────────────────────────────

async def run_chat(
    session_id: str,
    case_id: str,
    role: str,
    message: str,
) -> AsyncGenerator[str, None]:
    """
    Yield SSE-formatted strings for the FastAPI StreamingResponse.

    Event types emitted:
      {"type": "text-delta",  "content": "<token>"}
      {"type": "tool-status", "tool": "<name>", "status": "running"}
      {"type": "done"}
      {"type": "error",       "message": "<msg>"}
    """
    logger.info("[CHAT] run_chat  session_id=%s case_id=%s role=%s msg_len=%d",
                session_id, case_id, role, len(message))
    agent = create_agent(role)
    event_count = 0

    try:
        async for event in agent.stream_async(message):
            # TextStreamEvent yields {"data": "<token>", "delta": ...}
            text = event.get("data", "") if isinstance(event, dict) else ""
            if text:
                event_count += 1
                yield f"data: {json.dumps({'type': 'text-delta', 'content': text})}\n\n"
                continue

            # ToolUseStreamEvent yields {"current_tool_use": {"name": ...}, "delta": ...}
            tool_use = event.get("current_tool_use") if isinstance(event, dict) else None
            if tool_use and tool_use.get("name"):
                tool_name = tool_use["name"]
                logger.info("[CHAT] tool_invoked  session_id=%s tool=%s", session_id, tool_name)
                event_count += 1
                yield f"data: {json.dumps({'type': 'tool-status', 'tool': tool_name, 'status': 'running'})}\n\n"
    except Exception as exc:
        logger.error("[CHAT] agent_error  session_id=%s error=%s", session_id, exc)
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    logger.info("[CHAT] stream_complete  session_id=%s events_emitted=%d", session_id, event_count)
    yield f"data: {json.dumps({'type': 'done'})}\n\n"
