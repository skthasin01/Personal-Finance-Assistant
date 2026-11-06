import { useEffect, useState } from 'react'
import { useSubmit } from '../../hooks/useApi'
import { createTransaction, createTransfer, listTransactions, updateTransaction } from '../../services/transactionService'
import { formatMoney, validateAmount } from '../../utils/currency'
import { formatDate, todayISO } from '../../utils/date'
import { FormError } from '../common/States'
import { SelectInput, TextInput } from '../common/ui'

const TYPES = [
  { value: 'expense', label: 'Expense' },
  { value: 'income', label: 'Income' },
  { value: 'transfer', label: 'Transfer' },
  { value: 'refund', label: 'Refund' },
]

/**
 * Create or edit a transaction.
 * - Transfers move money between two of the user's accounts (not income/expense).
 * - Refunds must point to the original expense and reduce expense totals.
 */
export default function TransactionForm({ accounts, categories, initial, timezone, currency, onSaved, onCancel }) {
  const editing = !!initial
  const activeAccounts = accounts.filter((a) => a.is_active || a.id === initial?.account_id)
  const [type, setType] = useState(initial?.transaction_type || 'expense')
  const [form, setForm] = useState({
    account_id: initial?.account_id || activeAccounts[0]?.id || '',
    to_account_id: '',
    category_id: initial?.category_id || '',
    amount: initial?.amount || '',
    transaction_date: initial?.transaction_date || todayISO(timezone),
    description: initial?.description || '',
    related_transaction_id: initial?.related_transaction_id || '',
  })
  const [errors, setErrors] = useState({})
  const [expenses, setExpenses] = useState([])
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  useEffect(() => {
    if (type === 'refund' && !editing) {
      listTransactions({ type: 'expense', page_size: 50 }).then((p) => setExpenses(p.items)).catch(() => setExpenses([]))
    }
  }, [type, editing])

  const action = async () => {
    const payload = { amount: form.amount, transaction_date: form.transaction_date, description: form.description || null }
    if (editing) {
      if (type !== 'transfer') {
        payload.account_id = form.account_id
        if (type !== 'refund') payload.category_id = form.category_id
      }
      return updateTransaction(initial.id, payload)
    }
    if (type === 'transfer') {
      return createTransfer({ ...payload, from_account_id: form.account_id, to_account_id: form.to_account_id })
    }
    return createTransaction({
      ...payload, transaction_type: type, account_id: form.account_id,
      category_id: type === 'refund' ? null : form.category_id,
      related_transaction_id: type === 'refund' ? form.related_transaction_id : null,
    })
  }
  const { submit, submitting, error, fieldErrors } = useSubmit(action)

  const validate = () => {
    const e = {}
    const amountErr = validateAmount(form.amount)
    if (amountErr) e.amount = amountErr
    if (!form.account_id) e.account_id = 'Choose an account'
    if (!form.transaction_date) e.transaction_date = 'Choose a date'
    if ((type === 'income' || type === 'expense') && !form.category_id) e.category_id = 'Choose a category'
    if (type === 'transfer' && !editing) {
      if (!form.to_account_id) e.to_account_id = 'Choose the destination account'
      else if (form.to_account_id === form.account_id) e.to_account_id = 'Choose a different account'
    }
    if (type === 'refund' && !editing && !form.related_transaction_id) e.related_transaction_id = 'Choose the original expense'
    setErrors(e)
    return !Object.keys(e).length
  }

  const onSubmit = async (ev) => {
    ev.preventDefault()
    if (!validate()) return
    try {
      await submit()
      onSaved()
    } catch { /* shown via error state */ }
  }

  const err = (k) => errors[k] || fieldErrors[k]
  const cats = categories.filter((c) => c.type === (type === 'income' ? 'income' : 'expense') && (c.is_active || c.id === initial?.category_id))
  const selectedExpense = expenses.find((x) => x.id === form.related_transaction_id)

  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      <FormError message={error} />
      {!editing && (
        <fieldset>
          <legend className="label">Type</legend>
          <div className="grid grid-cols-4 gap-1 rounded-lg bg-slate-100 p-1">
            {TYPES.map((t) => (
              <button key={t.value} type="button" onClick={() => { setType(t.value); setErrors({}) }}
                aria-pressed={type === t.value}
                className={`rounded-md px-2 py-1.5 text-sm font-medium transition ${
                  type === t.value ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}>
                {t.label}
              </button>
            ))}
          </div>
        </fieldset>
      )}

      {type === 'refund' && !editing && (
        <SelectInput label="Original expense" value={form.related_transaction_id} onChange={set('related_transaction_id')}
          error={err('related_transaction_id')} help="Refunds reduce your expense totals; they are not income.">
          <option value="">Select the expense being refunded…</option>
          {expenses.map((x) => (
            <option key={x.id} value={x.id}>
              {formatDate(x.transaction_date)} · {x.category_name} · {formatMoney(x.amount, currency)}
              {x.description ? ` · ${x.description}` : ''}
            </option>
          ))}
        </SelectInput>
      )}
      {selectedExpense && Number(selectedExpense.refunded_amount) > 0 && (
        <p className="text-xs text-slate-500">Already refunded: {formatMoney(selectedExpense.refunded_amount, currency)}</p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <TextInput label="Amount" inputMode="decimal" placeholder="0.00" value={form.amount} onChange={set('amount')} error={err('amount')} />
        <TextInput label="Date" type="date" value={form.transaction_date} onChange={set('transaction_date')} error={err('transaction_date')} />
      </div>

      {type !== 'transfer' || !editing ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectInput label={type === 'transfer' ? 'From account' : type === 'refund' ? 'Refunded to account' : 'Account'}
            value={form.account_id} onChange={set('account_id')} error={err('account_id')}>
            <option value="">Select…</option>
            {activeAccounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </SelectInput>
          {type === 'transfer' ? (
            <SelectInput label="To account" value={form.to_account_id} onChange={set('to_account_id')} error={err('to_account_id')}>
              <option value="">Select…</option>
              {activeAccounts.filter((a) => a.id !== form.account_id).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </SelectInput>
          ) : type !== 'refund' ? (
            <SelectInput label="Category" value={form.category_id} onChange={set('category_id')} error={err('category_id')}>
              <option value="">Select…</option>
              {cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </SelectInput>
          ) : null}
        </div>
      ) : (
        <p className="text-xs text-slate-500">To change transfer accounts, delete this transfer and record a new one.</p>
      )}

      <TextInput label="Description (optional)" maxLength={255} value={form.description} onChange={set('description')} error={err('description')} />
      {type === 'transfer' && !editing && (
        <p className="text-xs text-slate-500">Transfers between your own accounts change balances but are not counted as income or expenses.</p>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <button type="button" className="btn-secondary" onClick={onCancel}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Saving…' : editing ? 'Save changes' : 'Add'}</button>
      </div>
    </form>
  )
}
