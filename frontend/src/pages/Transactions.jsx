import { useEffect, useState } from 'react'
import Icon from '../components/common/Icon'
import Modal, { ConfirmDialog } from '../components/common/Modal'
import { DataState } from '../components/common/States'
import { Badge, PageHeader } from '../components/common/ui'
import TransactionForm from '../components/forms/TransactionForm'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useApi } from '../hooks/useApi'
import { parseError } from '../services/api'
import { listAccounts, listCategories } from '../services/accountService'
import { deleteTransaction, listTransactions } from '../services/transactionService'
import { formatMoney } from '../utils/currency'
import { formatDate } from '../utils/date'

const TYPE_BADGE = { income: ['green', 'Income'], expense: ['slate', 'Expense'], transfer: ['blue', 'Transfer'], refund: ['violet', 'Refund'] }
const EMPTY_FILTERS = { search: '', type: '', account_id: '', category_id: '', start_date: '', end_date: '', sort: 'date_desc' }

export default function Transactions() {
  const { currency, timezone } = useAuth()
  const toast = useToast()
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [modal, setModal] = useState(null) // null | {item?}
  const [confirm, setConfirm] = useState(null)
  const [busy, setBusy] = useState(false)

  // Debounce search typing
  useEffect(() => {
    const t = setTimeout(() => { setFilters((f) => ({ ...f, search })); setPage(1) }, 350)
    return () => clearTimeout(t)
  }, [search])

  const refs = useApi(async () => {
    const [accounts, categories] = await Promise.all([listAccounts(), listCategories({ include_inactive: true })])
    return { accounts, categories }
  }, [])
  const txs = useApi(() => listTransactions({ ...filters, page, page_size: 20 }), [filters, page])

  const setFilter = (k) => (e) => { setFilters((f) => ({ ...f, [k]: e.target.value })); setPage(1) }
  const hasFilters = Object.entries(filters).some(([k, v]) => v && v !== EMPTY_FILTERS[k])

  const doDelete = async () => {
    setBusy(true)
    try {
      await deleteTransaction(confirm.id)
      toast('Transaction deleted')
      setConfirm(null)
      txs.reload()
    } catch (e) {
      toast(parseError(e).message, 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Transactions" description="Income, expenses, transfers between your accounts, and refunds."
        actions={<button className="btn-primary" onClick={() => setModal({})} disabled={!refs.data}><Icon name="plus" className="h-4 w-4" />Add transaction</button>} />

      <div className="card p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <label className="lg:col-span-2">
            <span className="sr-only">Search descriptions</span>
            <input className="input" placeholder="Search descriptions…" value={search} onChange={(e) => setSearch(e.target.value)} />
          </label>
          <label><span className="sr-only">Type</span>
            <select className="input" value={filters.type} onChange={setFilter('type')}>
              <option value="">All types</option>
              {Object.entries(TYPE_BADGE).map(([v, [, l]]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label><span className="sr-only">Account</span>
            <select className="input" value={filters.account_id} onChange={setFilter('account_id')}>
              <option value="">All accounts</option>
              {refs.data?.accounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </label>
          <label><span className="sr-only">Category</span>
            <select className="input" value={filters.category_id} onChange={setFilter('category_id')}>
              <option value="">All categories</option>
              {refs.data?.categories.map((c) => <option key={c.id} value={c.id}>{c.name} ({c.type})</option>)}
            </select>
          </label>
          <label><span className="sr-only">Sort</span>
            <select className="input" value={filters.sort} onChange={setFilter('sort')}>
              <option value="date_desc">Newest first</option>
              <option value="date_asc">Oldest first</option>
              <option value="amount_desc">Largest amount</option>
              <option value="amount_asc">Smallest amount</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-500">From
            <input type="date" className="input" value={filters.start_date} onChange={setFilter('start_date')} />
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-500">To
            <input type="date" className="input" value={filters.end_date} onChange={setFilter('end_date')} />
          </label>
          {hasFilters && (
            <button className="btn-ghost justify-self-start" onClick={() => { setFilters(EMPTY_FILTERS); setSearch(''); setPage(1) }}>Clear filters</button>
          )}
        </div>
      </div>

      <div className="card overflow-hidden">
        <DataState loading={txs.loading} error={txs.error} onRetry={txs.reload} empty={!txs.data?.items.length}
          emptyProps={{ icon: 'list', title: hasFilters ? 'No transactions match your filters' : 'No transactions yet',
            description: hasFilters ? 'Try clearing some filters.' : 'Record your first income or expense to get started.' }}>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="table-th">Date</th>
                  <th className="table-th">Details</th>
                  <th className="table-th hidden md:table-cell">Account</th>
                  <th className="table-th text-right">Amount</th>
                  <th className="table-th"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {txs.data?.items.map((t) => {
                  const [color, label] = TYPE_BADGE[t.transaction_type]
                  const positive = ['income', 'refund'].includes(t.transaction_type) || t.direction === 'in'
                  const detail = t.transaction_type === 'transfer'
                    ? `${t.direction === 'out' ? 'To' : 'From'} ${t.counterpart_account_name}` : t.category_name
                  return (
                    <tr key={t.id} className="hover:bg-slate-50">
                      <td className="table-td whitespace-nowrap">{formatDate(t.transaction_date)}</td>
                      <td className="table-td">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <Badge color={color}>{label}</Badge>
                          {t.is_bill_payment && <Badge color="amber">Bill</Badge>}
                          <span className="font-medium text-slate-800">{detail}</span>
                        </div>
                        {t.description && <div className="mt-0.5 max-w-xs truncate text-xs text-slate-500">{t.description}</div>}
                        {Number(t.refunded_amount) > 0 && <div className="text-xs text-violet-700">Refunded {formatMoney(t.refunded_amount, currency)}</div>}
                        <div className="text-xs text-slate-500 md:hidden">{t.account_name}</div>
                      </td>
                      <td className="table-td hidden md:table-cell">{t.account_name}</td>
                      <td className={`table-td whitespace-nowrap text-right font-medium tabular-nums ${t.transaction_type === 'transfer' ? 'text-slate-500' : positive ? 'text-emerald-700' : 'text-slate-900'}`}>
                        {positive ? '+' : '−'}{formatMoney(t.amount, currency)}
                      </td>
                      <td className="table-td whitespace-nowrap text-right">
                        <button className="btn-ghost" onClick={() => setModal({ item: t })} aria-label="Edit transaction"><Icon name="edit" className="h-4 w-4" /></button>
                        <button className="btn-ghost" onClick={() => setConfirm(t)} aria-label="Delete transaction"><Icon name="trash" className="h-4 w-4" /></button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-sm text-slate-600">
            <span>{txs.data?.total} transaction{txs.data?.total === 1 ? '' : 's'}</span>
            <div className="flex items-center gap-2">
              <button className="btn-secondary px-2" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} aria-label="Previous page"><Icon name="chevronLeft" className="h-4 w-4" /></button>
              <span>Page {txs.data?.page} of {Math.max(1, txs.data?.pages || 1)}</span>
              <button className="btn-secondary px-2" disabled={page >= (txs.data?.pages || 1)} onClick={() => setPage((p) => p + 1)} aria-label="Next page"><Icon name="chevronRight" className="h-4 w-4" /></button>
            </div>
          </div>
        </DataState>
      </div>

      <Modal open={!!modal} onClose={() => setModal(null)} title={modal?.item ? 'Edit transaction' : 'Add transaction'}>
        {modal && refs.data && (
          <TransactionForm accounts={refs.data.accounts} categories={refs.data.categories} initial={modal.item}
            timezone={timezone} currency={currency} onCancel={() => setModal(null)}
            onSaved={() => { setModal(null); txs.reload(); toast('Transaction saved') }} />
        )}
      </Modal>
      <ConfirmDialog open={!!confirm} onClose={() => setConfirm(null)} onConfirm={doDelete} busy={busy}
        title="Delete transaction?"
        message={confirm?.transaction_type === 'transfer'
          ? 'Both sides of this transfer will be deleted and account balances updated.'
          : confirm?.is_bill_payment ? 'This is a bill payment. The bill will be marked unpaid again.'
          : 'This permanently removes the transaction and updates your balances and reports.'} />
    </div>
  )
}
