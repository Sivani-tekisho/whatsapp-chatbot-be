import { useState } from 'react'
import { Send } from 'lucide-react'

export default function ChatWindow({
  messages,
  loading,
  conversationId,
  onSend,
  sending,
}) {
  const [draft, setDraft] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!draft.trim() || !conversationId || sending) return
    onSend(draft.trim())
    setDraft('')
  }

  if (!conversationId) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center p-4 text-center text-sm text-slate-500">
        <p>Select a conversation to view history and send a reply.</p>
        <p className="mt-2 text-xs">
          Incoming messages appear here after someone texts your business number on WhatsApp.
          Check the backend terminal for <code className="rounded bg-slate-200 px-1 dark:bg-slate-800">[WHATSAPP] INBOUND POST</code> logs.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-1 flex-col min-h-0">
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <p className="text-sm text-slate-500">Loading messages...</p>
        ) : !messages?.length ? (
          <p className="text-sm text-slate-500">No messages yet. Send a reply below.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {messages.map((msg) => {
              const isUser = msg.role === 'user'
              return (
                <div
                  key={msg.id}
                  className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                      isUser
                        ? 'bg-brand-500 text-white'
                        : 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100'
                    }`}
                  >
                    <p>{msg.message}</p>
                    {msg.timestamp && (
                      <p
                        className={`mt-1 text-[10px] ${
                          isUser ? 'text-brand-100' : 'text-slate-400'
                        }`}
                      >
                        {new Date(msg.timestamp).toLocaleString()}
                      </p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="flex gap-2 border-t border-slate-200 p-3 dark:border-slate-800"
      >
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Type a reply to send on WhatsApp..."
          className="flex-1 rounded-md border border-slate-200 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
          disabled={sending}
        />
        <button
          type="submit"
          disabled={sending || !draft.trim()}
          className="flex items-center gap-1 rounded-md bg-brand-600 px-3 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50"
        >
          <Send size={14} />
          {sending ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  )
}
