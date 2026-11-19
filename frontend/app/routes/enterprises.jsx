import { useLoaderData } from 'react-router'
import Page from '../../src/site/pages/Enterprises.jsx'
import { pageMeta } from '../seo.js'

export async function loader() {
  const { loadPage } = await import('../snapshot.server.js')
  return loadPage('enterprises')
}

export const meta = (args) => pageMeta('enterprises', args)

export default function Route() {
  return <Page data={useLoaderData()} />
}
