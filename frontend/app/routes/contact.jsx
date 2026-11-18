import { useLoaderData } from 'react-router'
import Page from '../../src/site/pages/Contact.jsx'
import { pageMeta } from '../seo.js'

export async function loader() {
  const { loadPage } = await import('../snapshot.server.js')
  return loadPage('contact')
}

export const meta = (args) => pageMeta('contact', args)

export default function Route() {
  return <Page data={useLoaderData()} />
}
