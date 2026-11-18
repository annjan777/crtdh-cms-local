import { useLoaderData } from 'react-router'
import Page from '../../src/site/pages/Facilities.jsx'
import { pageMeta } from '../seo.js'

export async function loader() {
  const { loadPage } = await import('../snapshot.server.js')
  return loadPage('facilities')
}

export const meta = (args) => pageMeta('facilities', args)

export default function Route() {
  return <Page data={useLoaderData()} />
}
