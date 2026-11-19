import Page from '../../src/site/pages/NotFound.jsx'
import { pageMeta } from '../seo.js'

// No loader: the designed 404 renders from the root (layout) data only, so it also
// works as 404.html for any unknown path on the static host.
export const meta = (args) => pageMeta('notfound', args)

export default function Route() {
  return <Page data={{ singletons: {}, collections: {}, media: {} }} />
}
