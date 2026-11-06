import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { SectionCard } from '../components/cards/Cards'
import Modal from '../components/common/Modal'
import { FormError } from '../components/common/States'
import { PageHeader, SelectInput, TextInput } from '../components/common/ui'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { parseError } from '../services/api'
import { deleteMe } from '../services/authService'

const TIMEZONES = ['Asia/Dhaka', 'Asia/Kolkata', 'Asia/Dubai', 'Asia/Singapore', 'Europe/London', 'America/New_York', 'UTC']
const CURRENCIES = [['BDT', 'Bangladeshi Taka (৳)'], ['USD', 'US Dollar ($)'], ['EUR', 'Euro (€)'], ['GBP', 'Pound (£)'], ['INR', 'Indian Rupee (₹)']]

export default function Settings() {
  const { user, updateProfile, setUser } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [profile, setProfile] = useState({ full_name: user.full_name, currency_code: user.currency_code, timezone: user.timezone })
  const [prefs, setPrefs] = useState({
    notify_bills: user.notify_bills, notify_budgets: user.notify_budgets, notify_goals: user.notify_goals,
    budget_warning_threshold: user.budget_warning_threshold, bill_reminder_days: user.bill_reminder_days,
  })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [password, setPassword] = useState('')
  const [deleteError, setDeleteError] = useState(null)

  const save = async (section, payload) => {
    setSaving(section)
    setErrors({})
    try {
      await updateProfile(payload)
      toast('Settings saved')
    } catch (e) {
      const p = parseError(e)
      setErrors({ ...p.fieldErrors, _form: p.message })
    } finally {
      setSaving(null)
    }
  }

  const removeAccount = async () => {
    setDeleteError(null)
    try {
      await deleteMe(password)
      setUser(null)
      navigate('/login')
    } catch (e) {
      setDeleteError(parseError(e).message)
    }
  }

  const tzOptions = TIMEZONES.includes(user.timezone) ? TIMEZONES : [user.timezone, ...TIMEZONES]

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader title="Settings" description="Profile, preferences, privacy and your data." />
      <FormError message={errors._form} />

      <SectionCard title="Profile">
        <form className="space-y-4" onSubmit={(e) => {
          e.preventDefault()
          if (profile.full_name.trim().length < 2) return setErrors({ full_name: 'Enter at least 2 characters' })
          save('profile', profile)
        }} noValidate>
          <TextInput label="Full name" value={profile.full_name} error={errors.full_name}
            onChange={(e) => setProfile({ ...profile, full_name: e.target.value })} />
          <TextInput label="Email" value={user.email} disabled help="Email cannot be changed." />
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectInput label="Display currency" value={profile.currency_code} error={errors.currency_code}
              onChange={(e) => setProfile({ ...profile, currency_code: e.target.value })}
              help="Changes display only; amounts are not converted.">
              {CURRENCIES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </SelectInput>
            <SelectInput label="Timezone" value={profile.timezone} error={errors.timezone}
              onChange={(e) => setProfile({ ...profile, timezone: e.target.value })} help="Used for 'today', months and reminders.">
              {tzOptions.map((t) => <option key={t} value={t}>{t}</option>)}
            </SelectInput>
          </div>
          <button className="btn-primary" disabled={saving === 'profile'}>{saving === 'profile' ? 'Saving…' : 'Save profile'}</button>
        </form>
      </SectionCard>

      <SectionCard title="Notifications">
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); save('prefs', { ...prefs,
          budget_warning_threshold: Number(prefs.budget_warning_threshold), bill_reminder_days: Number(prefs.bill_reminder_days) }) }}>
          {[['notify_bills', 'Upcoming and overdue bills'], ['notify_budgets', 'Budget warnings and overspending'], ['notify_goals', 'Savings goal milestones']].map(([k, l]) => (
            <label key={k} className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" className="h-4 w-4 rounded border-slate-300" checked={prefs[k]} onChange={(e) => setPrefs({ ...prefs, [k]: e.target.checked })} />
              {l}
            </label>
          ))}
          <div className="grid gap-4 sm:grid-cols-2">
            <TextInput label="Budget warning threshold (%)" type="number" min={1} max={100} value={prefs.budget_warning_threshold}
              error={errors.budget_warning_threshold} onChange={(e) => setPrefs({ ...prefs, budget_warning_threshold: e.target.value })} />
            <TextInput label="Remind me about bills (days before)" type="number" min={0} max={30} value={prefs.bill_reminder_days}
              error={errors.bill_reminder_days} onChange={(e) => setPrefs({ ...prefs, bill_reminder_days: e.target.value })} />
          </div>
          <button className="btn-primary" disabled={saving === 'prefs'}>{saving === 'prefs' ? 'Saving…' : 'Save preferences'}</button>
        </form>
      </SectionCard>

      <SectionCard title="AI & privacy">
        <div className="space-y-3 text-sm text-slate-600">
          <p>
            When an external AI provider is configured, the assistant sends a <strong>minimised summary</strong> of your
            records (totals, category amounts, budgets, bills, goals) to answer your question. Your name, email, password,
            tokens and transaction descriptions are never sent. The AI cannot move money or change records.
          </p>
          <label className="flex items-center gap-2 text-slate-800">
            <input type="checkbox" className="h-4 w-4 rounded border-slate-300" checked={user.ai_consent}
              onChange={(e) => save('ai', { ai_consent: e.target.checked })} />
            Allow the AI assistant to process my financial summary
          </label>
          {user.ai_consent_at && <p className="text-xs text-slate-400">Consent given {new Date(user.ai_consent_at).toLocaleString()}</p>}
          <p className="text-xs">You can delete individual AI conversations from the AI Assistant page at any time.</p>
        </div>
      </SectionCard>

      {user.is_demo ? (
        <SectionCard title="Demo workspace">
          <p className="text-sm text-slate-600">This temporary demo workspace and all its data are deleted automatically within 24 hours. Log out to leave it now.</p>
        </SectionCard>
      ) : (
        <SectionCard title="Delete account">
          <p className="text-sm text-slate-600">Permanently delete your account and all financial data (accounts, transactions, budgets, bills, goals, AI conversations). This cannot be undone.</p>
          <button className="btn-danger mt-3" onClick={() => setDeleteOpen(true)}>Delete my account</button>
        </SectionCard>
      )}

      <Modal open={deleteOpen} onClose={() => setDeleteOpen(false)} title="Delete account permanently?" size="sm"
        footer={<>
          <button className="btn-secondary" onClick={() => setDeleteOpen(false)}>Cancel</button>
          <button className="btn-danger" onClick={removeAccount} disabled={!password}>Delete everything</button>
        </>}>
        <div className="space-y-3">
          <FormError message={deleteError} />
          <p className="text-sm text-slate-600">Enter your password to confirm.</p>
          <TextInput label="Password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
      </Modal>
    </div>
  )
}
