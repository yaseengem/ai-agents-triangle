"""
Calvin — master claims processing agent for ABC Insurance.

Provides:
  create_agent(role, user_id, session_id)  → configured Strands Agent
  run_chat(session_id, case_id, role, user_id, message)  → async SSE generator
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import AsyncGenerator

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from strands import Agent  # noqa: E402

from utils.logger import get_logger  # noqa: E402
from .model import get_model  # noqa: E402
from .prompts import CALVIN_SYSTEM_PROMPT  # noqa: E402

# Sub-agents (Agents-as-Tools)
from .sub_agents.intake import intake_agent  # noqa: E402
from .sub_agents.extraction import extraction_agent  # noqa: E402
from .sub_agents.validation import validation_agent  # noqa: E402
from .sub_agents.medical_review import medical_review_agent  # noqa: E402
from .sub_agents.fraud import fraud_agent  # noqa: E402
from .sub_agents.adjudication import adjudication_agent  # noqa: E402
from .sub_agents.decision_qa import decision_qa_agent  # noqa: E402
from .sub_agents.communication import communication_agent  # noqa: E402

# Direct tools on master
from .tools.csv_store import (  # noqa: E402
    query_policies, query_claims_history, query_fraud_patterns,
    query_claims_metadata, approve_case,
)
from .tools.audit_log import read_audit_log, log_decision  # noqa: E402
from .tools.memory import memory_save, memory_load  # noqa: E402

logger = get_logger(__name__)

_ALL_TOOLS = [
    # Pipeline sub-agents
    intake_agent, extraction_agent, validation_agent, medical_review_agent,
    fraud_agent, adjudication_agent, decision_qa_agent, communication_agent,
    # Direct query tools
    query_policies, query_claims_history, query_fraud_patterns, query_claims_metadata,
    # Approval
    approve_case,
    # Audit
    read_audit_log, log_decision,
    # Session memory
    memory_save, memory_load,
]


# ── Agent factory ──────────────────────────────────────────────────────────────

def create_agent(role: str = "end_user", user_id: str = "", session_id: str = "") -> Agent:
    """
    Create a Calvin agent instance for the given role.
    A new instance is created per request so context is always fresh.

    Args:
        role:       end_user | support_exec | admin
        user_id:    The caller's user ID (required for end_user role).
        session_id: The current session identifier for memory continuity.
    """
    logger.info("[AGENT] create_agent  role=%s user_id=%s session_id=%s", role, user_id, session_id)

    # Inject role + identity context into the system prompt
    context_block = (
        f"\n\n=== CURRENT SESSION CONTEXT ===\n"
        f"Role:       {role}\n"
        f"User ID:    {user_id or 'unknown'}\n"
        f"Session ID: {session_id or 'unknown'}\n"
        f"=================================\n"
    )
    system_prompt = CALVIN_SYSTEM_PROMPT + context_block

    agent = Agent(
        model=get_model(),
        system_prompt=system_prompt,
        tools=_ALL_TOOLS,
    )
    logger.info("[AGENT] create_agent  ready  role=%s tools=%d", role, len(_ALL_TOOLS))
    return agent


# ── SSE chat stream ────────────────────────────────────────────────────────────

async def run_chat(
    session_id: str,
    role: str,
    user_id: str,
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
    logger.info(
        "[CHAT] run_chat  session_id=%s role=%s user_id=%s msg_len=%d",
        session_id, role, user_id, len(message),
    )
    agent = create_agent(role=role, user_id=user_id, session_id=session_id)
    event_count = 0

    try:
        async for event in agent.stream_async(message):
            if isinstance(event, dict):
                text = event.get("data", "")
                if text:
                    event_count += 1
                    yield f"data: {json.dumps({'type': 'text-delta', 'content': text})}\n\n"
                    continue

                tool_use = event.get("current_tool_use")
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
