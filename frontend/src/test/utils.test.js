import { describe, expect, it } from 'vitest'
import { formatMoney, formatPercent, validateAmount } from '../utils/currency'
import { monthBounds, shiftMonth } from '../utils/date'
import { validateRegistration } from '../pages/auth/Register'
import { parseError } from '../services/api'

describe('currency', () => {
  it('formats BDT with lakh grouping and the taka sign', () => {
    expect(formatMoney('125000.5', 'BDT')).toBe('৳1,25,000.50')
    expect(formatMoney('-20', 'BDT')).toBe('−৳20.00')
    expect(formatMoney(null)).toBe('—')
  })
  it('shows n/a for missing percentages', () => {
    expect(formatPercent(null)).toBe('n/a')
    expect(formatPercent('12.5', { sign: true })).toBe('+12.5%')
  })
  it('validates money input', () => {
    expect(validateAmount('')).toMatch(/required/)
    expect(validateAmount('0')).toMatch(/greater than 0/)
    expect(validateAmount('1.234')).toMatch(/2 decimal/)
    expect(validateAmount('-5')).toBeTruthy()
    expect(validateAmount('0', { allowZero: true })).toBeNull()
    expect(validateAmount('1500.50')).toBeNull()
  })
})

describe('dates', () => {
  it('computes month bounds including leap years', () => {
    expect(monthBounds(2028, 2)).toEqual({ start: '2028-02-01', end: '2028-02-29' })
    expect(shiftMonth(2026, 1, -1)).toEqual({ year: 2025, month: 12 })
  })
})

describe('registration validation', () => {
  it('reports field-level errors', () => {
    const e = validateRegistration({ full_name: 'A', email: 'bad', password: 'abcdefgh', confirm: 'x' })
    expect(Object.keys(e).sort()).toEqual(['confirm', 'email', 'full_name', 'password'])
    expect(validateRegistration({ full_name: 'Ana', email: 'a@b.co', password: 'abc12345', confirm: 'abc12345' })).toEqual({})
  })
})

describe('parseError', () => {
  it('maps API validation details to fields', () => {
    const err = { response: { status: 422, data: { error: { message: 'Invalid request data',
      details: [{ field: 'amount', message: 'Value error, must be positive' }] } } } }
    expect(parseError(err).fieldErrors).toEqual({ amount: 'must be positive' })
  })
  it('handles network failures', () => {
    expect(parseError(new Error('x')).message).toMatch(/Cannot reach the server/)
  })
})
