/** Budgets, bills, savings goals, notifications and AI assistant endpoints. */
import api from './api'

// Budgets
export const listBudgets = (params = {}) => api.get('/budgets', { params }).then((r) => r.data)
export const createBudget = (payload) => api.post('/budgets', payload).then((r) => r.data)
export const updateBudget = (id, payload) => api.patch(`/budgets/${id}`, payload).then((r) => r.data)
export const deleteBudget = (id) => api.delete(`/budgets/${id}`).then((r) => r.data)

// Bills
export const listBills = (params = {}) => api.get('/bills', { params }).then((r) => r.data)
export const createBill = (payload) => api.post('/bills', payload).then((r) => r.data)
export const updateBill = (id, payload) => api.patch(`/bills/${id}`, payload).then((r) => r.data)
export const deleteBill = (id) => api.delete(`/bills/${id}`).then((r) => r.data)
export const payBill = (id, payload) => api.post(`/bills/${id}/pay`, payload).then((r) => r.data)

// Savings goals
export const listGoals = () => api.get('/savings-goals').then((r) => r.data)
export const getGoal = (id) => api.get(`/savings-goals/${id}`).then((r) => r.data)
export const createGoal = (payload) => api.post('/savings-goals', payload).then((r) => r.data)
export const updateGoal = (id, payload) => api.patch(`/savings-goals/${id}`, payload).then((r) => r.data)
export const deleteGoal = (id) => api.delete(`/savings-goals/${id}`).then((r) => r.data)
export const addContribution = (id, payload) =>
  api.post(`/savings-goals/${id}/contributions`, payload).then((r) => r.data)
export const deleteContribution = (goalId, cid) =>
  api.delete(`/savings-goals/${goalId}/contributions/${cid}`).then((r) => r.data)

// Notifications
export const listNotifications = (params = {}) => api.get('/notifications', { params }).then((r) => r.data)
export const markNotification = (id, is_read) => api.patch(`/notifications/${id}`, { is_read }).then((r) => r.data)
export const markAllNotificationsRead = () => api.post('/notifications/mark-all-read').then((r) => r.data)

// AI assistant
export const getAIStatus = () => api.get('/ai/status').then((r) => r.data)
export const listConversations = () => api.get('/ai/conversations').then((r) => r.data)
export const getConversation = (id) => api.get(`/ai/conversations/${id}`).then((r) => r.data)
export const createConversation = (title) => api.post('/ai/conversations', { title }).then((r) => r.data)
export const deleteConversation = (id) => api.delete(`/ai/conversations/${id}`).then((r) => r.data)
export const sendMessage = (id, content) =>
  api.post(`/ai/conversations/${id}/messages`, { content }).then((r) => r.data)
