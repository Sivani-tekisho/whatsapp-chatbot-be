import { useEffect, useState } from 'react'
import { getSettings, updateSettings } from '../services/api'

export default function Settings() {
  const [form, setForm] = useState({
    name: '',
    bot_name: '',
    system_prompt: '',
    greeting_message: '',
    fallback_message: '',
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    getSettings()
      .then((res) => setForm(res.data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setMessage('')
    try {
      await updateSettings(form)
      setMessage('Settings saved successfully')
    } catch {
      setMessage('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <p className="p-4 text-sm text-slate-500">Loading settings...</p>
  }

  const fields = [
    { name: 'name', label: 'Company Name', type: 'text' },
    { name: 'bot_name', label: 'Bot Name', type: 'text' },
    { name: 'greeting_message', label: 'Greeting Message', type: 'textarea' },
    { name: 'fallback_message', label: 'Fallback Message', type: 'textarea' },
    { name: 'system_prompt', label: 'System Prompt', type: 'textarea', rows: 6 },
  ]

  return (
    <div className="max-w-2xl p-4">
      <header className="mb-4">
        <h1 className="text-lg font-semibold">Settings</h1>
        <p className="text-sm text-slate-500">Configure bot behavior and prompts</p>
      </header>

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
      >
        {fields.map(({ name, label, type, rows }) => (
          <div key={name}>
            <label className="mb-1 block text-xs font-medium text-slate-500">
              {label}
            </label>
            {type === 'textarea' ? (
              <textarea
                name={name}
                value={form[name] || ''}
                onChange={handleChange}
                rows={rows || 3}
                className="w-full rounded-md border border-slate-200 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
              />
            ) : (
              <input
                name={name}
                type="text"
                value={form[name] || ''}
                onChange={handleChange}
                className="w-full rounded-md border border-slate-200 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
              />
            )}
          </div>
        ))}

        {message && (
          <p className="text-xs text-brand-600">{message}</p>
        )}

        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </form>
    </div>
  )
}
