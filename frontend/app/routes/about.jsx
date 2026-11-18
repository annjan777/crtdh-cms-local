import { useLoaderData } from 'react-router'
import Page from '../../src/site/pages/About.jsx'
import { pageMeta } from '../seo.js'

export async function loader() {
  const { loadPage } = await import('../snapshot.server.js')
  return loadPage('about')
}

export const meta = (args) => pageMeta('about', args)

export default function Route() {
  return <Page data={useLoaderData()} />
}
