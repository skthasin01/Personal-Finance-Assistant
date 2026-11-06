import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import Icon from '../common/Icon'

export default function Navbar({ onMenu, unread = 0 }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const initials = (user?.full_name || '?').split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur lg:px-8">
      <button type="button" className="btn-ghost lg:hidden" onClick={onMenu} aria-label="Open navigation menu">
        <Icon name="menu" />
      </button>
      <div className="flex-1" />
      <Link to="/notifications" className="btn-ghost relative" aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}>
        <Icon name="bell" />
        {unread > 0 && <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-red-500" />}
      </Link>
      <div className="hidden items-center gap-2 sm:flex">
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-xs font-semibold text-slate-700">
          {initials}
        </div>
        <span className="max-w-[12rem] truncate text-sm text-slate-700">{user?.full_name}</span>
      </div>
      <button
        type="button"
        className="btn-ghost"
        onClick={async () => {
          await logout()
          navigate('/login')
        }}
        aria-label="Log out"
        title="Log out"
      >
        <Icon name="logout" />
      </button>
    </header>
  )
}
