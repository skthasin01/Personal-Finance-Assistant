/**
 * Axios client.
 *
 * Token strategy (see backend routers/auth.py):
 *  - The short-lived access token lives ONLY in this module's memory (never
 *    localStorage), so injected scripts cannot read it from storage.
 *  - The refresh token is an HttpOnly cookie the browser sends automatically to
 *    /api/v1/auth/*. JavaScript cannot read it.
 *  - On a 401, one shared refresh request is made; queued requests retry after it.
 */
import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || '/api/v1'

const api = axios.create({
  baseURL,
  withCredentials: true,
  timeout: 45000,
  headers: { 'X-Requested-With': 'XMLHttpRequest' },
})

let accessToken = null
let onSessionExpired = () => {}
let refreshPromise = null

export function setAccessToken(token) {
  accessToken = token
}
export function getAccessToken() {
  return accessToken
}
export function setSessionExpiredHandler(fn) {
  onSessionExpired = fn
}

/** Ask the backend for a new access token using the HttpOnly refresh cookie. */
export function refreshSession() {
  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${baseURL}/auth/refresh`, null, {
        withCredentials: true,
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      })
      .then((res) => {
        setAccessToken(res.data.access_token)
        return res.data
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    const status = error.response?.status
    const isAuthCall = original?.url?.includes('/auth/')
    if (status === 401 && original && !original._retried && !isAuthCall) {
      original._retried = true
      try {
        await refreshSession()
        original.headers.Authorization = `Bearer ${accessToken}`
        return api(original)
      } catch {
        setAccessToken(null)
        onSessionExpired()
      }
    }
    return Promise.reject(error)
  },
)

/** Turn any API error into { message, fieldErrors, status, code } for display. */
export function parseError(error) {
  if (!error?.response) {
    return { message: 'Cannot reach the server. Check your connection and try again.', fieldErrors: {}, status: 0 }
  }
  const body = error.response.data?.error || {}
  const fieldErrors = {}
  if (Array.isArray(body.details)) {
    for (const d of body.details) {
      if (d.field) fieldErrors[d.field.split('.').pop()] = d.message.replace(/^Value error, /, '')
    }
  }
  let message = body.message || 'Something went wrong. Please try again.'
  if (message === 'Invalid request data' && Array.isArray(body.details) && body.details.length) {
    const first = body.details[0]
    message = first.field ? 'Please fix the highlighted fields.' : first.message.replace(/^Value error, /, '')
  }
  return {
    message,
    fieldErrors,
    status: error.response.status,
    code: body.details?.code || body.code,
  }
}

export default api
