import { useId } from 'react'

export function PageHeader({ title, description, actions }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">{title}</h1>
        {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

/** Label + control + error/help text, wired up with ids for accessibility. */
export function Field({ label, error, help, children, className = '' }) {
  const id = useId()
  const describedBy = error ? `${id}-err` : help ? `${id}-help` : undefined
  const control = typeof children === 'function' ? children({ id, describedBy, invalid: !!error }) : children
  return (
    <div className={className}>
      <label htmlFor={id} className="label">{label}</label>
      {control}
      {error ? (
        <p id={`${id}-err`} className="mt-1 text-xs text-red-600">{error}</p>
      ) : help ? (
        <p id={`${id}-help`} className="mt-1 text-xs text-slate-500">{help}</p>
      ) : null}
    </div>
  )
}

export function TextInput({ label, error, help, className, ...props }) {
  return (
    <Field label={label} error={error} help={help} className={className}>
      {({ id, describedBy, invalid }) => (
        <input id={id} aria-describedby={describedBy} aria-invalid={invalid}
          className={`input ${invalid ? 'input-error' : ''}`} {...props} />
      )}
    </Field>
  )
}

export function SelectInput({ label, error, help, className, children, ...props }) {
  return (
    <Field label={label} error={error} help={help} className={className}>
      {({ id, describedBy, invalid }) => (
        <select id={id} aria-describedby={describedBy} aria-invalid={invalid}
          className={`input ${invalid ? 'input-error' : ''}`} {...props}>
          {children}
        </select>
      )}
    </Field>
  )
}

const BADGE = {
  green: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20',
  red: 'bg-red-50 text-red-700 ring-red-600/20',
  amber: 'bg-amber-50 text-amber-800 ring-amber-600/20',
  blue: 'bg-sky-50 text-sky-700 ring-sky-600/20',
  slate: 'bg-slate-100 text-slate-600 ring-slate-500/20',
  violet: 'bg-violet-50 text-violet-700 ring-violet-600/20',
}
export function Badge({ color = 'slate', children }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${BADGE[color]}`}>
      {children}
    </span>
  )
}

export function ProgressBar({ value, status = 'ok', label }) {
  const pct = Math.max(0, Math.min(100, Number(value) || 0))
  const color = status === 'exceeded' ? 'bg-red-500' : status === 'warning' ? 'bg-amber-500' : 'bg-brand-600'
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100" role="progressbar"
      aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
    </div>
  )
}

export function MonthPicker({ year, month, onChange, label }) {
  const value = `${year}-${String(month).padStart(2, '0')}`
  return (
    <label className="flex items-center gap-2 text-sm text-slate-600">
      <span className="sr-only">{label || 'Select month'}</span>
      <input
        type="month"
        className="input w-auto"
        value={value}
        onChange={(e) => {
          const [y, m] = e.target.value.split('-').map(Number)
          if (y && m) onChange({ year: y, month: m })
        }}
      />
    </label>
  )
}
