import api from './api'

export const listAccounts = () => api.get('/accounts').then((r) => r.data)
export const createAccount = (payload) => api.post('/accounts', payload).then((r) => r.data)
export const updateAccount = (id, payload) => api.patch(`/accounts/${id}`, payload).then((r) => r.data)
export const deleteAccount = (id) => api.delete(`/accounts/${id}`).then((r) => r.data)

export const listCategories = (params = {}) => api.get('/categories', { params }).then((r) => r.data)
export const createCategory = (payload) => api.post('/categories', payload).then((r) => r.data)
export const updateCategory = (id, payload) => api.patch(`/categories/${id}`, payload).then((r) => r.data)
export const deleteCategory = (id) => api.delete(`/categories/${id}`).then((r) => r.data)
