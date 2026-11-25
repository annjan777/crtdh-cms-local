import { useLoaderData } from 'react-router'
import Page from '../../src/site/pages/Research.jsx'
import { pageMeta } from '../seo.js'

export async function loader() {
  const { loadPage } = await import('../snapshot.server.js')
  return loadPage('research')
}

export const meta = (args) => pageMeta('research', args)

export default function Route() {
  return <Page data={useLoaderData()} />
}
