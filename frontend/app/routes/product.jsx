import { useLoaderData } from 'react-router'
import Page from '../../src/site/pages/Product.jsx'
import { pageMeta } from '../seo.js'

export async function loader() {
  const { loadPage } = await import('../snapshot.server.js')
  return loadPage('product')
}

export const meta = (args) => pageMeta('product', args)

export default function Route() {
  return <Page data={useLoaderData()} />
}
