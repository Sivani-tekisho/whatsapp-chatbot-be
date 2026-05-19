import { useEffect, useState } from 'react'
import { MessageSquare, Users, CheckCircle, Clock } from 'lucide-react'
import MetricsCard from '../components/MetricsCard'
import { getMetrics } from '../services/api'

export default function Dashboard() {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMetrics()
      .then((res) => setMetrics(res.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const cards = [
    {
      title: 'Total Conversations',
      value: metrics?.total_conversations ?? '—',
      icon: Users,
    },
    {
      title: 'Messages Today',
      value: metrics?.messages_today ?? '—',
      icon: MessageSquare,
    },
    {
      title: 'Resolved',
      value: metrics?.resolved_conversations ?? '—',
      icon: CheckCircle,
    },
    {
      title: 'Avg Response Time',
      value: metrics
        ? `${metrics.average_response_time_seconds}s`
        : '—',
      icon: Clock,
    },
  ]

  return (
    <div className="p-4">
      <header className="mb-4">
        <h1 className="text-lg font-semibold">Dashboard</h1>
        <p className="text-sm text-slate-500">
          WhatsApp chatbot performance overview
        </p>
      </header>

      {loading ? (
        <p className="text-sm text-slate-500">Loading metrics...</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {cards.map((card) => (
            <MetricsCard key={card.title} {...card} />
          ))}
        </div>
      )}

    </div>
  )
}
