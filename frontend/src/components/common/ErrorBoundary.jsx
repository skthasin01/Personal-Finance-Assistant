import { Component } from 'react'

/** Catches render errors so users see a recoverable message instead of a blank page. */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error) {
    // Log the message only; never log financial data or tokens.
    console.error('UI error:', error?.message)
  }

  render() {
    if (!this.state.hasError) return this.props.children
    return (
      <div role="alert" className="flex min-h-full flex-col items-center justify-center gap-3 p-8 text-center">
        <h1 className="text-lg font-semibold text-slate-900">Something went wrong</h1>
        <p className="max-w-sm text-sm text-slate-600">The page hit an unexpected error. Your data is safe. Reload to continue.</p>
        <button type="button" className="btn-primary" onClick={() => window.location.reload()}>Reload</button>
      </div>
    )
  }
}
