import { useCallback, useEffect, useRef, useState } from 'react'
import { parseError } from '../services/api'

/**
 * Load data with loading / error state.
 *   const { data, loading, error, reload } = useApi(() => listAccounts(), [])
 */
export function useApi(fetcher, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetcherRef.current()
      setData(result)
      return result
    } catch (e) {
      setError(parseError(e).message)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { data, loading, error, reload, setData }
}

/** Wrap a mutation with submitting state and parsed errors for forms. */
export function useSubmit(action) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})

  const submit = useCallback(
    async (...args) => {
      setSubmitting(true)
      setError(null)
      setFieldErrors({})
      try {
        return await action(...args)
      } catch (e) {
        const parsed = parseError(e)
        setError(parsed.message)
        setFieldErrors(parsed.fieldErrors)
        throw parsed
      } finally {
        setSubmitting(false)
      }
    },
    [action],
  )
  return { submit, submitting, error, fieldErrors, setFieldErrors, setError }
}
