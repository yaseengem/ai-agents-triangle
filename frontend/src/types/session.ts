export type WorkflowStatus =
  | 'INITIATED'
  | 'PROCESSING'
  | 'PENDING_HUMAN_APPROVAL'
  | 'APPROVED'
  | 'REJECTED'
  | 'CLOSING'
  | 'CLOSED'
  | 'EXPIRED'
  | 'ERROR'

export interface ToolEvent {
  tool: string
  status: 'running' | 'done' | 'error'
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  isStreaming?: boolean
  toolEvents?: ToolEvent[]
}

export interface FileRef {
  file_ref: string
  case_id: string
  session_id: string
}

export interface RuleSet {
  rules: string[]
}

export interface SessionStatus {
  session_id: string
  case_id: string
  status: WorkflowStatus
  created_at: string
  updated_at: string
  data?: Record<string, unknown>
}

export interface SessionSummary {
  session_id: string
  case_id: string
  status: WorkflowStatus
  created_at: string
  updated_at: string
}
