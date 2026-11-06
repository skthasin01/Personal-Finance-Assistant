import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CategoryDonut, TrendChart } from '../components/charts/Charts'
import { InsightCard, SectionCard, StatCard } from '../components/cards/Cards'
import { DataState, EmptyState, ErrorState, LoadingState } from '../components/common/States'
import { Badge, MonthPicker, PageHeader, ProgressBar } from '../components/common/ui'
import { useAuth } from '../context/AuthContext'
import { useApi } from '../hooks/useApi'
import { listAccounts } from '../services/accountService'
import { dismissInsight, getCategories, getInsights, getSummary, getTrends } from '../services/analyticsService'
import { listBills, listBudgets, listGoals } from '../services/planningService'
import { listTransactions } from '../services/transactionService'
import { formatMoney, formatPercent } from '../utils/currency'
import { formatDate, monthBounds, monthLabel, todayISO } from '../utils/date'

export default function Dashboard() {
  const { user, currency, timezone } = useAuth()
  const [ty, tm] = todayISO(timezone).split('-').map(Number)
  const [period, setPeriod] = useState({ year: ty, month: tm })
  const { start, end } = monthBounds(period.year, period.month)

  const dash = useApi(async () => {
    const [summary, trends, cats, recent, budgets, bills, goals, accounts] = await Promise.all([
      getSummary({ start_date: start, end_date: end }),
      getTrends({ granularity: 'month', months: 6 }),
      getCategories({ start_date: start, end_date: end }),
      listTransactions({ page_size: 6, start_date: start, end_date: end }),
      listBudgets({ month: period.month, year: period.year }),
      listBills({ status: 'pending', page_size: 5 }),
      listGoals(),
      listAccounts(),
    ])
    return { summary, trends, cats, recent, budgets, bills, goals, accounts }
  }, [start, end])
  const insights = useApi(() => getInsights(), [])

  const onDismiss = async (id) => {
    await dismissInsight(id)
    insights.setData((list) => list.filter((i) => i.id !== id))
  }

  if (dash.loading && !dash.data) return <LoadingState label="Loading your dashboard…" />
  if (dash.error) return <ErrorState message={dash.error} onRetry={dash.reload} />
  const { summary, trends, cats, recent, budgets, bills, goals, accounts } = dash.data
  const cur = summary.current
  const fmt = (v) => formatMoney(v, currency)
  const firstName = user?.full_name?.split(' ')[0]

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Hello, ${firstName}`}
        description={`Your overview for ${monthLabel(period.year, period.month)}`}
        actions={<MonthPicker {...period} onChange={setPeriod} label="Dashboard month" />}
      />

      {!summary.has_data && (
        <div className="card border-dashed p-5 text-sm text-slate-600">
          <strong className="text-slate-900">No transactions for this month yet.</strong>{' '}
          Start by <Link className="font-medium text-brand-700 hover:underline" to="/accounts">adding your accounts</Link> and{' '}
          <Link className="font-medium text-brand-700 hover:underline" to="/transactions">recording income and expenses</Link>.
          Figures here are always calculated from your own records.
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        <StatCard label="Income" value={fmt(cur.income)} change={summary.income_change_percent} />
        <StatCard label="Expenses" value={fmt(cur.expense)} change={summary.expense_change_percent} invertChange
          hint={Number(cur.refunds) > 0 ? `after ${fmt(cur.refunds)} refunds` : undefined} />
        <StatCard label="Net cash flow" value={formatMoney(cur.net_cash_flow, currency, { sign: true })}
          tone={Number(cur.net_cash_flow) < 0 ? 'negative' : Number(cur.net_cash_flow) > 0 ? 'positive' : 'default'}
          hint="Income − expenses (transfers excluded)" />
        <StatCard label="Savings rate" value={cur.savings_rate === null ? 'n/a' : formatPercent(cur.savings_rate)}
          hint={cur.savings_rate === null ? 'Needs recorded income' : `Total balance ${fmt(summary.total_balance)}`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <SectionCard title="Income vs expenses (6 months)" className="lg:col-span-2">
          {trends.points.some((p) => Number(p.income) || Number(p.expense))
            ? <TrendChart points={trends.points} currency={currency} />
            : <EmptyState icon="chart" title="No history yet" description="Your monthly trend appears once you record transactions." />}
        </SectionCard>
        <SectionCard title="Where your money went">
          {cats.categories.length
            ? <CategoryDonut categories={cats.categories} currency={currency} total={cats.total} />
            : <EmptyState icon="pie" title="No expenses this month" />}
        </SectionCard>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <SectionCard title="AI insights" className="lg:col-span-2"
          action={<Link to="/assistant" className="text-sm font-medium text-brand-700 hover:underline">Ask the assistant</Link>}>
          <DataState loading={insights.loading} error={insights.error} onRetry={insights.reload}
            empty={!insights.data?.length} emptyProps={{ icon: 'sparkles', title: 'No insights right now' }}>
            <div className="space-y-2">
              {insights.data?.slice(0, 5).map((i) => <InsightCard key={i.id} insight={i} onDismiss={onDismiss} />)}
            </div>
          </DataState>
        </SectionCard>
        <SectionCard title="Account balances" action={<Link to="/accounts" className="text-sm font-medium text-brand-700 hover:underline">Manage</Link>}>
          <ul className="divide-y divide-slate-100">
            {accounts.filter((a) => a.is_active).map((a) => (
              <li key={a.id} className="flex items-center justify-between py-2 text-sm">
                <span className="text-slate-700">{a.name}</span>
                <span className={`font-medium tabular-nums ${Number(a.current_balance) < 0 ? 'text-red-600' : 'text-slate-900'}`}>{fmt(a.current_balance)}</span>
              </li>
            ))}
          </ul>
        </SectionCard>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <SectionCard title="Budget progress" action={<Link to="/budgets" className="text-sm font-medium text-brand-700 hover:underline">View all</Link>}>
          {budgets.length ? (
            <ul className="space-y-4">
              {budgets.slice(0, 5).map((b) => (
                <li key={b.id}>
                  <div className="mb-1 flex flex-wrap justify-between gap-x-3 text-sm">
                    <span className="font-medium text-slate-700">{b.is_overall ? 'Overall' : b.category_name}</span>
                    <span className="tabular-nums text-slate-500">{fmt(b.spent_amount)} / {fmt(b.limit_amount)}</span>
                  </div>
                  <ProgressBar value={b.utilization_percent} status={b.status} label={`${b.is_overall ? 'Overall' : b.category_name} budget used`} />
                </li>
              ))}
            </ul>
          ) : <EmptyState icon="pie" title="No budgets for this month" action={<Link to="/budgets" className="btn-secondary">Create a budget</Link>} />}
        </SectionCard>
        <SectionCard title="Upcoming bills" action={<Link to="/bills" className="text-sm font-medium text-brand-700 hover:underline">View all</Link>}>
          {bills.items.length ? (
            <ul className="divide-y divide-slate-100">
              {bills.items.map((b) => (
                <li key={b.id} className="flex items-center justify-between gap-2 py-2 text-sm">
                  <div className="min-w-0">
                    <div className="truncate font-medium text-slate-700">{b.title}</div>
                    <div className="text-xs text-slate-500">Due {formatDate(b.due_date)}</div>
                  </div>
                  <div className="text-right">
                    <div className="tabular-nums text-slate-900">{fmt(b.amount)}</div>
                    {b.display_status === 'overdue' && <Badge color="red">Overdue</Badge>}
                  </div>
                </li>
              ))}
            </ul>
          ) : <EmptyState icon="receipt" title="No unpaid bills" />}
        </SectionCard>
        <SectionCard title="Savings goals" action={<Link to="/savings" className="text-sm font-medium text-brand-700 hover:underline">View all</Link>}>
          {goals.length ? (
            <ul className="space-y-4">
              {goals.slice(0, 4).map((g) => (
                <li key={g.id}>
                  <div className="mb-1 flex flex-wrap justify-between gap-x-3 text-sm">
                    <span className="truncate font-medium text-slate-700">{g.title}</span>
                    <span className="tabular-nums text-slate-500">{formatPercent(g.progress_percent)}</span>
                  </div>
                  <ProgressBar value={g.progress_percent} label={`${g.title} progress`} />
                  <div className="mt-1 text-xs text-slate-500">{fmt(g.saved_amount)} of {fmt(g.target_amount)}</div>
                </li>
              ))}
            </ul>
          ) : <EmptyState icon="target" title="No savings goals yet" action={<Link to="/savings" className="btn-secondary">Create a goal</Link>} />}
        </SectionCard>
      </div>

      <SectionCard title="Recent transactions" action={<Link to="/transactions" className="text-sm font-medium text-brand-700 hover:underline">View all</Link>}>
        {recent.items.length ? (
          <ul className="divide-y divide-slate-100">
            {recent.items.map((t) => <RecentRow key={t.id} t={t} currency={currency} />)}
          </ul>
        ) : <EmptyState icon="list" title="No transactions in this month" />}
      </SectionCard>
    </div>
  )
}

function RecentRow({ t, currency }) {
  const positive = t.transaction_type === 'income' || t.transaction_type === 'refund' || t.direction === 'in'
  const label = t.transaction_type === 'transfer'
    ? `Transfer ${t.direction === 'out' ? 'to' : 'from'} ${t.counterpart_account_name}`
    : t.category_name || 'Uncategorised'
  return (
    <li className="flex items-center justify-between gap-3 py-2.5 text-sm">
      <div className="min-w-0">
        <div className="truncate font-medium text-slate-700">{t.description || label}</div>
        <div className="text-xs text-slate-500">{formatDate(t.transaction_date)} · {label} · {t.account_name}</div>
      </div>
      <div className={`shrink-0 font-medium tabular-nums ${t.transaction_type === 'transfer' ? 'text-slate-500' : positive ? 'text-emerald-700' : 'text-slate-900'}`}>
        {positive ? '+' : '−'}{formatMoney(t.amount, currency)}
      </div>
    </li>
  )
}
