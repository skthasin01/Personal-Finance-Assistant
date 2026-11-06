import { NavLink } from 'react-router-dom'
import Icon from '../common/Icon'

export const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: 'dashboard', end: true },
  { to: '/accounts', label: 'Accounts', icon: 'wallet' },
  { to: '/transactions', label: 'Transactions', icon: 'list' },
  { to: '/budgets', label: 'Budgets', icon: 'pie' },
  { to: '/bills', label: 'Bills', icon: 'receipt' },
  { to: '/savings', label: 'Savings Goals', icon: 'target' },
  { to: '/analytics', label: 'Analytics', icon: 'chart' },
  { to: '/assistant', label: 'AI Assistant', icon: 'sparkles' },
  { to: '/notifications', label: 'Notifications', icon: 'bell' },
  { to: '/settings', label: 'Settings', icon: 'settings' },
]

export function Brand() {
  return (
    <div className="flex items-center gap-2.5 px-2">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-700 text-lg font-bold text-white">৳</div>
      <div className="leading-tight">
        <div className="text-sm font-semibold text-slate-900">Taka Wise</div>
        <div className="text-xs text-slate-500">Finance assistant</div>
      </div>
    </div>
  )
}

export default function Sidebar({ onNavigate, unread = 0 }) {
  return (
    <nav aria-label="Main navigation" className="flex h-full flex-col gap-6 p-4">
      <Brand />
      <ul className="flex flex-col gap-0.5">
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.end}
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive ? 'bg-brand-50 text-brand-800' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`
              }
            >
              <Icon name={item.icon} className="h-[18px] w-[18px]" />
              <span className="flex-1">{item.label}</span>
              {item.to === '/notifications' && unread > 0 && (
                <span className="rounded-full bg-red-500 px-1.5 text-xs font-semibold text-white" aria-label={`${unread} unread`}>
                  {unread > 99 ? '99+' : unread}
                </span>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
      <p className="mt-auto px-3 text-xs leading-relaxed text-slate-400">
        For personal organisation and education. Not professional financial advice.
      </p>
    </nav>
  )
}
