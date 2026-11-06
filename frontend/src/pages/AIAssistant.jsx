import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import Icon from '../components/common/Icon'
import { ConfirmDialog } from '../components/common/Modal'
import { ErrorState, LoadingState, Spinner } from '../components/common/States'
import { PageHeader } from '../components/common/ui'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useApi } from '../hooks/useApi'
import { parseError } from '../services/api'
import {
  createConversation, deleteConversation, getAIStatus, getConversation, listConversations, sendMessage,
} from '../services/planningService'

const SUGGESTIONS = [
  'Where did most of my money go this month?',
  'Am I over budget anywhere?',
  'How do my bills compare with last time?',
  'Am I on track for my savings goals?',
  'Compare my spending with last month',
  'Give me 3 realistic ways to save more',
]

const DISCLAIMER = 'AI-generated, for information and education only — not professional financial, tax, legal or investment advice.'

export default function AIAssistant() {
  const { user, updateProfile } = useAuth()
  const toast = useToast()
  const status = useApi(() => getAIStatus(), [])
  const conversations = useApi(() => listConversations(), [])
  const [activeId, setActiveId] = useState(null)
  const [messages, setMessages] = useState([])
  const [dataUsed, setDataUsed] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [loadingConv, setLoadingConv] = useState(false)
  const [error, setError] = useState(null)
  const [confirm, setConfirm] = useState(null)
  const endRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView?.({ behavior: 'smooth' }) }, [messages, sending])

  const openConversation = async (id) => {
    setActiveId(id)
    setError(null)
    setDataUsed([])
    setLoadingConv(true)
    try {
      setMessages((await getConversation(id)).messages)
    } catch (e) {
      setError(parseError(e).message)
    } finally {
      setLoadingConv(false)
    }
  }

  const ask = async (text) => {
    const content = (text ?? input).trim()
    if (!content || sending) return
    setSending(true)
    setError(null)
    setInput('')
    const tempId = `tmp-${Date.now()}`
    setMessages((m) => [...m, { id: tempId, role: 'user', content }])
    try {
      let id = activeId
      if (!id) {
        id = (await createConversation()).id
        setActiveId(id)
      }
      const reply = await sendMessage(id, content)
      setMessages((m) => [...m.filter((x) => x.id !== tempId), reply.user_message, reply.assistant_message])
      setDataUsed(reply.data_used)
      conversations.reload()
    } catch (e) {
      setMessages((m) => m.filter((x) => x.id !== tempId))
      setInput(content)
      setError(parseError(e).message)
    } finally {
      setSending(false)
    }
  }

  const remove = async () => {
    try {
      await deleteConversation(confirm.id)
      if (confirm.id === activeId) { setActiveId(null); setMessages([]) }
      setConfirm(null)
      conversations.reload()
      toast('Conversation deleted')
    } catch (e) { toast(parseError(e).message, 'error') }
  }

  if (status.loading) return <LoadingState />
  if (status.error) return <ErrorState message={status.error} onRetry={status.reload} />
  const needsConsent = status.data.consent_required && !user.ai_consent

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="AI finance assistant"
        description="Ask about your spending, budgets, bills and goals. Answers use figures calculated from your own records." />

      {needsConsent ? (
        <ConsentCard status={status.data} onAccept={async () => {
          try { await updateProfile({ ai_consent: true }); toast('AI assistant enabled') } catch (e) { toast(parseError(e).message, 'error') }
        }} />
      ) : (
        <div className="grid min-h-[60vh] gap-4 lg:grid-cols-[16rem_1fr]">
          <aside className="card hidden flex-col overflow-hidden lg:flex" aria-label="Conversations">
            <div className="border-b border-slate-100 p-3">
              <button className="btn-secondary w-full" onClick={() => { setActiveId(null); setMessages([]); setDataUsed([]) }}>
                <Icon name="plus" className="h-4 w-4" />New chat
              </button>
            </div>
            <ul className="flex-1 overflow-y-auto p-2">
              {conversations.data?.map((c) => (
                <li key={c.id} className="group flex items-center">
                  <button onClick={() => openConversation(c.id)}
                    className={`flex-1 truncate rounded-md px-2 py-1.5 text-left text-sm ${c.id === activeId ? 'bg-brand-50 text-brand-800' : 'text-slate-600 hover:bg-slate-100'}`}>
                    {c.title}
                  </button>
                  <button className="btn-ghost opacity-60 group-hover:opacity-100" onClick={() => setConfirm(c)} aria-label={`Delete conversation ${c.title}`}>
                    <Icon name="trash" className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
              {!conversations.data?.length && <li className="px-2 py-4 text-center text-xs text-slate-400">No conversations yet</li>}
            </ul>
          </aside>

          <section className="card flex min-h-[60vh] flex-col" aria-label="Chat">
            <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6" aria-live="polite">
              {loadingConv ? <LoadingState /> : messages.length === 0 ? (
                <div className="mx-auto max-w-lg py-8 text-center">
                  <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-700"><Icon name="sparkles" className="h-6 w-6" /></div>
                  <h2 className="font-semibold text-slate-900">What would you like to know?</h2>
                  <p className="mt-1 text-sm text-slate-500">Try one of these:</p>
                  <div className="mt-4 flex flex-wrap justify-center gap-2">
                    {SUGGESTIONS.map((s) => (
                      <button key={s} className="rounded-full border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50" onClick={() => ask(s)}>{s}</button>
                    ))}
                  </div>
                </div>
              ) : messages.map((m) => (
                <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    m.role === 'user' ? 'bg-brand-700 text-white' : 'bg-slate-100 text-slate-800'}`}>
                    <span className="sr-only">{m.role === 'user' ? 'You said: ' : 'Assistant: '}</span>
                    {m.content}
                  </div>
                </div>
              ))}
              {sending && <div className="flex items-center gap-2 text-sm text-slate-500"><Spinner className="h-4 w-4" />Analysing your finances…</div>}
              <div ref={endRef} />
            </div>
            {dataUsed.length > 0 && (
              <details className="border-t border-slate-100 px-4 py-2 text-xs text-slate-500">
                <summary className="cursor-pointer">Data used for the last answer</summary>
                <ul className="mt-1 list-disc pl-5">{dataUsed.map((d) => <li key={d}>{d}</li>)}</ul>
              </details>
            )}
            {error && <div role="alert" className="mx-4 mb-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
            <form className="flex gap-2 border-t border-slate-100 p-3" onSubmit={(e) => { e.preventDefault(); ask() }}>
              <label htmlFor="ask" className="sr-only">Ask a question about your finances</label>
              <input id="ask" className="input" placeholder="Ask about your spending, budgets, bills or goals…" maxLength={2000}
                value={input} onChange={(e) => setInput(e.target.value)} disabled={sending} />
              <button type="submit" className="btn-primary" disabled={sending || !input.trim()} aria-label="Send">
                <Icon name="send" className="h-4 w-4" />
              </button>
            </form>
            <p className="px-4 pb-3 text-[11px] text-slate-400">{DISCLAIMER} The assistant cannot move money or change your records.</p>
          </section>
        </div>
      )}
      <ConfirmDialog open={!!confirm} onClose={() => setConfirm(null)} onConfirm={remove} title="Delete conversation?"
        message="This permanently deletes the conversation and its messages." />
    </div>
  )
}

function ConsentCard({ status, onAccept }) {
  return (
    <div className="card mx-auto max-w-2xl p-6">
      <h2 className="text-lg font-semibold text-slate-900">Allow the AI assistant to read your financial summary?</h2>
      <p className="mt-2 text-sm text-slate-600">
        To answer your questions, a minimised summary of your records is sent to an external AI provider. Here is exactly what is shared:
      </p>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-700">
        {status.data_shared_description.map((d) => <li key={d}>{d}</li>)}
      </ul>
      <p className="mt-3 text-sm text-slate-600">You can turn this off at any time in <Link to="/settings" className="font-medium text-brand-700 hover:underline">Settings</Link>.</p>
      <div className="mt-5 flex gap-2">
        <button className="btn-primary" onClick={onAccept}>I agree, enable the assistant</button>
        <Link to="/" className="btn-secondary">Not now</Link>
      </div>
    </div>
  )
}
