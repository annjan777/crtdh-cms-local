import { useLoaderData } from 'react-router'
import Page from '../../src/site/pages/Team.jsx'
import { pageMeta } from '../seo.js'

export async function loader() {
  const { loadPage } = await import('../snapshot.server.js')
  return loadPage('team')
}

export const meta = (args) => pageMeta('team', args)

export default function Route() {
  return <Page data={useLoaderData()} />
}
