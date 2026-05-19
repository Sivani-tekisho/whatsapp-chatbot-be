import { useEffect, useState } from 'react'
import { Trash2, FileText } from 'lucide-react'
import UploadDocument from '../components/UploadDocument'
import { getDocuments, deleteDocument } from '../services/api'

export default function KnowledgeBase() {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    getDocuments()
      .then((res) => setDocs(res.data.items))
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const handleDelete = async (id) => {
    if (!confirm('Delete this document and all its chunks?')) return
    await deleteDocument(id)
    load()
  }

  return (
    <div className="grid gap-4 p-4 lg:grid-cols-3">
      <div className="lg:col-span-1">
        <header className="mb-3">
          <h1 className="text-lg font-semibold">Knowledge Base</h1>
          <p className="text-sm text-slate-500">Documents used for RAG answers</p>
        </header>
        <UploadDocument onSuccess={load} />
      </div>

      <div className="lg:col-span-2">
        <div className="rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
          <div className="border-b border-slate-200 px-4 py-3 dark:border-slate-800">
            <h2 className="text-sm font-semibold">Uploaded Documents</h2>
          </div>
          {loading ? (
            <p className="p-4 text-sm text-slate-500">Loading...</p>
          ) : docs.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">
              No documents yet. Upload PDFs or add URLs.
            </p>
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {docs.map((doc) => (
                <li
                  key={doc.id}
                  className="flex items-center justify-between px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <FileText size={16} className="text-brand-600" />
                    <div>
                      <p className="text-sm font-medium">{doc.title}</p>
                      <p className="text-xs text-slate-500">
                        {doc.source_type}
                        {doc.source_url && ` · ${doc.source_url}`}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDelete(doc.id)}
                    className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10"
                  >
                    <Trash2 size={14} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
