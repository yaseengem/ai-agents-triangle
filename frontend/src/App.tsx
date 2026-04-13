/**
 * App — React Router v6 root with all routes wrapped in AppShell.
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { AgentListPage } from '@/pages/AgentListPage'
import { RoleSelectPage } from '@/pages/RoleSelectPage'
import { UserChatPage } from '@/pages/UserChatPage'
import { SupportChatPage } from '@/pages/SupportChatPage'
import { AdminChatPage } from '@/pages/AdminChatPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AppShell>
        <Routes>
          <Route path="/" element={<AgentListPage />} />
          <Route path="/agents/:agentId" element={<RoleSelectPage />} />
          <Route path="/agents/:agentId/user" element={<UserChatPage />} />
          <Route path="/agents/:agentId/support" element={<SupportChatPage />} />
          <Route path="/agents/:agentId/admin" element={<AdminChatPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  )
}
