# Iteration 1 — Implementation Plan

**Epics:** EP-1 (Project Foundation) · EP-2 (Neural Frontend) · EP-3 (Claims Processing Agent)  
**Sprint Goal:** Fully functional frontend with mock APIs + complete Claims agent end-to-end  
**Duration:** 4 weeks (Sprint 1 = EP-1 + EP-2 · Sprint 2 = EP-3)

---

## Context

Neural has complete architecture documentation and user story planning but zero source code. This iteration delivers the first two sprints: a React frontend that works entirely on mock APIs (so it can be demoed before backend is ready), and a fully wired Claims Processing agent with FastAPI backend, Strands agentic workflow, human-in-the-loop approval, and file system storage.

---

## Dependency Graph

```
EP-1: memory_backend.py  ──────────────────────────────────────────┐
EP-1: .gitignore · README.md · .env.example · storage stubs        │
                                                                    ↓
EP-3 agentic:  prompts.py → memory_manager.py → approval_hook.py → tools.py → agent.py
EP-3 api:      schemas.py → service.py → routes.py → main.py

EP-2: types/ → config/ → api/mock.ts → api/client.ts
      → hooks/ (parallel) → components/ (parallel) → pages/ → App.tsx
```

EP-2 and EP-3 can be built in parallel. The only shared contract is the API shape —
defined on Day 1 by `schemas.py` (backend) and `types/api.ts` (frontend).

---

## Epic 1 — Project Foundation (US-01 → US-04)

### Files

| File | US | Purpose |
|---|---|---|
| `.gitignore` | US-01 | Ignore `node_modules/`, `__pycache__/`, `.env`, `storage/` |
| `README.md` | US-01 | Project overview, prerequisites, quickstart, env var table |
| `requirements.txt` | US-01 | Single root Python requirements file for the whole project |
| `.env.example` | US-04 | Backend env vars template with inline comments |
| `frontend/.env.example` | US-04 | Frontend env vars template |
| `storage/claims/.gitkeep` | US-02 | Claims storage stub |
| `storage/underwriting/.gitkeep` | US-02 | Underwriting storage stub |
| `storage/loan/.gitkeep` | US-02 | Loan storage stub |
| `storage/memory/.gitkeep` | US-02 | Memory backend storage stub |
| `storage/memory_backend.py` | US-03 | `LocalMemoryStore` + factory — **critical shared dep** |
| `scripts/start.sh` | US-01 | Start all services (3 FastAPI + Vite) in the background |
| `scripts/stop.sh` | US-01 | Stop all running Neural services |
| `scripts/restart.sh` | US-01 | Stop then start all services |

### `requirements.txt` (root — single file for the whole project)

```
fastapi==0.116.1
uvicorn[standard]==0.35.0
python-multipart==0.0.9
pydantic>=2.0
boto3>=1.40.1
strands-agents
pypdf>=4.0.0
Pillow>=10.0.0
filelock>=3.12.0
python-dotenv>=1.0.0
```

Install once from the repo root: `pip install -r requirements.txt`

### `.env.example` Variables

```
AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
STORAGE_PATH=./storage          # /opt/ai-agents/storage on EC2
MEMORY_BACKEND=local            # "local" | "agentcore" (future EP-7)
CLAIMS_API_PORT=8001
UNDERWRITING_API_PORT=8002
LOAN_API_PORT=8003
APPROVAL_TIMEOUT_SECONDS=86400
```

### `scripts/` — Service Management

All three scripts source `.env` from the repo root so ports are read from environment.

**`scripts/start.sh`**
- Sources `.env`
- Activates `.venv` if present
- Starts each FastAPI service with `uvicorn` in the background, writing PID to `scripts/pids/{service}.pid` and log to `logs/{service}.log`
- Starts `npm run dev` (from `frontend/`) in the background
- Prints the URL of each service when done

**`scripts/stop.sh`**
- Reads PIDs from `scripts/pids/*.pid`
- Kills each process gracefully (`kill -TERM`), falls back to `kill -KILL` after 5 s
- Removes PID files
- Stops the Vite dev server by PID

**`scripts/restart.sh`**
- Calls `stop.sh` then `start.sh`

### `storage/memory_backend.py` — Design

```python
class LocalMemoryStore:
    # path: {STORAGE_PATH}/memory/{agent_name}_memory.json
    # get(key) → Any | None
    # set(key, value)           atomic: .tmp → os.replace()
    # delete(key)
    # list_keys() → list[str]
    # Thread-safe: FileLock (cross-process) + threading.RLock (in-process)

class StubAgentCoreMemory:
    # All methods raise NotImplementedError with migration instructions

def create_memory_backend(agent_name) → LocalMemoryStore | StubAgentCoreMemory:
    # Reads MEMORY_BACKEND env var
    # "local" (default) → LocalMemoryStore
    # "agentcore"       → StubAgentCoreMemory
```

### Storage Directory Layout (per case)

```
storage/{domain}/{case_id}/
  input/                      ← uploaded files (POST /upload)
  analysis/
    document_extract.json     ← document_parser tool output
    analysis_result.json      ← agent analysis output
  decisions/
    decision_log.json
    approval_record.json
  chat_history/
    user_chat.json
    support_chat.json
    admin_chat.json
  status.json                 ← canonical WorkflowStatus
  interrupt.json              ← written by ApprovalHook on pause
  closure_summary.json
```

`STORAGE_PATH` env var controls the root. Default `./storage` locally; `/opt/ai-agents/storage` on EC2.

---

## Epic 2 — Neural Frontend (US-05 → US-15)

### Bootstrap

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install react-router-dom react-markdown tailwindcss autoprefixer postcss @tailwindcss/typography
```

### Configuration Files

| File | Key Details |
|---|---|
| `frontend/vite.config.ts` | Path alias `@/` → `./src/`; dev proxy to `:8001-8003` |
| `frontend/tailwind.config.ts` | `typography` plugin; content `./src/**/*.{ts,tsx}` |
| `frontend/tsconfig.json` | Strict mode; `baseUrl: "."`, paths alias `@/*` |

---

### Layer 1 — TypeScript Types (build first; everything depends on these)

**`src/types/agent.ts`**
```ts
export type AgentId = 'claims' | 'underwriting' | 'loan';
export type Role    = 'user' | 'support' | 'admin';
export interface AgentConfig {
  id: AgentId; name: string; description: string;
  color: string; icon: string; apiUrl: string;
}
```

**`src/types/session.ts`**
```ts
export type WorkflowStatus =
  'INITIATED' | 'PROCESSING' | 'PENDING_HUMAN_APPROVAL' |
  'APPROVED'  | 'REJECTED'   | 'CLOSING' | 'CLOSED' | 'EXPIRED';

export interface Message {
  id: string; role: 'user' | 'assistant' | 'system';
  content: string; timestamp: string;
  isStreaming?: boolean; toolEvents?: ToolEvent[];
}
export interface ToolEvent  { tool: string; status: 'running' | 'done' | 'error'; }
export interface FileRef    { file_ref: string; case_id: string; session_id: string; }
export interface RuleSet    { rules: string[]; }
export interface SessionStatus {
  session_id: string; case_id: string; status: WorkflowStatus;
  created_at: string; updated_at: string; data?: Record<string, unknown>;
}
```

**`src/types/api.ts`** — request/response shapes for every endpoint  
(`PostChatRequest`, `PostProcessRequest`, `ApproveRequest`, `RejectRequest`, `SessionSummary`, `FileUploadResponse`)

---

### Layer 2 — Agent Registry & API Client

**`src/config/agents.ts`**  
Static registry of 3 agents. `getAgent(id: AgentId)` helper.

| id | name | color | icon | port |
|---|---|---|---|---|
| `claims` | Claims Processing | blue | 📋 | 8001 |
| `underwriting` | Underwriting | green | 📊 | 8002 |
| `loan` | Loan Processing | purple | 💰 | 8003 |

**`src/api/client.ts`**  
`getApiClient(agentId) → ApiClient`  
Reads `VITE_USE_MOCK_API`. Real SSE: `fetch()` + `ReadableStream.getReader()`, parse `text/event-stream` line-by-line.

**`src/api/mock.ts`** (US-14 — build right after `client.ts`)

All 9 required mock functions (one per API endpoint):

| Function | Behaviour |
|---|---|
| `mockPostProcess` | Returns `{session_id, case_id, status: "INITIATED"}` after 200 ms |
| `mockPostUpload` | 1 s delay; returns `{file_ref: "mock-ref-001", case_id: "CLAIM-001", session_id: "mock-session-001"}` |
| `mockPostChat` | `setInterval` 50 ms; emits `text-delta` word-by-word, then `tool-status`, then `done` |
| `mockGetStatus` | Module-level `Map<sessionId, WorkflowStatus>`; starts `PROCESSING`, transitions to `PENDING_HUMAN_APPROVAL` after 5 s |
| `mockPostApprove` / `mockPostReject` | Advance mock status to `APPROVED` / `REJECTED` |
| `mockGetRules` | Returns static 4-rule `RuleSet` |
| `mockPostRules` | Accepts new rules array, stores in module-level variable, returns `{status: "ok"}` |
| `mockGetSessions` | Returns a static list of 3 session summaries |

All mock functions are agent-aware: they accept `agentId` and return mock data labelled for that agent (e.g. `case_id: "CLAIM-001"` for claims, `"UW-001"` for underwriting, `"LOAN-001"` for loan). The `VITE_USE_MOCK_API=true` toggle applies to all three agents identically.

---

### Layer 3 — Custom Hooks (build in parallel after `client.ts`)

**`src/hooks/useChat.ts`** (US-10)  
`useChat(agentId, sessionId, role)` → `{sendMessage, messages, isStreaming, error}`
- `sendMessage` adds user message → calls `apiClient.postChat` → opens SSE stream
- Event routing: `text-delta` → append to last assistant message; `tool-status` → push `ToolEvent`; `done` → `isStreaming = false`; `error` → set error state
- Single retry on network error via `retryCount` ref

**`src/hooks/useAgentStatus.ts`** (US-11)  
`useAgentStatus(agentId, sessionId)` → `{status, lastUpdated, error}`
- Polls `GET /status/{sessionId}` every 5 s
- Stops when `status` is `CLOSED | REJECTED | EXPIRED`
- Clears interval in `useEffect` cleanup

**`src/hooks/useFileUpload.ts`** (US-12)  
`useFileUpload(agentId)` → `{uploadFile, fileRef, isUploading, uploadProgress, error}`
- Uses `XMLHttpRequest` for `xhr.upload.onprogress` (0–100 %)
- Sends `FormData` with `file` + optional `case_id`

---

### Layer 4 — Shared Components (build in parallel after types)

| File | US | Key Details |
|---|---|---|
| `components/chat/MessageBubble.tsx` | US-13 | User = right blue bubble; assistant = left, `react-markdown` + `prose`; inline `ToolExecutionBadge` per tool event |
| `components/chat/StreamingText.tsx` | US-13 | Blinking `▋` cursor via `animate-pulse` when `isStreaming=true` |
| `components/chat/ToolExecutionBadge.tsx` | US-13 | Pill: spinner=running · ✓=done · ✗=error; maps tool names to human labels |
| `components/chat/ChatInputArea.tsx` | US-13 | Grows to 5 rows; Enter=submit · Shift+Enter=newline; disabled while streaming |
| `components/chat/FileUpload.tsx` | US-13 | Drag-drop zone + browse; accepts `.pdf .png .jpg .jpeg .docx`; progress bar |
| `components/ui/StatusBadge.tsx` | US-13 | Colour-coded pill per workflow state |
| `components/ui/ApprovalBanner.tsx` | US-13 | Amber banner; Approve (green) + Reject (red); calls `postApprove` / `postReject` |
| `components/admin/RulePanelSidebar.tsx` | US-09 | `w-72` right sidebar; fetches `GET /rules` on mount + refresh-trigger prop |
| `components/agent/AgentCard.tsx` | US-05 | Clickable card; navigates to `/agents/{id}` |
| `components/layout/AppShell.tsx` | US-15 | Header "Neural" + breadcrumb nav from route |
| `components/support/CaseSearch.tsx` | US-08 | Input + "Load Case"; validates via `getStatus`; fires `onSessionLoad` |

**`StatusBadge` colour map:**

| Status | Style |
|---|---|
| `INITIATED` | gray |
| `PROCESSING` | blue + spinner |
| `PENDING_HUMAN_APPROVAL` | amber + pulse |
| `APPROVED` / `CLOSED` | green |
| `REJECTED` / `EXPIRED` | red |

---

### Layer 5 — Pages (build after components)

| File | Route | US | Key Details |
|---|---|---|---|
| `pages/AgentListPage.tsx` | `/` | US-05 | Responsive grid 1→2→3 cols; `document.title = "Neural"` |
| `pages/RoleSelectPage.tsx` | `/agents/:agentId` | US-06 | 3 role buttons + description; validates `agentId`; **Back button** → `/`; `document.title = "{AgentName}"` |
| `pages/UserChatPage.tsx` | `/agents/:agentId/user` | US-07 | FileUpload + StatusBadge + ApprovalBanner + chat; session init from `fileRef.session_id`; **Back button** → `/agents/:agentId`; `document.title = "{AgentName} — User"` |
| `pages/SupportChatPage.tsx` | `/agents/:agentId/support` | US-08 | CaseSearch top bar; no file upload; `role: 'support'`; **Back button** → `/agents/:agentId`; `document.title = "{AgentName} — Support"` |
| `pages/AdminChatPage.tsx` | `/agents/:agentId/admin` | US-09 | Two-column flex: chat + RulePanelSidebar; auto-refresh sidebar on rule-change response; **Back button** → `/agents/:agentId`; `document.title = "{AgentName} — Admin"` |
| `pages/NotFoundPage.tsx` | `*` | US-15 | 404 + "Go Home" |

Back button implementation: each chat page renders a `← Back` link (using React Router `<Link>`) in the `AppShell` breadcrumb row. The `AppShell` derives the back target from the current route — no prop drilling required.

### Layer 6 — Router

**`src/App.tsx`** — React Router v6; all routes wrapped in `<AppShell>`

```tsx
<BrowserRouter>
  <AppShell>
    <Routes>
      <Route path="/"                          element={<AgentListPage />} />
      <Route path="/agents/:agentId"           element={<RoleSelectPage />} />
      <Route path="/agents/:agentId/user"      element={<UserChatPage />} />
      <Route path="/agents/:agentId/support"   element={<SupportChatPage />} />
      <Route path="/agents/:agentId/admin"     element={<AdminChatPage />} />
      <Route path="*"                          element={<NotFoundPage />} />
    </Routes>
  </AppShell>
</BrowserRouter>
```

---

### EP-2 File Manifest (33 files)

```
frontend/
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── index.html                          ← generated by Vite scaffold
├── package.json                        ← generated by Vite scaffold
└── src/
    ├── main.tsx                        ← Vite entry point
    ├── App.tsx                         ← Router root
    ├── types/
    │   ├── agent.ts
    │   ├── session.ts
    │   └── api.ts
    ├── config/
    │   └── agents.ts
    ├── api/
    │   ├── client.ts
    │   └── mock.ts
    ├── hooks/
    │   ├── useChat.ts
    │   ├── useAgentStatus.ts
    │   └── useFileUpload.ts
    ├── components/
    │   ├── chat/
    │   │   ├── MessageBubble.tsx
    │   │   ├── StreamingText.tsx
    │   │   ├── ToolExecutionBadge.tsx
    │   │   ├── ChatInputArea.tsx
    │   │   └── FileUpload.tsx
    │   ├── ui/
    │   │   ├── StatusBadge.tsx
    │   │   └── ApprovalBanner.tsx
    │   ├── admin/
    │   │   └── RulePanelSidebar.tsx
    │   ├── agent/
    │   │   └── AgentCard.tsx
    │   ├── layout/
    │   │   └── AppShell.tsx
    │   └── support/
    │       └── CaseSearch.tsx
    └── pages/
        ├── AgentListPage.tsx
        ├── RoleSelectPage.tsx
        ├── UserChatPage.tsx
        ├── SupportChatPage.tsx
        ├── AdminChatPage.tsx
        └── NotFoundPage.tsx
```

---

## Epic 3 — Claims Processing Agent (US-16 → US-30)

### Build Sequence (strict order — each step depends on the previous)

```
schemas.py                          ← API contract (Day 1, shared with frontend)
prompts.py                          ← defines DEFAULT_RULES
memory_manager.py                   ← uses memory_backend + prompts
approval_hook.py                    ← asyncio pause/resume
tools.py                            ← @tool functions
agent.py                            ← integrates all agentic components
service.py                          ← bridges API ↔ agentic layer
routes.py                           ← FastAPI route handlers
main.py                             ← FastAPI app entry point
```

---

### `agents/claims/apis/schemas.py` (US-16)

Pydantic v2 models:

| Model | Fields |
|---|---|
| `ProcessRequest` | `case_id`, `payload: dict`, `user_id` |
| `ChatRequest` | `message`, `role: Literal['user','support','admin']`, `user_id` |
| `ApprovalRequest` | `notes: Optional[str]` |
| `RejectionRequest` | `reason: str` |
| `WorkflowStatus` | `session_id`, `case_id`, `status`, `created_at`, `updated_at`, `data: Optional[dict]` |
| `RuleSet` | `rules: list[str]` |
| `SessionSummary` | `session_id`, `case_id`, `status`, `created_at`, `updated_at` |
| `FileUploadResponse` | `file_ref`, `case_id`, `session_id` |

---

### `agents/claims/agentic/prompts.py` (US-25)

```python
SYSTEM_PROMPT        # Claims agent identity; never fabricate data
ROLE_INSTRUCTIONS    # dict: user / support / admin
RULES_TEMPLATE       # "Current operating rules:\n{rules}"
DEFAULT_RULES = [
    "Claims under $1,000 may be auto-approved if documentation is complete "
    "and there are no fraud indicators.",
    "Claims over $50,000 require supervisor review before approval.",
    "Medical claims require a physician's report in the uploaded documents.",
    "Claims submitted more than 90 days after the incident date must be flagged for review.",
    "Fraud indicators (inconsistent dates, duplicate claims, altered documents) "
    "trigger automatic escalation.",
]
```

---

### `agents/claims/agentic/memory_manager.py` (US-26)

```python
class ClaimsMemoryManager:
    def __init__(self):
        self._store = create_memory_backend("claims")
        self._seed_defaults()       # sets DEFAULT_RULES if key missing

    def get_rules() → list[str]
    def set_rules(rules: list[str])
    def add_rule(rule: str)         # appends if not duplicate
    def remove_rule(rule: str)      # removes by exact match

# Module-level singleton — instantiated once per process
_manager = ClaimsMemoryManager()
```

---

### `agents/claims/agentic/approval_hook.py` (US-29)

Module-level registries (safe because **single-worker uvicorn** — document in README):

```python
_approval_events: dict[str, asyncio.Event] = {}
_decisions:       dict[str, str]           = {}

class ApprovalHook:
    async def request_approval(session_id, case_id, summary) → str:
        # 1. Register asyncio.Event
        # 2. Write interrupt.json atomically
        # 3. Update status.json → PENDING_HUMAN_APPROVAL
        # 4. await asyncio.wait_for(event.wait(), APPROVAL_TIMEOUT_SECONDS)
        # 5a. Timeout → status → EXPIRED; return "expired"
        # 5b. Resume → return _decisions.pop(session_id)

    def resume(session_id, decision) → bool:
        # Sync-safe: event.set() may be called from any coroutine
        # Returns False if no waiting event found (session not pending)
```

`APPROVAL_TIMEOUT_SECONDS` from env var (default 86400).

---

### `agents/claims/agentic/tools.py` (US-27, US-28)

All functions decorated with `@tool` from `strands`.  
`case_id` validated against `r'^[a-zA-Z0-9_-]+$'` on every tool to prevent path traversal.

| Tool | Input | Output | Writes |
|---|---|---|---|
| `document_parser(file_ref)` | `"{case_id}/{filename}"` | `{document_type, raw_text, extracted_fields}` | `analysis/document_extract.json` |
| `read_case_status(case_id)` | case_id | `status.json` contents | — |
| `read_case_analysis(case_id)` | case_id | `analysis/analysis_result.json` | — |
| `read_decision_log(case_id)` | case_id | `decisions/decision_log.json` | — |
| `search_cases(query)` | free-text query | `list[{case_id, status, updated_at}]` max 20 | — |
| `write_analysis_result(case_id, analysis)` | dict | `"ok"` | `analysis/analysis_result.json` |
| `write_decision_log(case_id, decision)` | dict | `"ok"` | `decisions/decision_log.json` |

PDF extraction: `pypdf.PdfReader`. Images: Pillow dimensions + note (vision via Bedrock optional).  
All tools return error strings (not exceptions) for missing files.

---

### `agents/claims/agentic/agent.py` (US-24, US-25, US-30)

```python
# Module-level singletons
_memory_manager = ClaimsMemoryManager()
_approval_hook  = ApprovalHook(STORAGE_PATH)

def build_system_prompt(role: str) → str:
    # SYSTEM_PROMPT + ROLE_INSTRUCTIONS[role] + RULES_TEMPLATE.format(rules=...)

def create_agent(role: str) → Agent:
    # New Agent per request → captures current rules in system prompt
    # BedrockModel with adaptive retry (max 5 attempts)
    # All 7 tools registered

async def run_processing_workflow(session_id, case_id, payload):
    # status → PROCESSING
    # agent.invoke_async("Process this claim...")
    # write analysis artifacts
    # await _approval_hook.request_approval(...)   ← workflow suspends here
    # decision == "approved" → CLOSING → CLOSED
    # decision == "rejected" → REJECTED

async def run_chat(session_id, case_id, role, message) → AsyncGenerator[str, None]:
    # agent.stream_async(message)
    # Map Strands events → Neural SSE format:
    #   data: {"type": "text-delta", "content": "..."}
    #   data: {"type": "tool-status", "tool": "...", "status": "running|done"}
    #   data: {"type": "done"}
```

> If Strands does not natively persist conversation history across HTTP requests,
> `service.py` loads from `chat_history/{role}_chat.json` before each invocation
> and saves after — keeping agent.py clean of HTTP concerns.

---

### `agents/claims/apis/service.py` (US-17 → US-23)

```python
class ClaimsService:
    _sessions: dict[str, str] = {}   # session_id → case_id (falls back to storage scan)

    def create_session(case_id, payload, user_id) → dict
        # 400 if active session exists
        # UUID session_id
        # Create dirs: input/ analysis/ decisions/ chat_history/
        # Write status.json {status: INITIATED, ...}
        # asyncio.create_task(run_processing_workflow(...))
        # Return {session_id, case_id, status: "INITIATED"}

    def get_status(session_id) → dict | None
        # Resolve case_id from _sessions; fallback: scan storage/claims/*/status.json

    async def chat_stream(session_id, req) → AsyncGenerator
        # yield from run_chat(...)

    def record_decision(session_id, decision, notes) → bool
        # 400 if status != PENDING_HUMAN_APPROVAL
        # Write decisions/approval_record.json
        # _approval_hook.resume(session_id, decision)

    def get_rules() → list[str]
    def set_rules(rules)

    def list_sessions(status_filter, role_filter, user_id_filter) → list[dict]
        # Walk storage/claims/*/status.json; apply ?status= / ?role= / ?user_id= filters
        # Sort by updated_at desc
```

---

### `agents/claims/apis/routes.py` (US-16 → US-23)

`service = ClaimsService()` — module-level singleton

| Method | Path | Handler |
|---|---|---|
| GET | `/ping` | `{"status": "ok", "agent": "claims"}` |
| POST | `/process` | `service.create_session()` |
| POST | `/upload` | validate ≤ 20 MB, accept pdf/png/jpg/jpeg/docx; save to `input/`; `file_ref = "{case_id}/{filename}"` |
| POST | `/chat/{session_id}` | `StreamingResponse(service.chat_stream(...), media_type="text/event-stream")` · 404 if not found |
| GET | `/status/{session_id}` | read `status.json` · 404 if not found |
| POST | `/approve/{session_id}` | `service.record_decision(...)` · `400` if not `PENDING_HUMAN_APPROVAL` · `404` if session not found |
| POST | `/reject/{session_id}` | `service.record_decision(...)` · `400` if not `PENDING_HUMAN_APPROVAL` · `404` if session not found |
| GET | `/rules` | `RuleSet(rules=service.get_rules())` |
| POST | `/rules` | `service.set_rules(ruleset.rules)` |
| GET | `/sessions` | `service.list_sessions(status, role, user_id)` — supports `?status=`, `?role=`, `?user_id=` filters; sorted by `updated_at` desc |

---

### `agents/claims/apis/main.py` (US-16)

```python
app = FastAPI(title="Neural Claims API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
app.include_router(router)

if __name__ == "__main__":
    port = int(os.getenv("CLAIMS_API_PORT", "8001"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
    # ⚠️ Single worker only — asyncio.Event requires shared process memory
```

---

### EP-3 File Manifest (10 files)

```
agents/claims/
├── agentic/
│   ├── prompts.py
│   ├── memory_manager.py
│   ├── approval_hook.py
│   ├── tools.py
│   └── agent.py
└── apis/
    ├── schemas.py
    ├── service.py
    ├── routes.py
    └── main.py
```

> Dependencies are installed from the single root `requirements.txt` — no per-agent requirements files.

---

## Key Risks

| Risk | Mitigation |
|---|---|
| `asyncio.Event` breaks with multiple uvicorn workers | Single worker always; documented in README |
| Strands may not persist chat history across requests | `service.py` loads/saves `chat_history/{role}_chat.json` per request |
| SSE connection drops | Single retry in `useChat`; each `sendMessage` is a fresh HTTP request |
| `file_ref` format inconsistency | Standard `"{case_id}/{filename}"`; `document_parser` splits on first `/` |
| `_sessions` dict lost on restart | Fallback: scan `storage/claims/*/status.json` for session lookup |

---

## Verification Checklist

### EP-1
- [ ] `pip install -r requirements.txt` completes without errors
- [ ] `./scripts/start.sh` starts all services; `./scripts/stop.sh` stops them cleanly

### EP-2
- [ ] `VITE_USE_MOCK_API=true` in `frontend/.env`
- [ ] `./scripts/start.sh` → navigate to `http://localhost:5173`
- [ ] Walk: AgentListPage → RoleSelect → UserChatPage (upload, stream, ApprovalBanner) → SupportChatPage (case search) → AdminChatPage (rules sidebar)

### EP-3
- [ ] `./scripts/start.sh` → `curl localhost:8001/ping` → `{"status":"ok","agent":"claims"}`
- [ ] Set `VITE_USE_MOCK_API=false`; upload PDF via UserChatPage; verify `storage/claims/{case_id}/` created; SSE streams in browser; approve/reject changes `status.json`
