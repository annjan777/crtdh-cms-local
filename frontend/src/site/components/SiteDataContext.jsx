import { createContext, useContext } from 'react'

// Provides nav-items + site-settings fetched once at the Layout level so
// every page (and the footer/header) can read them without re-fetching.
export const SiteDataContext = createContext({
  navItems: [],
  siteSettings: null,
  navLoading: true,
  settingsLoading: true,
})

export function useSiteData() {
  return useContext(SiteDataContext)
}
