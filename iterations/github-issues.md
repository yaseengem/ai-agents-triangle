# Neural — Sprints, Epics & User Stories

> Project: **Neural** — Multi-agent AI platform for financial services  
> Agents: Claims Processing · Underwriting · Loan Processing  
> Stack: React · FastAPI · AWS Strands · AWS Bedrock

---

## Sprint Plan

| Sprint | Goal | Epics | Duration |
|--------|------|-------|----------|
| **Sprint 1** | Working frontend with mock APIs + project scaffold | EP-1, EP-2 | 2 weeks |
| **Sprint 2** | Claims agent fully functional end-to-end | EP-3 | 2 weeks |
| **Sprint 3** | Underwriting and Loan agents complete | EP-4, EP-5 | 2 weeks |
| **Sprint 4** | All agents wired to frontend, tested, deployed to EC2 | EP-6 | 2 weeks |
| **Sprint 5** _(future)_ | Strands workflows migrated to AgentCore | EP-7 | 2 weeks |

---

## Epics

---

### EP-1 — Project Foundation & Scaffold
**Type:** Epic | **Sprint:** 1 | **Labels:** `epic`, `foundation`

#### Overview
Set up the Neural project structure, environment configuration, file system storage layout, and local memory backend so all subsequent development has a consistent, runnable base.

#### Stories
- US-01, US-02, US-03, US-04

---

### EP-2 — Neural Frontend
**Type:** Epic | **Sprint:** 1 | **Labels:** `epic`, `frontend`

#### Overview
Build the complete React frontend for Neural — agent list, role selection, and all three chat screens (User, Support, Admin) — wired to a mock API layer so the UI is fully testable before backend is ready.

#### Stories
- US-05, US-06, US-07, US-08, US-09, US-10, US-11, US-12, US-13, US-14, US-15

---

### EP-3 — Claims Processing Agent
**Type:** Epic | **Sprint:** 2 | **Labels:** `epic`, `claims`

#### Overview
Build the full Claims Processing agent: FastAPI backend (`apis/`) with all endpoints including SSE streaming and human approval flow, and the Strands agentic workflow (`agentic/`) with role-aware prompts, agent memory for rules, document tools, and human-in-the-loop pause/resume.

#### Stories
- US-16, US-17, US-18, US-19, US-20, US-21, US-22, US-23, US-24, US-25, US-26, US-27, US-28, US-29, US-30

---

### EP-4 — Underwriting Agent
**Type:** Epic | **Sprint:** 3 | **Labels:** `epic`, `underwriting`

#### Overview
Build the Underwriting agent following the same pattern as Claims. Includes underwriting-specific tools, rules, and prompts. Isolated from all other agents.

#### Stories
- US-31, US-32, US-33, US-34

---

### EP-5 — Loan Processing Agent
**Type:** Epic | **Sprint:** 3 | **Labels:** `epic`, `loan`

#### Overview
Build the Loan Processing agent following the same pattern as Claims. Includes loan-specific tools, rules, and prompts. Isolated from all other agents.

#### Stories
- US-35, US-36, US-37, US-38

---

### EP-6 — EC2 Deployment
**Type:** Epic | **Sprint:** 4 | **Labels:** `epic`, `deployment`

#### Overview
Deploy all Neural services to AWS EC2 — React frontend behind Nginx, three FastAPI services managed by systemd, with environment variable–driven config so no code changes are needed.

#### Stories
- US-39, US-40, US-41, US-42

---

### EP-7 — AgentCore Migration _(Future)_
**Type:** Epic | **Sprint:** 5 | **Labels:** `epic`, `agentcore`, `future`

#### Overview
Migrate the three Strands agentic workflows to AWS Bedrock AgentCore Runtime. Swap `LocalMemoryStore` to `AgentCoreMemorySessionManager` via env var, add CDK stacks for AgentCore Runtime and MCP Gateway.

#### Stories
- US-43, US-44, US-45, US-46

---

---

## User Stories

---

### US-01 — Project Scaffold and Folder Structure
**Type:** User Story | **Epic:** EP-1 | **Sprint:** 1 | **Points:** 2 | **Labels:** `story`, `foundation`

#### User Story
**As a** developer,
**I want** the Neural project scaffolded with the correct folder structure,
**so that** all team members work in a consistent, predictable layout from day one.

#### Acceptance Criteria
- [ ] Root folders exist: `frontend/`, `agents/`, `storage/`, `test/`, `docs/`, `iterations/`
- [ ] Each agent folder has `apis/` and `agentic/` subfolders: `agents/claims/`, `agents/underwriting/`, `agents/loan/`
- [ ] `test/` has subfolders: `claims/`, `underwriting/`, `loan/`
- [ ] `.gitignore` covers `node_modules/`, `__pycache__/`, `.env`, `storage/`
- [ ] Root `README.md` describes the project and how to run it locally

---

### US-02 — File System Storage Layout
**Type:** User Story | **Epic:** EP-1 | **Sprint:** 1 | **Points:** 1 | **Labels:** `story`, `foundation`

#### User Story
**As a** developer,
**I want** the storage directory structure created and documented,
**so that** all agents write artifacts to predictable, consistent paths.

#### Acceptance Criteria
- [ ] `storage/claims/`, `storage/underwriting/`, `storage/loan/` directories created
- [ ] `storage/memory/` directory created for local memory backend files
- [ ] Each case sub-structure documented: `{case_id}/input/`, `analysis/`, `decisions/`, `chat_history/`, `status.json`
- [ ] `STORAGE_PATH` env var controls the root path (default `./storage`)
- [ ] `storage/` is git-ignored

---

### US-03 — Local Memory Backend
**Type:** User Story | **Epic:** EP-1 | **Sprint:** 1 | **Points:** 3 | **Labels:** `story`, `foundation`, `memory`

#### User Story
**As a** developer,
**I want** a `LocalMemoryStore` class that persists agent memory (rules + conversation history) to a JSON file,
**so that** agents have durable memory locally with zero cloud dependency, and switching to AgentCore Memory requires only an env var change.

#### Acceptance Criteria
- [ ] `LocalMemoryStore` class with `get(key)`, `set(key, value)`, `delete(key)`, `list_keys()` methods
- [ ] Data persisted to `storage/memory/{agent}_memory.json`
- [ ] Thread-safe writes using file locking
- [ ] `create_memory_backend(agent_name)` factory function reads `MEMORY_BACKEND` env var: `local` → `LocalMemoryStore`, `agentcore` → stub/placeholder
- [ ] Unit tests for read/write/persistence

---

### US-04 — Environment Configuration
**Type:** User Story | **Epic:** EP-1 | **Sprint:** 1 | **Points:** 1 | **Labels:** `story`, `foundation`

#### User Story
**As a** developer,
**I want** a `.env.example` file at the project root,
**so that** anyone can run Neural locally by copying it to `.env` and filling in their AWS credentials.

#### Acceptance Criteria
- [ ] `.env.example` includes: `AWS_REGION`, `BEDROCK_MODEL_ID`, `STORAGE_PATH`, `MEMORY_BACKEND`, `CLAIMS_API_PORT`, `UNDERWRITING_API_PORT`, `LOAN_API_PORT`
- [ ] Each variable has an inline comment explaining its purpose and accepted values
- [ ] Frontend `.env.example` includes `VITE_CLAIMS_API_URL`, `VITE_UNDERWRITING_API_URL`, `VITE_LOAN_API_URL`
- [ ] Root `README.md` references `.env.example`

---

### US-05 — Agent List Page
**Type:** User Story | **Epic:** EP-2 | **Sprint:** 1 | **Points:** 2 | **Labels:** `story`, `frontend`

#### User Story
**As a** user,
**I want** to see a landing page showing all available Neural agents as cards,
**so that** I can choose which agent to interact with.

#### Acceptance Criteria
- [ ] `AgentListPage` renders one `AgentCard` per agent: Claims, Underwriting, Loan
- [ ] Each card shows: agent name, short description, icon/colour
- [ ] Clicking a card navigates to `/agents/{agent-id}`
- [ ] Cards are responsive (2-col tablet, 3-col desktop, 1-col mobile)
- [ ] Page title is "Neural"

---

### US-06 — Role Selection Screen
**Type:** User Story | **Epic:** EP-2 | **Sprint:** 1 | **Points:** 2 | **Labels:** `story`, `frontend`

#### User Story
**As a** user,
**I want** to select my role (User, Support, Admin) after choosing an agent,
**so that** I see the correct interface for my level of access — with no login required.

#### Acceptance Criteria
- [ ] `RoleSelectPage` at `/agents/{agent-id}` shows three role buttons: User, Support, Admin
- [ ] Each button shows the role name and a one-line description of capabilities
- [ ] Selecting a role navigates to `/agents/{agent-id}/{role}`
- [ ] Selected role is stored in component/URL state and passed as `role` in every API call
- [ ] No authentication — role is selected on trust for demo

---

### US-07 — User Chat Screen
**Type:** User Story | **Epic:** EP-2 | **Sprint:** 1 | **Points:** 5 | **Labels:** `story`, `frontend`

#### User Story
**As an** end user,
**I want** a chat screen where I can upload my document and ask questions about my case,
**so that** I can submit and track my claim/loan/application without calling support.

#### Acceptance Criteria
- [ ] `UserChatPage` at `/agents/{agent-id}/user`
- [ ] `FileUpload` component: drag-drop zone + browse button, shows file name on attach
- [ ] Attached file sent with first chat message or via upload button
- [ ] `ChatInputArea` with send on Enter, shift-Enter for newline
- [ ] `MessageBubble` renders user messages (right) and assistant messages (left) with timestamps
- [ ] `StatusBadge` shows current workflow state (INITIATED / PROCESSING / PENDING_APPROVAL / CLOSED)
- [ ] `ApprovalBanner` appears when status = `PENDING_HUMAN_APPROVAL` with Approve and Reject buttons
- [ ] All responses streamed via SSE — tokens appended as they arrive

---

### US-08 — Support Chat Screen
**Type:** User Story | **Epic:** EP-2 | **Sprint:** 1 | **Points:** 3 | **Labels:** `story`, `frontend`

#### User Story
**As a** support agent,
**I want** a chat screen where I can search for any case and ask the agent questions about it,
**so that** I can help users understand their case outcomes quickly.

#### Acceptance Criteria
- [ ] `SupportChatPage` at `/agents/{agent-id}/support`
- [ ] `CaseSearch` input at the top: enter `case_id` to load a session
- [ ] On session load, `StatusBadge` shows current state
- [ ] Chat window shows conversation history for the loaded session
- [ ] New messages sent with `role: support` in request body
- [ ] No file upload component on this screen
- [ ] Streamed SSE responses rendered same as User screen

---

### US-09 — Admin Chat Screen
**Type:** User Story | **Epic:** EP-2 | **Sprint:** 1 | **Points:** 4 | **Labels:** `story`, `frontend`

#### User Story
**As an** admin/supervisor,
**I want** a chat screen with a rules sidebar panel plus full support capabilities,
**so that** I can manage agent behaviour and query any case from one place.

#### Acceptance Criteria
- [ ] `AdminChatPage` at `/agents/{agent-id}/admin`
- [ ] `RulePanelSidebar` fetches `GET /rules` on load and displays current rules as a list
- [ ] Sidebar has a refresh button to reload rules
- [ ] Chat window supports everything on the Support screen (case search, session history)
- [ ] Messages sent with `role: admin`
- [ ] When admin sends a rule-change message, sidebar auto-refreshes after response
- [ ] Streamed SSE responses rendered same as other screens

---

### US-10 — useChat Hook (SSE Streaming)
**Type:** User Story | **Epic:** EP-2 | **Sprint:** 1 | **Points:** 3 | **Labels:** `story`, `frontend`

#### User Story
**As a** developer,
**I want** a `useChat` hook that handles POST to `/chat/{sessionId}` and parses the SSE stream,
**so that** every chat screen gets real-time token streaming with a single hook call.

#### Acceptance Criteria
- [ ] `useChat(agentType, sessionId, role)` returns `{ sendMessage, messages, isStreaming, error }`
- [ ] Parses SSE event types: `text-delta`, `tool-status`, `done`, `error`
- [ ] Appends tokens to the last assistant message as they arrive
- [ ] `tool-status` events render as `ToolExecutionBadge` inline
- [ ] Sets `isStreaming = false` on `done` event
- [ ] Retries once on network error before surfacing to UI

---

### US-11 — useAgentStatus Hook
**Type:** User Story | **Epic:** EP-2 | **Sprint:** 1 | **Points:** 2 | **Labels:** `story`, `frontend`

#### User Story
**As a** developer,
**I want** a `useAgentStatus` hook that polls `GET /status/{sessionId}`,
**so that** every screen shows an up-to-date workflow state without manual refresh.

#### Acceptance Criteria
- [ ] `useAgentStatus(agentType, sessionId)` returns `{ status, lastUpdated, error }`
- [ ] Polls every 5 seconds when status is `INITIATED` or `PROCESSING`
- [ ] Stops polling when status is `CLOSED` or `REJECTED`
- [ ] Returns `PENDING_HUMAN_APPROVAL` immediately so `ApprovalBanner` renders
- [ ] Works with mock API in Sprint 1

---

### US-12 — useFileUpload Hook
**Type:** User Story | **Epic:** EP-2 | **Sprint:** 1 | **Points:** 2 | **Labels:** `story`, `frontend`

#### User Story
**As a** developer,
**I want** a `useFileUpload` hook that POSTs to `/upload`,
**so that** file upload logic is reusable and decoupled from the chat components.

#### Acceptance Criteria
- [ ] `useFileUpload(agentType)` returns `{ uploadFile, fileRef, isUploading, error }`
- [ ] Accepts `File` object, sends as `multipart/form-data`
- [ ] Returns `{ file_ref, case_id }` from response
- [ ] Shows upload progress (0–100%)
- [ ] Clears state on successful upload and surfaces `file_ref` to caller

---

### US-13 — Shared Chat Components
**Type:** User Story | **Epic:** EP-2 | **Sprint:** 1 | **Points:** 3 | **Labels:** `story`, `frontend`

#### User Story
**As a** developer,
**I want** shared chat UI components used across all three screens,
**so that** all agent interfaces look and behave consistently.

#### Acceptance Criteria
- [ ] `MessageBubble`: renders user/assistant/system messages, supports markdown in assistant messages
- [ ] `StreamingText`: renders token-by-token with a blinking cursor while streaming
- [ ] `ToolExecutionBadge`: compact badge showing tool name + status (running / done / error)
- [ ] `ChatInputArea`: textarea, send button, attach button, disabled while streaming
- [ ] `StatusBadge`: colour-coded pill for each workflow state
- [ ] `ApprovalBanner`: dismissible banner with Approve / Reject buttons and summary text

---

### US-14 — Mock API Layer
**Type:** User Story | **Epic:** EP-2 | **Sprint:** 1 | **Points:** 2 | **Labels:** `story`, `frontend`

#### User Story
**As a** developer,
**I want** a mock API layer that returns realistic fake responses for all endpoints,
**so that** the frontend can be fully developed and demoed before backend is ready.

#### Acceptance Criteria
- [ ] Mock functions for: `postProcess`, `postUpload`, `postChat`, `getStatus`, `postApprove`, `postReject`, `getRules`, `postRules`, `getSessions`
- [ ] `postChat` mock simulates SSE by yielding tokens at 50ms intervals
- [ ] `getStatus` mock cycles through states: `PROCESSING` → `PENDING_HUMAN_APPROVAL` after 5s
- [ ] Toggle between mock and real API via `VITE_USE_MOCK_API=true` env var
- [ ] Mock data covers all three agents (claims, underwriting, loan)

---

### US-15 — Frontend Routing and Layout
**Type:** User Story | **Epic:** EP-2 | **Sprint:** 1 | **Points:** 2 | **Labels:** `story`, `frontend`

#### User Story
**As a** user,
**I want** smooth navigation between pages with a consistent layout and back-navigation,
**so that** Neural feels like a polished, coherent application.

#### Acceptance Criteria
- [ ] React Router v6 routes: `/`, `/agents/:agentId`, `/agents/:agentId/:role`
- [ ] Shared `AppShell` layout with Neural header and breadcrumb trail
- [ ] Back button on role select and chat screens
- [ ] 404 page for unknown routes
- [ ] Agent name and role shown in browser tab title

---

### US-16 — Claims FastAPI App Setup
**Type:** User Story | **Epic:** EP-3 | **Sprint:** 2 | **Points:** 2 | **Labels:** `story`, `claims`, `api`

#### User Story
**As a** developer,
**I want** the Claims FastAPI application bootstrapped with CORS, routing, and uvicorn entrypoint,
**so that** it runs on `localhost:8001` and is ready for endpoint implementation.

#### Acceptance Criteria
- [ ] `agents/claims/apis/main.py` creates `FastAPI` app with CORS middleware (all origins for demo)
- [ ] `APIRouter` imported from `routes.py` and mounted at `/`
- [ ] `GET /ping` returns `{"status": "ok", "agent": "claims"}`
- [ ] Runs via `uvicorn main:app --port 8001 --reload`
- [ ] `requirements.txt` includes: `fastapi`, `uvicorn`, `python-multipart`, `pydantic`, `boto3`
- [ ] All Pydantic schemas defined in `schemas.py`

---

### US-17 — Claims POST /process Endpoint
**Type:** User Story | **Epic:** EP-3 | **Sprint:** 2 | **Points:** 3 | **Labels:** `story`, `claims`, `api`

#### User Story
**As a** developer,
**I want** `POST /process` to create a session and kick off the claims workflow asynchronously,
**so that** test scripts and integrations can start claim processing without the chat UI.

#### Acceptance Criteria
- [ ] Accepts `ProcessRequest`: `case_id`, `payload` (dict), `user_id`
- [ ] Generates `session_id` (UUID), creates `storage/claims/{case_id}/` directory structure
- [ ] Writes `status.json` with `{status: INITIATED, session_id, created_at}`
- [ ] Spawns Strands workflow as background `asyncio.Task`
- [ ] Returns `{session_id, case_id, status: INITIATED}` immediately (does not wait for workflow)
- [ ] Returns `400` if `case_id` already has an active session

---

### US-18 — Claims POST /upload Endpoint
**Type:** User Story | **Epic:** EP-3 | **Sprint:** 2 | **Points:** 2 | **Labels:** `story`, `claims`, `api`

#### User Story
**As an** end user,
**I want** to upload a claim document via the chat UI,
**so that** the agent can read and process my document.

#### Acceptance Criteria
- [ ] Accepts `multipart/form-data` with `file` field and optional `user_id`
- [ ] Saves file to `storage/claims/{case_id}/input/{filename}`
- [ ] Generates `case_id` if not provided; reuses existing if provided
- [ ] Returns `{file_ref, case_id, session_id}`
- [ ] Rejects files > 20MB with `413`
- [ ] Accepts: PDF, PNG, JPG, DOCX

---

### US-19 — Claims POST /chat SSE Endpoint
**Type:** User Story | **Epic:** EP-3 | **Sprint:** 2 | **Points:** 5 | **Labels:** `story`, `claims`, `api`

#### User Story
**As a** user (any role),
**I want** my chat message to stream back a response token-by-token,
**so that** the interface feels responsive even for long agent answers.

#### Acceptance Criteria
- [ ] Accepts `ChatRequest`: `message`, `role` (user/support/admin), `user_id`
- [ ] Returns `StreamingResponse` with `Content-Type: text/event-stream`
- [ ] SSE event format: `data: {"type": "text-delta", "content": "..."}` per token
- [ ] `tool-status` events emitted when agent calls a tool: `{"type": "tool-status", "tool": "...", "status": "running|done"}`
- [ ] Final `{"type": "done"}` event closes the stream
- [ ] Loads session by `session_id` from path; returns `404` if not found
- [ ] `role` injected into agent system prompt on every call

---

### US-20 — Claims GET /status Endpoint
**Type:** User Story | **Epic:** EP-3 | **Sprint:** 2 | **Points:** 1 | **Labels:** `story`, `claims`, `api`

#### User Story
**As a** frontend hook (`useAgentStatus`),
**I want** to poll the workflow state of a session,
**so that** the UI always reflects the current processing status.

#### Acceptance Criteria
- [ ] Returns `WorkflowStatus`: `session_id`, `case_id`, `status`, `created_at`, `updated_at`, `data` (dict)
- [ ] Reads from `storage/claims/{case_id}/status.json`
- [ ] Returns `404` if session not found
- [ ] `data` field includes relevant summary when status is `PENDING_HUMAN_APPROVAL` or `CLOSED`

---

### US-21 — Claims Approval Endpoints
**Type:** User Story | **Epic:** EP-3 | **Sprint:** 2 | **Points:** 3 | **Labels:** `story`, `claims`, `api`

#### User Story
**As a** supervisor,
**I want** to approve or reject a pending claim via the API,
**so that** the workflow resumes or closes based on my decision.

#### Acceptance Criteria
- [ ] `POST /approve/{session_id}` accepts `ApprovalRequest`: `notes` (optional)
- [ ] `POST /reject/{session_id}` accepts `RejectionRequest`: `reason` (required)
- [ ] Both write a record to `storage/claims/{case_id}/decisions/approval_record.json`
- [ ] Both update `status.json` and signal the paused workflow via `asyncio.Event`
- [ ] Return `400` if session status is not `PENDING_HUMAN_APPROVAL`
- [ ] Return `404` if session not found

---

### US-22 — Claims Rules Endpoints
**Type:** User Story | **Epic:** EP-3 | **Sprint:** 2 | **Points:** 2 | **Labels:** `story`, `claims`, `api`

#### User Story
**As an** admin,
**I want** REST endpoints to view and replace the claims agent ruleset,
**so that** the frontend rules sidebar always shows the current rules.

#### Acceptance Criteria
- [ ] `GET /rules` reads rules from memory backend and returns `RuleSet {rules: [...]}`
- [ ] `POST /rules` accepts `RuleSet`, writes to memory backend, returns `{status: ok}`
- [ ] Changes take effect on the next agent invocation (no restart required)
- [ ] `GET /sessions` accepts `?role=support&user_id=X` and returns list of `Session` summaries from `storage/claims/`

---

### US-23 — Claims Session Listing
**Type:** User Story | **Epic:** EP-3 | **Sprint:** 2 | **Points:** 1 | **Labels:** `story`, `claims`, `api`

#### User Story
**As a** support agent,
**I want** to list all claims sessions,
**so that** I can search for a specific case to query.

#### Acceptance Criteria
- [ ] `GET /sessions` scans `storage/claims/` for `status.json` files
- [ ] Returns list of `{session_id, case_id, status, created_at, updated_at}`
- [ ] Supports `?status=PENDING_HUMAN_APPROVAL` filter
- [ ] Results sorted by `updated_at` descending

---

### US-24 — Claims Strands Agent Setup
**Type:** User Story | **Epic:** EP-3 | **Sprint:** 2 | **Points:** 3 | **Labels:** `story`, `claims`, `agentic`

#### User Story
**As a** developer,
**I want** the Claims Strands agent bootstrapped with a `BedrockModel`, memory manager, and tools list,
**so that** it can be invoked for both processing and chat from the API service.

#### Acceptance Criteria
- [ ] `agents/claims/agentic/agent.py` defines `ClaimsAgent` using Strands `Agent()`
- [ ] Model configured from `BEDROCK_MODEL_ID` env var
- [ ] Memory backend created via `create_memory_backend("claims")` factory
- [ ] All domain tools registered on the agent
- [ ] Agent callable as `agent(message)` for chat and `agent.run(task)` for processing
- [ ] `requirements.txt` includes: `strands-agents`, `boto3`, `fastapi`

---

### US-25 — Claims Role-Aware System Prompts
**Type:** User Story | **Epic:** EP-3 | **Sprint:** 2 | **Points:** 3 | **Labels:** `story`, `claims`, `agentic`

#### User Story
**As a** developer,
**I want** the Claims agent to adjust its behaviour based on the caller's role,
**so that** a user gets empathetic case updates, support gets factual summaries, and admin gets full audit detail plus rule management.

#### Acceptance Criteria
- [ ] `agents/claims/agentic/prompts.py` defines `SYSTEM_PROMPT` base and `ROLE_INSTRUCTIONS` dict with keys `user`, `support`, `admin`
- [ ] `user` instructions: empathetic, no jargon, focus on own case only
- [ ] `support` instructions: factual, reference case files, explain decisions
- [ ] `admin` instructions: full access, rule management, audit trail
- [ ] `RULES_TEMPLATE` inserts current ruleset into system prompt: `"Current operating rules:\n{rules}"`
- [ ] Prompt built per call: `SYSTEM_PROMPT + ROLE_INSTRUCTIONS[role] + RULES_TEMPLATE.format(rules=...)`

---

### US-26 — Claims Memory Manager
**Type:** User Story | **Epic:** EP-3 | **Sprint:** 2 | **Points:** 3 | **Labels:** `story`, `claims`, `agentic`, `memory`

#### User Story
**As a** developer,
**I want** the Claims agent to load and save rules and conversation history from the memory backend,
**so that** rules persist across restarts and agent context is maintained per session.

#### Acceptance Criteria
- [ ] `agents/claims/agentic/memory_manager.py` wraps `LocalMemoryStore` (or future AgentCore Memory)
- [ ] `get_rules()` → returns `list[str]` of current rules; returns default rules if none stored
- [ ] `set_rules(rules: list[str])` → persists to memory backend
- [ ] `add_rule(rule: str)` → appends to existing list and persists
- [ ] `remove_rule(rule: str)` → removes by exact match and persists
- [ ] Default rules seeded on first run from `prompts.py::DEFAULT_RULES`
- [ ] Conversation history managed by Strands session manager (separate from rules)

---

### US-27 — Claims Document Processing Tool
**Type:** User Story | **Epic:** EP-3 | **Sprint:** 2 | **Points:** 4 | **Labels:** `story`, `claims`, `agentic`

#### User Story
**As the** claims agent,
**I want** a tool that reads and extracts structured data from uploaded documents,
**so that** I can analyse a claim without manual data entry.

#### Acceptance Criteria
- [ ] `@tool document_parser(file_path: str) -> dict` in `tools.py`
- [ ] Reads PDF/image from `storage/claims/{case_id}/input/`
- [ ] Extracts text content (use `pypdf` for PDF, `Pillow` for images via Bedrock vision if needed)
- [ ] Returns structured dict: `{document_type, raw_text, extracted_fields}`
- [ ] Writes extraction result to `storage/claims/{case_id}/analysis/document_extract.json`
- [ ] Returns error message (not exception) if file not found

---

### US-28 — Claims Case File Tools
**Type:** User Story | **Epic:** EP-3 | **Sprint:** 2 | **Points:** 3 | **Labels:** `story`, `claims`, `agentic`

#### User Story
**As the** claims agent,
**I want** tools to read and search case files on the file system,
**so that** support and admin can ask questions about any processed case and get accurate answers.

#### Acceptance Criteria
- [ ] `@tool read_case_status(case_id: str) -> dict` — reads `status.json`
- [ ] `@tool read_case_analysis(case_id: str) -> dict` — reads `analysis/analysis_result.json`
- [ ] `@tool read_decision_log(case_id: str) -> dict` — reads `decisions/decision_log.json`
- [ ] `@tool search_cases(query: str) -> list` — scans all `status.json` files, filters by status/date
- [ ] All tools return informative error strings (not exceptions) for missing files
- [ ] Tools validate `case_id` against path traversal (only `[a-zA-Z0-9_-]`)

---

### US-29 — Claims Human-in-the-Loop Approval Hook
**Type:** User Story | **Epic:** EP-3 | **Sprint:** 2 | **Points:** 5 | **Labels:** `story`, `claims`, `agentic`

#### User Story
**As the** claims workflow,
**I want** to pause execution and wait for a human approval signal before proceeding to closure,
**so that** high-stakes decisions always have a human review step.

#### Acceptance Criteria
- [ ] `agents/claims/agentic/approval_hook.py` defines `ApprovalHook`
- [ ] `request_approval(session_id, summary)` writes `interrupt.json`, updates `status.json` to `PENDING_HUMAN_APPROVAL`, and calls `asyncio.Event.wait()`
- [ ] `resume(decision: str)` — called by API service — sets the `asyncio.Event`, workflow proceeds
- [ ] Active events stored in a module-level `dict[session_id → asyncio.Event]`
- [ ] Approval decision (`approved`/`rejected`) returned to the workflow coroutine from `request_approval()`
- [ ] If timeout (configurable, default 24h) passes with no decision, workflow moves to `EXPIRED`

---

### US-30 — Claims Dual Entry Processing
**Type:** User Story | **Epic:** EP-3 | **Sprint:** 2 | **Points:** 3 | **Labels:** `story`, `claims`, `agentic`

#### User Story
**As a** developer,
**I want** the claims agent to start processing both from a chat message with a file attachment and from a direct `POST /process` API call,
**so that** users and automated systems both trigger the same workflow.

#### Acceptance Criteria
- [ ] Chat path: agent detects `file_ref` in message context → calls `document_parser` → begins analysis
- [ ] API path: `POST /process` with `payload` → workflow calls analysis tools → begins analysis
- [ ] Both paths transition: `INITIATED → PROCESSING → PENDING_HUMAN_APPROVAL`
- [ ] Both paths write the same artifacts to the file system
- [ ] Processing result written to `storage/claims/{case_id}/analysis/analysis_result.json`
- [ ] Decision written to `storage/claims/{case_id}/decisions/decision_log.json`

---

### US-31 — Underwriting APIs
**Type:** User Story | **Epic:** EP-4 | **Sprint:** 3 | **Points:** 3 | **Labels:** `story`, `underwriting`, `api`

#### User Story
**As a** developer,
**I want** the Underwriting FastAPI backend with all endpoints matching the claims contract,
**so that** the frontend and test scripts can interact with the underwriting agent identically to claims.

#### Acceptance Criteria
- [ ] `agents/underwriting/apis/` has all files matching claims structure (`main.py`, `routes.py`, `service.py`, `schemas.py`)
- [ ] Runs on port `8002` (configurable via `UNDERWRITING_API_PORT`)
- [ ] All endpoints implemented: `/process`, `/upload`, `/chat/{id}`, `/status/{id}`, `/approve/{id}`, `/reject/{id}`, `/rules`, `/sessions`, `/ping`
- [ ] Storage path: `storage/underwriting/{case_id}/`
- [ ] Domain label: `"agent": "underwriting"` in ping response

---

### US-32 — Underwriting Agentic Workflow
**Type:** User Story | **Epic:** EP-4 | **Sprint:** 3 | **Points:** 3 | **Labels:** `story`, `underwriting`, `agentic`

#### User Story
**As a** developer,
**I want** the Underwriting Strands agent set up following the same pattern as Claims,
**so that** it is fully functional with role-aware prompts, memory, and approval flow.

#### Acceptance Criteria
- [ ] `agents/underwriting/agentic/` has all files: `agent.py`, `tools.py`, `state.py`, `prompts.py`, `approval_hook.py`, `memory_manager.py`
- [ ] Memory backend keyed to `"underwriting"` — isolated from claims memory
- [ ] Approval hook and dual-entry pattern identical to claims
- [ ] Default rules relevant to underwriting loaded on first run

---

### US-33 — Underwriting Domain Tools
**Type:** User Story | **Epic:** EP-4 | **Sprint:** 3 | **Points:** 3 | **Labels:** `story`, `underwriting`, `agentic`

#### User Story
**As the** underwriting agent,
**I want** domain-specific tools for risk assessment,
**so that** I can evaluate applications with underwriting-relevant data.

#### Acceptance Criteria
- [ ] `@tool read_application(case_id)` — reads application documents from `input/`
- [ ] `@tool risk_assessment(application_data: dict) -> dict` — scores applicant risk (rule-based + LLM)
- [ ] `@tool check_coverage_eligibility(application_data: dict) -> dict` — validates against coverage rules
- [ ] `@tool read_case_analysis(case_id)` and `@tool search_cases(query)` (same pattern as claims)
- [ ] Results written to `storage/underwriting/{case_id}/analysis/`

---

### US-34 — Underwriting Default Rules
**Type:** User Story | **Epic:** EP-4 | **Sprint:** 3 | **Points:** 1 | **Labels:** `story`, `underwriting`, `agentic`

#### User Story
**As an** admin,
**I want** the Underwriting agent to start with sensible default operating rules,
**so that** it processes applications correctly without requiring manual rule setup.

#### Acceptance Criteria
- [ ] `DEFAULT_RULES` list in `agents/underwriting/agentic/prompts.py` with at least 5 underwriting rules
- [ ] Rules loaded into memory on first run if no rules exist
- [ ] Rules viewable via `GET /rules` on the underwriting API

---

### US-35 — Loan Processing APIs
**Type:** User Story | **Epic:** EP-5 | **Sprint:** 3 | **Points:** 3 | **Labels:** `story`, `loan`, `api`

#### User Story
**As a** developer,
**I want** the Loan Processing FastAPI backend with all endpoints matching the claims/underwriting contract,
**so that** the loan agent integrates consistently with the frontend and test suite.

#### Acceptance Criteria
- [ ] `agents/loan/apis/` has all files matching claims structure
- [ ] Runs on port `8003` (configurable via `LOAN_API_PORT`)
- [ ] All endpoints implemented — same contract as claims
- [ ] Storage path: `storage/loan/{case_id}/`
- [ ] Domain label: `"agent": "loan"` in ping response

---

### US-36 — Loan Processing Agentic Workflow
**Type:** User Story | **Epic:** EP-5 | **Sprint:** 3 | **Points:** 3 | **Labels:** `story`, `loan`, `agentic`

#### User Story
**As a** developer,
**I want** the Loan Processing Strands agent set up following the same pattern as Claims,
**so that** it is fully functional with role-aware prompts, memory, and approval flow.

#### Acceptance Criteria
- [ ] `agents/loan/agentic/` has all files: `agent.py`, `tools.py`, `state.py`, `prompts.py`, `approval_hook.py`, `memory_manager.py`
- [ ] Memory backend keyed to `"loan"` — isolated from claims and underwriting memory
- [ ] Approval hook and dual-entry pattern identical to claims
- [ ] Default rules relevant to loan processing loaded on first run

---

### US-37 — Loan Domain Tools
**Type:** User Story | **Epic:** EP-5 | **Sprint:** 3 | **Points:** 3 | **Labels:** `story`, `loan`, `agentic`

#### User Story
**As the** loan processing agent,
**I want** domain-specific tools for credit and loan evaluation,
**so that** I can assess loan applications with loan-relevant criteria.

#### Acceptance Criteria
- [ ] `@tool read_loan_application(case_id)` — reads application docs from `input/`
- [ ] `@tool credit_assessment(application_data: dict) -> dict` — evaluates creditworthiness (rule-based + LLM)
- [ ] `@tool calculate_loan_eligibility(application_data: dict) -> dict` — applies loan rules to determine eligibility and amount
- [ ] `@tool read_case_analysis(case_id)` and `@tool search_cases(query)` (same pattern as claims)
- [ ] Results written to `storage/loan/{case_id}/analysis/`

---

### US-38 — Loan Default Rules
**Type:** User Story | **Epic:** EP-5 | **Sprint:** 3 | **Points:** 1 | **Labels:** `story`, `loan`, `agentic`

#### User Story
**As an** admin,
**I want** the Loan agent to start with sensible default operating rules,
**so that** it evaluates applications correctly without requiring manual rule setup.

#### Acceptance Criteria
- [ ] `DEFAULT_RULES` list in `agents/loan/agentic/prompts.py` with at least 5 loan processing rules
- [ ] Rules loaded into memory on first run if no rules exist
- [ ] Rules viewable via `GET /rules` on the loan API

---

### US-39 — Nginx Configuration
**Type:** User Story | **Epic:** EP-6 | **Sprint:** 4 | **Points:** 2 | **Labels:** `story`, `deployment`

#### User Story
**As a** developer,
**I want** an Nginx config that serves the React build and reverse-proxies the three agent APIs,
**so that** Neural is accessible on a single EC2 public IP with no CORS issues.

#### Acceptance Criteria
- [ ] Nginx serves React build from `/var/www/neural/`
- [ ] `/api/claims/` proxied to `localhost:8001`
- [ ] `/api/underwriting/` proxied to `localhost:8002`
- [ ] `/api/loan/` proxied to `localhost:8003`
- [ ] SSE proxying configured: `proxy_buffering off`, `X-Accel-Buffering no`
- [ ] Config file at `infrastructure/nginx/neural.conf`

---

### US-40 — systemd Service Files
**Type:** User Story | **Epic:** EP-6 | **Sprint:** 4 | **Points:** 2 | **Labels:** `story`, `deployment`

#### User Story
**As a** developer,
**I want** systemd service files for each uvicorn process,
**so that** all three agent APIs start automatically on boot and restart on failure.

#### Acceptance Criteria
- [ ] Three service files: `neural-claims.service`, `neural-underwriting.service`, `neural-loan.service`
- [ ] Each starts uvicorn with `--workers 1` and the correct port
- [ ] `Restart=on-failure`, `RestartSec=5`
- [ ] `.env` file loaded via `EnvironmentFile=`
- [ ] Service files at `infrastructure/systemd/`

---

### US-41 — EC2 Deployment Script
**Type:** User Story | **Epic:** EP-6 | **Sprint:** 4 | **Points:** 2 | **Labels:** `story`, `deployment`

#### User Story
**As a** developer,
**I want** a shell script that deploys Neural to a fresh EC2 instance,
**so that** the full deployment can be reproduced in under 15 minutes.

#### Acceptance Criteria
- [ ] `infrastructure/deploy-ec2.sh` installs: Python 3.11, Node.js 20, Nginx
- [ ] Installs Python dependencies for each agent API
- [ ] Builds React frontend (`npm run build`) and copies to Nginx root
- [ ] Copies systemd service files and enables them
- [ ] Copies `.env` from local if present, otherwise prompts
- [ ] Prints the public IP and URLs at the end

---

### US-42 — EC2 Environment Configuration
**Type:** User Story | **Epic:** EP-6 | **Sprint:** 4 | **Points:** 1 | **Labels:** `story`, `deployment`

#### User Story
**As a** developer,
**I want** the EC2 environment variables documented and verified,
**so that** Neural runs correctly on EC2 with no code changes from local.

#### Acceptance Criteria
- [ ] `.env.ec2.example` at project root with EC2-specific values
- [ ] `STORAGE_PATH=/opt/neural/storage`, `MEMORY_BACKEND=local`
- [ ] `BEDROCK_MODEL_ID` and `AWS_REGION` set
- [ ] `VITE_*_API_URL` variables point to EC2 Nginx proxy paths
- [ ] All env var differences from local documented in `docs/deployment.md`

---

### US-43 — Dockerize Agentic Workflows
**Type:** User Story | **Epic:** EP-7 | **Sprint:** 5 | **Labels:** `story`, `agentcore`, `future`

#### User Story
**As a** developer,
**I want** each agentic workflow packaged as a Docker container,
**so that** it can be deployed to AgentCore Runtime without changing application code.

#### Acceptance Criteria
- [ ] `Dockerfile` in each `agents/{agent}/agentic/` following AgentCore pattern (ARM64, port 9000)
- [ ] Entrypoint: `uvicorn main:app --host 0.0.0.0 --port 9000`
- [ ] Health check endpoint at `GET /health`
- [ ] Images built and pushed to ECR via `deploy.sh` script
- [ ] Local `docker-compose.yml` at project root for running all containers together

---

### US-44 — AgentCore Memory Backend Swap
**Type:** User Story | **Epic:** EP-7 | **Sprint:** 5 | **Labels:** `story`, `agentcore`, `future`

#### User Story
**As a** developer,
**I want** to switch from `LocalMemoryStore` to `AgentCoreMemorySessionManager` by changing one env var,
**so that** all three agents get persistent LTM and rule storage on AgentCore with no code change.

#### Acceptance Criteria
- [ ] `create_memory_backend(agent_name)` factory handles `MEMORY_BACKEND=agentcore`
- [ ] `AgentCoreMemorySessionManager` configured with `AGENTCORE_MEMORY_ID` env var
- [ ] Rules migrated from `LocalMemoryStore` to AgentCore Memory on first AgentCore startup
- [ ] Conversation history managed by AgentCore Memory (replaces file-based chat history)

---

### US-45 — AgentCore CDK Runtime Stack
**Type:** User Story | **Epic:** EP-7 | **Sprint:** 5 | **Labels:** `story`, `agentcore`, `future`

#### User Story
**As a** developer,
**I want** CDK TypeScript stacks that provision AgentCore Runtime for each agent workflow,
**so that** deployment to AgentCore is reproducible and infrastructure-as-code.

#### Acceptance Criteria
- [ ] One CDK stack per agent in `infrastructure/cdk/stacks/`
- [ ] Each stack: ECR repo, IAM execution role, AgentCore Runtime resource, AgentCore Memory resource
- [ ] IAM role grants: `bedrock:InvokeModel`, `logs:*`, `s3:*` on storage bucket
- [ ] `cdk deploy` deploys all three stacks
- [ ] Stack outputs include AgentCore endpoint URLs for use in API service `.env`

---

### US-46 — AgentCore MCP Gateway for Lambda Tools
**Type:** User Story | **Epic:** EP-7 | **Sprint:** 5 | **Labels:** `story`, `agentcore`, `future`

#### User Story
**As a** developer,
**I want** domain-specific Lambda functions exposed via AgentCore MCP Gateway,
**so that** agents can call external tools (policy lookup, fraud check, credit bureau) with SigV4 security.

#### Acceptance Criteria
- [ ] Lambda functions created for: `policy-lookup`, `fraud-check`, `compliance-check`, `credit-bureau`
- [ ] Each Lambda follows the pattern from reference code: routes by `bedrockAgentCoreToolName`
- [ ] MCP Gateway CDK stack registers all Lambda tools with `AWS_IAM` auth
- [ ] Agents updated to use `MCPClient` connecting to Gateway URL from Parameter Store
- [ ] Gateway URL stored in SSM Parameter Store, read at agent startup

---

## Labels Reference

| Label | Used for |
|---|---|
| `epic` | Epic-level issues |
| `story` | User story issues |
| `foundation` | Project setup, config, shared infra |
| `frontend` | React UI work |
| `claims` | Claims agent (API or agentic) |
| `underwriting` | Underwriting agent |
| `loan` | Loan agent |
| `api` | FastAPI backend work |
| `agentic` | Strands workflow work |
| `memory` | Memory backend / rules storage |
| `deployment` | EC2 / Nginx / systemd |
| `agentcore` | AgentCore migration |
| `future` | Sprint 5 — not in current scope |

## Milestones

| Milestone | Issues |
|---|---|
| Sprint 1 — Foundation + Frontend | EP-1, EP-2, US-01–US-15 |
| Sprint 2 — Claims Agent | EP-3, US-16–US-30 |
| Sprint 3 — Underwriting + Loan | EP-4, EP-5, US-31–US-38 |
| Sprint 4 — Integration + EC2 | EP-6, US-39–US-42 |
| Sprint 5 — AgentCore (future) | EP-7, US-43–US-46 |
