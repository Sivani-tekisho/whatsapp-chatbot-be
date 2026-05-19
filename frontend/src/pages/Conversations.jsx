import { useEffect, useState } from 'react'
import { Search, RefreshCw } from 'lucide-react'
import ChatWindow from '../components/ChatWindow'
import { getConversations, getConversation, sendReply } from '../services/api'

export default function Conversations() {
  const [list, setList] = useState([])
  const [selected, setSelected] = useState(null)
  const [messages, setMessages] = useState([])
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [loadingList, setLoadingList] = useState(true)
  const [loadingChat, setLoadingChat] = useState(false)
  const [sending, setSending] = useState(false)

  const loadList = () => {
    setLoadingList(true)
    getConversations({ search: search || undefined, status: status || undefined })
      .then((res) => setList(res.data.items))
      .catch(console.error)
      .finally(() => setLoadingList(false))
  }

  useEffect(() => {
    loadList()
  }, [search, status])

  const loadChat = (conv) => {
    setLoadingChat(true)
    getConversation(conv.id)
      .then((res) => setMessages(res.data.messages))
      .catch(console.error)
      .finally(() => setLoadingChat(false))
  }

  const selectConversation = (conv) => {
    setSelected(conv)
    loadChat(conv)
  }

  const handleSend = async (text) => {
    if (!selected) return
    setSending(true)
    try {
      await sendReply(selected.id, text)
      await loadChat(selected)
      loadList()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to send message')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex h-full flex-col p-4">
      <header className="mb-3 flex items-start justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">Conversations</h1>
          <p className="mt-1 text-xs text-slate-500">
          </p>
        </div>
        <button
          type="button"
          onClick={loadList}
          className="flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
        >
          <RefreshCw size={12} />
          Refresh
        </button>
      </header>

      <div className="flex min-h-0 flex-1 gap-3">
        <div className="flex w-72 flex-col rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          <div className="space-y-2 border-b border-slate-200 p-2 dark:border-slate-800">
            <div className="relative">
              <Search
                size={14}
                className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search phone..."
                className="w-full rounded-md border border-slate-200 bg-transparent py-1.5 pl-7 pr-2 text-sm dark:border-slate-700"
              />
            </div>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full rounded-md border border-slate-200 bg-transparent px-2 py-1.5 text-sm dark:border-slate-700"
            >
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>

          <div className="flex-1 overflow-y-auto">
            {loadingList ? (
              <p className="p-3 text-xs text-slate-500">Loading...</p>
            ) : list.length === 0 ? (
              <p className="p-3 text-xs text-slate-500">No conversations yet</p>
            ) : (
              list.map((conv) => (
                <button
                  key={conv.id}
                  type="button"
                  onClick={() => selectConversation(conv)}
                  className={`w-full border-b border-slate-100 px-3 py-2 text-left text-sm hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50 ${
                    selected?.id === conv.id ? 'bg-brand-50 dark:bg-brand-500/10' : ''
                  }`}
                >
                  <p className="font-medium">+{conv.phone}</p>
                  <p className="truncate text-xs text-slate-500">
                    {conv.last_message || 'No messages'}
                  </p>
                  <span className="text-[10px] uppercase text-slate-400">
                    {conv.status} · {conv.message_count} msgs
                  </span>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="flex flex-1 flex-col rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          {selected && (
            <div className="border-b border-slate-200 px-4 py-2 dark:border-slate-800">
              <p className="text-sm font-medium">+{selected.phone}</p>
            </div>
          )}
          <ChatWindow
            messages={messages}
            loading={loadingChat}
            conversationId={selected?.id}
            onSend={handleSend}
            sending={sending}
          />
        </div>
      </div>
    </div>
  )
}
