import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { setSessionExpiredHandler } from '../services/api'
import * as authService from '../services/authService'

const AuthContext = createContext(null)

/**
 * App-wide auth state. On first load we try a silent refresh using the HttpOnly
 * cookie, so a page reload keeps the user signed in without storing tokens.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [initializing, setInitializing] = useState(true)

  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null))
    authService
      .restoreSession()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setInitializing(false))
  }, [])

  const login = useCallback(async (email, password) => {
    const u = await authService.login(email, password)
    setUser(u)
    return u
  }, [])

  const register = useCallback(async (name, email, password) => {
    const u = await authService.register(name, email, password)
    setUser(u)
    return u
  }, [])

  const loginDemo = useCallback(async () => {
    const u = await authService.demoLogin()
    setUser(u)
    return u
  }, [])

  const logout = useCallback(async () => {
    try {
      await authService.logout()
    } finally {
      setUser(null)
    }
  }, [])

  const updateProfile = useCallback(async (payload) => {
    const u = await authService.updateMe(payload)
    setUser(u)
    return u
  }, [])

  const value = useMemo(
    () => ({ user, initializing, login, loginDemo, register, logout, updateProfile, setUser,
      currency: user?.currency_code || 'BDT', timezone: user?.timezone || 'Asia/Dhaka' }),
    [user, initializing, login, loginDemo, register, logout, updateProfile],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
