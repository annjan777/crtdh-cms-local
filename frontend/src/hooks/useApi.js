import { useEffect, useRef, useState } from 'react'

/**
 * Runs an async fetcher on mount (and whenever `deps` change), tracking
 * loading/error/data state. The fetcher itself is expected to already
 * swallow network errors and resolve to a fallback value (see
 * api/client.js fetchList/fetchOne) — this hook additionally guards
 * against updating state after unmount and against the fetcher throwing.
 *
 * @param {() => Promise<T>} fetcher
 * @param {any[]} deps
 * @param {T} initialValue
 */
export function useApi(fetcher, deps = [], initialValue = null) {
  const [data, setData] = useState(initialValue)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    fetcherRef
      .current()
      .then((result) => {
        if (!cancelled) {
          setData(result)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error('[useApi] fetch failed:', err)
          setError(err)
          setData(initialValue)
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { data, loading, error }
}
