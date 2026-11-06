import { useState } from 'react'
import Icon from '../components/common/Icon'
import Modal, { ConfirmDialog } from '../components/common/Modal'
import { DataState, LoadingState } from '../components/common/States'
import { Badge, PageHeader, ProgressBar } from '../components/common/ui'
import { ContributionForm, GoalForm } from '../components/forms/SimpleForms'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useApi } from '../hooks/useApi'
import { parseError } from '../services/api'
import { listAccounts } from '../services/accountService'
import {
  addContribution, createGoal, deleteContribution, deleteGoal, getGoal, listGoals, updateGoal,
} from '../services/planningService'
import { formatMoney, formatPercent } from '../utils/currency'
import { formatDate } from '../utils/date'

const STATUS = { active: ['blue', 'Active'], completed: ['green', 'Completed'], cancelled: ['slate', 'Cancelled'] }

export default function SavingsGoals() {
  const { currency, timezone } = useAuth()
  const toast = useToast()
  const goals = useApi(() => listGoals(), [])
  const accounts = useApi(() => listAccounts(), [])
  const [modal, setModal] = useState(null) // {mode:'goal'|'contribute'|'history', item?}
  const [confirm, setConfirm] = useState(null)
  const fmt = (v) => formatMoney(v, currency)

  const doDelete = async () => {
    try {
      await deleteGoal(confirm.id)
      setConfirm(null)
      goals.reload()
      toast('Goal deleted')
    } catch (e) { toast(parseError(e).message, 'error') }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Savings goals" description="Progress is calculated from your contribution history."
        actions={<button className="btn-primary" onClick={() => setModal({ mode: 'goal' })}><Icon name="plus" className="h-4 w-4" />New goal</button>} />

      <DataState loading={goals.loading} error={goals.error} onRetry={goals.reload} empty={!goals.data?.length}
        emptyProps={{ icon: 'target', title: 'No savings goals yet', description: 'An emergency fund of 3–6 months of expenses is a common first goal.',
          action: <button className="btn-primary" onClick={() => setModal({ mode: 'goal' })}>Create a goal</button> }}>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {goals.data?.map((g) => {
            const [color, label] = STATUS[g.status]
            const p = g.projection
            return (
              <div key={g.id} className="card flex flex-col p-5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-semibold text-slate-900">{g.title}</div>
                    <div className="mt-0.5 flex items-center gap-1.5 text-xs text-slate-500">
                      <Badge color={color}>{label}</Badge>
                      {g.target_date && <span>by {formatDate(g.target_date)}</span>}
                    </div>
                  </div>
                  <div className="flex">
                    <button className="btn-ghost" onClick={() => setModal({ mode: 'goal', item: g })} aria-label={`Edit ${g.title}`}><Icon name="edit" className="h-4 w-4" /></button>
                    <button className="btn-ghost" onClick={() => setConfirm(g)} aria-label={`Delete ${g.title}`}><Icon name="trash" className="h-4 w-4" /></button>
                  </div>
                </div>
                <div className="mt-4 flex items-baseline justify-between">
                  <span className="text-2xl font-semibold tabular-nums text-slate-900">{fmt(g.saved_amount)}</span>
                  <span className="text-sm text-slate-500">of {fmt(g.target_amount)}</span>
                </div>
                <div className="mt-2"><ProgressBar value={g.progress_percent} label={`${g.title} progress`} /></div>
                <div className="mt-1 text-xs text-slate-500">{formatPercent(g.progress_percent)} · {g.contribution_count} contribution(s)</div>
                <div className={`mt-3 rounded-lg p-3 text-xs ${p.on_track === false ? 'bg-amber-50 text-amber-900' : 'bg-slate-50 text-slate-600'}`}>
                  {p.required_monthly !== null && g.status === 'active' && (
                    <div className="mb-1 font-medium">Needed: {fmt(p.required_monthly)}/month{p.on_track === true && ' · on track'}{p.on_track === false && ' · behind'}</div>
                  )}
                  {p.explanation}
                </div>
                <div className="mt-4 flex gap-2">
                  {g.status === 'active' && (
                    <button className="btn-primary flex-1 px-3 py-1.5" onClick={() => setModal({ mode: 'contribute', item: g })}>Add money</button>
                  )}
                  <button className="btn-secondary flex-1 px-3 py-1.5" onClick={() => setModal({ mode: 'history', item: g })}>History</button>
                </div>
              </div>
            )
          })}
        </div>
      </DataState>

      <Modal open={!!modal} onClose={() => setModal(null)} size={modal?.mode === 'history' ? 'lg' : 'md'}
        title={modal?.mode === 'contribute' ? `Add to ${modal.item.title}` : modal?.mode === 'history' ? `${modal.item.title} — contributions`
          : modal?.item ? 'Edit goal' : 'New savings goal'}>
        {modal?.mode === 'goal' && (
          <>
            <GoalForm initial={modal.item} onCancel={() => setModal(null)}
              onSubmitAction={(p) => (modal.item ? updateGoal(modal.item.id, p) : createGoal(p))}
              onSaved={() => { setModal(null); goals.reload(); toast('Goal saved') }} />
            {modal.item && modal.item.status !== 'active' && (
              <button className="btn-ghost mt-2" onClick={() => updateGoal(modal.item.id, { status: 'active' }).then(() => { setModal(null); goals.reload() })}>Reopen goal</button>
            )}
          </>
        )}
        {modal?.mode === 'contribute' && (
          <ContributionForm accounts={accounts.data || []} timezone={timezone} onCancel={() => setModal(null)}
            onSubmitAction={(p) => addContribution(modal.item.id, p)}
            onSaved={() => { setModal(null); goals.reload(); toast('Contribution added') }} />
        )}
        {modal?.mode === 'history' && <History goalId={modal.item.id} currency={currency} onChanged={goals.reload} />}
      </Modal>
      <ConfirmDialog open={!!confirm} onClose={() => setConfirm(null)} onConfirm={doDelete} title={`Delete ${confirm?.title}?`}
        message="The goal and its contribution records will be deleted. Any transfers you recorded between accounts stay in your ledger." />
    </div>
  )
}

function History({ goalId, currency, onChanged }) {
  const toast = useToast()
  const detail = useApi(() => getGoal(goalId), [goalId])
  if (detail.loading) return <LoadingState />
  const remove = async (cid) => {
    try {
      await deleteContribution(goalId, cid)
      detail.reload()
      onChanged()
    } catch (e) { toast(parseError(e).message, 'error') }
  }
  return (
    <DataState error={detail.error} onRetry={detail.reload} empty={!detail.data?.contributions.length}
      emptyProps={{ icon: 'target', title: 'No contributions yet' }}>
      <ul className="divide-y divide-slate-100">
        {detail.data?.contributions.map((c) => (
          <li key={c.id} className="flex items-center gap-3 py-2.5 text-sm">
            <div className="flex-1">
              <div className="font-medium tabular-nums text-slate-900">{formatMoney(c.amount, currency)}</div>
              <div className="text-xs text-slate-500">{formatDate(c.contribution_date)}{c.note && ` · ${c.note}`}{c.related_transaction_id && ' · recorded as transfer'}</div>
            </div>
            <button className="btn-ghost" onClick={() => remove(c.id)} aria-label="Delete contribution"><Icon name="trash" className="h-4 w-4" /></button>
          </li>
        ))}
      </ul>
    </DataState>
  )
}
