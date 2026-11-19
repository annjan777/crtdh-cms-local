import { resolve, usePageData } from '../api/data.jsx'

/**
 * Same return shape as the old fetch hook ({ data, loading, error }), but synchronous: the data is
 * already in the pre-built page, so there is never a loading state and pages render complete HTML.
 */
export function useApi(fetcher, _deps = [], initialValue = null) {
  const data = usePageData()
  const value = resolve(data, fetcher())
  return { data: value === undefined ? initialValue : value, loading: false, error: null }
}
