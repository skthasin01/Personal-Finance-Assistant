import { useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import Icon from '../components/common/Icon'
import { DataState } from '../components/common/States'
import { PageHeader } from '../components/common/ui'
import { useAuth } from '../context/AuthContext'
import { useApi } from '../hooks/useApi'
import { listNotifications, markAllNotificationsRead, markNotification } from '../services/planningService'
import { formatDateTime } from '../utils/date'

const TYPE_ICON = { bill_due: 'receipt', bill_overdue: 'alert', budget_warning: 'pie', budget_exceeded: 'alert', goal_milestone: 'target' }
const LINK = { bill: '/bills', budget: '/budgets', savings_goal: '/savings' }

export default function Notifications() {
  const { timezone } = useAuth()
  const { refreshUnread } = useOutletContext() || {}
  const [unreadOnly, setUnreadOnly] = useState(false)
  const list = useApi(() => listNotifications({ unread_only: unreadOnly, page_size: 100 }), [unreadOnly])

  const toggle = async (n) => {
    await markNotification(n.id, !n.is_read)
    list.reload()
    refreshUnread?.()
  }
  const allRead = async () => {
    await markAllNotificationsRead()
    list.reload()
    refreshUnread?.()
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Notifications" description="Bill reminders, budget alerts and savings milestones."
        actions={<>
          <button className="btn-secondary" onClick={() => setUnreadOnly((v) => !v)} aria-pressed={unreadOnly}>{unreadOnly ? 'Show all' : 'Unread only'}</button>
          <button className="btn-secondary" onClick={allRead} disabled={!list.data?.unread_count}>Mark all read</button>
        </>} />
      <div className="card">
        <DataState loading={list.loading} error={list.error} onRetry={list.reload} empty={!list.data?.items.length}
          emptyProps={{ icon: 'bell', title: unreadOnly ? 'You are all caught up' : 'No notifications yet',
            description: 'You will be notified about upcoming and overdue bills, budget thresholds and goal milestones.' }}>
          <ul className="divide-y divide-slate-100">
            {list.data?.items.map((n) => (
              <li key={n.id} className={`flex gap-3 px-4 py-3 ${n.is_read ? '' : 'bg-brand-50/40'}`}>
                <Icon name={TYPE_ICON[n.notification_type] || 'bell'} className={`mt-0.5 h-5 w-5 shrink-0 ${n.notification_type.includes('overdue') || n.notification_type.includes('exceeded') ? 'text-red-600' : 'text-slate-500'}`} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`text-sm ${n.is_read ? 'text-slate-700' : 'font-semibold text-slate-900'}`}>{n.title}</span>
                    {!n.is_read && <span className="h-2 w-2 rounded-full bg-brand-600" aria-label="Unread" />}
                  </div>
                  <p className="text-sm text-slate-600">{n.message}</p>
                  <div className="mt-1 flex gap-3 text-xs text-slate-400">
                    <span>{formatDateTime(n.created_at, timezone)}</span>
                    {LINK[n.related_record_type] && <Link to={LINK[n.related_record_type]} className="font-medium text-brand-700 hover:underline">View</Link>}
                  </div>
                </div>
                <button className="btn-ghost self-start text-xs" onClick={() => toggle(n)}>{n.is_read ? 'Mark unread' : 'Mark read'}</button>
              </li>
            ))}
          </ul>
        </DataState>
      </div>
    </div>
  )
}
