import { index, route } from '@react-router/dev/routes'

// One module per page, so each page ships as its own chunk.
export default [
  index('routes/home.jsx'),
  route('about', 'routes/about.jsx'),
  route('team', 'routes/team.jsx'),
  route('innovations', 'routes/innovations.jsx'),
  route('facilities', 'routes/facilities.jsx'),
  route('services', 'routes/services.jsx'),
  route('product', 'routes/product.jsx'),
  route('enterprises', 'routes/enterprises.jsx'),
  route('social-impact', 'routes/social-impact.jsx'),
  route('covid-19', 'routes/covid-19.jsx'),
  route('media', 'routes/media.jsx'),
  route('contact', 'routes/contact.jsx'),
  route('*', 'routes/not-found.jsx'),
]
