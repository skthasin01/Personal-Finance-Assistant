import api, { refreshSession, setAccessToken } from './api'

export async function login(email, password) {
  const { data } = await api.post('/auth/login', { email, password })
  setAccessToken(data.access_token)
  return data.user
}

export async function register(full_name, email, password) {
  const { data } = await api.post('/auth/register', { full_name, email, password })
  setAccessToken(data.access_token)
  return data.user
}

/** Whether the backend offers one-click demo workspaces (DEMO_MODE). */
export const getDemoStatus = () => api.get('/auth/demo').then((r) => r.data)

/** Create a fresh private demo workspace with sample data and sign in. */
export async function demoLogin() {
  const { data } = await api.post('/auth/demo')
  setAccessToken(data.access_token)
  return data.user
}

export async function restoreSession() {
  const data = await refreshSession()
  return data.user
}

export async function logout() {
  try {
    await api.post('/auth/logout')
  } finally {
    setAccessToken(null)
  }
}

export const getMe = () => api.get('/users/me').then((r) => r.data)
export const updateMe = (payload) => api.patch('/users/me', payload).then((r) => r.data)
export const deleteMe = (password) => api.delete('/users/me', { data: { password } }).then((r) => r.data)
