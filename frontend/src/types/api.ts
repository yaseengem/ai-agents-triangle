import type { Role } from './agent'
import type { RuleSet, SessionStatus, SessionSummary, FileRef } from './session'

export type { RuleSet, SessionStatus, SessionSummary, FileRef }

// ── requests ──────────────────────────────────────────────────────────────────

export interface PostProcessRequest {
  case_id: string
  payload: Record<string, unknown>
  user_id: string
}

export interface PostChatRequest {
  message: string
  role: Role
  user_id: string
  file_ref?: string
}

export interface ApproveRequest {
  notes?: string
}

export interface RejectRequest {
  reason: string
}

// ── responses ─────────────────────────────────────────────────────────────────

export interface ProcessResponse {
  session_id: string
  case_id: string
  status: string
}

// ── SSE event types ───────────────────────────────────────────────────────────

export interface SSETextDelta {
  type: 'text-delta'
  content: string
}

export interface SSEToolStatus {
  type: 'tool-status'
  tool: string
  status: 'running' | 'done' | 'error'
}

export interface SSEDone {
  type: 'done'
}

export interface SSEError {
  type: 'error'
  message: string
}

export type SSEEvent = SSETextDelta | SSEToolStatus | SSEDone | SSEError

// ── API client interface ──────────────────────────────────────────────────────

export interface ApiClient {
  postProcess(request: PostProcessRequest): Promise<ProcessResponse>
  postUpload(file: File, caseId?: string, userId?: string): Promise<FileRef>
  postChat(
    sessionId: string,
    request: PostChatRequest,
    onEvent: (event: SSEEvent) => void,
  ): Promise<void>
  getStatus(sessionId: string): Promise<SessionStatus>
  postApprove(sessionId: string, request: ApproveRequest): Promise<void>
  postReject(sessionId: string, request: RejectRequest): Promise<void>
  getRules(): Promise<RuleSet>
  postRules(ruleset: RuleSet): Promise<void>
  getSessions(filters?: {
    status?: string
    role?: string
    user_id?: string
  }): Promise<SessionSummary[]>
}
