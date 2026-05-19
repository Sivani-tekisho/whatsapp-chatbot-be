export default function MetricsCard({ title, value, subtitle, icon: Icon }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {title}
          </p>
          <p className="mt-1 text-2xl font-semibold">{value}</p>
          {subtitle && (
            <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>
          )}
        </div>
        {Icon && (
          <div className="rounded-md bg-brand-50 p-2 text-brand-600 dark:bg-brand-500/10 dark:text-brand-500">
            <Icon size={18} />
          </div>
        )}
      </div>
    </div>
  )
}
