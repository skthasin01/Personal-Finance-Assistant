import api from './api'

const clean = (params) => Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null))

export const getSummary = (params = {}) => api.get('/analytics/summary', { params: clean(params) }).then((r) => r.data)
export const getTrends = (params = {}) => api.get('/analytics/trends', { params: clean(params) }).then((r) => r.data)
export const getCategories = (params = {}) =>
  api.get('/analytics/categories', { params: clean(params) }).then((r) => r.data)
export const getCashFlow = (params = {}) => api.get('/analytics/cash-flow', { params: clean(params) }).then((r) => r.data)

/** Download the CSV report through the authenticated client, then save it. */
export async function downloadCsv(params = {}) {
  const res = await api.get('/analytics/export.csv', { params: clean(params), responseType: 'blob' })
  const disposition = res.headers['content-disposition'] || ''
  const name = /filename="([^"]+)"/.exec(disposition)?.[1] || 'finance-report.csv'
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export const getInsights = () => api.get('/insights').then((r) => r.data)
export const dismissInsight = (id) => api.patch(`/insights/${id}`, { is_dismissed: true }).then((r) => r.data)
