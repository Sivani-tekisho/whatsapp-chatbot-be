import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  MessageSquare,
  BookOpen,
  Settings,
  Moon,
  Sun,
  Bot,
} from 'lucide-react'
import { useTheme } from '../hooks/useTheme'

const links = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/conversations', icon: MessageSquare, label: 'Conversations' },
  { to: '/knowledge', icon: BookOpen, label: 'Knowledge Base' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  const { dark, toggle } = useTheme()

  return (
    <aside className="flex h-screen w-56 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-4 dark:border-slate-800">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500 text-white">
          <Bot size={18} />
        </div>
        <div>
          <p className="text-sm font-semibold">WhatsApp AI</p>
          <p className="text-xs text-slate-500">Admin Console</p>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 p-2">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
                isActive
                  ? 'bg-brand-50 text-brand-700 dark:bg-brand-500/10 dark:text-brand-500'
                  : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-200 p-2 dark:border-slate-800">
        <button
          type="button"
          onClick={toggle}
          className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
        >
          {dark ? <Sun size={16} /> : <Moon size={16} />}
          {dark ? 'Light mode' : 'Dark mode'}
        </button>
      </div>
    </aside>
  )
}
