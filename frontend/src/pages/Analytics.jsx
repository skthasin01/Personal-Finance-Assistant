import { useState } from 'react'
import { CategoryDonut, TrendChart } from '../components/charts/Charts'
import { SectionCard, StatCard } from '../components/cards/Cards'
import Icon from '../components/common/Icon'
import { DataState, EmptyState } from '../components/common/States'
import { PageHeader } from '../components/common/ui'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useApi } from '../hooks/useApi'
import { parseError } from '../services/api'
import { downloadCsv, getCashFlow, getCategories, getSummary, getTrends } from '../services/analyticsService'
import { formatMoney, formatPercent } from '../utils/currency'
import { formatDate, monthBounds, shiftMonth, todayISO } from '../utils/date'

function presetRange(preset, today) {
  const [y, m, d] = today.split('-').map(Number)
  const base = new Date(Date.UTC(y, m - 1, d))
  const iso = (dt) => dt.toISOString().slice(0, 10)
  const minus = (days) => iso(new Date(base.getTime() - days * 86400000))
  switch (preset) {
    case 'today': return { start: today, end: today, granularity: 'day' }
    case 'week': return { start: minus(6), end: today, granularity: 'day' }
    case 'last_month': { const p = shiftMonth(y, m, -1); return { ...monthBounds(p.year, p.month), granularity: 'week' } }
    case 'quarter': { const p = shiftMonth(y, m, -2); return { start: monthBounds(p.year, p.month).start, end: monthBounds(y, m).end, granularity: 'month' } }
    case 'year': return { start: `${y}-01-01`, end: `${y}-12-31`, granularity: 'month' }
    default: return { ...monthBounds(y, m), granularity: 'week' }
  }
}

const PRESETS = [['today', 'Today'], ['week', 'Last 7 days'], ['month', 'This month'], ['last_month', 'Last month'],
  ['quarter', 'Last 3 months'], ['year', 'This year'], ['custom', 'Custom']]

export default function Analytics() {
  const { currency, timezone } = useAuth()
  const toast = useToast()
  const today = todayISO(timezone)
  const [preset, setPreset] = useState('month')
  const [custom, setCustom] = useState(() => presetRange('month', today))
  const range = preset === 'custom' ? { ...custom, granularity: 'day' } : presetRange(preset, today)
  const params = { start_date: range.start, end_date: range.end }
  const fmt = (v) => formatMoney(v, currency)

  const data = useApi(async () => {
    const [summary, trends, expense, income, cash] = await Promise.all([
      getSummary(params), getTrends({ ...params, granularity: range.granularity }),
      getCategories({ ...params, type: 'expense' }), getCategories({ ...params, type: 'income' }), getCashFlow(params),
    ])
    return { summary, trends, expense, income, cash }
  }, [range.start, range.end, range.granularity])

  const exportCsv = async () => {
    try {
      await downloadCsv(params)
      toast('Report downloaded')
    } catch (e) { toast(parseError(e).message, 'error') }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Analytics & reports" description={`${formatDate(range.start)} – ${formatDate(range.end)}`}
        actions={<button className="btn-secondary" onClick={exportCsv}><Icon name="download" className="h-4 w-4" />Export CSV</button>} />

      <div className="flex flex-wrap items-center gap-2">
        {PRESETS.map(([v, l]) => (
          <button key={v} onClick={() => setPreset(v)} aria-pressed={preset === v}
            className={`rounded-full px-3 py-1 text-sm font-medium ${preset === v ? 'bg-brand-700 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50'}`}>
            {l}
          </button>
        ))}
        {preset === 'custom' && (
          <div className="flex flex-wrap items-center gap-2">
            <label className="sr-only" htmlFor="from">From</label>
            <input id="from" type="date" className="input w-auto" value={custom.start} onChange={(e) => setCustom({ ...custom, start: e.target.value })} />
            <span className="text-slate-400">to</span>
            <label className="sr-only" htmlFor="to">To</label>
            <input id="to" type="date" className="input w-auto" value={custom.end} onChange={(e) => setCustom({ ...custom, end: e.target.value })} />
          </div>
        )}
      </div>

      <DataState loading={data.loading} error={data.error} onRetry={data.reload}>
        {data.data && (() => {
          const { summary, trends, expense, income, cash } = data.data
          const cur = summary.current
          return (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                <StatCard label="Income" value={fmt(cur.income)} change={summary.income_change_percent} />
                <StatCard label="Net expenses" value={fmt(cur.expense)} change={summary.expense_change_percent} invertChange
                  hint={`Gross ${fmt(cur.gross_expense)} − refunds ${fmt(cur.refunds)}`} />
                <StatCard label="Net cash flow" value={formatMoney(cur.net_cash_flow, currency, { sign: true })}
                  tone={Number(cur.net_cash_flow) < 0 ? 'negative' : 'default'} />
                <StatCard label="Savings rate" value={cur.savings_rate === null ? 'n/a' : formatPercent(cur.savings_rate)}
                  hint={`Previous period: ${summary.previous.savings_rate === null ? 'n/a' : formatPercent(summary.previous.savings_rate)}`} />
              </div>
              <p className="text-xs text-slate-500">
                Compared with {formatDate(summary.previous.start_date)} – {formatDate(summary.previous.end_date)}.
                Transfers between your own accounts are excluded from income and expenses.
              </p>

              <SectionCard title="Income vs expenses over time">
                {trends.points.some((p) => Number(p.income) || Number(p.expense))
                  ? <TrendChart points={trends.points} currency={currency} />
                  : <EmptyState icon="chart" title="No transactions in this period" />}
              </SectionCard>

              <div className="grid gap-6 lg:grid-cols-2">
                <SectionCard title="Expenses by category">
                  {expense.categories.length ? (
                    <>
                      <CategoryDonut categories={expense.categories} currency={currency} total={expense.total} />
                      <table className="mt-4 w-full text-sm">
                        <caption className="sr-only">Category spending compared with the previous period</caption>
                        <thead><tr className="text-left text-xs text-slate-500"><th className="py-1 font-medium">Category</th><th className="py-1 text-right font-medium">Now</th><th className="py-1 text-right font-medium">Previous</th><th className="py-1 text-right font-medium">Change</th></tr></thead>
                        <tbody className="divide-y divide-slate-100">
                          {expense.categories.map((c) => (
                            <tr key={c.name}>
                              <td className="py-1.5 text-slate-700">{c.name}</td>
                              <td className="py-1.5 text-right tabular-nums">{fmt(c.amount)}</td>
                              <td className="py-1.5 text-right tabular-nums text-slate-500">{fmt(c.previous_amount)}</td>
                              <td className={`py-1.5 text-right tabular-nums ${c.change_percent === null ? 'text-slate-400' : Number(c.change_percent) > 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                                {c.change_percent === null ? 'n/a' : formatPercent(c.change_percent, { sign: true })}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </>
                  ) : <EmptyState icon="pie" title="No expenses in this period" />}
                </SectionCard>
                <div className="space-y-6">
                  <SectionCard title="Income sources">
                    {income.categories.length ? (
                      <ul className="space-y-2">
                        {income.categories.map((c) => (
                          <li key={c.name} className="flex items-center gap-2 text-sm">
                            <span className="h-2.5 w-2.5 rounded-full" style={{ background: c.color }} aria-hidden="true" />
                            <span className="flex-1 text-slate-700">{c.name}</span>
                            <span className="text-slate-500">{c.percent}%</span>
                            <span className="w-28 text-right font-medium tabular-nums">{fmt(c.amount)}</span>
                          </li>
                        ))}
                      </ul>
                    ) : <EmptyState icon="wallet" title="No income in this period" />}
                  </SectionCard>
                  <SectionCard title="Cash flow by account">
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead><tr className="text-left text-xs text-slate-500"><th className="py-1 font-medium">Account</th><th className="py-1 text-right font-medium">In</th><th className="py-1 text-right font-medium">Out</th><th className="py-1 text-right font-medium">Transfers</th><th className="py-1 text-right font-medium">Net</th></tr></thead>
                        <tbody className="divide-y divide-slate-100">
                          {cash.accounts.map((a) => (
                            <tr key={a.account_id}>
                              <td className="py-1.5 text-slate-700">{a.account_name}</td>
                              <td className="py-1.5 text-right tabular-nums text-emerald-700">{fmt(a.inflow)}</td>
                              <td className="py-1.5 text-right tabular-nums">{fmt(a.outflow)}</td>
                              <td className="py-1.5 text-right tabular-nums text-slate-500">{formatMoney(Number(a.transfers_in) - Number(a.transfers_out), currency, { sign: true })}</td>
                              <td className={`py-1.5 text-right font-medium tabular-nums ${Number(a.net) < 0 ? 'text-red-600' : ''}`}>{formatMoney(a.net, currency, { sign: true })}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </SectionCard>
                </div>
              </div>
            </div>
          )
        })()}
      </DataState>
    </div>
  )
}
