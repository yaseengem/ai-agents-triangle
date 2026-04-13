export type AgentId = 'claims' | 'underwriting' | 'loan'
export type Role = 'user' | 'support' | 'admin'

export interface AgentConfig {
  id: AgentId
  name: string
  description: string
  color: string   // Tailwind color name, e.g. "blue"
  icon: string    // emoji
  apiUrl: string
}
