import { useLoaderData } from 'react-router'
import Page from '../../src/site/pages/Innovations.jsx'
import { pageMeta } from '../seo.js'

export async function loader() {
  const { loadPage } = await import('../snapshot.server.js')
  return loadPage('innovations')
}

export const meta = (args) => pageMeta('innovations', args)

export default function Route() {
  return <Page data={useLoaderData()} />
}
