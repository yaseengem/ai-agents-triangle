/**
 * RulePanelSidebar — fixed right sidebar that shows + edits the agent's rules.
 *
 * Fetches GET /rules on mount and whenever `refreshTrigger` changes.
 * Supports adding and removing rules inline.
 */

import { useEffect, useState } from 'react'
import type { AgentId } from '@/types/agent'
import { getApiClient } from '@/api/client'

interface RulePanelSidebarProps {
  agentId: AgentId
  refreshTrigger?: number
}

export function RulePanelSidebar({ agentId, refreshTrigger }: RulePanelSidebarProps) {
  const [rules, setRules] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [newRule, setNewRule] = useState('')

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getApiClient(agentId).getRules()
      setRules(data.rules)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load rules')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId, refreshTrigger])

  const save = async (updated: string[]) => {
    setSaving(true)
    setError(null)
    try {
      await getApiClient(agentId).postRules({ rules: updated })
      setRules(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save rules')
    } finally {
      setSaving(false)
    }
  }

  const addRule = () => {
    const trimmed = newRule.trim()
    if (!trimmed || rules.includes(trimmed)) return
    save([...rules, trimmed])
    setNewRule('')
  }

  const removeRule = (index: number) => {
    save(rules.filter((_, i) => i !== index))
  }

  return (
    <aside className="w-72 flex-shrink-0 border-l border-gray-200 bg-white flex flex-col h-full">
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-900">Operating Rules</h2>
        <button
          onClick={load}
          disabled={loading}
          className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-40"
          aria-label="Refresh rules"
        >
          ↻
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {loading && (
          <p className="text-xs text-gray-400 text-center py-4">Loading…</p>
        )}

        {!loading && rules.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">No rules defined</p>
        )}

        {rules.map((rule, i) => (
          <div
            key={i}
            className="group flex items-start gap-2 rounded-lg bg-gray-50 px-3 py-2 text-xs text-gray-700"
          >
            <span className="flex-1 leading-relaxed">{rule}</span>
            <button
              onClick={() => removeRule(i)}
              disabled={saving}
              className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 flex-shrink-0 transition-opacity disabled:cursor-not-allowed"
              aria-label="Remove rule"
            >
              ✕
            </button>
          </div>
        ))}

        {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
      </div>

      {/* Add rule */}
      <div className="p-4 border-t border-gray-200 space-y-2">
        <textarea
          value={newRule}
          onChange={(e) => setNewRule(e.target.value)}
          placeholder="Add a new rule…"
          rows={2}
          className="w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-xs text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              addRule()
            }
          }}
        />
        <button
          onClick={addRule}
          disabled={saving || !newRule.trim()}
          className="w-full rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? 'Saving…' : 'Add Rule'}
        </button>
      </div>
    </aside>
  )
}
