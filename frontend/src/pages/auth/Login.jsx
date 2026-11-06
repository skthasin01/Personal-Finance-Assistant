import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import Icon from '../../components/common/Icon'
import { FormError } from '../../components/common/States'
import { TextInput } from '../../components/common/ui'
import { useAuth } from '../../context/AuthContext'
import { parseError } from '../../services/api'
import { getDemoStatus } from '../../services/authService'
import AuthShell from './AuthShell'

export default function Login() {
  const { login, loginDemo } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ email: '', password: '' })
  const [errors, setErrors] = useState({})
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(null) // null | 'login' | 'demo'
  const [demo, setDemo] = useState(null) // {enabled, ttl_hours}

  useEffect(() => {
    getDemoStatus().then(setDemo).catch(() => setDemo(null))
  }, [])

  const validate = () => {
    const e = {}
    if (!/^\S+@\S+\.\S+$/.test(form.email)) e.email = 'Enter a valid email address'
    if (!form.password) e.password = 'Password is required'
    setErrors(e)
    return !Object.keys(e).length
  }

  const onSubmit = async (ev) => {
    ev.preventDefault()
    setError(null)
    if (!validate()) return
    setBusy('login')
    try {
      await login(form.email, form.password)
      navigate(location.state?.from || '/', { replace: true })
    } catch (e) {
      setError(parseError(e).message)
    } finally {
      setBusy(null)
    }
  }

  const onDemo = async () => {
    setError(null)
    setBusy('demo')
    try {
      await loginDemo()
      navigate('/', { replace: true })
    } catch (e) {
      setError(parseError(e).message)
    } finally {
      setBusy(null)
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Log in to see your budgets, bills and savings."
      footer={<>New here? <Link to="/register" className="font-medium text-brand-700 hover:underline">Create an account</Link></>}
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <FormError message={error} />
        <TextInput label="Email" type="email" autoComplete="email" value={form.email} error={errors.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <TextInput label="Password" type="password" autoComplete="current-password" value={form.password}
          error={errors.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <button type="submit" className="btn-primary w-full" disabled={!!busy}>{busy === 'login' ? 'Logging in…' : 'Log in'}</button>
      </form>

      {demo?.enabled && (
        <div className="mt-6">
          <div className="relative mb-4 text-center text-xs uppercase tracking-wide text-slate-400">
            <span className="relative z-10 bg-white px-2">or</span>
            <span className="absolute inset-x-0 top-1/2 border-t border-slate-200" aria-hidden="true" />
          </div>
          <button type="button" className="btn-secondary w-full" onClick={onDemo} disabled={!!busy}>
            <Icon name="sparkles" className="h-4 w-4 text-brand-700" />
            {busy === 'demo' ? 'Preparing your demo…' : 'Try the demo account'}
          </button>
          <p className="mt-2 text-center text-xs text-slate-500">
            Opens a private workspace with sample data labelled [Demo]. It is deleted after {demo.ttl_hours} hours.
          </p>
        </div>
      )}
    </AuthShell>
  )
}
