import { useState } from 'react'
import { SectionCard } from '../components/cards/Cards'
import Icon from '../components/common/Icon'
import Modal, { ConfirmDialog } from '../components/common/Modal'
import { DataState } from '../components/common/States'
import { Badge, PageHeader } from '../components/common/ui'
import { ACCOUNT_TYPES, AccountForm, CategoryForm } from '../components/forms/SimpleForms'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useApi } from '../hooks/useApi'
import { parseError } from '../services/api'
import {
  createAccount, createCategory, deleteAccount, deleteCategory, listAccounts, listCategories, updateAccount, updateCategory,
} from '../services/accountService'
import { formatMoney } from '../utils/currency'

const TYPE_LABEL = Object.fromEntries(ACCOUNT_TYPES)

export default function Accounts() {
  const { currency } = useAuth()
  const toast = useToast()
  const accounts = useApi(() => listAccounts(), [])
  const categories = useApi(() => listCategories({ include_inactive: true }), [])
  const [editing, setEditing] = useState(null) // {kind:'account'|'category', item?}
  const [confirm, setConfirm] = useState(null)
  const [busy, setBusy] = useState(false)

  const total = (accounts.data || []).filter((a) => a.is_active).reduce((s, a) => s + Number(a.current_balance), 0)

  const doDelete = async () => {
    setBusy(true)
    try {
      const fn = confirm.kind === 'account' ? deleteAccount : deleteCategory
      const res = await fn(confirm.item.id)
      toast(res.message)
      confirm.kind === 'account' ? accounts.reload() : categories.reload()
      setConfirm(null)
    } catch (e) {
      toast(parseError(e).message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const toggleAccount = async (a) => {
    try {
      await updateAccount(a.id, { is_active: !a.is_active })
      accounts.reload()
    } catch (e) { toast(parseError(e).message, 'error') }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Accounts & categories"
        description="Cash, bank, bKash, Nagad and other places your money lives."
        actions={<button className="btn-primary" onClick={() => setEditing({ kind: 'account' })}><Icon name="plus" className="h-4 w-4" />Add account</button>}
      />

      <SectionCard title={`Accounts · total ${formatMoney(total, currency)}`}>
        <DataState loading={accounts.loading} error={accounts.error} onRetry={accounts.reload} empty={!accounts.data?.length}
          emptyProps={{ icon: 'wallet', title: 'No accounts yet', description: 'Add your first account to start recording transactions.' }}>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {accounts.data?.map((a) => (
              <div key={a.id} className={`rounded-lg border p-4 ${a.is_active ? 'border-slate-200' : 'border-dashed border-slate-300 bg-slate-50'}`}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate font-medium text-slate-900">{a.name}</div>
                    <div className="mt-0.5 flex gap-1.5">
                      <Badge color="blue">{TYPE_LABEL[a.account_type]}</Badge>
                      {!a.is_active && <Badge>Inactive</Badge>}
                    </div>
                  </div>
                  <div className="flex">
                    <button className="btn-ghost" onClick={() => setEditing({ kind: 'account', item: a })} aria-label={`Edit ${a.name}`}><Icon name="edit" className="h-4 w-4" /></button>
                    <button className="btn-ghost" onClick={() => setConfirm({ kind: 'account', item: a })} aria-label={`Delete ${a.name}`}><Icon name="trash" className="h-4 w-4" /></button>
                  </div>
                </div>
                <div className={`mt-3 text-xl font-semibold tabular-nums ${Number(a.current_balance) < 0 ? 'text-red-600' : 'text-slate-900'}`}>
                  {formatMoney(a.current_balance, a.currency_code)}
                </div>
                <div className="mt-1 flex items-center justify-between text-xs text-slate-500">
                  <span>Opening {formatMoney(a.opening_balance, a.currency_code)}</span>
                  <button className="font-medium text-brand-700 hover:underline" onClick={() => toggleAccount(a)}>
                    {a.is_active ? 'Deactivate' : 'Reactivate'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </DataState>
      </SectionCard>

      <SectionCard title="Categories" action={<button className="btn-secondary" onClick={() => setEditing({ kind: 'category' })}><Icon name="plus" className="h-4 w-4" />Add category</button>}>
        <DataState loading={categories.loading} error={categories.error} onRetry={categories.reload}>
          <div className="grid gap-6 md:grid-cols-2">
            {['expense', 'income'].map((type) => (
              <div key={type}>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{type} categories</h3>
                <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
                  {categories.data?.filter((c) => c.type === type).map((c) => (
                    <li key={c.id} className="flex items-center gap-3 px-3 py-2 text-sm">
                      <span className="h-3 w-3 rounded-full" style={{ background: c.color }} aria-hidden="true" />
                      <span className={`flex-1 ${c.is_active ? 'text-slate-700' : 'text-slate-400 line-through'}`}>{c.name}</span>
                      {!c.is_active && (
                        <button className="text-xs font-medium text-brand-700 hover:underline"
                          onClick={() => updateCategory(c.id, { is_active: true }).then(categories.reload)}>Restore</button>
                      )}
                      <button className="btn-ghost" onClick={() => setEditing({ kind: 'category', item: c })} aria-label={`Edit ${c.name}`}><Icon name="edit" className="h-4 w-4" /></button>
                      {c.is_active && (
                        <button className="btn-ghost" onClick={() => setConfirm({ kind: 'category', item: c })} aria-label={`Delete ${c.name}`}><Icon name="trash" className="h-4 w-4" /></button>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </DataState>
      </SectionCard>

      <Modal open={!!editing} onClose={() => setEditing(null)}
        title={`${editing?.item ? 'Edit' : 'New'} ${editing?.kind === 'category' ? 'category' : 'account'}`}>
        {editing?.kind === 'account' && (
          <AccountForm initial={editing.item} onCancel={() => setEditing(null)}
            onSubmitAction={(f) => (editing.item ? updateAccount(editing.item.id, f) : createAccount(f))}
            onSaved={() => { setEditing(null); accounts.reload(); toast('Account saved') }} />
        )}
        {editing?.kind === 'category' && (
          <CategoryForm initial={editing.item} onCancel={() => setEditing(null)}
            onSubmitAction={(f) => (editing.item ? updateCategory(editing.item.id, { name: f.name, color: f.color }) : createCategory(f))}
            onSaved={() => { setEditing(null); categories.reload(); toast('Category saved') }} />
        )}
      </Modal>

      <ConfirmDialog open={!!confirm} onClose={() => setConfirm(null)} onConfirm={doDelete} busy={busy}
        title={`Delete ${confirm?.item?.name}?`}
        message={confirm?.kind === 'account'
          ? 'If this account has transactions it will be deactivated instead, so your history and reports stay correct.'
          : 'If this category is used by transactions, budgets or bills it will be deactivated instead.'} />
    </div>
  )
}
