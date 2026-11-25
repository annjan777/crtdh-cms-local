import { useLoaderData } from 'react-router'
import Page from '../../src/site/pages/ResearchTranslation.jsx'
import { pageMeta } from '../seo.js'

export async function loader() {
  const { loadPage } = await import('../snapshot.server.js')
  return loadPage('research-translation')
}

export const meta = (args) => pageMeta('research-translation', args)

export default function Route() {
  return <Page data={useLoaderData()} />
}
