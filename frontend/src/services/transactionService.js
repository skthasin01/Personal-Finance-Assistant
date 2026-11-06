import api from './api'

const clean = (params) => Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null))

export const listTransactions = (params = {}) => api.get('/transactions', { params: clean(params) }).then((r) => r.data)
export const createTransaction = (payload) => api.post('/transactions', payload).then((r) => r.data)
export const createTransfer = (payload) => api.post('/transactions/transfers', payload).then((r) => r.data)
export const updateTransaction = (id, payload) => api.patch(`/transactions/${id}`, payload).then((r) => r.data)
export const deleteTransaction = (id) => api.delete(`/transactions/${id}`).then((r) => r.data)
