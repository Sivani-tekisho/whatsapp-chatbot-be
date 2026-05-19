import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Conversations from './pages/Conversations'
import KnowledgeBase from './pages/KnowledgeBase'
import Settings from './pages/Settings'

function Layout({ children }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  )
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/conversations" element={<Conversations />} />
        <Route path="/knowledge" element={<KnowledgeBase />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  )
}
