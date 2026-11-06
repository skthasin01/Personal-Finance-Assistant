import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { DataState } from '../components/common/States'
import TransactionForm from '../components/forms/TransactionForm'

vi.mock('../services/transactionService', () => ({
  createTransaction: vi.fn(() => Promise.resolve({})),
  createTransfer: vi.fn(() => Promise.resolve({})),
  updateTransaction: vi.fn(),
  listTransactions: vi.fn(() => Promise.resolve({ items: [] })),
}))
import { createTransaction, createTransfer } from '../services/transactionService'

const accounts = [
  { id: 'a1', name: 'Cash', is_active: true },
  { id: 'a2', name: 'bKash', is_active: true },
]
const categories = [
  { id: 'c1', name: 'Groceries', type: 'expense', is_active: true },
  { id: 'c2', name: 'Salary', type: 'income', is_active: true },
]

describe('DataState', () => {
  it('shows loading, error with retry, empty and content states', async () => {
    const retry = vi.fn()
    const { rerender } = render(<DataState loading>content</DataState>)
    expect(screen.getByRole('status')).toHaveTextContent('Loading')
    rerender(<DataState error="Boom" onRetry={retry}>content</DataState>)
    expect(screen.getByRole('alert')).toHaveTextContent('Boom')
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(retry).toHaveBeenCalled()
    rerender(<DataState empty emptyProps={{ title: 'Nothing here' }}>content</DataState>)
    expect(screen.getByText('Nothing here')).toBeInTheDocument()
    rerender(<DataState>content</DataState>)
    expect(screen.getByText('content')).toBeInTheDocument()
  })
})

describe('TransactionForm', () => {
  const setup = () => {
    const onSaved = vi.fn()
    render(<TransactionForm accounts={accounts} categories={categories} timezone="Asia/Dhaka" currency="BDT"
      onSaved={onSaved} onCancel={() => {}} />)
    return { onSaved }
  }

  it('shows field errors and does not submit invalid data', async () => {
    setup()
    await userEvent.click(screen.getByRole('button', { name: 'Add' }))
    expect(screen.getByText('Amount is required')).toBeInTheDocument()
    expect(screen.getByText('Choose a category')).toBeInTheDocument()
    expect(createTransaction).not.toHaveBeenCalled()
  })

  it('submits a valid expense with only expense categories offered', async () => {
    const { onSaved } = setup()
    const category = screen.getByLabelText('Category')
    expect(category).not.toHaveTextContent('Salary')
    await userEvent.type(screen.getByLabelText('Amount'), '250.50')
    await userEvent.selectOptions(category, 'c1')
    await userEvent.click(screen.getByRole('button', { name: 'Add' }))
    expect(createTransaction).toHaveBeenCalledWith(expect.objectContaining({
      transaction_type: 'expense', amount: '250.50', account_id: 'a1', category_id: 'c1' }))
    expect(onSaved).toHaveBeenCalled()
  })

  it('requires two different accounts for a transfer', async () => {
    setup()
    await userEvent.click(screen.getByRole('button', { name: 'Transfer' }))
    await userEvent.type(screen.getByLabelText('Amount'), '100')
    await userEvent.click(screen.getByRole('button', { name: 'Add' }))
    expect(screen.getByText('Choose the destination account')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('To account'), 'a2')
    await userEvent.click(screen.getByRole('button', { name: 'Add' }))
    expect(createTransfer).toHaveBeenCalledWith(expect.objectContaining({ from_account_id: 'a1', to_account_id: 'a2' }))
  })
})
