/**
 * Money formatting. The API sends money as decimal STRINGS ("1250.50"). We only
 * convert to Number for display/chart scaling; no money math happens here —
 * all authoritative totals come from the backend.
 */
const SYMBOLS = { BDT: '৳', USD: '$', EUR: '€', GBP: '£', INR: '₹' }

export function formatMoney(value, currency = 'BDT', { compact = false, sign = false } = {}) {
  if (value === null || value === undefined || value === '') return '—'
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  const symbol = SYMBOLS[currency] ?? `${currency} `
  const abs = Math.abs(n)
  const body = compact && abs >= 100000
    ? new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 }).format(abs)
    : new Intl.NumberFormat(currency === 'BDT' || currency === 'INR' ? 'en-IN' : 'en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(abs)
  const prefix = n < 0 ? '−' : sign && n > 0 ? '+' : ''
  return `${prefix}${symbol}${body}`
}

export function formatPercent(value, { sign = false } = {}) {
  if (value === null || value === undefined) return 'n/a'
  const n = Number(value)
  return `${sign && n > 0 ? '+' : ''}${n.toFixed(1)}%`
}

export const toNumber = (v) => (v === null || v === undefined ? 0 : Number(v))

/** Validate a user-entered money string: positive, max 2 decimals. */
export function validateAmount(value, { allowZero = false } = {}) {
  const s = String(value ?? '').trim()
  if (!s) return 'Amount is required'
  if (!/^\d{1,12}(\.\d{1,2})?$/.test(s)) return 'Enter a number with up to 2 decimal places'
  if (!allowZero && Number(s) <= 0) return 'Amount must be greater than 0'
  return null
}
