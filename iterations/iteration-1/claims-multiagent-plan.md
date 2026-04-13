# Claims Processing Multi-Agent System — Strands SDK Plan

## Context

A multi-agent claims processing system using the AWS Strands **Agents-as-Tools** pattern. The agent, named **Calvin**, serves ABC Insurance and handles three personas — end users (claimants), support executives, and admins — all through a **chatbot interface**. Calvin delegates all specialized work to 8 sub-agents. Every decision is logged to a per-case audit text file. All case metadata is stored and queried via four dedicated, record-type-specific CSV query tools (no external APIs, no vector search). Document extraction uses PyPDF for now and is designed to be **extensible** (Bedrock Data Automation for OCR can be plugged in later). The `send_email` tool writes to a `.md` file for demo; real SMTP integration comes later. A **human-in-the-loop approval step** is required before any communication is sent — the reviewer can chat with Calvin, ask questions, and approve or override the decision.

---

## Strands Core Pattern

```python
from strands import Agent, tool

@tool
def intake_agent(claim_input: str) -> str:
    """Call this FIRST for any new claim submission. Handles FNOL,
    verifies policy, assigns claim type and priority, creates case record."""
    agent = Agent(system_prompt=INTAKE_SYSTEM_PROMPT, tools=[...])
    return str(agent(claim_input))

master = Agent(
    system_prompt=MASTER_SYSTEM_PROMPT,   # Calvin, ABC Insurance
    tools=[
        # Sub-agents (pipeline order)
        intake_agent, extraction_agent, validation_agent, medical_review_agent,
        fraud_agent, adjudication_agent, decision_qa_agent, communication_agent,
        # Direct tools on master (query, approval, memory)
        query_policies, query_claims_history, query_fraud_patterns, query_claims_metadata,
        read_audit_log, approve_case,
        memory_save, memory_load
    ]
)
```

The **docstring** of each `@tool` is what Calvin reads to decide when to call it — docstrings must be precise and action-oriented.

---

## Three Personas — One Chatbot (Calvin)

All three personas interact with Calvin through the **same chatbot interface**. Calvin's behaviour adapts based on the role injected by the API layer.

| Persona | Chatbot experience |
|---|---|
| **End User (Claimant)** | Submit claims, ask status of their own cases only. `query_claims_metadata` auto-filters to their `user_id` at the data layer. |
| **Support Executive** | Full conversational access — ask about any case, policy, audit log, aggregate stats. Can chat with Calvin about a case, ask why a decision was made, then approve or override. |
| **Admin** | Everything support_exec can do + full unfiltered access to all cases and data. |

---

## Full Agent Architecture

```
                    ┌──────────────────────────────────────────────────┐
                    │         CALVIN — MASTER CLAIMS AGENT             │
                    │     ABC Insurance Claims Processing Assistant    │
                    │  (Single chatbot entry point for all personas)   │
                    │                                                  │
                    │  Personas: end_user | support_exec | admin       │
                    │  Memory: per-session conversation context        │
                    │  Direct tools: query_policies,                  │
                    │    query_claims_history, query_fraud_patterns,   │
                    │    query_claims_metadata, read_audit_log,        │
                    │    approve_case, memory_save, memory_load        │
                    └────────────────────┬─────────────────────────────┘
                                         │ delegates via @tool calls
  ┌────────┬────────┬──────────┬─────────┼──────────┬──────────┬──────────┐
  │        │        │          │         │          │          │          │
  ▼        ▼        ▼          ▼         ▼          ▼          ▼          ▼
Intake  Extract  Validation  Medical  Fraud     Adjudication  QA     Communication
Agent   Agent    Agent       Review   Agent     Agent         Agent  Agent
                             Agent
                                                              │
                                              ┌──────────────┘
                                              │ PASS → pending_approval
                                              │ FIX_REQUIRED → re-run flagged agent (max 2x)
                                              │ ESCALATE → escalated_to_human (with QA notes)
                                              ▼
                                    Human Review via Calvin chatbot
                                    (support_exec or admin chats with Calvin,
                                     asks questions, then approves / overrides)
                                              │ approved or overridden
                                              ▼
                                    communication_agent → write email .md file
```

---

## Claim Processing Pipeline (ordered)

```
New Claim Submitted
        │
        ▼
1. intake_agent ──────────────────────► query_policies(filters={"policy_no": "..."})
        │                                create_case_record in claims_metadata.csv
        │
        ▼ (if PDFs or .txt files submitted)
2. extraction_agent ──────────────────► extract_pdf (PyPDF) or extract_text_file (.txt)
        │                                classify_document → label each doc type
        │                                update_case_csv: documents_submitted, extracted_summary
        │
        ▼
3. validation_agent ──────────────────► query_policies — check active, coverage, dates
        │                                query_claims_history — prior claims count
        │                                EARLY EXIT: if lapsed/excluded → skip to denied
        │                                update_case_csv: validation_status, coverage_limit, deductible
        │
        ▼ (health claim only, AND physician_report + medical_bill both present)
4. medical_review_agent ──────────────► extract_pdf(physician_report) → extract diagnosis
        │                                extract_pdf(medical_bills) → extract itemized charges
        │                                cross-check ailment vs billed items vs amounts
        │                                update_case_csv: medical_review_status, discrepancy_details
        │
        ▼
5. fraud_agent ───────────────────────► query_fraud_patterns — known risk records
        │                                query_claims_history — frequency/amount patterns
        │                                update_case_csv: fraud_score, fraud_recommendation
        │
        ▼
6. adjudication_agent ────────────────► query_policies — coverage limit + deductible
        │                                query_claims_metadata — full case context
        │                                calculate settlement, render decision
        │                                update_case_csv: adjudication_decision, settlement_amount
        │
        ▼
7. decision_qa_agent ─────────────────► query_claims_metadata — full case row
        │                                read_audit_log — all prior agent entries
        │                                validate consistency across all stages
        │
        ├──► PASS → status = pending_approval
        │
        ├──► FIX_REQUIRED → master re-invokes named agent → QA runs again (attempt 2)
        │         └──► PASS → status = pending_approval
        │         └──► FIX_REQUIRED again → ESCALATE
        │
        └──► ESCALATE → status = escalated_to_human (with QA notes in CSV + audit log)
        │
        ▼
Human reviews via Calvin chatbot:
  - Asks questions: "why was this approved?", "show me the fraud details"
  - Calvin answers using query_claims_metadata, read_audit_log, query_policies
  - Reviewer decides: approve / reject / override (change decision or amount)
  - Calls: approve_case(case_id, approver_id, decision, notes,
                        override_decision=None, override_amount=None)
        │ approved or overridden
        ▼
8. communication_agent ───────────────► write email content to data/emails/{case_id}_email.md
                                         update_case_csv: communication_status, email_file_path
```

---

## Sub-Agent Definitions

### 1. Intake Agent
**Trigger:** Any new claim submission or FNOL  
**Tools:** `generate_case_id`, `create_case_record`, `query_policies`, `current_time`, `log_decision`, `memory_save`  
**What it does:**
- Collects claimant identity, policy number, incident description
- Calls `query_policies(filters={"policy_no": "..."})` to verify policy exists
- Classifies claim type: `auto | property | health | liability`
- Assigns triage priority: `low | medium | high | critical`
- Creates the case row in `claims_metadata.csv` via `create_case_record`

**CSV fields it writes:** `case_id`, `created_at`, `user_id`, `policy_no`, `claim_type`, `priority`, `status=intake_complete`  
**Log entry:** FNOL received, policy verified, claim type and priority set with reasoning

---

### 2. Document Extraction Agent
**Trigger:** PDF or .txt documents submitted with the claim  
**Tools:** `extract_pdf`, `extract_text_file`, `classify_document`, `update_case_csv`, `log_decision`  
**What it does:**
- For `.pdf` files: calls `extract_pdf` (PyPDF — text extraction only; extensible to Bedrock Data Automation for OCR later)
- For `.txt` files: calls `extract_text_file` to read raw text content
- Calls `classify_document` on extracted text to label each doc: `physician_report | medical_bill | police_report | repair_estimate | invoice | other`
- LLM reasons over extracted text to pull key fields (amounts, dates, parties, diagnoses)

**Extensibility note:** `extract_pdf` is implemented behind a `DocumentExtractor` abstraction with a strategy pattern. Swapping in Bedrock Data Automation for scanned/image PDFs requires only adding a new strategy class — no agent or tool signature changes.

**CSV fields it writes:** `documents_submitted`, `extraction_status`, `extracted_summary`  
**Log entry:** Each document processed, type classified, key fields found

---

### 3. Policy Validation Agent  *(early-exit gate)*
**Trigger:** After extraction (or directly after intake if no documents)  
**Tools:** `query_policies`, `query_claims_history`, `current_time`, `update_case_csv`, `log_decision`  
**What it does:**
- `query_policies(filters={"policy_no": "..."}, columns=["status","start_date","end_date","covered_claim_types","exclusions","coverage_limit","deductible"])` → full policy row
- Verifies: policy `status=active`, incident date within `start_date`–`end_date`, claim type is in `covered_claim_types`, not in `exclusions`
- `query_claims_history(filters={"policy_no": "..."}, columns=["claim_id","claim_date","claimed_amount"])` → prior claims count
- **Early-exit gate:** if policy is lapsed or claim type is excluded, the flow stops here — adjudication is called directly with `denied` context, skipping medical review and fraud

**CSV fields it writes:** `validation_status`, `coverage_limit`, `deductible`, `validation_notes`  
**Log entry:** Policy status, each check result, coverage limit and deductible confirmed, or denial reason if early exit

---

### 4. Medical Review Agent  *(health claims only)*
**Trigger:** After validation PASS — only when `claim_type=health` AND both `physician_report` AND `medical_bill` are in `documents_submitted`  
**Tools:** `extract_pdf`, `update_case_csv`, `log_decision`  
**What it does:**
- Re-reads physician report PDF → extracts: diagnosis/ailment, ICD codes, recommended treatments, physician details
- Re-reads medical bills PDF → extracts: itemized line items, procedure codes, billed amounts per item, billing provider
- **Cross-checks:**
  - Are billed procedures consistent with the diagnosis?
  - Is total billed amount reasonable for the ailment and number of sessions?
  - Are there line items on the bill with no corresponding mention in the physician report?
- Sets `recommended_coverage_amount` based on only the consistent, justified items

**CSV fields it writes:** `medical_review_status` (consistent/discrepant/partial), `diagnosis`, `billed_amount`, `recommended_coverage_amount`, `discrepancy_details`  
**Log entry:** Diagnosis extracted, all billed items listed, cross-check verdict, specific discrepant line items flagged with reason

---

### 5. Fraud Detection Agent
**Trigger:** After validation (and medical review if applicable), always before adjudication  
**Tools:** `query_fraud_patterns`, `query_claims_history`, `query_claims_metadata`, `update_case_csv`, `log_decision`  
**What it does:**
- `query_fraud_patterns(filters={"policy_no": "..."})` — known fraud records for this policy
- `query_fraud_patterns(filters={"user_id": "..."})` — check user_id across all policies
- `query_claims_history(filters={"policy_no": "...", "claim_date__gte": "90-days-ago"})` — frequency check
- Checks: multiple claims in short window, claimed amount >> historical average, duplicate claim type within 90 days, policy in fraud DB
- Assigns fraud risk score: `low | medium | high`
- Recommendation: `proceed | flag-for-review | deny`

**CSV fields it writes:** `fraud_score`, `fraud_recommendation`, `fraud_flags`  
**Log entry:** Each check performed, patterns matched, risk score with specific reasoning

---

### 6. Adjudication Agent
**Trigger:** After fraud check  
**Tools:** `query_claims_metadata`, `query_policies`, `update_case_csv`, `log_decision`, `current_time`  
**What it does:**
- `query_claims_metadata(filters={"case_id": "..."})` → full case row (all prior agent outputs)
- `query_policies(filters={"policy_no": "..."}, columns=["coverage_limit","deductible"])` → confirm settlement parameters
- Calculates eligible settlement: `min(claimed_amount, coverage_limit) - deductible`
- For health claims with discrepancy: uses `recommended_coverage_amount` instead of billed amount
- Renders decision: `approved | partial | denied | escalate`
- Auto-escalates if: `fraud_score=high` OR claim amount > 80% of coverage limit OR `medical_review_status=discrepant`
- Does NOT set `pending_approval` — that is set by the QA agent

**CSV fields it writes:** `adjudication_decision`, `settlement_amount`, `decision_reason`, `status=adjudicated`  
**Log entry:** Full decision rationale, settlement calculation breakdown, escalation reason if applicable

---

### 7. Decision QA Agent  *(self-correction loop)*
**Trigger:** Always runs after adjudication, before any human sees the case  
**Tools:** `query_claims_metadata`, `read_audit_log`, `update_case_csv`, `log_decision`  
**What it does:**
- `query_claims_metadata(filters={"case_id": "..."})` → full case row with all agent outputs
- `read_audit_log(case_id)` → full audit trail
- Validates:
  - All required pipeline stages completed and logged
  - Decision consistent with fraud score (high fraud → cannot be auto-approved)
  - Decision consistent with validation result (lapsed policy → must be denied)
  - For health claims: settlement uses `recommended_coverage_amount` if discrepancy found
  - No contradictions between agent outputs
  - Settlement arithmetic correct
- Verdict:
  - `PASS` → sets `status=pending_approval`
  - `FIX_REQUIRED` → returns specific fix instruction to master → master re-invokes named agent → QA runs again
  - After 2nd `FIX_REQUIRED` OR unresolvable contradiction → `ESCALATE` → `status=escalated_to_human` with detailed QA comments

**CSV fields it writes:** `qa_verdict`, `qa_comments`, `qa_attempts`, `status` (→ `pending_approval` or `escalated_to_human`)  
**Log entry:** Each check performed, verdict with reasoning, fix instructions or escalation comments

---

### 8. Communication Agent
**Trigger:** Only after `approve_case` is called by support_exec or admin  
**Tools:** `send_email`, `query_claims_metadata`, `query_policies`, `update_case_csv`, `log_decision`, `current_time`  
**What it does:**
- `query_claims_metadata(filters={"case_id": "..."})` → get decision, settlement amount, policy number
- `query_policies(filters={"policy_no": "..."}, columns=["email","holder_name"])` → get claimant email address
- Composes email content appropriate to decision: approval + amount, partial + explanation, denial + reason
- Calls `send_email` → writes email to `data/emails/{case_id}_email.md` (no real SMTP for demo)
- Stores file path in case metadata

**CSV fields it writes:** `communication_status=sent`, `email_file_path`, `last_communication_at`, `updated_at`  
**Log entry:** Email file written to path, decision communicated, ready for future SMTP integration

---

## Human-in-the-Loop: Chat, Review, and Override

Cases land at `status=pending_approval` (QA passed) or `status=escalated_to_human` (QA flagged issues). The communication agent is blocked until a support_exec or admin acts via the Calvin chatbot.

The reviewer is not limited to approve/reject — they can **have a full conversation with Calvin** about the case before deciding, and can **override** the adjudication decision (change decision type or settlement amount).

**Full review conversation example:**
```
Support exec: "show me cases pending my review"
Calvin: [calls query_claims_metadata(status__in=[pending_approval, escalated_to_human])]
         → formatted table of 3 cases

Support exec: "tell me about CLM-20260414-0042"
Calvin: [calls query_claims_metadata + read_audit_log]
         → full case summary + complete audit trail

Support exec: "why was this approved despite the medical discrepancy?"
Calvin: [reads qa_comments and audit log entries for ADJUDICATION_AGENT and MEDICAL_REVIEW_AGENT]
         → "The adjudication agent used billed_amount instead of recommended_coverage_amount.
            The QA agent flagged this and re-ran adjudication. On second attempt the correct
            amount was used. The discrepancy was partial — 2 of 8 line items were unrelated."

Support exec: "the settlement seems high — override to $6,000 and approve"
Calvin: [calls approve_case(case_id="CLM-20260414-0042", approver_id="SUPP-007",
                             decision="overridden", notes="Reviewer reduced settlement",
                             override_decision="approved", override_amount=6000.00)]
         → CSV updated, communication_agent invoked, email file written

Support exec: "reject case CLM-20260414-0099 — duplicate claim"
Calvin: [calls approve_case(..., decision="rejected", notes="Duplicate of CLM-20260414-0080")]
         → CSV updated, status=rejected, no email
```

**Updated `approve_case` tool signature:**
```python
@tool
def approve_case(case_id: str, approver_id: str, decision: str, notes: str,
                 override_decision: str = None, override_amount: float = None) -> str:
    """
    Record human approval, rejection, or override of a claim decision.
    decision: 'approved' | 'rejected' | 'overridden'
    override_decision: (if overriding) new decision type — 'approved' | 'partial' | 'denied'
    override_amount: (if overriding) new settlement amount in dollars
    Only callable by support_exec or admin roles. On approval/override, triggers communication_agent.
    """
```

---

## Shared Primitive Tools (23 tools)

### CSV Data Tools  (tools/csv_store.py)

One dedicated query tool per record type. Each supports DB-style filtering — agents never scan full files.

| Tool | Signature | File | Purpose |
|---|---|---|---|
| `generate_case_id` | `() -> str` | — | Unique case ID e.g. `CLM-20260414-0042` |
| `create_case_record` | `(case_id, user_id, policy_no, claim_type, priority) -> str` | claims_metadata.csv | Initialize new case row |
| `update_case_csv` | `(case_id, fields: dict) -> str` | claims_metadata.csv | Update specific columns for a case |
| `query_policies` | `(filters, columns, limit) -> str` | policies.csv | Query policy records |
| `query_claims_history` | `(filters, columns, limit) -> str` | claims_history.csv | Query prior claims records |
| `query_fraud_patterns` | `(filters, columns, limit) -> str` | fraud_patterns.csv | Query known fraud risk records |
| `query_claims_metadata` | `(filters, columns, limit, role, user_id) -> str` | claims_metadata.csv | Query live cases. `end_user` auto-restricted to their `user_id` |
| `approve_case` | `(case_id, approver_id, decision, notes, override_decision, override_amount) -> str` | claims_metadata.csv | Human approval/rejection/override. Role-gated: support_exec/admin only |

**All query tools support the same filter operators:**
- `{"field": "value"}` — exact match
- `{"field__in": ["v1","v2"]}` — value in list
- `{"field__gte": "2026-01-01"}` — greater than or equal
- `{"field__lte": "value"}` — less than or equal
- `{"field__contains": "text"}` — substring match

**Example calls:**
```python
query_policies(filters={"policy_no": "POL-1001"},
               columns=["holder_name","status","coverage_limit","deductible","end_date","covered_claim_types"])

query_claims_history(filters={"policy_no": "POL-1004", "claim_date__gte": "2026-01-15"},
                     columns=["claim_id","claim_date","claimed_amount","status"])

query_fraud_patterns(filters={"policy_no": "POL-1004", "risk_level": "high"},
                     columns=["flag_type","description","flagged_date"])

query_claims_metadata(filters={"status__in": ["pending_approval","escalated_to_human"]},
                      columns=["case_id","user_id","claim_type","adjudication_decision","settlement_amount"],
                      role="support_exec")

query_claims_metadata(filters={"claim_type": "health"}, columns=["case_id","status","settlement_amount"],
                      role="end_user", user_id="USR-001")
```

---

### Audit Logging Tools  (tools/audit_log.py)

| Tool | Signature | Purpose |
|---|---|---|
| `log_decision` | `(case_id, agent_name, decision, reasoning) -> None` | Append entry to `logs/cases/{case_id}.txt`. **Mandatory for every agent after every action** |
| `read_audit_log` | `(case_id, role, user_id) -> str` | Read full audit log for a case. Role-gated |

**Audit log format:**
```
[2026-04-14 10:30:05] [INTAKE_AGENT]
  Decision : FNOL accepted. Case CLM-20260414-0042 created. Claim type: AUTO. Priority: MEDIUM.
  Reasoning: Policy POL-1002 active (expires 2026-05-31). Single-vehicle collision, no injuries.

[2026-04-14 10:30:12] [EXTRACTION_AGENT]
  Decision : 2 files processed. police_report.pdf → police_report. repair_estimate_auto.txt → repair_estimate.
  Reasoning: Extracted incident date 2026-04-10, location I-95 N, repair cost $8,500.

[2026-04-14 10:30:18] [VALIDATION_AGENT]
  Decision : Coverage VERIFIED. PASS.
  Reasoning: Policy active. Incident date within coverage. AUTO covered. No exclusions.
             Coverage limit $25,000. Deductible $1,000.

[2026-04-14 10:30:24] [FRAUD_AGENT]
  Decision : Fraud risk LOW. Recommendation: PROCEED.
  Reasoning: No fraud_patterns entries for POL-1002. No prior claims in 90 days.

[2026-04-14 10:30:30] [ADJUDICATION_AGENT]
  Decision : APPROVED. Settlement $7,500 (repair $8,500 − deductible $1,000).
  Reasoning: Within $25,000 limit. Low fraud risk. Estimate supported by extracted docs.

[2026-04-14 10:30:35] [DECISION_QA_AGENT]
  Decision : PASS. All checks consistent.
  Reasoning: Fraud=LOW → APPROVED consistent. Validation=PASS → no contradiction.
             Arithmetic correct. Status → pending_approval.

[2026-04-14 10:45:00] [MASTER_AGENT]
  Decision : Case overridden and approved by SUPP-007. Settlement changed to $7,000.
  Reasoning: approve_case called with decision=overridden, override_amount=7000.

[2026-04-14 10:45:05] [COMMUNICATION_AGENT]
  Decision : Email written to data/emails/CLM-20260414-0042_email.md
  Reasoning: Decision APPROVED (overridden), settlement $7,000. Ready for SMTP integration.
```

---

### Document Extraction Tools  (tools/document.py)

| Tool | Signature | Purpose |
|---|---|---|
| `extract_pdf` | `(file_path) -> str` | Extract text from PDF via `pypdf`. Backed by `DocumentExtractor` strategy — swap in Bedrock Data Automation for OCR without changing tool signature |
| `extract_text_file` | `(file_path) -> str` | Read content of plain `.txt` files directly |
| `classify_document` | `(extracted_text) -> str` | LLM classifies as: `physician_report \| medical_bill \| police_report \| repair_estimate \| invoice \| other` |

**Extensibility design:**
```python
class DocumentExtractor:
    """Strategy base — swap extractor without changing tool interface."""
    def extract(self, file_path: str) -> str: ...

class PyPDFExtractor(DocumentExtractor): ...        # current
class BedrockDataAutomationExtractor(DocumentExtractor): ...  # future — OCR for scanned/image PDFs

@tool
def extract_pdf(file_path: str) -> str:
    """Extract text from a PDF file for LLM reasoning."""
    extractor = get_extractor()   # returns PyPDFExtractor now, BedrockDataAutomationExtractor later
    return extractor.extract(file_path)
```

---

### Communication Tools  (tools/communication.py)

| Tool | Signature | Purpose |
|---|---|---|
| `send_email` | `(to_address, subject, body) -> str` | **Demo mode:** writes email content to `data/emails/{case_id}_email.md`. Returns file path. Real SMTP integration added later without changing tool name or signature. |

---

### Memory Tools  (tools/memory.py)

| Tool | Signature | Purpose |
|---|---|---|
| `memory_save` | `(session_id, key, value) -> None` | Save session facts (current case_id, user identity, last intent) |
| `memory_load` | `(session_id) -> dict` | Load full session memory for chatbot turn continuity |

---

### Utility  (tools/utils.py)

| Tool | Signature | Purpose |
|---|---|---|
| `current_time` | `() -> str` | UTC timestamp for audit log entries |

---

## Quick-Reference: Tool → Agent Mapping (23 tools)

| Tool | Intake | Extract | Valid. | Med.Rev | Fraud | Adjud. | QA | Comms | Master |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `generate_case_id` | ✓ | | | | | | | | |
| `create_case_record` | ✓ | | | | | | | | |
| `update_case_csv` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| `query_policies` | ✓ | | ✓ | | | ✓ | | ✓ | ✓ |
| `query_claims_history` | | | ✓ | | ✓ | | | | ✓ |
| `query_fraud_patterns` | | | | | ✓ | | | | ✓ |
| `query_claims_metadata` | | | | | ✓ | ✓ | ✓ | ✓ | ✓ |
| `approve_case` | | | | | | | | | ✓ |
| `log_decision` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `read_audit_log` | | | | | | | ✓ | | ✓ |
| `extract_pdf` | | ✓ | | ✓ | | | | | |
| `extract_text_file` | | ✓ | | | | | | | |
| `classify_document` | | ✓ | | | | | | | |
| `send_email` | | | | | | | | ✓ | |
| `memory_save` | ✓ | | | | | | | | ✓ |
| `memory_load` | | | | | | | | | ✓ |
| `current_time` | ✓ | | ✓ | | | ✓ | ✓ | ✓ | |

---

## Master Agent System Prompt (Calvin — role-aware)

```
You are Calvin, the Claims Processing Assistant for ABC Insurance.
Your role is to assist claimants, support executives, and administrators
with insurance claim processing. Be professional, clear, and precise.

Caller role is injected into your context: end_user | support_exec | admin.

ROLE: end_user
- Help submit new claims. Always start with intake_agent.
- For status queries, use query_claims_metadata(filters={...}, role="end_user", user_id=<their id>)
- Never reveal another user's case data.

ROLE: support_exec / admin
- Full conversational access. Answer any question about cases, policies, fraud records, or audit logs.
- Look up cases: query_claims_metadata(filters={"case_id": "..."}, role="support_exec")
- List/filter cases: query_claims_metadata with any filter combination
- Look up policy details: query_policies(filters={"policy_no": "..."})
- Check prior claims: query_claims_history(filters={"policy_no": "..."})
- Check fraud records: query_fraud_patterns(filters={"policy_no": "..."})
- Read audit trail: read_audit_log(case_id)
- Approve/reject: approve_case(case_id, approver_id, "approved"|"rejected", notes)
- Override decision or amount: approve_case(..., decision="overridden",
    override_decision="approved"|"partial"|"denied", override_amount=<float>)
- Present case lists as formatted tables.

Claim processing pipeline order (follow strictly for new claims):
1. intake_agent
2. extraction_agent (if PDF or .txt files submitted)
3. validation_agent → EARLY EXIT if policy invalid (skip 4, 5, go to adjudication with denial)
4. medical_review_agent (health claims only, after validation PASS, physician_report + medical_bill present)
5. fraud_agent
6. adjudication_agent
7. decision_qa_agent (always — never skip)
8. Wait for human review and approval via approve_case
9. communication_agent (only after approval or override)

Rules:
- Call log_decision after every agent completes.
- Never make claim decisions yourself — always delegate to the appropriate sub-agent.
- Maintain case context across turns using memory_save / memory_load.
- Introduce yourself as Calvin from ABC Insurance on first interaction.
```

---

## CSV Schemas

### data/claims_metadata.csv  (live — created at runtime)
```
case_id, created_at, updated_at, user_id, policy_no, claim_type, priority,
status, intake_status, extraction_status, documents_submitted, extracted_summary,
validation_status, coverage_limit, deductible, validation_notes,
medical_review_status, diagnosis, billed_amount, recommended_coverage_amount, discrepancy_details,
fraud_score, fraud_recommendation, fraud_flags,
adjudication_decision, settlement_amount, decision_reason,
qa_verdict, qa_comments, qa_attempts,
approval_status, approver_id, approval_notes, approval_timestamp,
override_decision, override_amount,
communication_status, email_file_path, last_communication_at
```

**Status lifecycle:**
```
intake_complete → extraction_complete → validated → medical_reviewed → fraud_checked
→ adjudicated → pending_approval | escalated_to_human → approved_for_comm | rejected | overridden → communicated
```

---

### dummy_data/policies.csv — designed to cover all demo scenarios

```
policy_no, holder_name, user_id, email, phone, policy_type,
start_date, end_date, status, coverage_limit, deductible,
covered_claim_types, exclusions, premium_monthly
```

| policy_no | holder_name | user_id | type | status | limit | deductible | scenario |
|---|---|---|---|---|---|---|---|
| POL-1001 | John Doe | USR-001 | health | active | 50000 | 500 | Scenarios 1, 2 (clean + discrepant health) |
| POL-1002 | Jane Smith | USR-002 | auto | active | 25000 | 1000 | Scenarios 5, 14 (clean auto, no docs) |
| POL-1003 | Bob Kumar | USR-003 | health | expired | 30000 | 750 | Scenario 4 (lapsed policy denial) |
| POL-1004 | Alice Tan | USR-004 | health | active | 40000 | 500 | Scenario 3 (fraud trigger) |
| POL-1005 | Mike Chen | USR-005 | health | active | 35000 | 600 | Scenarios 6, 7 (QA self-correction + escalation) |

---

### dummy_data/claims_history.csv — fraud triggers + normal history

```
claim_id, policy_no, user_id, claim_date, claim_type, claimed_amount, status, fraud_flagged
```

| claim_id | policy_no | claim_date | claimed_amount | purpose |
|---|---|---|---|---|
| CLM-H-001 | POL-1004 | 2026-01-15 | 38000 | First large health claim for Alice |
| CLM-H-002 | POL-1004 | 2026-03-20 | 41000 | Second large claim within 90 days → fraud trigger |
| CLM-A-001 | POL-1002 | 2025-11-10 | 4500 | Normal prior auto claim for Jane |
| CLM-H-003 | POL-1005 | 2026-02-01 | 32000 | Prior claim for Mike — high amount for QA scenario |
| CLM-H-004 | POL-1005 | 2026-03-28 | 33500 | Second claim in 60 days — QA contradiction trigger |

---

### dummy_data/fraud_patterns.csv — risk records covering all scenarios

```
pattern_id, policy_no, user_id, flag_type, description, risk_level, flagged_date
```

| pattern_id | policy_no | flag_type | risk_level | description | scenario |
|---|---|---|---|---|---|
| FP-001 | POL-1004 | multiple_claims | high | Two claims >$35k within 90 days | Scenario 3 |
| FP-002 | POL-1002 | inflated_estimate | medium | Repair estimate 3x market rate | Scenario 5 (medium risk, still proceeds) |
| FP-003 | POL-9999 | stolen_policy | high | Policy number used fraudulently | Edge case |
| FP-004 | POL-1005 | inconsistent_amounts | medium | Claimed amounts inconsistent with diagnosis | Scenario 6/7 QA trigger |

---

### dummy_data/sample_documents/ — PDFs and .txt files covering all scenarios

| File | Type | Used in |
|---|---|---|
| `physician_report_case1.pdf` | physician_report | Scenario 1 — consistent diagnosis |
| `medical_bills_case1.pdf` | medical_bill | Scenario 1 — matching itemized bills |
| `physician_report_case2.pdf` | physician_report | Scenario 2 — partial diagnosis |
| `medical_bills_case2.pdf` | medical_bill | Scenario 2 — has items NOT in physician report |
| `police_report_auto.pdf` | police_report | Scenario 5 — auto accident |
| `repair_estimate_auto.txt` | repair_estimate | Scenario 5 — .txt file (tests extract_text_file) |
| `physician_report_case3.pdf` | physician_report | Scenario 6/7 — QA contradiction case |
| `medical_bills_case3.pdf` | medical_bill | Scenario 6/7 — inflated amounts |

---

## File Structure

```
agents/claims/
├── agentic/
│   ├── master_agent.py          # Calvin — role-aware system prompt, all tools
│   ├── sub_agents/
│   │   ├── __init__.py
│   │   ├── intake.py            # @tool intake_agent
│   │   ├── extraction.py        # @tool extraction_agent (PyPDF + txt, extensible)
│   │   ├── validation.py        # @tool validation_agent (early-exit gate)
│   │   ├── medical_review.py    # @tool medical_review_agent (health claims only)
│   │   ├── fraud.py             # @tool fraud_agent
│   │   ├── adjudication.py      # @tool adjudication_agent
│   │   ├── decision_qa.py       # @tool decision_qa_agent (self-correction loop)
│   │   └── communication.py     # @tool communication_agent (writes email .md)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── csv_store.py         # generate_case_id, create_case_record, update_case_csv,
│   │   │                        # query_policies, query_claims_history,
│   │   │                        # query_fraud_patterns, query_claims_metadata, approve_case
│   │   ├── audit_log.py         # log_decision, read_audit_log
│   │   ├── document.py          # DocumentExtractor base, PyPDFExtractor,
│   │   │                        # extract_pdf (@tool), extract_text_file (@tool),
│   │   │                        # classify_document (@tool)
│   │   ├── communication.py     # send_email (@tool) — writes to .md, SMTP-ready interface
│   │   ├── memory.py            # memory_save, memory_load
│   │   └── utils.py             # current_time
│   ├── prompts.py               # All system prompts as constants (one per agent + master)
│   └── memory_manager.py        # Session memory store (JSON or SQLite)
├── dummy_data/
│   ├── policies.csv             # 5 policies covering all demo scenarios
│   ├── claims_history.csv       # Prior claims — fraud frequency patterns
│   ├── fraud_patterns.csv       # Risk records — high/medium, all scenarios covered
│   ├── sample_documents/
│   │   ├── physician_report_case1.pdf
│   │   ├── medical_bills_case1.pdf
│   │   ├── physician_report_case2.pdf
│   │   ├── medical_bills_case2.pdf
│   │   ├── police_report_auto.pdf
│   │   ├── repair_estimate_auto.txt   ← .txt file to demo extract_text_file
│   │   ├── physician_report_case3.pdf
│   │   └── medical_bills_case3.pdf
│   └── demo_scenarios.md        # Full demo guide with steps and expected outputs
├── data/
│   ├── claims_metadata.csv      # Live case tracking (auto-created at runtime)
│   ├── emails/                  # {case_id}_email.md — written by send_email tool
│   └── logs/
│       └── cases/               # {case_id}.txt per-case audit logs
├── apis/
│   ├── routes.py                # FastAPI — injects role + user_id into Calvin's context
│   ├── schemas.py               # Pydantic models (ClaimRequest, ChatMessage, etc.)
│   └── service.py               # Bridges API ↔ master_agent, manages session_id
```

---

## Demo Scenarios  (also written to dummy_data/demo_scenarios.md)

| # | Scenario | Policy/User | Key Agents | Expected Outcome |
|---|---|---|---|---|
| 1 | **Clean health claim** | POL-1001, USR-001 + case1 PDFs | All 8 in order | Approved, QA PASS, email .md written after human approval |
| 2 | **Health claim — medical discrepancy** | POL-1001 + case2 PDFs | Medical review flags mismatch | Partial adjudication, QA may re-run, human reviews |
| 3 | **Fraud — repeat large claims** | POL-1004, USR-004 | Fraud hits fraud_patterns.csv, high score | Adjudication escalates, QA escalates to human with notes |
| 4 | **Lapsed policy — early exit** | POL-1003, USR-003 | Validation early exit | Denied, medical review + fraud skipped entirely |
| 5 | **Clean auto claim with .txt file** | POL-1002, USR-002 + .txt estimate | No medical review | extract_text_file used, approved, settlement = estimate - deductible |
| 6 | **QA self-correction** | POL-1005, USR-005 | QA finds contradiction → re-runs adjudication | Second attempt fixes it → pending_approval |
| 7 | **QA escalation** | POL-1005, USR-005 | QA fails twice | escalated_to_human with detailed QA notes |
| 8 | **Admin lists pending reviews** | All cases | query_claims_metadata(pending_approval) | Formatted table of cases awaiting decision |
| 9 | **Support exec approves a case** | Any pending | approve_case(approved) | Email .md written, status=communicated |
| 10 | **Support exec overrides settlement** | Any pending | approve_case(overridden, override_amount=X) | New amount stored, email .md written |
| 11 | **Support exec rejects a decision** | Any pending | approve_case(rejected) | No email, status=rejected |
| 12 | **Human reviewer chats before deciding** | escalated_to_human case | Calvin answers questions via query + audit log | Reviewer gets full context, then approves/overrides |
| 13 | **End user checks their claim status** | USR-001 | query_claims_metadata (end_user filtered) | Only their own rows returned |
| 14 | **End user tries another user's case** | USR-001 → USR-002 | query_claims_metadata role-gate | Access denied at data layer |
| 15 | **Admin reads full audit trail** | Any case_id | read_audit_log | Every agent decision + reasoning |
| 16 | **No documents submitted** | POL-1002 | Extraction skipped | intake → validation → fraud → adjudication → QA |

---

## Key Design Decisions

| Decision | Reasoning |
|---|---|
| **Agent named Calvin, ABC Insurance** | Single identity across all personas. System prompt introduces Calvin on first interaction. |
| **Document extraction is extensible** | `extract_pdf` is backed by a `DocumentExtractor` strategy class. PyPDF now, Bedrock Data Automation (OCR) later — no tool signature changes needed. |
| **`extract_text_file` as a separate tool** | .txt files don't need PDF parsing. Keeps tools focused and avoids branching logic inside `extract_pdf`. |
| **`send_email` writes to .md for demo** | Tool name and signature stay the same. Real SMTP integration only requires swapping the implementation inside the tool, not changing any agent code. Email path stored in metadata. |
| **Human reviewer has full chat before approving** | Reviewer can ask Calvin anything about the case before acting. `approve_case` supports `override_decision` and `override_amount` so reviewers aren't forced into a binary approve/reject. |
| **Separate query tool per record type** | `query_policies`, `query_claims_history`, `query_fraud_patterns`, `query_claims_metadata` — LLM knows exactly which tool to call. Role-gate on `query_claims_metadata` enforced at data layer. |
| **Validation before medical review** | Lapsed/uncovered policy = early exit. No point running medical review or fraud check if validation fails. |
| **`log_decision` mandatory for every agent** | Populates the per-case audit text file. Without it, the case has no trace. |
| **Decision QA with self-correction** | Catches contradictions before human review. Max 2 auto-fix attempts, then escalates with notes. |
| **Dummy data covers all 16 scenarios** | 5 policies, targeted claims history rows, and fraud pattern rows specifically chosen to trigger each scenario cleanly. |

---

## Verification / Testing

1. **Clean health claim (Scenario 1):** USR-001 + case1 PDFs → all 8 agents run, CSV and audit log populated, email .md written
2. **Medical discrepancy (Scenario 2):** case2 PDFs → medical_review flags mismatch → adjudication uses recommended_coverage_amount
3. **Fraud trigger (Scenario 3):** USR-004 → fraud_agent matches fraud_patterns.csv → high score → escalated
4. **Lapsed policy early exit (Scenario 4):** USR-003 → validation reads expired → denied, steps 4–5 not called
5. **Text file extraction (Scenario 5):** repair_estimate_auto.txt → extract_text_file called instead of extract_pdf
6. **QA self-correction (Scenario 6):** force contradiction → QA FIX_REQUIRED → re-run adjudication → passes
7. **Override (Scenario 10):** support exec says "override to $6,000" → approve_case with override_amount=6000
8. **Human chat before approval (Scenario 12):** reviewer asks "why was this escalated?" → Calvin explains using audit log
9. **Role isolation (Scenario 14):** end user queries another user's case → query_claims_metadata blocks it
10. **Email .md file:** after approval, verify `data/emails/{case_id}_email.md` exists and path is in CSV

---

## Dependencies

```
strands-agents>=1.0
strands-agents-tools>=1.0
pypdf                   # PDF text extraction (current)
pdfplumber              # PDF table extraction (supplementary)
pandas                  # CSV read/filter/write
smtplib                 # Email stdlib — ready when SMTP integration is added
# boto3               # Uncomment when Bedrock Data Automation OCR is added
```
