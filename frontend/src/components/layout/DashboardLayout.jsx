import { useCallback, useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { listNotifications } from '../../services/planningService'
import Icon from '../common/Icon'
import Navbar from './Navbar'
import Sidebar from './Sidebar'

export default function DashboardLayout() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [unread, setUnread] = useState(0)
  const location = useLocation()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const refreshUnread = useCallback(() => {
    listNotifications({ page_size: 1 }).then((r) => setUnread(r.unread_count)).catch(() => {})
  }, [])

  useEffect(() => {
    refreshUnread()
    setMenuOpen(false)
  }, [location.pathname, refreshUnread])

  return (
    <div className="min-h-full lg:pl-64">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2">
        Skip to content
      </a>
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200 bg-white lg:block">
        <Sidebar unread={unread} />
      </aside>

      {menuOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation menu">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setMenuOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 max-w-[85%] bg-white shadow-xl">
            <button type="button" className="btn-ghost absolute right-2 top-3" onClick={() => setMenuOpen(false)} aria-label="Close menu">
              <Icon name="x" />
            </button>
            <Sidebar onNavigate={() => setMenuOpen(false)} unread={unread} />
          </div>
        </div>
      )}

      <Navbar onMenu={() => setMenuOpen(true)} unread={unread} />
      {user?.is_demo && (
        <div role="note" className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-sm text-amber-900 lg:px-8">
          You are using a temporary <strong>demo workspace</strong> with sample data. Changes are private to you and
          deleted within 24 hours.{' '}
          <button type="button" className="font-medium underline"
            onClick={async () => { await logout(); navigate('/register') }}>Create a real account</button>
        </div>
      )}
      <main id="main" className="mx-auto max-w-7xl px-4 py-6 lg:px-8 lg:py-8">
        <Outlet context={{ refreshUnread }} />
      </main>
    </div>
  )
}
