import { useLoaderData } from 'react-router'
import Page from '../../src/site/pages/Services.jsx'
import { pageMeta } from '../seo.js'

export async function loader() {
  const { loadPage } = await import('../snapshot.server.js')
  return loadPage('services')
}

export const meta = (args) => pageMeta('services', args)

export default function Route() {
  return <Page data={useLoaderData()} />
}
