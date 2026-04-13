"""Intake sub-agent — FNOL, policy verification, case record creation."""
from __future__ import annotations

from strands import Agent, tool

from ..prompts import INTAKE_SYSTEM_PROMPT
from ..tools.csv_store import generate_case_id, create_case_record, query_policies, update_case_csv
from ..tools.audit_log import log_decision
from ..tools.memory import memory_save
from ..tools.utils import current_time


def _make_agent() -> Agent:
    from ..model import get_model
    return Agent(
        model=get_model(),
        system_prompt=INTAKE_SYSTEM_PROMPT,
        tools=[
            generate_case_id, create_case_record, query_policies,
            update_case_csv, log_decision, memory_save, current_time,
        ],
    )


@tool
def intake_agent(claim_input: str) -> str:
    """
    Call this FIRST for any new claim submission or FNOL.
    Handles: policy verification, claim type classification, triage priority assignment,
    case record creation in claims_metadata.csv.
    Input should include: claimant name, user_id, policy number, incident description,
    incident date, and any initial claim amount.
    Returns: case_id, claim_type, priority, policy status, and next recommended step.
    """
    return str(_make_agent()(claim_input))
