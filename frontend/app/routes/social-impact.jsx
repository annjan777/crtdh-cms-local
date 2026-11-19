import { useLoaderData } from 'react-router'
import Page from '../../src/site/pages/SocialImpact.jsx'
import { pageMeta } from '../seo.js'

export async function loader() {
  const { loadPage } = await import('../snapshot.server.js')
  return loadPage('social-impact')
}

export const meta = (args) => pageMeta('social-impact', args)

export default function Route() {
  return <Page data={useLoaderData()} />
}
