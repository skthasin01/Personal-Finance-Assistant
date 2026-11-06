/**
 * Charts with labels, legends, tooltips and a screen-reader text summary.
 * Values arrive as decimal strings; Number() is used only for drawing.
 */
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { formatMoney } from '../../utils/currency'

const INCOME = '#059669'
const EXPENSE = '#e11d48'

function shortPeriod(p) {
  if (/^\d{4}-\d{2}$/.test(p)) {
    const [y, m] = p.split('-').map(Number)
    return new Date(Date.UTC(y, m - 1, 1)).toLocaleString('en-GB', { month: 'short', timeZone: 'UTC' })
  }
  return p.replace('Week of ', '').slice(5)
}

export function TrendChart({ points, currency }) {
  const data = points.map((p) => ({ name: shortPeriod(p.period), period: p.period,
    Income: Number(p.income), Expenses: Number(p.expense) }))
  const summary = points.map((p) => `${p.period}: income ${formatMoney(p.income, currency)}, expenses ${formatMoney(p.expense, currency)}`).join('; ')
  return (
    <figure>
      <div className="h-64 w-full" aria-hidden="true">
        <ResponsiveContainer>
          <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} width={64}
              tickFormatter={(v) => formatMoney(v, currency, { compact: true }).replace('.00', '')} />
            <Tooltip formatter={(v) => formatMoney(v, currency)} labelFormatter={(_, p) => p?.[0]?.payload?.period}
              contentStyle={{ borderRadius: 8, borderColor: '#e2e8f0', fontSize: 13 }} />
            <Legend wrapperStyle={{ fontSize: 13 }} />
            <Bar dataKey="Income" fill={INCOME} radius={[4, 4, 0, 0]} maxBarSize={32} />
            <Bar dataKey="Expenses" fill={EXPENSE} radius={[4, 4, 0, 0]} maxBarSize={32} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="sr-only">Income versus expenses by period. {summary}</figcaption>
    </figure>
  )
}

export function CategoryDonut({ categories, currency, total }) {
  const data = categories.map((c) => ({ name: c.name, value: Number(c.amount), color: c.color, pct: c.percent }))
  return (
    <figure className="flex flex-col gap-4 sm:flex-row sm:items-center">
      <div className="h-52 w-full sm:w-52 sm:shrink-0" aria-hidden="true">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius="58%" outerRadius="90%" paddingAngle={1.5} stroke="none">
              {data.map((d) => <Cell key={d.name} fill={d.color} />)}
            </Pie>
            <Tooltip formatter={(v) => formatMoney(v, currency)} contentStyle={{ borderRadius: 8, fontSize: 13 }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="min-w-0 flex-1">
        <span className="sr-only">Expense breakdown by category, total {formatMoney(total, currency)}.</span>
        <ul className="space-y-2">
          {categories.slice(0, 7).map((c) => (
            <li key={c.name} className="flex items-center gap-2 text-sm">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: c.color }} aria-hidden="true" />
              <span className="min-w-0 flex-1 truncate text-slate-700">{c.name}</span>
              <span className="tabular-nums text-slate-500">{c.percent}%</span>
              <span className="w-28 text-right font-medium tabular-nums text-slate-900">{formatMoney(c.amount, currency)}</span>
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  )
}
