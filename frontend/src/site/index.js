// Shared public-site package. The public app (React Router, prerendered) and the
// admin preview (via a Vite alias) render the same components from the same
// snapshot-shaped data: { singletons, collections, media }.
//
//   import { pages, Layout, LinkProvider, PAGE_NEEDS } from '<alias>/src/site'
//   import '<alias>/src/site/styles/index.css'
//
// Components take props only; none of them import the router.
import Home from './pages/Home.jsx'
import About from './pages/About.jsx'
import Team from './pages/Team.jsx'
import Innovations from './pages/Innovations.jsx'
import Facilities from './pages/Facilities.jsx'
import Services from './pages/Services.jsx'
import Product from './pages/Product.jsx'
import Enterprises from './pages/Enterprises.jsx'
import SocialImpact from './pages/SocialImpact.jsx'
import Covid19 from './pages/Covid19.jsx'
import Media from './pages/Media.jsx'
import Contact from './pages/Contact.jsx'
import NotFound from './pages/NotFound.jsx'

/** Registry page id → page component `({ data }) => JSX`. */
export const pages = {
  home: Home,
  about: About,
  team: Team,
  innovations: Innovations,
  facilities: Facilities,
  services: Services,
  product: Product,
  enterprises: Enterprises,
  'social-impact': SocialImpact,
  'covid-19': Covid19,
  media: Media,
  contact: Contact,
}

export { NotFound }
export { default as Layout, groupNav } from './components/Layout.jsx'
export { LinkProvider } from './link.jsx'
export { MediaProvider } from './media.jsx'
export { PAGES, PAGE_PATHS, PAGE_NEEDS, LAYOUT_NEEDS, REQUIRED, selectData } from './registry.js'
export { SEO } from './seo.js'

/** Path of the CSS entry, for bundlers that need it explicitly. */
export const CSS_ENTRY = './styles/index.css'
