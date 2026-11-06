import { useState } from 'react'
import Icon from '../components/common/Icon'
import Modal, { ConfirmDialog } from '../components/common/Modal'
import { DataState } from '../components/common/States'
import { Badge, MonthPicker, PageHeader, ProgressBar } from '../components/common/ui'
import { BudgetForm } from '../components/forms/SimpleForms'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useApi } from '../hooks/useApi'
import { parseError } from '../services/api'
import { listCategories } from '../services/accountService'
import { createBudget, deleteBudget, listBudgets, updateBudget } from '../services/planningService'
import { formatMoney, formatPercent } from '../utils/currency'
import { monthLabel, todayISO } from '../utils/date'

const STATUS = { ok: ['green', 'On track'], warning: ['amber', 'Near limit'], exceeded: ['red', 'Exceeded'] }

export default function Budgets() {
  const { currency, timezone, user } = useAuth()
  const toast = useToast()
  const [ty, tm] = todayISO(timezone).split('-').map(Number)
  const [period, setPeriod] = useState({ year: ty, month: tm })
  const [modal, setModal] = useState(null)
  const [confirm, setConfirm] = useState(null)
  const budgets = useApi(() => listBudgets(period), [period.year, period.month])
  const categories = useApi(() => listCategories({ type: 'expense' }), [])
  const fmt = (v) => formatMoney(v, currency)

  const overall = budgets.data?.find((b) => b.is_overall)
  const byCategory = budgets.data?.filter((b) => !b.is_overall) || []

  const doDelete = async () => {
    try {
      await deleteBudget(confirm.id)
      setConfirm(null)
      budgets.reload()
      toast('Budget deleted')
    } catch (e) { toast(parseError(e).message, 'error') }
  }

  const Row = ({ b }) => {
    const [color, label] = STATUS[b.status]
    return (
      <div className="rounded-lg border border-slate-200 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            {b.category_color && <span className="h-3 w-3 rounded-full" style={{ background: b.category_color }} aria-hidden="true" />}
            <span className="font-medium text-slate-900">{b.is_overall ? 'Overall spending' : b.category_name}</span>
            <Badge color={color}>{label}</Badge>
          </div>
          <div className="flex">
            <button className="btn-ghost" onClick={() => setModal({ item: b })} aria-label="Edit budget"><Icon name="edit" className="h-4 w-4" /></button>
            <button className="btn-ghost" onClick={() => setConfirm(b)} aria-label="Delete budget"><Icon name="trash" className="h-4 w-4" /></button>
          </div>
        </div>
        <div className="mt-3"><ProgressBar value={b.utilization_percent} status={b.status} label={`${b.category_name || 'Overall'} budget used`} /></div>
        <div className="mt-2 flex flex-wrap justify-between gap-2 text-sm">
          <span className="text-slate-600">Spent <strong className="tabular-nums text-slate-900">{fmt(b.spent_amount)}</strong> of {fmt(b.limit_amount)}</span>
          <span className={`tabular-nums ${Number(b.remaining_amount) < 0 ? 'text-red-600' : 'text-slate-600'}`}>
            {Number(b.remaining_amount) < 0 ? `${fmt(-Number(b.remaining_amount))} over` : `${fmt(b.remaining_amount)} left`} · {formatPercent(b.utilization_percent)}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Budgets" description={`Monthly limits for ${monthLabel(period.year, period.month)}. Warning at ${user?.budget_warning_threshold}% (change in Settings).`}
        actions={<>
          <MonthPicker {...period} onChange={setPeriod} label="Budget month" />
          <button className="btn-primary" onClick={() => setModal({})}><Icon name="plus" className="h-4 w-4" />New budget</button>
        </>} />
      <DataState loading={budgets.loading} error={budgets.error} onRetry={budgets.reload} empty={!budgets.data?.length}
        emptyProps={{ icon: 'pie', title: 'No budgets for this month', description: 'Set an overall limit or limits per category to track your spending.',
          action: <button className="btn-primary" onClick={() => setModal({})}>Create a budget</button> }}>
        <div className="space-y-6">
          {overall && (
            <section>
              <h2 className="mb-2 text-sm font-semibold text-slate-700">Overall limit</h2>
              <Row b={overall} />
              <p className="mt-2 text-xs text-slate-500">The overall budget is compared with all net expenses this month. It is a separate limit, not the sum of category budgets.</p>
            </section>
          )}
          {byCategory.length > 0 && (
            <section>
              <h2 className="mb-2 text-sm font-semibold text-slate-700">By category</h2>
              <div className="grid gap-3 md:grid-cols-2">{byCategory.map((b) => <Row key={b.id} b={b} />)}</div>
            </section>
          )}
        </div>
      </DataState>

      <Modal open={!!modal} onClose={() => setModal(null)} title={modal?.item ? 'Edit budget limit' : 'New budget'}>
        {modal && (
          <BudgetForm initial={modal.item} categories={categories.data || []}
            defaultMonth={`${period.year}-${String(period.month).padStart(2, '0')}`}
            onCancel={() => setModal(null)}
            onSubmitAction={(p) => (modal.item ? updateBudget(modal.item.id, { limit_amount: p.limit_amount }) : createBudget(p))}
            onSaved={() => { setModal(null); budgets.reload(); toast('Budget saved') }} />
        )}
      </Modal>
      <ConfirmDialog open={!!confirm} onClose={() => setConfirm(null)} onConfirm={doDelete} title="Delete budget?"
        message="Your transactions are not affected; only this limit is removed." />
    </div>
  )
}
