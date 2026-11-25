import { useLayoutEffect } from 'react'
import { Link, Links, Meta, Outlet, Scripts, ScrollRestoration, isRouteErrorResponse, useLoaderData, useLocation, useNavigationType, useRouteError } from 'react-router'
import SiteLayout from '../src/site/components/Layout.jsx'
import { LinkProvider } from '../src/site/link.jsx'
import '../src/site/styles/index.css'

export async function loader() {
  const { loadLayout } = await import('./snapshot.server.js')
  return loadLayout()
}

export const links = () => [
  { rel: 'icon', href: '/favicon.ico', sizes: '48x48' },
  { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/favicon-32x32.png' },
  { rel: 'apple-touch-icon', href: '/apple-touch-icon.png' },
]

export function Layout({ children }) {
  return (
    <html lang="en-IN">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#0b3550" />
        <Meta />
        <Links />
      </head>
      <body>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  )
}

export default function App() {
  const data = useLoaderData()
  const { pathname, hash } = useLocation()
  const navType = useNavigationType()
  // A new page opens at the top. The site scrolls smoothly (html { scroll-behavior: smooth }), and on phones
  // the closing menu interrupted that smooth scroll, so the new page opened where the old one was.
  // Jump instantly instead; Back/Forward (POP) and #anchors are left to ScrollRestoration.
  useLayoutEffect(() => {
    if (navType !== 'POP' && !hash) window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
  }, [pathname, hash, navType])
  return (
    <LinkProvider component={Link}>
      <SiteLayout data={data} currentPath={pathname}>
        <Outlet />
      </SiteLayout>
    </LinkProvider>
  )
}

export function ErrorBoundary() {
  const error = useRouteError()
  const status = isRouteErrorResponse(error) ? error.status : 500
  return (
    <main id="main" className="wrap section">
      <h1>{status === 404 ? 'Page not found' : 'This page could not be shown'}</h1>
      <p className="lead">
        <a href="/">Go to the CRTDH home page</a>
      </p>
    </main>
  )
}
