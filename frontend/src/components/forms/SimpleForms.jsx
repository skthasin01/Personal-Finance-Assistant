/** Smaller forms: account, category, budget, bill, bill payment, goal, contribution. */
import { useState } from 'react'
import { useSubmit } from '../../hooks/useApi'
import { validateAmount } from '../../utils/currency'
import { todayISO } from '../../utils/date'
import { FormError } from '../common/States'
import { SelectInput, TextInput } from '../common/ui'

function useFormState(initial) {
  const [form, setForm] = useState(initial)
  const [errors, setErrors] = useState({})
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))
  return { form, setForm, errors, setErrors, set }
}

function Actions({ onCancel, submitting, label = 'Save' }) {
  return (
    <div className="flex justify-end gap-2 pt-2">
      <button type="button" className="btn-secondary" onClick={onCancel}>Cancel</button>
      <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Saving…' : label}</button>
    </div>
  )
}

function useFormSubmit(action, validate, setErrors, onSaved) {
  const s = useSubmit(action)
  const onSubmit = async (ev) => {
    ev.preventDefault()
    const e = validate()
    setErrors(e)
    if (Object.keys(e).length) return
    try {
      const result = await s.submit()
      onSaved(result)
    } catch { /* error displayed */ }
  }
  return { ...s, onSubmit }
}

export const ACCOUNT_TYPES = [
  ['cash', 'Cash'], ['bank', 'Bank'], ['bkash', 'bKash'], ['nagad', 'Nagad'], ['rocket', 'Rocket'],
  ['card', 'Card'], ['savings', 'Savings'], ['other', 'Other'],
]

export function AccountForm({ initial, onSubmitAction, onSaved, onCancel }) {
  const { form, errors, setErrors, set } = useFormState({
    name: initial?.name || '', account_type: initial?.account_type || 'bank', opening_balance: initial?.opening_balance || '0',
  })
  const validate = () => {
    const e = {}
    if (!form.name.trim()) e.name = 'Name is required'
    const a = validateAmount(form.opening_balance, { allowZero: true })
    if (a) e.opening_balance = a
    return e
  }
  const { onSubmit, submitting, error, fieldErrors } = useFormSubmit(() => onSubmitAction(form), validate, setErrors, onSaved)
  const err = (k) => errors[k] || fieldErrors[k]
  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      <FormError message={error} />
      <TextInput label="Account name" placeholder="e.g. Dutch-Bangla Bank" value={form.name} onChange={set('name')} error={err('name')} maxLength={80} />
      <SelectInput label="Type" value={form.account_type} onChange={set('account_type')} error={err('account_type')}>
        {ACCOUNT_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </SelectInput>
      <TextInput label="Opening balance" inputMode="decimal" value={form.opening_balance} onChange={set('opening_balance')}
        error={err('opening_balance')} help="The balance before your first recorded transaction." />
      <Actions onCancel={onCancel} submitting={submitting} />
    </form>
  )
}

export function CategoryForm({ initial, onSubmitAction, onSaved, onCancel }) {
  const { form, errors, setErrors, set } = useFormState({
    name: initial?.name || '', type: initial?.type || 'expense', color: initial?.color || '#64748b',
  })
  const validate = () => (form.name.trim() ? {} : { name: 'Name is required' })
  const { onSubmit, submitting, error, fieldErrors } = useFormSubmit(() => onSubmitAction(form), validate, setErrors, onSaved)
  const err = (k) => errors[k] || fieldErrors[k]
  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      <FormError message={error} />
      <TextInput label="Category name" value={form.name} onChange={set('name')} error={err('name')} maxLength={60} />
      {!initial && (
        <SelectInput label="Type" value={form.type} onChange={set('type')}>
          <option value="expense">Expense</option>
          <option value="income">Income</option>
        </SelectInput>
      )}
      <TextInput label="Colour" type="color" className="w-32" value={form.color} onChange={set('color')} error={err('color')} />
      <Actions onCancel={onCancel} submitting={submitting} />
    </form>
  )
}

export function BudgetForm({ initial, categories, defaultMonth, onSubmitAction, onSaved, onCancel }) {
  const { form, errors, setErrors, set } = useFormState({
    category_id: initial?.category_id || '', limit_amount: initial?.limit_amount || '',
    period: initial ? `${initial.year}-${String(initial.month).padStart(2, '0')}` : defaultMonth,
  })
  const validate = () => {
    const e = {}
    const a = validateAmount(form.limit_amount)
    if (a) e.limit_amount = a
    if (!form.period) e.period = 'Choose a month'
    return e
  }
  const { onSubmit, submitting, error, fieldErrors } = useFormSubmit(() => {
    const [year, month] = form.period.split('-').map(Number)
    return onSubmitAction({ category_id: form.category_id || null, limit_amount: form.limit_amount, month, year })
  }, validate, setErrors, onSaved)
  const err = (k) => errors[k] || fieldErrors[k]
  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      <FormError message={error} />
      {!initial && (
        <>
          <SelectInput label="Budget for" value={form.category_id} onChange={set('category_id')} error={err('category_id')}
            help="The overall budget is a separate limit for all spending; it is not the sum of category budgets.">
            <option value="">Overall monthly spending</option>
            {categories.filter((c) => c.type === 'expense' && c.is_active).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </SelectInput>
          <TextInput label="Month" type="month" value={form.period} onChange={set('period')} error={err('period')} />
        </>
      )}
      <TextInput label="Monthly limit" inputMode="decimal" placeholder="0.00" value={form.limit_amount} onChange={set('limit_amount')} error={err('limit_amount')} />
      <Actions onCancel={onCancel} submitting={submitting} />
    </form>
  )
}

export const BILL_TYPES = [
  ['electricity', 'Electricity'], ['water', 'Water'], ['gas', 'Gas'], ['internet', 'Internet'], ['rent', 'Rent'],
  ['mobile', 'Mobile'], ['subscription', 'Subscription'], ['custom', 'Other'],
]

export function BillForm({ initial, categories, timezone, onSubmitAction, onSaved, onCancel }) {
  const { form, errors, setErrors, set } = useFormState({
    title: initial?.title || '', bill_type: initial?.bill_type || 'electricity', category_id: initial?.category_id || '',
    amount: initial?.amount || '', due_date: initial?.due_date || todayISO(timezone),
    billing_period_start: initial?.billing_period_start || '', billing_period_end: initial?.billing_period_end || '',
    recurrence_rule: initial?.recurrence_rule || '', notes: initial?.notes || '',
  })
  const validate = () => {
    const e = {}
    if (!form.title.trim()) e.title = 'Title is required'
    const a = validateAmount(form.amount)
    if (a) e.amount = a
    if (!form.due_date) e.due_date = 'Due date is required'
    if (form.billing_period_start && form.billing_period_end && form.billing_period_end < form.billing_period_start)
      e.billing_period_end = 'End must be on or after start'
    return e
  }
  const { onSubmit, submitting, error, fieldErrors } = useFormSubmit(() => onSubmitAction({
    ...form, category_id: form.category_id || null, recurrence_rule: form.recurrence_rule || null,
    billing_period_start: form.billing_period_start || null, billing_period_end: form.billing_period_end || null,
    notes: form.notes || null,
  }), validate, setErrors, onSaved)
  const err = (k) => errors[k] || fieldErrors[k]
  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      <FormError message={error} />
      <TextInput label="Title" placeholder="e.g. DESCO electricity" value={form.title} onChange={set('title')} error={err('title')} maxLength={120} />
      <div className="grid gap-4 sm:grid-cols-2">
        <SelectInput label="Bill type" value={form.bill_type} onChange={set('bill_type')}>
          {BILL_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </SelectInput>
        <SelectInput label="Expense category" value={form.category_id} onChange={set('category_id')} help="Used when the bill is paid">
          <option value="">Bills & Utilities (default)</option>
          {categories.filter((c) => c.type === 'expense' && c.is_active).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </SelectInput>
        <TextInput label="Amount" inputMode="decimal" value={form.amount} onChange={set('amount')} error={err('amount')} />
        <TextInput label="Due date" type="date" value={form.due_date} onChange={set('due_date')} error={err('due_date')} />
        <TextInput label="Billing period start" type="date" value={form.billing_period_start} onChange={set('billing_period_start')} />
        <TextInput label="Billing period end" type="date" value={form.billing_period_end} onChange={set('billing_period_end')} error={err('billing_period_end')} />
      </div>
      <SelectInput label="Repeats" value={form.recurrence_rule} onChange={set('recurrence_rule')}
        help="When a repeating bill is paid, the next one is created automatically.">
        <option value="">Does not repeat</option>
        <option value="monthly">Monthly</option>
        <option value="quarterly">Quarterly</option>
        <option value="yearly">Yearly</option>
      </SelectInput>
      <TextInput label="Notes (optional)" value={form.notes} onChange={set('notes')} maxLength={255} />
      <Actions onCancel={onCancel} submitting={submitting} />
    </form>
  )
}

export function PayBillForm({ bill, accounts, timezone, onSubmitAction, onSaved, onCancel }) {
  const active = accounts.filter((a) => a.is_active)
  const { form, errors, setErrors, set } = useFormState({ account_id: active[0]?.id || '', paid_date: todayISO(timezone), amount: bill.amount })
  const validate = () => {
    const e = {}
    if (!form.account_id) e.account_id = 'Choose the account you paid from'
    const a = validateAmount(form.amount)
    if (a) e.amount = a
    return e
  }
  const { onSubmit, submitting, error, fieldErrors } = useFormSubmit(() => onSubmitAction(form), validate, setErrors, onSaved)
  const err = (k) => errors[k] || fieldErrors[k]
  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      <FormError message={error} />
      <p className="text-sm text-slate-600">This records <strong>one</strong> expense transaction linked to the bill, so it is never counted twice.</p>
      <SelectInput label="Paid from" value={form.account_id} onChange={set('account_id')} error={err('account_id')}>
        <option value="">Select…</option>
        {active.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
      </SelectInput>
      <div className="grid gap-4 sm:grid-cols-2">
        <TextInput label="Amount paid" inputMode="decimal" value={form.amount} onChange={set('amount')} error={err('amount')} />
        <TextInput label="Payment date" type="date" value={form.paid_date} onChange={set('paid_date')} />
      </div>
      <Actions onCancel={onCancel} submitting={submitting} label="Mark as paid" />
    </form>
  )
}

export function GoalForm({ initial, onSubmitAction, onSaved, onCancel }) {
  const { form, errors, setErrors, set } = useFormState({
    title: initial?.title || '', target_amount: initial?.target_amount || '', target_date: initial?.target_date || '',
  })
  const validate = () => {
    const e = {}
    if (!form.title.trim()) e.title = 'Title is required'
    const a = validateAmount(form.target_amount)
    if (a) e.target_amount = a
    return e
  }
  const { onSubmit, submitting, error, fieldErrors } = useFormSubmit(
    () => onSubmitAction({ ...form, target_date: form.target_date || null }), validate, setErrors, onSaved)
  const err = (k) => errors[k] || fieldErrors[k]
  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      <FormError message={error} />
      <TextInput label="Goal" placeholder="e.g. Emergency fund" value={form.title} onChange={set('title')} error={err('title')} maxLength={120} />
      <div className="grid gap-4 sm:grid-cols-2">
        <TextInput label="Target amount" inputMode="decimal" value={form.target_amount} onChange={set('target_amount')} error={err('target_amount')} />
        <TextInput label="Target date (optional)" type="date" value={form.target_date} onChange={set('target_date')} error={err('target_date')} />
      </div>
      <Actions onCancel={onCancel} submitting={submitting} />
    </form>
  )
}

export function ContributionForm({ accounts, timezone, onSubmitAction, onSaved, onCancel }) {
  const active = accounts.filter((a) => a.is_active)
  const { form, errors, setErrors, set } = useFormState({
    amount: '', contribution_date: todayISO(timezone), note: '', move: false, from_account_id: '', to_account_id: '',
  })
  const validate = () => {
    const e = {}
    const a = validateAmount(form.amount)
    if (a) e.amount = a
    if (form.move) {
      if (!form.from_account_id) e.from_account_id = 'Choose the source account'
      if (!form.to_account_id) e.to_account_id = 'Choose the savings account'
      else if (form.to_account_id === form.from_account_id) e.to_account_id = 'Choose a different account'
    }
    return e
  }
  const { onSubmit, submitting, error, fieldErrors } = useFormSubmit(() => onSubmitAction({
    amount: form.amount, contribution_date: form.contribution_date, note: form.note || null,
    from_account_id: form.move ? form.from_account_id : null, to_account_id: form.move ? form.to_account_id : null,
  }), validate, setErrors, onSaved)
  const err = (k) => errors[k] || fieldErrors[k]
  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      <FormError message={error} />
      <div className="grid gap-4 sm:grid-cols-2">
        <TextInput label="Amount" inputMode="decimal" value={form.amount} onChange={set('amount')} error={err('amount')} />
        <TextInput label="Date" type="date" value={form.contribution_date} onChange={set('contribution_date')} />
      </div>
      <TextInput label="Note (optional)" value={form.note} onChange={set('note')} maxLength={255} />
      <label className="flex items-start gap-2 text-sm text-slate-700">
        <input type="checkbox" className="mt-0.5 h-4 w-4 rounded border-slate-300" checked={form.move} onChange={set('move')} />
        <span>Also record moving this money between my accounts (as a transfer — not an expense)</span>
      </label>
      {form.move && (
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectInput label="From" value={form.from_account_id} onChange={set('from_account_id')} error={err('from_account_id')}>
            <option value="">Select…</option>
            {active.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </SelectInput>
          <SelectInput label="To" value={form.to_account_id} onChange={set('to_account_id')} error={err('to_account_id')}>
            <option value="">Select…</option>
            {active.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </SelectInput>
        </div>
      )}
      <Actions onCancel={onCancel} submitting={submitting} label="Add contribution" />
    </form>
  )
}
