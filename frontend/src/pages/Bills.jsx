import { useState } from 'react'
import Icon from '../components/common/Icon'
import Modal, { ConfirmDialog } from '../components/common/Modal'
import { DataState } from '../components/common/States'
import { Badge, PageHeader } from '../components/common/ui'
import { BILL_TYPES, BillForm, PayBillForm } from '../components/forms/SimpleForms'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useApi } from '../hooks/useApi'
import { parseError } from '../services/api'
import { listAccounts, listCategories } from '../services/accountService'
import { createBill, deleteBill, listBills, payBill, updateBill } from '../services/planningService'
import { formatMoney } from '../utils/currency'
import { formatDate } from '../utils/date'

const TABS = [['upcoming', 'Upcoming'], ['overdue', 'Overdue'], ['paid', 'Paid'], ['', 'All']]
const STATUS = { pending: ['blue', 'Pending'], overdue: ['red', 'Overdue'], paid: ['green', 'Paid'], cancelled: ['slate', 'Cancelled'] }
const TYPE_LABEL = Object.fromEntries(BILL_TYPES)

export default function Bills() {
  const { currency, timezone } = useAuth()
  const toast = useToast()
  const [tab, setTab] = useState('upcoming')
  const [modal, setModal] = useState(null) // {mode:'edit'|'pay', item?}
  const [confirm, setConfirm] = useState(null)
  const bills = useApi(() => listBills({ status: tab || undefined, page_size: 100 }), [tab])
  const refs = useApi(async () => {
    const [accounts, categories] = await Promise.all([listAccounts(), listCategories({ type: 'expense' })])
    return { accounts, categories }
  }, [])
  const fmt = (v) => formatMoney(v, currency)

  const doDelete = async () => {
    try {
      await deleteBill(confirm.id)
      setConfirm(null)
      bills.reload()
      toast('Bill deleted')
    } catch (e) { toast(parseError(e).message, 'error') }
  }

  const dueText = (b) => {
    if (b.status === 'paid') return `Paid ${formatDate(b.paid_at?.slice(0, 10))}`
    if (b.days_until_due === null) return `Due ${formatDate(b.due_date)}`
    if (b.days_until_due < 0) return `${-b.days_until_due} day(s) overdue`
    if (b.days_until_due === 0) return 'Due today'
    return `Due in ${b.days_until_due} day(s) · ${formatDate(b.due_date)}`
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Bills" description="Electricity, water, gas, internet, rent, mobile and subscriptions."
        actions={<button className="btn-primary" onClick={() => setModal({ mode: 'edit' })} disabled={!refs.data}><Icon name="plus" className="h-4 w-4" />Add bill</button>} />

      <div role="tablist" aria-label="Bill status" className="inline-flex rounded-lg bg-slate-100 p-1">
        {TABS.map(([v, l]) => (
          <button key={l} role="tab" aria-selected={tab === v} onClick={() => setTab(v)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${tab === v ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'}`}>{l}</button>
        ))}
      </div>

      <DataState loading={bills.loading} error={bills.error} onRetry={bills.reload} empty={!bills.data?.items.length}
        emptyProps={{ icon: 'receipt', title: tab === 'overdue' ? 'Nothing overdue' : 'No bills here', description: 'Add bills to get due-date reminders and compare amounts over time.' }}>
        <div className="grid gap-3 md:grid-cols-2">
          {bills.data?.items.map((b) => {
            const [color, label] = STATUS[b.display_status]
            const cmp = b.comparison
            return (
              <div key={b.id} className={`card p-4 ${b.display_status === 'overdue' ? 'border-red-200' : ''}`}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="font-medium text-slate-900">{b.title}</span>
                      <Badge color={color}>{label}</Badge>
                      {b.recurrence_rule && <Badge>{b.recurrence_rule}</Badge>}
                    </div>
                    <div className="mt-0.5 text-xs text-slate-500">{TYPE_LABEL[b.bill_type]} · {dueText(b)}</div>
                  </div>
                  <div className="text-right text-lg font-semibold tabular-nums text-slate-900">{fmt(b.amount)}</div>
                </div>
                {cmp && (
                  <p className={`mt-2 text-xs ${cmp.change_percent === null ? 'text-slate-500' : Number(cmp.change_percent) > 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                    {cmp.message}{cmp.previous_amount && ` (previous: ${fmt(cmp.previous_amount)})`}
                  </p>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  {b.status === 'pending' && (
                    <button className="btn-primary px-3 py-1.5" onClick={() => setModal({ mode: 'pay', item: b })}><Icon name="check" className="h-4 w-4" />Mark paid</button>
                  )}
                  <button className="btn-secondary px-3 py-1.5" onClick={() => setModal({ mode: 'edit', item: b })}>Edit</button>
                  {b.status !== 'paid' && <button className="btn-ghost text-red-600" onClick={() => setConfirm(b)}>Delete</button>}
                </div>
              </div>
            )
          })}
        </div>
      </DataState>

      <Modal open={!!modal} onClose={() => setModal(null)}
        title={modal?.mode === 'pay' ? `Pay ${modal.item.title}` : modal?.item ? 'Edit bill' : 'Add bill'}>
        {modal?.mode === 'edit' && refs.data && (
          <BillForm initial={modal.item} categories={refs.data.categories} timezone={timezone} onCancel={() => setModal(null)}
            onSubmitAction={(p) => (modal.item ? updateBill(modal.item.id, p) : createBill(p))}
            onSaved={() => { setModal(null); bills.reload(); toast('Bill saved') }} />
        )}
        {modal?.mode === 'pay' && refs.data && (
          <PayBillForm bill={modal.item} accounts={refs.data.accounts} timezone={timezone} onCancel={() => setModal(null)}
            onSubmitAction={(p) => payBill(modal.item.id, p)}
            onSaved={(res) => {
              setModal(null)
              bills.reload()
              toast(res.next_bill ? `Paid. Next bill due ${formatDate(res.next_bill.due_date)}` : 'Bill marked as paid')
            }} />
        )}
      </Modal>
      <ConfirmDialog open={!!confirm} onClose={() => setConfirm(null)} onConfirm={doDelete} title={`Delete ${confirm?.title}?`}
        message="This removes the bill. Paid bills cannot be deleted because they are part of your history." />
    </div>
  )
}
