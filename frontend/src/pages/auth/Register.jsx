import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FormError } from '../../components/common/States'
import { TextInput } from '../../components/common/ui'
import { useAuth } from '../../context/AuthContext'
import { parseError } from '../../services/api'
import AuthShell from './AuthShell'

export function validateRegistration(form) {
  const e = {}
  if (form.full_name.trim().length < 2) e.full_name = 'Enter your name (at least 2 characters)'
  if (!/^\S+@\S+\.\S+$/.test(form.email)) e.email = 'Enter a valid email address'
  if (form.password.length < 8) e.password = 'Use at least 8 characters'
  else if (!/[A-Za-z]/.test(form.password) || !/\d/.test(form.password))
    e.password = 'Include at least one letter and one number'
  if (form.confirm !== form.password) e.confirm = 'Passwords do not match'
  return e
}

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ full_name: '', email: '', password: '', confirm: '' })
  const [errors, setErrors] = useState({})
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const onSubmit = async (ev) => {
    ev.preventDefault()
    setError(null)
    const e = validateRegistration(form)
    setErrors(e)
    if (Object.keys(e).length) return
    setBusy(true)
    try {
      await register(form.full_name.trim(), form.email, form.password)
      navigate('/', { replace: true })
    } catch (err) {
      const parsed = parseError(err)
      setError(parsed.message)
      setErrors(parsed.fieldErrors)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Your private workspace for budgets, bills and savings goals."
      footer={<>Already have an account? <Link to="/login" className="font-medium text-brand-700 hover:underline">Log in</Link></>}
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <FormError message={error} />
        <TextInput label="Full name" autoComplete="name" value={form.full_name} error={errors.full_name} onChange={set('full_name')} />
        <TextInput label="Email" type="email" autoComplete="email" value={form.email} error={errors.email} onChange={set('email')} />
        <TextInput label="Password" type="password" autoComplete="new-password" value={form.password}
          error={errors.password} help="At least 8 characters with a letter and a number" onChange={set('password')} />
        <TextInput label="Confirm password" type="password" autoComplete="new-password" value={form.confirm}
          error={errors.confirm} onChange={set('confirm')} />
        <button type="submit" className="btn-primary w-full" disabled={busy}>{busy ? 'Creating account…' : 'Create account'}</button>
      </form>
    </AuthShell>
  )
}
