import { useRef, useState } from 'react'
import { Upload, Link as LinkIcon } from 'lucide-react'
import { uploadDocument, ingestUrl } from '../services/api'

export default function UploadDocument({ onSuccess }) {
  const fileRef = useRef(null)
  const [url, setUrl] = useState('')
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setLoading(true)
    setError('')
    try {
      await uploadDocument(file)
      onSuccess?.()
      if (fileRef.current) fileRef.current.value = ''
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  const handleUrl = async (e) => {
    e.preventDefault()
    if (!url.trim()) return
    setLoading(true)
    setError('')
    try {
      await ingestUrl(url.trim(), title.trim() || undefined)
      setUrl('')
      setTitle('')
      onSuccess?.()
    } catch (err) {
      setError(err.response?.data?.detail || 'URL ingest failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <h3 className="text-sm font-semibold">Add to Knowledge Base</h3>

      {error && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-500/10 dark:text-red-400">
          {error}
        </p>
      )}

      <div>
        <label className="mb-1 block text-xs text-slate-500">Upload PDF or DOC</label>
        <label className="flex cursor-pointer items-center justify-center gap-2 rounded-md border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500 hover:border-brand-500 hover:text-brand-600 dark:border-slate-700">
          <Upload size={16} />
          {loading ? 'Processing...' : 'Choose file'}
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.doc,.docx"
            className="hidden"
            disabled={loading}
            onChange={handleFile}
          />
        </label>
      </div>

      <form onSubmit={handleUrl} className="space-y-2">
        <label className="block text-xs text-slate-500">Or add website URL</label>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com/about"
          className="w-full rounded-md border border-slate-200 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
          disabled={loading}
        />
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Optional title"
          className="w-full rounded-md border border-slate-200 bg-transparent px-3 py-2 text-sm dark:border-slate-700"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="flex items-center gap-2 rounded-md bg-brand-600 px-4 py-2 text-sm text-white hover:bg-brand-700 disabled:opacity-50"
        >
          <LinkIcon size={14} />
          Ingest URL
        </button>
      </form>
    </div>
  )
}
