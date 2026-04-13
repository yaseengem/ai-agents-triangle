/**
 * AdminChatPage — administrator view with chat + rules sidebar.
 *
 * Route: /agents/:agentId/admin
 *
 * Two-column layout:
 * - Left: chat with role='admin' (can create/modify sessions too)
 * - Right: RulePanelSidebar (refreshed after each done event that mentions rules)
 *
 * The admin can chat without needing to upload a file first.
 * A default "admin session" is created on mount.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import type { AgentId } from '@/types/agent'
import { getAgent } from '@/config/agents'
import { getApiClient } from '@/api/client'
import { useChat } from '@/hooks/useChat'
import { MessageBubble } from '@/components/chat/MessageBubble'
import { ChatInputArea } from '@/components/chat/ChatInputArea'
import { RulePanelSidebar } from '@/components/admin/RulePanelSidebar'

const RULE_KEYWORDS = ['rule', 'added', 'removed', 'updated', 'policy']

function mentionsRules(content: string): boolean {
  const lower = content.toLowerCase()
  return RULE_KEYWORDS.some((kw) => lower.includes(kw))
}

export function AdminChatPage() {
  const { agentId } = useParams<{ agentId: string }>()
  const agent = agentId ? getAgent(agentId as AgentId) : null

  const [sessionId, setSessionId] = useState<string | null>(null)
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [sessionError, setSessionError] = useState<string | null>(null)
  const prevMessageCountRef = useRef(0)

  // Create an admin session on mount
  useEffect(() => {
    if (!agentId) return
    getApiClient(agentId as AgentId)
      .postProcess({ case_id: `admin-${Date.now()}`, payload: {}, user_id: 'admin' })
      .then((res) => setSessionId(res.session_id))
      .catch(() => setSessionError('Failed to start admin session'))
  }, [agentId])

  const { messages, isStreaming, error: chatError, sendMessage } = useChat(
    agentId as AgentId,
    sessionId,
    'admin',
  )

  const messagesEndRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // After streaming ends, check if the new assistant message mentions rules
  useEffect(() => {
    if (isStreaming) return
    if (messages.length <= prevMessageCountRef.current) return
    prevMessageCountRef.current = messages.length
    const last = messages[messages.length - 1]
    if (last?.role === 'assistant' && mentionsRules(last.content)) {
      setRefreshTrigger((n) => n + 1)
    }
  }, [isStreaming, messages])

  if (!agent) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <p className="text-gray-500">Agent not found.</p>
      </div>
    )
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Chat column */}
      <div className="flex-1 flex flex-col min-w-0 p-4 sm:p-6 gap-4">
        <h2 className="text-lg font-semibold text-gray-900 flex-shrink-0">
          {agent.name} — Admin
        </h2>

        {(sessionError || chatError) && (
          <p className="text-xs text-red-600 text-center flex-shrink-0">
            {sessionError ?? chatError}
          </p>
        )}

        {!sessionId && !sessionError && (
          <p className="text-xs text-gray-400 text-center py-4">Starting admin session…</p>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-4 min-h-0">
          {sessionId && messages.length === 0 && (
            <p className="text-center text-sm text-gray-400 py-8">
              Admin session ready. You can manage rules, review cases, or ask anything.
            </p>
          )}
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>

        {sessionId && (
          <ChatInputArea
            onSend={sendMessage}
            isStreaming={isStreaming}
            placeholder="Manage rules or query cases…"
          />
        )}
      </div>

      {/* Rules sidebar */}
      <RulePanelSidebar agentId={agentId as AgentId} refreshTrigger={refreshTrigger} />
    </div>
  )
}
