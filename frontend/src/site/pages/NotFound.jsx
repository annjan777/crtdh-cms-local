import { PageDataProvider } from '../api/data.jsx'
import { Link } from '../router.jsx'

function NotFoundView() {
  return (
    <div className="section text-center">
      <div className="container">
        <span className="eyebrow">404</span>
        <h1>Page not found</h1>
        <p>The page you're looking for doesn't exist or may have moved.</p>
        <Link className="btn btn--primary" to="/">
          Back to home
        </Link>
      </div>
    </div>
  )
}

/** Page component `({ data }) => JSX`: `data` is this page's snapshot slice (route loader or CMS preview). */
export default function NotFound({ data }) {
  return (
    <PageDataProvider data={data}>
      <NotFoundView />
    </PageDataProvider>
  )
}
