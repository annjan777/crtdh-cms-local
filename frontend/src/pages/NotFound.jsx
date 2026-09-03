import { Link } from 'react-router-dom'

export default function NotFound() {
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
