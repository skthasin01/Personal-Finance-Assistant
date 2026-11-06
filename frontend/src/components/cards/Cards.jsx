import Icon from '../common/Icon'
import { formatPercent } from '../../utils/currency'

export function StatCard({ label, value, hint, change, invertChange = false, tone = 'default' }) {
  let changeEl = null
  if (change !== undefined) {
    if (change === null) {
      changeEl = <span className="text-xs text-slate-400">No previous data</span>
    } else {
      const n = Number(change)
      const good = invertChange ? n <= 0 : n >= 0
      changeEl = (
        <span className={`text-xs font-medium ${good ? 'text-emerald-700' : 'text-red-600'}`}>
          {formatPercent(n, { sign: true })} vs previous
        </span>
      )
    }
  }
  const toneCls = tone === 'positive' ? 'text-emerald-700' : tone === 'negative' ? 'text-red-600' : 'text-slate-900'
  return (
    <div className="card p-4 sm:p-5">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1.5 text-xl font-semibold tabular-nums sm:text-2xl ${toneCls}`}>{value}</div>
      <div className="mt-1 min-h-[1rem]">{changeEl || (hint && <span className="text-xs text-slate-500">{hint}</span>)}</div>
    </div>
  )
}

const SEVERITY = {
  critical: { cls: 'border-red-200 bg-red-50', icon: 'alert', iconCls: 'text-red-600' },
  warning: { cls: 'border-amber-200 bg-amber-50', icon: 'alert', iconCls: 'text-amber-600' },
  positive: { cls: 'border-emerald-200 bg-emerald-50', icon: 'check', iconCls: 'text-emerald-600' },
  info: { cls: 'border-sky-200 bg-sky-50', icon: 'info', iconCls: 'text-sky-600' },
}

export function InsightCard({ insight, onDismiss }) {
  const s = SEVERITY[insight.severity] || SEVERITY.info
  return (
    <div className={`flex gap-3 rounded-lg border p-3 ${s.cls}`}>
      <Icon name={s.icon} className={`mt-0.5 h-5 w-5 shrink-0 ${s.iconCls}`} />
      <div className="min-w-0 flex-1">
        <div className="text-sm font-semibold text-slate-900">{insight.title}</div>
        <p className="mt-0.5 text-sm text-slate-700">{insight.content}</p>
      </div>
      {onDismiss && (
        <button type="button" className="btn-ghost self-start" onClick={() => onDismiss(insight.id)} aria-label={`Dismiss insight: ${insight.title}`}>
          <Icon name="x" className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}

export function SectionCard({ title, action, children, className = '' }) {
  return (
    <section className={`card ${className}`}>
      <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-4 py-3 sm:px-5">
        <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
        {action}
      </div>
      <div className="p-4 sm:p-5">{children}</div>
    </section>
  )
}
